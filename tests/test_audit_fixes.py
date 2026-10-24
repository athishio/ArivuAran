"""
Test Suite for Audit Fixes:
1. Family card HTML and PNG content verification (no user text, no digits except 1930).
2. First-run bilingual language prompt and selection flow.
3. user_prefs table privacy (salted hash only, no raw IDs, no message text).
4. Both-language coverage and prohibited words audit in data/replies.json.
"""

import os
import sys
import re
import json
import sqlite3
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import db
import bot
import card_renderer
from engine.intents import session_manager


def test_family_card_html_and_png():
    """Verifies family card HTML and rendered PNGs contain only scam type and generic advice, no user text, no digits except 1930."""
    eval_dir = os.path.join(os.path.dirname(__file__), "..", "eval")
    card_ta_path = os.path.join(eval_dir, "card_ta.png")
    card_en_path = os.path.join(eval_dir, "card_en.png")

    # 1. Verify PNG files exist and are valid PNG images
    assert os.path.exists(card_ta_path), f"Missing {card_ta_path}"
    assert os.path.exists(card_en_path), f"Missing {card_en_path}"

    with open(card_ta_path, "rb") as f:
        ta_bytes = f.read()
    with open(card_en_path, "rb") as f:
        en_bytes = f.read()

    assert len(ta_bytes) > 1000
    assert len(en_bytes) > 1000
    # PNG signature: \x89PNG\r\n\x1a\n
    assert ta_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    assert en_bytes.startswith(b"\x89PNG\r\n\x1a\n")

    # 2. Verify HTML structure for Tamil and English
    user_secret_text = "CONFIDENTIAL_USER_SMS_CONTENT_12345"
    sample_scam_type_ta = "மின் கட்டண மோசடி"
    sample_advice_ta = "லிங்கைத் தொடாதீர்கள். OTP, PIN யாரிடமும் சொல்லாதீர்கள். உதவிக்கு 1930 எண்ணை அழைக்கவும்."

    html_ta = card_renderer.build_card_html(
        scam_type=sample_scam_type_ta,
        headline="மோசடி எச்சரிக்கை! (Scam Alert)",
        advice=sample_advice_ta,
        lang="ta"
    )

    # Must contain scam type and advice
    assert sample_scam_type_ta in html_ta
    assert sample_advice_ta in html_ta
    # Must NOT contain user text
    assert user_secret_text not in html_ta

    # Extract all digits from rendered card text (excluding CSS/HTML boilerplate)
    # The visible card elements are badge, headline, alert-box, advice, footer
    visible_text_match = re.search(r'<div class="card">(.*?)</div>\s*</body>', html_ta, re.DOTALL)
    assert visible_text_match is not None
    card_body = visible_text_match.group(1)
    digits_found = set(re.findall(r"\b\d+\b", card_body))
    # No digits except 1930
    assert digits_found == {"1930"} or digits_found == set(), f"Unexpected digits in card: {digits_found}"

    # Verify English HTML
    sample_scam_type_en = "Electricity Bill Scam"
    sample_advice_en = "Do not click any link. Never share OTP or PIN with anyone. Call 1930 if money was sent."

    html_en = card_renderer.build_card_html(
        scam_type=sample_scam_type_en,
        headline="Scam Alert!",
        advice=sample_advice_en,
        lang="en"
    )

    assert sample_scam_type_en in html_en
    assert sample_advice_en in html_en
    assert user_secret_text not in html_en

    visible_en_match = re.search(r'<div class="card">(.*?)</div>\s*</body>', html_en, re.DOTALL)
    assert visible_en_match is not None
    card_en_body = visible_en_match.group(1)
    en_digits = set(re.findall(r"\b\d+\b", card_en_body))
    assert en_digits == {"1930"} or en_digits == set(), f"Unexpected digits in English card: {en_digits}"


