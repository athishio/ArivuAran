"""
Test Suite for TTS Voice, Script Validation, Formatting, and Follow-Up Flow.
Tests verify:
1. TTS input validation rejects slot names, template IDs, braces, HTML tags, and emojis.
2. Spoken scripts contain no ASCII braces or tags.
3. Each language uses its own voice and cache key (no cross-language reuse).
4. Verdict voice length cap (target 10-15s, hard cap 20s, drops second reason if needed).
5. Follow-up message appears once per verdict in the selected language.
6. Buttons match the language, and for NO_RED_FLAGS 'Why?' is omitted.
"""

import os
import sys
import pytest
from unittest.mock import AsyncMock, patch

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import tts
import bot
from engine.decide import analyse
from engine.intents import session_manager


def test_tts_validation_rejects_slot_names_and_ids():
    """Verifies that validation rejects scripts with slot names, IDs, braces, tags, or emojis."""
    # 1. Unfilled slots / braces
    assert tts.validate_spoken_script("இது மோசடி. காரணங்கள்: 1. {reason1}", reply_id="V_SCAM") is False
    assert tts.validate_spoken_script("Check this {code} now", reply_id="test") is False

    # 2. Internal template IDs
    assert tts.validate_spoken_script("Error R_OTP occurred", reply_id="R_OTP") is False
    assert tts.validate_spoken_script("Refer to V_SCAM", reply_id="V_SCAM") is False
    assert tts.validate_spoken_script("Case INC_OTP logged", reply_id="INC_OTP") is False
    assert tts.validate_spoken_script("Step S_WELCOME done", reply_id="S_WELCOME") is False

    # 3. HTML tags & markdown
    assert tts.validate_spoken_script("⚠️ <b>இது மோசடி</b>", reply_id="V_SCAM") is False
    assert tts.validate_spoken_script("Check **bold** link", reply_id="test") is False

    # 4. Keyword 'reason' and URLs
    assert tts.validate_spoken_script("Primary reason is link shortener", reply_id="test") is False
    assert tts.validate_spoken_script("Visit http://example.com", reply_id="test") is False

    # 5. Clean scripts pass
    clean_ta = "இது மோசடி போல் உள்ளது. லிங்கைத் தொடாதீர்கள். ஓ டி பி, பின் யாரிடமும் சொல்லாதீர்கள்."
    assert tts.validate_spoken_script(clean_ta, reply_id="clean_ta") is True

    clean_en = "This looks like a scam. Do not click any link, and never share your O T P or P I N."
    assert tts.validate_spoken_script(clean_en, reply_id="clean_en") is True


def test_spoken_scripts_contain_no_ascii_braces_or_tags():
    """Verifies generated spoken scripts for all verdicts in ta and en are free of braces and tags."""
    sample_signals = ["SHORTENER", "ASK_SENSITIVE"]

    for verdict in ["SCAM", "SUSPICIOUS", "NO_RED_FLAGS"]:
        for lang in ["ta", "en"]:
            script = tts.build_verdict_spoken_script(verdict, sample_signals, lang=lang)
            # Must not contain braces or HTML tags
            assert "{" not in script
            assert "}" not in script
            assert "<" not in script
            assert ">" not in script
            assert "*" not in script
            # Must pass strict validation
            assert tts.validate_spoken_script(script, reply_id=f"V_{verdict}_{lang}") is True


def test_each_language_uses_its_own_voice_and_cache_key():
    """Verifies that each language has its own distinct voice and SHA-256 cache key."""
    ta_voice = tts.VOICE_CONFIG["ta"]["default"]
    en_voice = tts.VOICE_CONFIG["en"]["default"]
    assert ta_voice == "ta-IN-PallaviNeural"
    assert en_voice == "en-IN-NeerjaNeural"

    script = "This is a sample test script."
    key_ta = tts.get_cache_key("ta", ta_voice, "-10%", script)
    key_en = tts.get_cache_key("en", en_voice, "-10%", script)

    # Different languages produce completely different cache keys
    assert key_ta != key_en
    assert len(key_ta) == 64  # SHA-256 hex digest length
    assert len(key_en) == 64


