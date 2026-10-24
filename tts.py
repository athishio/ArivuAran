"""
Neural Text-to-Speech (TTS) Engine for ArivuAran.
Supports Tamil (ta-IN-PallaviNeural default / ta-IN-ValluvarNeural optional)
and Indian English (en-IN-NeerjaNeural default / en-IN-PrabhatNeural optional).
Includes script validation, rate control, SHA-256 caching, duration verification,
duration hard-cap shortening, and TTS abbreviation replacements.
"""

import os
import re
import hashlib
import logging
import asyncio
import subprocess
from typing import Optional, Tuple, List
import edge_tts

try:
    import av
    HAS_AV = True
except ImportError:
    HAS_AV = False

logger = logging.getLogger("arivuaran_tts")

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "audio")
DEFAULT_TTS_RATE = os.getenv("TTS_RATE", "-10%")

VOICE_CONFIG = {
    "ta": {
        "default": "ta-IN-PallaviNeural",
        "optional": "ta-IN-ValluvarNeural",
    },
    "en": {
        "default": "en-IN-NeerjaNeural",
        "optional": "en-IN-PrabhatNeural",
    }
}

# Replacement tables for natural speech synthesis
REPLACEMENTS_TA = [
    (r"\bOTP\b", "ஓ டி பி"),
    (r"\bPIN\b", "பின்"),
    (r"\bKYC\b", "கே ஒய் சி"),
    (r"\bUPI\b", "யு பி ஐ"),
    (r"\bSMS\b", "எஸ் எம் எஸ்"),
    (r"\bAPK\b", "ஏ பி கே"),
    (r"\bAnyDesk\b", "எனிடெஸ்க்"),
    (r"\b1930\b", "ஒன்று ஒன்பது மூன்று பூஜ்ஜியம்"),
]

REPLACEMENTS_EN = [
    (r"\b1930\b", "one nine three zero"),
    (r"\bOTP\b", "O T P"),
    (r"\bPIN\b", "P I N"),
    (r"\bUPI\b", "U P I"),
    (r"\bKYC\b", "K Y C"),
    (r"\bSMS\b", "S M S"),
    (r"\bAPK\b", "A P K"),
]

FORBIDDEN_SUBSTRINGS = ["R_", "F_", "INC_", "V_", "T_", "S_"]
FORBIDDEN_CHARACTERS = set("{}<>*`~#")
EMOJI_PATTERN = re.compile(
    r"[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|[\ufe00-\ufe0f]"
)


def apply_tts_replacements(text: str, lang: str = "ta") -> str:
    """Applies domain phonetic replacement tables for natural pronunciation."""
    result = text
    table = REPLACEMENTS_TA if lang == "ta" else REPLACEMENTS_EN
    for pattern, replacement in table:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def validate_spoken_script(script: str, reply_id: str = "unknown") -> bool:
    """
    Validates that a spoken script is strictly voice-safe before synthesis.
    Rejects scripts with braces, HTML tags, template IDs, internal slot names,
    URLs, emojis, or markdown syntax.
    """
    if not script or not script.strip():
        logger.warning(f"Spoken script rejected for reply '{reply_id}': empty script")
        return False

    # Check for forbidden characters: { } < > * ` ~ #
    for ch in script:
        if ch in FORBIDDEN_CHARACTERS:
            logger.warning(f"Spoken script rejected for reply '{reply_id}': contains forbidden character '{ch}'")
            return False

    # Check for internal IDs
    for sub in FORBIDDEN_SUBSTRINGS:
        if sub in script:
            logger.warning(f"Spoken script rejected for reply '{reply_id}': contains internal prefix '{sub}'")
            return False

    # Check for keywords "reason" or "http"
    if re.search(r"\breason\b|\bhttp\b", script, re.IGNORECASE):
        logger.warning(f"Spoken script rejected for reply '{reply_id}': contains forbidden keyword")
        return False

    # Check for emoji symbols
    if EMOJI_PATTERN.search(script):
        logger.warning(f"Spoken script rejected for reply '{reply_id}': contains emoji")
        return False

    return True


