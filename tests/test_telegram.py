"""
Unit and Integration Test Suite for Telegram Connection Layer (telegram_io.py & bot.py).
Tests verify:
1. Message routing (text, voice, buttons).
2. Action buttons attached after verdict: [ஏன்?] [என்ன செய்வது?] [கற்றுக்கொள்] [குடும்பத்துக்கு அனுப்பு] [நான் ஏற்கனவே...].
3. INC_MENU opens 5 emergency incident cases.
4. Error path: S_WORKING while processing and S_ERROR on exception with zero stack traces or message texts logged.
5. In-memory session expiry after 30 minutes.
6. Privacy guarantee: No message text, transcripts, or credentials reach database or logs.
"""

import os
import sys
import time
import pytest
import sqlite3
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

# Provide dummy tokens for testing environment
os.environ["BOT_TOKEN"] = "123456789:ABCDEF_mock_token_for_tests"
os.environ["SALT"] = "mock_salt_for_tests"

import telegram_io
import bot
import db
from engine.intents import session_manager
from telegram.error import RetryAfter
from telegram import InlineKeyboardMarkup


@pytest.fixture(autouse=True)
def setup_test_user_lang():
    db.init_db()
    for uid in ["12345", "554433", "998877", "771122"]:
        h = db.hash_sender(uid)
        db.set_user_language(h, "ta")


def test_mask_id():
    """Validates privacy masking of user and chat IDs."""
    assert telegram_io.mask_id(123456789) == "***89"
    assert telegram_io.mask_id("9876543210") == "***10"
    assert telegram_io.mask_id("42") == "**"
    assert telegram_io.mask_id(7) == "**"


@pytest.mark.asyncio
async def test_send_text():
    """Verifies send_text calls bot.send_message."""
    mock_bot = AsyncMock()
    telegram_io.set_bot(mock_bot)

    await telegram_io.send_text(chat_id=123456789, text="Hello world")
    mock_bot.send_message.assert_awaited_once_with(chat_id=123456789, text="Hello world", parse_mode="HTML")


@pytest.mark.asyncio
async def test_send_buttons():
    """Verifies send_buttons formats up to 3 buttons, 1 per row, capping title at 20 chars."""
    mock_bot = AsyncMock()
    telegram_io.set_bot(mock_bot)

    buttons = [
        {"id": "btn_1", "title": "First Button Title That Is Long"},
        {"id": "btn_2", "title": "Second Button"},
        {"id": "btn_3", "title": "Third Button"},
        {"id": "btn_4", "title": "Fourth Button Ignored"},
    ]

    await telegram_io.send_buttons(chat_id=123456789, text="Choose an option", buttons=buttons)
    mock_bot.send_message.assert_awaited_once()

    args, kwargs = mock_bot.send_message.call_args
    assert kwargs["chat_id"] == 123456789
    assert kwargs["text"] == "Choose an option"
    markup = kwargs["reply_markup"]
    assert isinstance(markup, InlineKeyboardMarkup)
    assert len(markup.inline_keyboard) == 3
    assert markup.inline_keyboard[0][0].text == "First Button Title T"
    assert markup.inline_keyboard[0][0].callback_data == "btn_1"
    assert markup.inline_keyboard[1][0].text == "Second Button"
    assert markup.inline_keyboard[1][0].callback_data == "btn_2"


@pytest.mark.asyncio
async def test_retry_after_handling():
    """Verifies that telegram_io retries once on RetryAfter."""
    mock_bot = MagicMock()
    mock_bot.send_message = AsyncMock(side_effect=[RetryAfter(0.01), "success_message"])
    telegram_io.set_bot(mock_bot)

    result = await telegram_io.send_text(chat_id=123456789, text="Retry test")
    assert result == "success_message"
    assert mock_bot.send_message.await_count == 2


@pytest.mark.asyncio
async def test_download_voice_and_cleanup():
    """Verifies download_voice creates an .ogg file and caller can clean it up."""
    mock_message = MagicMock()
    mock_message.chat_id = 987654321
    mock_file = AsyncMock()

    async def fake_download(custom_path):
        with open(custom_path, "wb") as f:
            f.write(b"fake_ogg_bytes")

    mock_file.download_to_drive.side_effect = fake_download
    mock_message.voice.get_file = AsyncMock(return_value=mock_file)

    temp_path = await telegram_io.download_voice(mock_message)
    assert os.path.exists(temp_path)
    assert temp_path.endswith(".ogg")

    os.remove(temp_path)
    assert not os.path.exists(temp_path)