def test_phonetic_replacements_applied():
    """Verifies acronym and number phonetic replacements in both languages."""
    # Tamil replacements
    ta_in = "உங்கள் OTP மற்றும் PIN சொல்லாதீர்கள். 1930 எண்ணை அழைக்கவும். KYC செய்யவும்."
    ta_out = tts.apply_tts_replacements(ta_in, lang="ta")
    assert "ஓ டி பி" in ta_out
    assert "பின்" in ta_out
    assert "ஒன்று ஒன்பது மூன்று பூஜ்ஜியம்" in ta_out
    assert "கே ஒய் சி" in ta_out

    # English replacements
    en_in = "Do not share OTP or PIN. Call 1930 for cyber crime. Update KYC via UPI."
    en_out = tts.apply_tts_replacements(en_in, lang="en")
    assert "O T P" in en_out
    assert "P I N" in en_out
    assert "one nine three zero" in en_out
    assert "K Y C" in en_out
    assert "U P I" in en_out


def test_followup_message_and_buttons_by_language():
    """Verifies follow-up message text and buttons for all verdicts in ta and en."""
    # 1. SCAM in Tamil: Why? is offered
    msg_ta_scam, btns_ta_scam = bot.build_followup_message("SCAM", lang="ta")
    assert msg_ta_scam == "மேலும் என்ன தெரிந்துகொள்ள வேண்டும்?"
    assert len(btns_ta_scam) == 5
    assert any(b["id"] == "F_WHY" and b["title"] == "ஏன்?" for b in btns_ta_scam)

    # 2. NO_RED_FLAGS in Tamil: Why? is omitted
    msg_ta_noflag, btns_ta_noflag = bot.build_followup_message("NO_RED_FLAGS", lang="ta")
    assert msg_ta_noflag == "மேலும் என்ன தெரிந்துகொள்ள வேண்டும்?"
    assert len(btns_ta_noflag) == 4
    assert not any(b["id"] == "F_WHY" for b in btns_ta_noflag)
    assert any(b["id"] == "F_TODO" and b["title"] == "என்ன செய்வது?" for b in btns_ta_noflag)

    # 3. SCAM in English: Why? is offered
    msg_en_scam, btns_en_scam = bot.build_followup_message("SCAM", lang="en")
    assert msg_en_scam == "What would you like to know next?"
    assert len(btns_en_scam) == 5
    assert any(b["id"] == "F_WHY" and b["title"] == "Why?" for b in btns_en_scam)

    # 4. NO_RED_FLAGS in English: Why? is omitted
    msg_en_noflag, btns_en_noflag = bot.build_followup_message("NO_RED_FLAGS", lang="en")
    assert msg_en_noflag == "What would you like to know next?"
    assert len(btns_en_noflag) == 4
    assert not any(b["id"] == "F_WHY" for b in btns_en_noflag)
    assert any(b["id"] == "F_TODO" and b["title"] == "What should I do?" for b in btns_en_noflag)


@pytest.mark.asyncio
async def test_verdict_voice_length_cap():
    """Verifies that verdict voice clips stay under 20 seconds, dropping second reason if needed."""
    # Tamil SCAM with 2 long reasons (which would exceed 20s if not shortened)
    signals = ["SHORTENER", "KYC_UPDATE"]
    res = await tts.synthesize_verdict_voice("SCAM", signals, lang="ta")
    assert res is not None
    path, dur = res
    assert os.path.exists(path)
    # Hard cap 20 seconds strictly enforced
    assert 3.0 <= dur <= 20.0


@pytest.mark.asyncio
async def test_followup_appears_once_per_verdict_with_language_switch():
    """Verifies language switching via /lang and that follow-up appears in the selected language."""
    chat_id = 771122
    with patch("telegram_io.send_text", new_callable=AsyncMock) as mock_send, \
         patch("tts.synthesize_verdict_voice", new_callable=AsyncMock, return_value=None):

        # Switch to English
        await bot.handle_message(user_id=chat_id, msg_type="text", content="/lang en", chat_id=chat_id)
        assert session_manager.get(chat_id).language == "en"

        # Check a scam message in English mode
        scam_msg = "Your SBI account is blocked. Update KYC at http://bit.ly/sbi-kyc"
        await bot.handle_message(user_id=chat_id, msg_type="text", content=scam_msg, chat_id=chat_id)

        # Call 1: /lang response
        # Call 2: S_WORKING
        # Call 3: English verdict card
        # Call 4: English follow-up message with English buttons
        assert mock_send.await_count == 4
        v_args = mock_send.call_args_list[2][0]
        assert "This looks like a scam." in v_args[1]

        f_args, f_kwargs = mock_send.call_args_list[3]
        assert f_args[1] == "What would you like to know next?"
        btns = f_kwargs["buttons"]
        assert btns[0]["title"] == "Why?"
        assert btns[1]["title"] == "What should I do?"
