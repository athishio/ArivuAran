import sys
import os
import time
from unittest.mock import patch, AsyncMock, MagicMock

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import bot
import config
import db
from engine.intents import session_manager


def run_coro(coro):
    """Executes a coroutine with mocked awaits synchronously."""
    try:
        while True:
            coro.send(None)
    except StopIteration as e:
        return e.value


def test1():
    print("Test 1: Voice disabled by default...", flush=True)
    chat_id = 998877
    sender_hash = db.hash_sender(str(chat_id))
    db.set_user_language(sender_hash, "ta")

    with patch.object(config, "VOICE_IN_ENABLED", False):
        with patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send:
            session_manager.clear(chat_id)
            session_manager.update(chat_id, language="ta")
            run_coro(bot.handle_message(chat_id, "audio", MagicMock(), chat_id))
            assert mock_send.call_count == 1
            reply_text = mock_send.call_args[0][1]
            assert "புரிந்துகொள்ள முடியவில்லை" in reply_text or "Couldn't understand" in reply_text
    print("PASS: Test 1 passed!", flush=True)


def test2():
    print("Test 2: Voice confidence gate retry...", flush=True)
    chat_id = 998878
    sender_hash = db.hash_sender(str(chat_id))
    db.set_user_language(sender_hash, "ta")

    mock_meta = {
        "text": "short",
        "confidence_passed": False,
        "avg_logprob": -1.5,
        "no_speech_prob": 0.6,
        "duration": 5.0,
        "words": 1
    }

    async def mock_wait(fut, timeout=None):
        return mock_meta

    with patch.object(config, "VOICE_IN_ENABLED", True):
        with patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send, \
             patch("telegram_io.download_voice", new_callable=AsyncMock, return_value="dummy.ogg"), \
             patch("asyncio.wait_for", side_effect=mock_wait):

            session_manager.clear(chat_id)
            session_manager.update(chat_id, language="ta")
            run_coro(bot.handle_message(chat_id, "audio", MagicMock(), chat_id))
            # 1: S_WORKING, 2: S_VOICE_RETRY
            assert mock_send.call_count == 2
            retry_call = mock_send.call_args_list[1][0][1]
            assert "I couldn't hear that clearly" in retry_call
    print("PASS: Test 2 passed!", flush=True)


def test3():
    print("Test 3: Voice confirmation flow scam...", flush=True)
    chat_id = 998879
    sender_hash = db.hash_sender(str(chat_id))
    db.set_user_language(sender_hash, "ta")

    raw_transcript = "போலிஸ் ஸ்டேஷனில் இருந்து பேசுகிறோம் உங்களுக்கு வந்த ஓட்டிப் பே சொல்லுங்கள்"
    mock_meta = {
        "text": raw_transcript,
        "confidence_passed": True,
        "avg_logprob": -0.3,
        "no_speech_prob": 0.05,
        "duration": 8.0,
        "words": 9
    }

    async def mock_wait(fut, timeout=None):
        return mock_meta

    with patch.object(config, "VOICE_IN_ENABLED", True):
        with patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send, \
             patch("telegram_io.download_voice", new_callable=AsyncMock, return_value="dummy.ogg"), \
             patch("asyncio.wait_for", side_effect=mock_wait), \
             patch("tts.synthesize_verdict_voice", new_callable=AsyncMock, return_value=None):

            session_manager.clear(chat_id)
            session_manager.update(chat_id, language="ta")

            # 1. Voice arrives -> sends S_WORKING then S_HEARD with buttons
            run_coro(bot.handle_message(chat_id, "audio", MagicMock(), chat_id))
            assert mock_send.call_count == 2
            heard_args, heard_kwargs = mock_send.call_args_list[1]
            assert "நான் கேட்டது" in heard_args[1]
            assert heard_kwargs.get("buttons")[0]["id"] == "V_CONFIRM"
            assert heard_kwargs.get("buttons")[1]["id"] == "V_RETRY"

            # 2. User confirms with V_CONFIRM -> SCAM detected via voice normaliser
            mock_send.reset_mock()
            run_coro(bot.handle_message(chat_id, "button", "V_CONFIRM", chat_id))
            verdict_text = mock_send.call_args_list[0][0][1]
            assert "மோசடி" in verdict_text or "SCAM" in verdict_text
    print("PASS: Test 3 passed!", flush=True)


def test4():
    print("Test 4: Voice no reassurance rule...", flush=True)
    chat_id = 998880
    sender_hash = db.hash_sender(str(chat_id))
    db.set_user_language(sender_hash, "ta")

    raw_transcript = "வணக்கம் நான் சென்னையில் இருந்து பேசுகிறேன் இன்று மழை பெய்கிறதா"
    mock_meta = {
        "text": raw_transcript,
        "confidence_passed": True,
        "avg_logprob": -0.2,
        "no_speech_prob": 0.01,
        "duration": 6.0,
        "words": 8
    }

    async def mock_wait(fut, timeout=None):
        return mock_meta

    with patch.object(config, "VOICE_IN_ENABLED", True):
        with patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send, \
             patch("telegram_io.download_voice", new_callable=AsyncMock, return_value="dummy.ogg"), \
             patch("asyncio.wait_for", side_effect=mock_wait), \
             patch("tts.synthesize_verdict_voice", new_callable=AsyncMock, return_value=None):

            session_manager.clear(chat_id)
            session_manager.update(chat_id, language="ta")

            # Voice arrives
            run_coro(bot.handle_message(chat_id, "audio", MagicMock(), chat_id))

            # User confirms with V_CONFIRM -> Never show NO_RED_FLAGS reassurance; show S_VOICE_NO_VERDICT
            mock_send.reset_mock()
            run_coro(bot.handle_message(chat_id, "button", "V_CONFIRM", chat_id))
            reply_text = mock_send.call_args[0][1]
            assert "1930" in reply_text
            assert "reliably check" in reply_text or "உண்மையான செய்தியை" in reply_text
    print("PASS: Test 4 passed!", flush=True)


def test5():
    print("Test 5: Voice retry button clears pending...", flush=True)
    chat_id = 998881
    sender_hash = db.hash_sender(str(chat_id))
    db.set_user_language(sender_hash, "ta")

    bot._pending_voice_transcripts[chat_id] = ("test pending", time.time())

    with patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send:
        run_coro(bot.handle_message(chat_id, "button", "V_RETRY", chat_id))
        assert chat_id not in bot._pending_voice_transcripts
        assert mock_send.call_count == 1
        assert "I couldn't hear that clearly" in mock_send.call_args[0][1]
    print("PASS: Test 5 passed!", flush=True)


if __name__ == "__main__":
    test1()
    test2()
    test3()
    test4()
    test5()
    print("\nALL 5 TARGETED VOICE SAFETY TESTS PASSED SUCCESSFULLY!")