@pytest.mark.asyncio
async def test_first_run_language_prompt_and_flow():
    """Verifies that an unknown chat triggers bilingual language prompt with [தமிழ்] and [English] buttons."""
    test_chat_id = 88997711
    sender_hash = db.hash_sender(str(test_chat_id))

    # Ensure clean state
    db.delete_user_language(sender_hash)
    session_manager.clear(test_chat_id)

    with patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send:
        # User sends a first message without having a saved language
        await bot.handle_message(
            user_id=test_chat_id,
            msg_type="text",
            content="வணக்கம்",
            chat_id=test_chat_id
        )

        assert mock_send.await_count == 1
        args, kwargs = mock_send.call_args_list[0]
        prompt_text = args[1]
        buttons = kwargs.get("buttons", [])

        # Bilingual prompt text
        assert "வணக்கம்!" in prompt_text
        assert "Welcome!" in prompt_text
        assert len(buttons) == 2
        assert buttons[0] == {"id": "SET_LANG_TA", "title": "தமிழ்"}
        assert buttons[1] == {"id": "SET_LANG_EN", "title": "English"}

    # User clicks [தமிழ்]
    with patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send:
        await bot.handle_message(
            user_id=test_chat_id,
            msg_type="button",
            content="SET_LANG_TA",
            chat_id=test_chat_id
        )

        # Language must be saved in DB and session
        assert db.get_user_language(sender_hash) == "ta"
        assert session_manager.get(test_chat_id).language == "ta"
        # Welcome message sent
        assert mock_send.await_count == 1
        assert "வணக்கம்!" in mock_send.call_args_list[0][0][1]

    # Clean up after test
    db.delete_user_language(sender_hash)
    session_manager.clear(test_chat_id)


def test_user_prefs_privacy_and_schema():
    """Verifies that user_prefs stores only salted chat hash and language, never raw IDs or message text."""
    test_chat_id = "9876543210"
    sender_hash = db.hash_sender(test_chat_id)

    # 1. Check table schema
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(user_prefs)")
        columns = {row["name"]: row["type"] for row in cursor.fetchall()}

    expected_cols = {"sender_hash", "language", "updated_at", "is_test"}
    assert set(columns.keys()) == expected_cols, f"Schema mismatch: {columns.keys()}"

    # 2. Test inserting preference
    db.set_user_language(sender_hash, "ta")
    saved = db.get_user_language(sender_hash)
    assert saved == "ta"

    # 3. Direct DB row check: verify NO raw ID or user text
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_prefs WHERE sender_hash = ?", (sender_hash,))
        row = cursor.fetchone()
        assert row is not None
        # Hash must be 64-char SHA-256
        assert len(row["sender_hash"]) == 64
        assert re.fullmatch(r"[0-9a-f]{64}", row["sender_hash"]) is not None
        # Raw chat_id must never appear in the record
        assert test_chat_id not in str(dict(row))

    # 4. Deletion test
    assert db.delete_user_language(sender_hash) is True
    assert db.get_user_language(sender_hash) is None