@pytest.mark.asyncio
async def test_handle_message_text_greeting():
    """Verifies greeting text triggers the Tamil welcome message (S_WELCOME) with Thirukkural 421."""
    with patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send:
        await bot.handle_message(user_id=12345, msg_type="text", content="Vanakkam")
        assert mock_send.await_count == 1
        args, _ = mock_send.call_args
        assert args[0] == 12345
        assert "வணக்கம்" in args[1]
        assert "அறிவற்றங் காக்கும் கருவி" in args[1]


@pytest.mark.asyncio
async def test_handle_message_text_scam():
    """Verifies scam text triggers S_WORKING first, verdict text, then follow-up with 5 action buttons."""
    scam_text = "Your SBI account is blocked. Update KYC immediately: http://sbi-kyc-verify.xyz"
    with patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send, \
         patch("tts.synthesize_verdict_voice", new_callable=AsyncMock, return_value=None):
        await bot.handle_message(user_id=12345, msg_type="text", content=scam_text)
        assert mock_send.await_count == 3
        # Call 1: S_WORKING
        assert "சரிபார்க்கிறேன்" in mock_send.call_args_list[0][0][1]
        # Call 2: Verdict Reply (HTML, no buttons)
        v_args, v_kwargs = mock_send.call_args_list[1]
        assert "மோசடி" in v_args[1]
        assert "buttons" not in v_kwargs or v_kwargs["buttons"] is None
        # Call 3: Follow-up message with 5 buttons
        f_args, f_kwargs = mock_send.call_args_list[2]
        assert "தெரிந்துகொள்ள" in f_args[1]
        buttons = f_kwargs.get("buttons", [])
        assert len(buttons) == 5
        btn_ids = [b["id"] for b in buttons]
        assert btn_ids == ["F_WHY", "F_TODO", "F_LEARN", "F_SHARE", "INC_MENU"]


@pytest.mark.asyncio
async def test_buttons_inc_menu_and_cases():
    """Verifies that clicking INC_MENU presents the 5 emergency incident buttons and triggers advice."""
    with patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send:
        # Step 1: Click INC_MENU
        await bot.handle_message(user_id=12345, msg_type="button", content="INC_MENU")
        assert mock_send.await_count == 1
        args, kwargs = mock_send.call_args
        buttons = kwargs.get("buttons", [])
        assert len(buttons) == 5
        assert [b["id"] for b in buttons] == ["INC_OTP", "INC_LINK", "INC_ANYDESK", "INC_PAID", "INC_CARD"]

        # Step 2: Click INC_OTP emergency button
        await bot.handle_message(user_id=12345, msg_type="button", content="INC_OTP")
        assert mock_send.await_count == 2
        call2_args, _ = mock_send.call_args_list[1]
        assert "பதற வேண்டாம்" in call2_args[1]
        assert "1930" in call2_args[1]


@pytest.mark.asyncio
async def test_buttons_followup_and_session_expiry():
    """Verifies follow-up buttons consult active session and expire after 30 minutes."""
    chat_id = 998877

    # Evaluate scam to seed session
    with patch("telegram_io.send_text", new_callable=AsyncMock), \
         patch("tts.synthesize_speech", new_callable=AsyncMock, return_value=None):
        await bot.handle_message(
            user_id=chat_id,
            msg_type="text",
            content="Urgent: update KYC now http://fake-sbi.xyz",
            chat_id=chat_id
        )

    # Tap F_WHY button -> should return reasons
    with patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send:
        await bot.handle_message(user_id=chat_id, msg_type="button", content="F_WHY", chat_id=chat_id)
        assert mock_send.await_count == 1
        assert "காரணங்கள் மீண்டும்" in mock_send.call_args[0][1]

    # Fast forward session by 31 minutes (session expires)
    sess = session_manager.get(chat_id)
    assert sess is not None
    sess.updated_at = time.time() - 1801.0

    # Tap F_WHY after expiry -> must ask user to send message first (F_NEED_VERDICT)
    with patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send:
        await bot.handle_message(user_id=chat_id, msg_type="button", content="F_WHY", chat_id=chat_id)
        assert mock_send.await_count == 1
        assert "செய்தியை எனக்கு அனுப்புங்கள்" in mock_send.call_args[0][1]