def get_cache_key(lang: str, voice: str, rate: str, script: str) -> str:
    """Computes SHA-256 cache key. Never reuses a Tamil clip for English."""
    payload = f"{lang}:{voice}:{rate}:{script}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def measure_audio_duration(path: str) -> float:
    """Measures audio file duration in seconds using PyAV."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return 0.0
    if HAS_AV:
        try:
            container = av.open(path)
            dur = float(container.duration) / av.time_base
            return dur
        except Exception as e:
            logger.warning(f"PyAV duration measurement failed: {e}")
    # Approximate fallback (~48kbps MP3 -> ~6000 bytes/sec)
    return round(os.path.getsize(path) / 6000.0, 2)


def convert_to_ogg_opus(in_path: str, out_path: str) -> bool:
    """Converts audio to OGG/Opus for Telegram voice notes using ffmpeg or PyAV."""
    if not os.path.exists(in_path) or os.path.getsize(in_path) == 0:
        return False

    ffmpeg_bin = os.getenv("FFMPEG_PATH", "ffmpeg")
    try:
        cmd = [
            ffmpeg_bin, "-y", "-i", in_path,
            "-c:a", "libopus", "-b:a", "32k", "-vn",
            out_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            return True
    except Exception:
        pass

    # PyAV fallback
    if HAS_AV:
        try:
            in_container = av.open(in_path)
            in_stream = in_container.streams.audio[0]
            out_container = av.open(out_path, mode='w', format='ogg')
            out_stream = out_container.add_stream('libopus', rate=48000)
            out_stream.bit_rate = 32000
            resampler = av.AudioResampler(format='s16', layout='mono', rate=48000)

            for packet in in_container.demux(in_stream):
                for frame in packet.decode():
                    frame.pts = None
                    resampled_frames = resampler.resample(frame)
                    if resampled_frames:
                        for rf in (resampled_frames if isinstance(resampled_frames, list) else [resampled_frames]):
                            rf.pts = None
                            for out_packet in out_stream.encode(rf):
                                out_container.mux(out_packet)

            for out_packet in out_stream.encode(None):
                out_container.mux(out_packet)

            in_container.close()
            out_container.close()
            if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                return True
        except Exception as e:
            logger.warning(f"PyAV OGG/Opus conversion failed: {e}")

    return False


async def synthesize_gtts(text: str, lang: str, out_path: str, timeout: float = 8.0) -> bool:
    """Fallback TTS provider using gTTS (unofficial Google Translate TTS API)."""
    try:
        from gtts import gTTS

        def _run_gtts():
            gtts_lang = "ta" if lang == "ta" else "en"
            tts_obj = gTTS(text=text, lang=gtts_lang, slow=False)
            tts_obj.save(out_path)
            return True

        return await asyncio.wait_for(asyncio.to_thread(_run_gtts), timeout=timeout)
    except Exception as e:
        logger.warning(f"gTTS fallback failed: {type(e).__name__} ({e})")
        return False


async def synthesize_speech(
    text: str,
    lang: str = "ta",
    voice: Optional[str] = None,
    rate: str = DEFAULT_TTS_RATE,
    reply_id: str = "generic"
) -> Optional[Tuple[str, float]]:
    """
    Synthesizes validated spoken script into audio.
    Fallback order: cache -> edge-tts (8s timeout) -> gTTS (Tamil 'ta', English 'en') -> text only with note.
    Converts to OGG/Opus for Telegram voice note.
    Returns (audio_filepath, duration_seconds) or None on failure or validation rejection.
    """
    clean_text = apply_tts_replacements(text.strip(), lang=lang)

    # Strict Voice Script Validation
    if not validate_spoken_script(clean_text, reply_id=reply_id):
        return None

    selected_voice = voice or VOICE_CONFIG.get(lang, {}).get("default", "ta-IN-PallaviNeural")
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_key = get_cache_key(lang, selected_voice, rate, clean_text)
    cache_mp3 = os.path.join(CACHE_DIR, f"{cache_key}.mp3")
    cache_ogg = os.path.join(CACHE_DIR, f"{cache_key}.ogg")

    # 1. Cache hit (prefer OGG/Opus if present, fallback to MP3)
    if os.path.exists(cache_ogg) and os.path.getsize(cache_ogg) > 0:
        dur = measure_audio_duration(cache_ogg)
        return cache_ogg, dur
    if os.path.exists(cache_mp3) and os.path.getsize(cache_mp3) > 0:
        if convert_to_ogg_opus(cache_mp3, cache_ogg):
            dur = measure_audio_duration(cache_ogg)
            return cache_ogg, dur
        dur = measure_audio_duration(cache_mp3)
        return cache_mp3, dur

    # 2. Synthesis provider 1: edge-tts (8-second timeout)
    success = False
    try:
        communicate = edge_tts.Communicate(clean_text, selected_voice, rate=rate)
        await asyncio.wait_for(communicate.save(cache_mp3), timeout=8.0)
        if os.path.exists(cache_mp3) and os.path.getsize(cache_mp3) > 0:
            success = True
            logger.info(f"Synthesized TTS audio via edge-tts: {cache_mp3}")
    except Exception as e:
        logger.warning(f"edge-tts failed or timed out for '{reply_id}': {type(e).__name__} ({e}). Falling back to gTTS...")
        if os.path.exists(cache_mp3):
            try:
                os.remove(cache_mp3)
            except Exception:
                pass

    # 3. Synthesis provider 2: gTTS fallback (unofficial Google Translate TTS API)
    if not success:
        success = await synthesize_gtts(clean_text, lang, cache_mp3, timeout=8.0)

    # 4. Fallback: text only with a note
    if not success or not os.path.exists(cache_mp3) or os.path.getsize(cache_mp3) == 0:
        logger.warning(f"TTS synthesis failed on all providers for '{reply_id}'. Audio unavailable, sending text only.")
        return None

    # 5. Convert to OGG/Opus for Telegram voice note
    if convert_to_ogg_opus(cache_mp3, cache_ogg):
        final_path = cache_ogg
    else:
        final_path = cache_mp3

    dur = measure_audio_duration(final_path)
    return final_path, dur


def build_verdict_spoken_script(
    verdict: str,
    signals: List[str],
    lang: str = "ta",
    max_reasons: int = 2
) -> str:
    """
    Constructs spoken script for verdict voice.
    Rule: headline + at most 2 reasons + ONE next step.
    Strictly uses approved existing Tamil spoken entries.
    Contains NO template IDs, braces, HTML tags, or markdown.
    """
    if lang == "en":
        # 1. Headline
        if verdict == "SCAM":
            headline = "This looks like a scam."
            step = "Do not click any link, and never share your O T P or P I N."
        elif verdict == "SUSPICIOUS":
            headline = "This looks suspicious."
            step = "Do not click the link, and never share your O T P or P I N."
        else:
            headline = "No red flags were found in this message."
            step = "Stay cautious if from an unknown number, and never share your O T P or P I N."

        # 2. Reasons (up to max_reasons)
        reasons: List[str] = []
        if verdict in ("SCAM", "SUSPICIOUS"):
            from engine.intents import SIGNAL_TO_REASON_ID, get_reply
            for code in signals:
                rid = SIGNAL_TO_REASON_ID.get(code)
                if rid:
                    r_entry = get_reply(rid)
                    if r_entry:
                        r_text = r_entry.get("en_gloss", "")
                        r_text = r_text.replace('"', '').replace("'", "").strip()
                        if r_text and r_text not in reasons:
                            reasons.append(r_text)
                        if len(reasons) >= max_reasons:
                            break

        parts = [headline]
        for r in reasons:
            parts.append(r)
        parts.append(step)
        return " ".join(parts)

    else:
        # Tamil (Strictly existing approved Tamil spoken texts)
        if verdict == "SCAM":
            headline = "இது மோசடி போல் உள்ளது."
            step = "லிங்கைத் தொடாதீர்கள். ஓ டி பி, பின் யாரிடமும் சொல்லாதீர்கள்."
        elif verdict == "SUSPICIOUS":
            headline = "இது சந்தேகத்துக்குரியது."
            step = "லிங்கைத் திறக்க வேண்டாம். ஓ டி பி, பின் யாரிடமும் சொல்லாதீர்கள்."
        else:
            headline = "இதில் எச்சரிக்கை அறிகுறிகள் எதுவும் கிடைக்கவில்லை."
            step = "தெரியாத எண்ணாக இருந்தால் கவனமாக இருங்கள். ஓ டி பி, பின் யாரிடமும் சொல்லாதீர்கள்."

        reasons = []
        if verdict in ("SCAM", "SUSPICIOUS"):
            from engine.intents import SIGNAL_TO_REASON_ID, get_reply
            for code in signals:
                rid = SIGNAL_TO_REASON_ID.get(code)
                if rid:
                    r_entry = get_reply(rid)
                    if r_entry:
                        r_text = r_entry.get("tts_text") or r_entry.get("ta", "")
                        r_text = r_text.replace('"', '').replace("'", "").strip()
                        if r_text and r_text not in reasons:
                            reasons.append(r_text)
                        if len(reasons) >= max_reasons:
                            break

        parts = [headline]
        for r in reasons:
            parts.append(r)
        parts.append(step)
        return " ".join(parts)


async def synthesize_verdict_voice(
    verdict: str,
    signals: List[str],
    lang: str = "ta"
) -> Optional[Tuple[str, float]]:
    """
    Synthesizes verdict voice note.
    Target: 10 to 15 seconds.
    Hard cap: 20 seconds. If longer, shortens by dropping the second reason.
    """
    # Try 2 reasons first
    script_2 = build_verdict_spoken_script(verdict, signals, lang=lang, max_reasons=2)
    res = await synthesize_speech(script_2, lang=lang, reply_id=f"V_{verdict}_{lang}")
    if res is None:
        return None
    path, dur = res

    # If duration exceeds 20.0 seconds and we had multiple reasons, drop the second reason
    if dur > 20.0 and len(signals) > 1:
        script_1 = build_verdict_spoken_script(verdict, signals, lang=lang, max_reasons=1)
        res_short = await synthesize_speech(script_1, lang=lang, reply_id=f"V_{verdict}_{lang}_short")
        if res_short is not None:
            return res_short

    return res