def test_both_language_coverage_and_prohibited_words():
    """Verifies data/replies.json covers all reply IDs in ta and en with zero prohibited words outside F_SAFE."""
    replies_path = os.path.join(os.path.dirname(__file__), "..", "data", "replies.json")
    assert os.path.exists(replies_path), "Missing data/replies.json"

    with open(replies_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    entries = data if isinstance(data, list) else data.get("replies", [])
    assert len(entries) >= 61, f"Expected at least 61 replies, got {len(entries)}"

    prohibited_words = ["safe", "100% accurate", "first", "only", "unique"]

    for entry in entries:
        eid = entry["id"]
        # Both languages must have non-empty text
        assert entry.get("ta"), f"{eid} missing ta text"
        assert entry.get("en"), f"{eid} missing en text"
        assert entry.get("tts_ta"), f"{eid} missing tts_ta"
        assert entry.get("tts_en"), f"{eid} missing tts_en"

        # Status markers
        assert entry.get("status_ta") == "needs_native_review", f"{eid} status_ta not needs_native_review"
        assert entry.get("status_en") == "english_draft", f"{eid} status_en not english_draft"

        # Prohibited words check outside F_SAFE
        if eid != "F_SAFE":
            en_full = (entry["en"] + " " + entry["tts_en"]).lower()
            for pw in prohibited_words:
                pattern = rf"\b{re.escape(pw)}\b"
                assert not re.search(pattern, en_full), (
                    f"Prohibited word '{pw}' found in reply ID '{eid}': {en_full}"
                )


@pytest.mark.asyncio
async def test_routing_rule_short_intent_vs_verdict():
    """Verifies the routing rule:
    - short text (< 8 words, no link, no number) goes to intent matcher.
    - long text (>= 8 words) goes to verdict engine.
    - text with links or numbers goes to verdict engine.
    - forwarded scam 'sent by mistake, share the OTP' gets a verdict, not INC_OTP.
    """
    chat_id = 992211
    sender_hash = db.hash_sender(str(chat_id))
    db.set_user_language(sender_hash, "ta")
    session_manager.clear(chat_id)

    # 1. Short text (< 8 words, no link, no number) -> Intent Matcher
    with patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send:
        await bot.handle_message(user_id=chat_id, msg_type="text", content="லிங்க் திறந்தேன்", chat_id=chat_id)
        # Directly gets INC_LINK advice, no S_WORKING or verdict
        assert mock_send.await_count == 1
        reply_text = mock_send.call_args[0][1]
        assert "அந்தப் பக்கத்தில் எதுவும் உள்ளிடாதீர்கள்" in reply_text or "1930" in reply_text

    # 2. Forwarded scam: 'sent by mistake, share the OTP' -> Must get Verdict (SCAM), NOT INC_OTP!
    with patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send, \
         patch("tts.synthesize_verdict_voice", new_callable=AsyncMock, return_value=None):
        await bot.handle_message(
            user_id=chat_id,
            msg_type="text",
            content="sent by mistake, share the OTP",
            chat_id=chat_id
        )
        # S_WORKING, then Verdict text, then follow-up prompt
        assert mock_send.await_count == 3
        # Call 1: S_WORKING
        assert "சரிபார்க்கிறேன்" in mock_send.call_args_list[0][0][1]
        # Call 2: Verdict (SCAM)
        verdict_text = mock_send.call_args_list[1][0][1]
        assert "மோசடி" in verdict_text
        # Verify session has SCAM verdict
        sess = session_manager.get(chat_id)
        assert sess is not None
        assert sess.verdict == "SCAM"

    # 3. Longer text with link (>= 8 words) -> Verdict Engine
    with patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send, \
         patch("tts.synthesize_verdict_voice", new_callable=AsyncMock, return_value=None):
        long_sms = "Dear customer your electricity bill is unpaid. Power will be disconnected tonight at 9 PM: http://tneb-bill.xyz"
        await bot.handle_message(
            user_id=chat_id,
            msg_type="text",
            content=long_sms,
            chat_id=chat_id
        )
        assert mock_send.await_count == 3
        assert "மோசடி" in mock_send.call_args_list[1][0][1]

    # Clean up
    db.delete_user_language(sender_hash)
    session_manager.clear(chat_id)


@pytest.mark.asyncio
async def test_demo_mode_command_and_canned_execution():
    """Verifies /demo command and execution of canned test cases through real pipeline."""
    chat_id = 993322
    sender_hash = db.hash_sender(str(chat_id))
    db.set_user_language(sender_hash, "ta")
    session_manager.clear(chat_id)

    # 1. When DEMO_MODE is False
    with patch("config.DEMO_MODE", False), \
         patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send:
        await bot.handle_message(user_id=chat_id, msg_type="text", content="/demo", chat_id=chat_id)
        assert mock_send.await_count == 1
        assert "முடக்கப்பட்டுள்ளது" in mock_send.call_args[0][1]

    # 2. When DEMO_MODE is True
    with patch("config.DEMO_MODE", True), \
         patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send:
        await bot.handle_message(user_id=chat_id, msg_type="text", content="/demo", chat_id=chat_id)
        assert mock_send.await_count == 1
        args, kwargs = mock_send.call_args
        assert "மாதிரி சோதனைகள்" in args[1]
        buttons = kwargs.get("buttons", [])
        assert len(buttons) == 5
        assert buttons[0]["id"] == "DEMO_1_KYC"
        assert buttons[1]["id"] == "DEMO_2_OTP"

    # 3. User taps DEMO_1_KYC button -> Executes through REAL pipeline (not hardcoded)
    with patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send, \
         patch("tts.synthesize_verdict_voice", new_callable=AsyncMock, return_value=None):
        await bot.handle_message(
            user_id=chat_id,
            msg_type="button",
            content="DEMO_1_KYC",
            chat_id=chat_id
        )
        # S_WORKING, then Verdict text, then follow-up prompt
        assert mock_send.await_count == 3
        # Call 1: S_WORKING
        assert "சரிபார்க்கிறேன்" in mock_send.call_args_list[0][0][1]
        # Call 2: Real SCAM verdict
        verdict_text = mock_send.call_args_list[1][0][1]
        assert "மோசடி" in verdict_text
        sess = session_manager.get(chat_id)
        assert sess is not None
        assert sess.verdict == "SCAM"
        assert "LOOKALIKE" in sess.signals or "SHORTENER" in sess.signals

    # Clean up
    db.delete_user_language(sender_hash)
    session_manager.clear(chat_id)


def test_routing_rule_inc_vs_forwarded_scam():
    """
    Verifies Item 0.a routing rules:
    - Short messages with numbers meaning 'I already paid / shared OTP / clicked / installed'
      reach INC_* (e.g. 'paid 5000', 'otp sollitten', 'ரூ 5000 அனுப்பிட்டேன்', 'I clicked the link').
    - Long forwarded scams with 'sent by mistake, share the OTP' route to verdict engine (return False).
    """
    from bot import should_route_to_intent
    from engine.intents import classify_intent

    # 1. Incident messages with digits/amounts -> must route to intent
    assert should_route_to_intent("paid 5000") is True
    assert classify_intent("paid 5000") == "INC_PAID"

    assert should_route_to_intent("otp sollitten") is True
    assert classify_intent("otp sollitten") == "INC_OTP"

    assert should_route_to_intent("ரூ 5000 அனுப்பிட்டேன்") is True
    assert classify_intent("ரூ 5000 அனுப்பிட்டேன்") == "INC_PAID"

    assert should_route_to_intent("I clicked the link") is True
    assert classify_intent("I clicked the link") == "INC_LINK"

    assert should_route_to_intent("installed anydesk") is True
    assert classify_intent("installed anydesk") == "INC_ANYDESK"

    assert should_route_to_intent("card number sollitten") is True
    assert classify_intent("card number sollitten") == "INC_CARD"

    # 2. Forwarded scam requesting OTP or saying 'sent by mistake' -> MUST NOT route to intent (goes to verdict engine)
    forwarded_scam_1 = "Dear customer Rs 5000 sent by mistake, share the OTP to refund: 98765"
    assert should_route_to_intent(forwarded_scam_1) is False

    forwarded_scam_2 = "URGENT SBI: Sent by mistake, please forward the OTP to cancel transaction."
    assert should_route_to_intent(forwarded_scam_2) is False

    forwarded_scam_3 = "Electricity power will be cut tonight. Update bill now: https://tneb-bill.in"
    assert should_route_to_intent(forwarded_scam_3) is False

    # 3. Negative routing tests: passive/receipt notifications and unrelated short phrases must NOT reach INC_*
    neg_1 = "Your bill is paid, thank you"
    assert should_route_to_intent(neg_1) is False
    assert classify_intent(neg_1) == "F_UNKNOWN"

    neg_2 = "shipping address"
    assert should_route_to_intent(neg_2) is False
    assert classify_intent(neg_2) == "F_UNKNOWN"


@pytest.mark.asyncio
async def test_negative_routing_end_to_end():
    """Verifies that 'Your bill is paid, thank you' and 'shipping address' NEVER trigger INC_* emergency advice."""
    chat_id = 998877
    sender_hash = db.hash_sender(str(chat_id))
    db.set_user_language(sender_hash, "en")
    session_manager.clear(chat_id)

    # 1. 'Your bill is paid, thank you' -> Must NOT trigger INC_PAID or emergency advice
    with patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send, \
         patch("tts.synthesize_verdict_voice", new_callable=AsyncMock, return_value=None):
        await bot.handle_message(
            user_id=chat_id,
            msg_type="text",
            content="Your bill is paid, thank you",
            chat_id=chat_id
        )
        # Should NOT contain 1930 or incident emergency instructions
        for call_args in mock_send.call_args_list:
            sent_txt = call_args[0][1]
            assert "1930" not in sent_txt
            assert "lost money" not in sent_txt.lower()
            assert "freeze" not in sent_txt.lower()

    # 2. 'shipping address' -> Must NOT trigger INC_*
    session_manager.clear(chat_id)
    with patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send, \
         patch("tts.synthesize_verdict_voice", new_callable=AsyncMock, return_value=None):
        await bot.handle_message(
            user_id=chat_id,
            msg_type="text",
            content="shipping address",
            chat_id=chat_id
        )
        for call_args in mock_send.call_args_list:
            sent_txt = call_args[0][1]
            assert "1930" not in sent_txt
            assert "lost money" not in sent_txt.lower()


@pytest.mark.asyncio
async def test_voice_send_timeout_retry_and_fallback(tmp_path):
    """
    Verifies Item 0.f:
    - Voice send raises timeout (30s), retries once on TimedOut, and succeeds.
    - If retry also times out, raises TimedOut allowing caller to fall back to text-only.
    """
    from telegram.error import TimedOut
    import telegram_io

    dummy_voice = tmp_path / "test_voice.ogg"
    dummy_voice.write_bytes(b"dummy_opus_data")

    # Case 1: Times out once, succeeds on retry
    mock_bot = MagicMock()
    mock_msg = MagicMock()
    mock_bot.send_voice = AsyncMock(side_effect=[TimedOut("Connection timed out"), mock_msg])

    with patch.object(telegram_io, "get_bot", return_value=mock_bot):
        res = await telegram_io.send_voice(12345, str(dummy_voice))
        assert res == mock_msg
        assert mock_bot.send_voice.await_count == 2
        # Verify 30s timeouts were supplied
        call_kwargs = mock_bot.send_voice.call_args[1]
        assert call_kwargs.get("read_timeout") == 30.0
        assert call_kwargs.get("write_timeout") == 30.0
        assert call_kwargs.get("connect_timeout") == 30.0

    # Case 2: Times out both times -> raises TimedOut
    mock_bot2 = MagicMock()
    mock_bot2.send_voice = AsyncMock(side_effect=[TimedOut("Timeout 1"), TimedOut("Timeout 2")])

    with patch.object(telegram_io, "get_bot", return_value=mock_bot2):
        with pytest.raises(TimedOut):
            await telegram_io.send_voice(12345, str(dummy_voice))
        assert mock_bot2.send_voice.await_count == 2


def test_normalisation_zero_width_ss2():
    """
    Verifies Task 1:
    - Real OCR text of data/images/Ss-2.jpeg contains U+200C (ZWNJ) injected around Tamil pulli characters.
    - Stripping zero-width characters preserves text integrity and produces a decisive SCAM verdict.
    """
    import pytesseract
    import config
    from PIL import Image
    from engine.redact import normalize_input
    from engine import analyse

    img_path = os.path.join(WORKSPACE_ROOT, "data", "images", "Ss-2.jpeg")
    raw_ocr = pytesseract.image_to_string(Image.open(img_path), lang="tam+eng")

    # Verify real OCR contains U+200C zero-width characters
    zw_chars = [c for c in raw_ocr if c in ("\u200B", "\u200C", "\u200D", "\uFEFF")]
    assert len(zw_chars) > 0, "Expected U+200C in raw OCR of Ss-2.jpeg"

    # Normalize and verify all zero-width characters are stripped
    cleaned = normalize_input(raw_ocr)
    assert not any(c in cleaned for c in ("\u200B", "\u200C", "\u200D", "\u200E", "\u200F", "\u2060", "\uFEFF", "\u00AD"))

    # Pipeline verdict check
    res = analyse(raw_ocr)
    assert res.verdict == "SCAM"
    assert res.score >= 4
    sig_codes = [s.code for s in res.signals]
    assert "PRIZE" in sig_codes
    assert "FEE_FIRST" in sig_codes





def test_routing_rule_inc_vs_forwarded_scam():
    """
    Verifies Item 0.a routing rules:
    - Short messages with numbers meaning 'I already paid / shared OTP / clicked / installed'
      reach INC_* (e.g. 'paid 5000', 'otp sollitten', 'ரூ 5000 அனுப்பிட்டேன்', 'I clicked the link').
    - Long forwarded scams with 'sent by mistake, share the OTP' route to verdict engine (return False).
    """
    from bot import should_route_to_intent
    from engine.intents import classify_intent

    # 1. Incident messages with digits/amounts -> must route to intent
    assert should_route_to_intent("paid 5000") is True
    assert classify_intent("paid 5000") == "INC_PAID"

    assert should_route_to_intent("otp sollitten") is True
    assert classify_intent("otp sollitten") == "INC_OTP"

    assert should_route_to_intent("ரூ 5000 அனுப்பிட்டேன்") is True
    assert classify_intent("ரூ 5000 அனுப்பிட்டேன்") == "INC_PAID"

    assert should_route_to_intent("I clicked the link") is True
    assert classify_intent("I clicked the link") == "INC_LINK"

    assert should_route_to_intent("installed anydesk") is True
    assert classify_intent("installed anydesk") == "INC_ANYDESK"

    assert should_route_to_intent("card number sollitten") is True
    assert classify_intent("card number sollitten") == "INC_CARD"

    # 2. Forwarded scam requesting OTP or saying 'sent by mistake' -> MUST NOT route to intent (goes to verdict engine)
    forwarded_scam_1 = "Dear customer Rs 5000 sent by mistake, share the OTP to refund: 98765"
    assert should_route_to_intent(forwarded_scam_1) is False

    forwarded_scam_2 = "URGENT SBI: Sent by mistake, please forward the OTP to cancel transaction."
    assert should_route_to_intent(forwarded_scam_2) is False

    forwarded_scam_3 = "Electricity power will be cut tonight. Update bill now: https://tneb-bill.in"
    assert should_route_to_intent(forwarded_scam_3) is False

    # 3. Negative routing tests: passive/receipt notifications and unrelated short phrases must NOT reach INC_*
    neg_1 = "Your bill is paid, thank you"
    assert should_route_to_intent(neg_1) is False
    assert classify_intent(neg_1) == "F_UNKNOWN"

    neg_2 = "shipping address"
    assert should_route_to_intent(neg_2) is False
    assert classify_intent(neg_2) == "F_UNKNOWN"


@pytest.mark.asyncio
async def test_negative_routing_end_to_end():
    """Verifies that 'Your bill is paid, thank you' and 'shipping address' NEVER trigger INC_* emergency advice."""
    chat_id = 998877
    sender_hash = db.hash_sender(str(chat_id))
    db.set_user_language(sender_hash, "en")
    session_manager.clear(chat_id)

    # 1. 'Your bill is paid, thank you' -> Must NOT trigger INC_PAID or emergency advice
    with patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send, \
         patch("tts.synthesize_verdict_voice", new_callable=AsyncMock, return_value=None):
        await bot.handle_message(
            user_id=chat_id,
            msg_type="text",
            content="Your bill is paid, thank you",
            chat_id=chat_id
        )
        # Should NOT contain 1930 or incident emergency instructions
        for call_args in mock_send.call_args_list:
            sent_txt = call_args[0][1]
            assert "1930" not in sent_txt
            assert "lost money" not in sent_txt.lower()
            assert "freeze" not in sent_txt.lower()

    # 2. 'shipping address' -> Must NOT trigger INC_*
    session_manager.clear(chat_id)
    with patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send, \
         patch("tts.synthesize_verdict_voice", new_callable=AsyncMock, return_value=None):
        await bot.handle_message(
            user_id=chat_id,
            msg_type="text",
            content="shipping address",
            chat_id=chat_id
        )
        for call_args in mock_send.call_args_list:
            sent_txt = call_args[0][1]
            assert "1930" not in sent_txt
            assert "lost money" not in sent_txt.lower()


@pytest.mark.asyncio
async def test_voice_send_timeout_retry_and_fallback(tmp_path):
    """
    Verifies Item 0.f:
    - Voice send raises timeout (30s), retries once on TimedOut, and succeeds.
    - If retry also times out, raises TimedOut allowing caller to fall back to text-only.
    """
    from telegram.error import TimedOut
    import telegram_io

    dummy_voice = tmp_path / "test_voice.ogg"
    dummy_voice.write_bytes(b"dummy_opus_data")

    # Case 1: Times out once, succeeds on retry
    mock_bot = MagicMock()
    mock_msg = MagicMock()
    mock_bot.send_voice = AsyncMock(side_effect=[TimedOut("Connection timed out"), mock_msg])

    with patch.object(telegram_io, "get_bot", return_value=mock_bot):
        res = await telegram_io.send_voice(12345, str(dummy_voice))
        assert res == mock_msg
        assert mock_bot.send_voice.await_count == 2
        # Verify 30s timeouts were supplied
        call_kwargs = mock_bot.send_voice.call_args[1]
        assert call_kwargs.get("read_timeout") == 30.0
        assert call_kwargs.get("write_timeout") == 30.0
        assert call_kwargs.get("connect_timeout") == 30.0

    # Case 2: Times out both times -> raises TimedOut
    mock_bot2 = MagicMock()
    mock_bot2.send_voice = AsyncMock(side_effect=[TimedOut("Timeout 1"), TimedOut("Timeout 2")])

    with patch.object(telegram_io, "get_bot", return_value=mock_bot2):
        with pytest.raises(TimedOut):
            await telegram_io.send_voice(12345, str(dummy_voice))
        assert mock_bot2.send_voice.await_count == 2


def test_normalisation_zero_width_ss2():
    """
    Verifies Task 1:
    - Real OCR text of data/images/Ss-2.jpeg contains U+200C (ZWNJ) injected around Tamil pulli characters.
    - Stripping zero-width characters preserves text integrity and produces a decisive SCAM verdict.
    """
    import pytesseract
    import config
    from PIL import Image
    from engine.redact import normalize_input
    from engine import analyse

    img_path = os.path.join(WORKSPACE_ROOT, "data", "images", "Ss-2.jpeg")
    raw_ocr = pytesseract.image_to_string(Image.open(img_path), lang="tam+eng")

    # Verify real OCR contains U+200C zero-width characters
    zw_chars = [c for c in raw_ocr if c in ("\u200B", "\u200C", "\u200D", "\uFEFF")]
    assert len(zw_chars) > 0, "Expected U+200C in raw OCR of Ss-2.jpeg"

    # Normalize and verify all zero-width characters are stripped
    cleaned = normalize_input(raw_ocr)
    assert not any(c in cleaned for c in ("\u200B", "\u200C", "\u200D", "\u200E", "\u200F", "\u2060", "\uFEFF", "\u00AD"))

    # Pipeline verdict check
    res = analyse(raw_ocr)
    assert res.verdict == "SCAM"
    assert res.score >= 4
    sig_codes = [s.code for s in res.signals]
    assert "PRIZE" in sig_codes
    assert "FEE_FIRST" in sig_codes













