import asyncio
import time
from unittest.mock import patch, AsyncMock, MagicMock
import pytest

import bot
import config
from engine.intents import session_manager


def test_voice_disabled_by_default():
    async def _run():
        chat_id = 998877

        with patch.object(config, "VOICE_IN_ENABLED", False), \
             patch("db.get_user_language", return_value="ta"), \
             patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send:

            session_manager.clear(chat_id)
            session_manager.update(chat_id, language="ta")

            await bot.handle_message(
                user_id=chat_id,
                msg_type="audio",
                content=MagicMock(),
                chat_id=chat_id
            )
            assert mock_send.call_count == 1
            reply_text = mock_send.call_args[0][1]
            assert "புரிந்துகொள்ள முடியவில்லை" in reply_text or "Couldn't understand" in reply_text

    asyncio.run(_run())


def test_voice_confidence_gate_retry():
    async def _run():
        chat_id = 998878

        mock_meta = {
            "text": "short",
            "confidence_passed": False,
            "avg_logprob": -1.5,
            "no_speech_prob": 0.6,
            "duration": 5.0,
            "words": 1
        }

        with patch.object(config, "VOICE_IN_ENABLED", True), \
             patch("db.get_user_language", return_value="ta"), \
             patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send, \
             patch("telegram_io.download_voice", new_callable=AsyncMock, return_value="dummy.ogg"), \
             patch("speech.transcribe_with_metadata", return_value=mock_meta):

            session_manager.clear(chat_id)
            session_manager.update(chat_id, language="ta")

            await bot.handle_message(
                user_id=chat_id,
                msg_type="audio",
                content=MagicMock(),
                chat_id=chat_id
            )
            assert mock_send.call_count == 2
            retry_call = mock_send.call_args_list[1][0][1]
            assert "I couldn't hear that clearly" in retry_call

    asyncio.run(_run())


def test_voice_heard_confirmation_flow_scam():
    async def _run():
        chat_id = 998879

        raw_transcript = "போலிஸ் ஸ்டேஷனில் இருந்து பேசுகிறோம் உங்களுக்கு வந்த ஓட்டிப் பே சொல்லுங்க"
        mock_meta = {
            "text": raw_transcript,
            "confidence_passed": True,
            "avg_logprob": -0.3,
            "no_speech_prob": 0.05,
            "duration": 8.0,
            "words": 9
        }

        with patch.object(config, "VOICE_IN_ENABLED", True), \
             patch("db.get_user_language", return_value="ta"), \
             patch("db.log_check"), \
             patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send, \
             patch("telegram_io.download_voice", new_callable=AsyncMock, return_value="dummy.ogg"), \
             patch("speech.transcribe_with_metadata", return_value=mock_meta), \
             patch("tts.synthesize_verdict_voice", new_callable=AsyncMock, return_value=None):

            session_manager.clear(chat_id)
            session_manager.update(chat_id, language="ta")

            # 1. Voice arrives -> sends S_WORKING then S_HEARD with buttons
            await bot.handle_message(
                user_id=chat_id,
                msg_type="audio",
                content=MagicMock(),
                chat_id=chat_id
            )
            assert mock_send.call_count == 2
            heard_args, heard_kwargs = mock_send.call_args_list[1]
            assert "நான் கேட்டது" in heard_args[1]
            assert heard_kwargs.get("buttons")[0]["id"] == "V_CONFIRM"
            assert heard_kwargs.get("buttons")[1]["id"] == "V_RETRY"

            # 2. User confirms with V_CONFIRM -> SCAM detected via voice normaliser
            mock_send.reset_mock()
            await bot.handle_message(
                user_id=chat_id,
                msg_type="button",
                content="V_CONFIRM",
                chat_id=chat_id
            )
            verdict_text = mock_send.call_args_list[0][0][1]
            assert "மோசடி" in verdict_text or "SCAM" in verdict_text

    asyncio.run(_run())


def test_voice_no_reassurance_no_red_flags():
    async def _run():
        chat_id = 998880

        raw_transcript = "வணக்கம் நான் சென்னையில் இருந்து பேசுகிறேன் இன்று மழை பெய்கிறதா"
        mock_meta = {
            "text": raw_transcript,
            "confidence_passed": True,
            "avg_logprob": -0.2,
            "no_speech_prob": 0.01,
            "duration": 6.0,
            "words": 8
        }

        with patch.object(config, "VOICE_IN_ENABLED", True), \
             patch("db.get_user_language", return_value="ta"), \
             patch("db.log_check"), \
             patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send, \
             patch("telegram_io.download_voice", new_callable=AsyncMock, return_value="dummy.ogg"), \
             patch("speech.transcribe_with_metadata", return_value=mock_meta), \
             patch("tts.synthesize_verdict_voice", new_callable=AsyncMock, return_value=None):

            session_manager.clear(chat_id)
            session_manager.update(chat_id, language="ta")

            # Voice arrives
            await bot.handle_message(
                user_id=chat_id,
                msg_type="audio",
                content=MagicMock(),
                chat_id=chat_id
            )

            # User confirms with V_CONFIRM -> Never show NO_RED_FLAGS reassurance; show S_VOICE_NO_VERDICT
            mock_send.reset_mock()
            await bot.handle_message(
                user_id=chat_id,
                msg_type="button",
                content="V_CONFIRM",
                chat_id=chat_id
            )
            reply_text = mock_send.call_args[0][1]
            assert "1930" in reply_text
            assert "reliably check" in reply_text or "உண்மையான செய்தியை" in reply_text

    asyncio.run(_run())


def test_non_blocking_slow_transcriber_and_concurrency():
    async def _run():
        chat_voice = 111001
        chat_text = 222002

        session_manager.clear(chat_voice)
        session_manager.update(chat_voice, language="en")
        session_manager.clear(chat_text)
        session_manager.update(chat_text, language="en")

        def slow_transcribe(*args, **kwargs):
            time.sleep(0.05)
            return {
                "text": "Hello this is a test audio message",
                "confidence_passed": True,
                "avg_logprob": -0.2,
                "no_speech_prob": 0.01,
                "duration": 5.0,
                "words": 7
            }

        with patch.object(config, "VOICE_IN_ENABLED", True), \
             patch("db.get_user_language", return_value="en"), \
             patch("db.log_check"), \
             patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send, \
             patch("telegram_io.download_voice", new_callable=AsyncMock, return_value="dummy.ogg"), \
             patch("speech.transcribe_with_metadata", side_effect=slow_transcribe), \
             patch("tts.synthesize_verdict_voice", new_callable=AsyncMock, return_value=None):

            voice_task = asyncio.create_task(
                bot.handle_message(
                    user_id=chat_voice,
                    msg_type="audio",
                    content=MagicMock(),
                    chat_id=chat_voice
                )
            )

            await asyncio.sleep(0.01)
            await bot.handle_message(
                user_id=chat_text,
                msg_type="text",
                content="Why do you check scams?",
                chat_id=chat_text
            )

            text_calls = [c for c in mock_send.call_args_list if c[0][0] == chat_text]
            assert len(text_calls) >= 1

            await voice_task
            voice_calls = [c for c in mock_send.call_args_list if c[0][0] == chat_voice]
            assert len(voice_calls) == 2

    asyncio.run(_run())