@pytest.mark.asyncio
async def test_error_path_shows_s_error_and_no_stacktrace():
    """Verifies that on internal exception, S_ERROR is sent and only exception type is logged."""
    with patch("bot.analyse", side_effect=ValueError("Simulated critical error")), \
         patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send, \
         patch.object(bot.logger, "error") as mock_log_error:

        await bot.handle_message(user_id=12345, msg_type="text", content="Check this message")

        # S_WORKING sent first, then S_ERROR on catch
        assert mock_send.await_count == 2
        error_call_text = mock_send.call_args_list[1][0][1]
        assert "மன்னிக்கவும், இப்போது சரிபார்க்க முடியவில்லை" in error_call_text

        # Verify logger recorded ONLY exception type, not exception message or stack trace
        mock_log_error.assert_called()
        logged_str = str(mock_log_error.call_args)
        assert "ValueError" in logged_str
        assert "Simulated critical error" not in logged_str


@pytest.mark.asyncio
async def test_privacy_guarantee_no_text_in_db():
    """Verifies that no user text or phone numbers are stored in database or session memory."""
    db.init_db()
    sensitive_sms = "Dear 9840123456 your SBI account is blocked update KYC: http://sbi-fake.xyz"

    with patch("telegram_io.send_text", new_callable=AsyncMock), \
         patch("tts.synthesize_speech", new_callable=AsyncMock, return_value=None):
        await bot.handle_message(user_id=554433, msg_type="text", content=sensitive_sms, chat_id=554433)

    # 1. Audit SQLite database directly
    conn = sqlite3.connect("arivaran.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(checks)")
    cols = [c[1] for c in cursor.fetchall()]
    assert "text" not in cols
    assert "message" not in cols
    assert "otp" not in cols
    assert "phone" not in cols

    # Verify rows in checks table contain no raw user text
    cursor.execute("SELECT * FROM checks ORDER BY id DESC LIMIT 1")
    row_str = str(cursor.fetchone())
    assert "9840123456" not in row_str
    assert "4492" not in row_str
    assert "fake.xyz" not in row_str
    conn.close()

    # 2. Audit Session Memory
    sess = session_manager.get(554433)
    assert sess is not None
    assert sess.verdict in ("SCAM", "SUSPICIOUS")
    # Verify session has no user text attributes
    assert not hasattr(sess, "text")
    assert not hasattr(sess, "message")


@pytest.mark.asyncio
async def test_commands():
    """Verifies /start, /help, /privacy and /delete commands."""
    with patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send:
        # /start
        await bot.handle_message(user_id=12345, msg_type="text", content="/start")
        start_reply = mock_send.call_args[0][1]
        assert "குறள் 421" in start_reply
        assert "<b>" in start_reply

        # /help lists active commands ONLY
        await bot.handle_message(user_id=12345, msg_type="text", content="/help")
        help_reply = mock_send.call_args[0][1]
        assert "/start" in help_reply
        assert "/help" in help_reply
        assert "/privacy" in help_reply
        assert "/delete" in help_reply
        assert "/demo" not in help_reply
        assert "/learn" not in help_reply

        # /privacy
        await bot.handle_message(user_id=12345, msg_type="text", content="/privacy")
        assert "சேமிப்பதில்லை" in mock_send.call_args[0][1]

        # /delete clears session
        session_manager.update(chat_id=12345, verdict="SCAM")
        assert session_manager.get(12345) is not None
        await bot.handle_message(user_id=12345, msg_type="text", content="/delete")
        assert session_manager.get(12345) is None
        assert "அழிக்கப்பட்டது" in mock_send.call_args[0][1]


@pytest.mark.asyncio
async def test_handle_message_audio_and_file_cleanup():
    """Verifies handle_message for audio transcribes, scores, replies, and deletes temporary file."""
    mock_msg = MagicMock()
    fake_temp_file = "test_voice_sample.ogg"
    with open(fake_temp_file, "wb") as f:
        f.write(b"sample_audio")

    with patch("telegram_io.download_voice", new_callable=AsyncMock, return_value=fake_temp_file) as mock_dl, \
         patch("speech.transcribe", return_value="உங்கள் அக்கவுண்ட் பிளாக் செய்யப்படும் உடனடியாக OTP சொல்லவும்"), \
         patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send, \
         patch("tts.synthesize_verdict_voice", new_callable=AsyncMock, return_value=None):

        await bot.handle_message(user_id=12345, msg_type="audio", content=mock_msg)
        mock_dl.assert_awaited_once_with(mock_msg)
        # S_WORKING + S_HEARD + Verdict text + Follow-up message
        assert mock_send.await_count == 4
        last_args, last_kwargs = mock_send.call_args_list[-1]
        assert "தெரிந்துகொள்ள" in last_args[1]
        assert "buttons" in last_kwargs and len(last_kwargs["buttons"]) == 5
        assert not os.path.exists(fake_temp_file)
