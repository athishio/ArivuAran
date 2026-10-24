"""
Voice note transcription layer for Arivaran.
Converts WhatsApp OGG/Opus voice notes to 16 kHz Mono WAV using PyAV,
and transcribes speech to text using faster-whisper (local).
Preserves Tamil-English code-switching without force-translating.
"""

import os
import sys
import wave
import logging
import tempfile
import subprocess
from typing import Optional, Dict, Any, Tuple
import numpy as np

logger = logging.getLogger("speech_transcriber")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Global cached model instance to avoid reloading weights on every voice note
_whisper_model = None

MIN_AUDIO_DURATION_SECONDS = 1.0
MAX_AUDIO_DURATION_SECONDS = 60.0


def _get_whisper_model(model_name_or_path: str = "small", cpu_threads: int = 10):
    """Lazy loader for faster-whisper model kept warm in memory."""
    global _whisper_model
    if _whisper_model is None:
        try:
            from faster_whisper import WhisperModel
            logger.info(f"Loading faster-whisper model ('{model_name_or_path}', cpu, int8, threads={cpu_threads})...")
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            _whisper_model = WhisperModel(model_name_or_path, device="cpu", compute_type="int8", cpu_threads=cpu_threads)
            logger.info("faster-whisper model loaded successfully.")
        except ImportError:
            logger.error("faster-whisper is not installed. Run 'pip install faster-whisper'.")
            raise
    return _whisper_model


def get_audio_duration_wave(wav_path: str) -> float:
    """Returns duration of WAV file in seconds."""
    with wave.open(wav_path, "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)


def convert_ogg_to_wav(ogg_path: str) -> str:
    """
    Converts WhatsApp ogg/opus to 16 kHz mono WAV using PyAV (in-process) or ffmpeg fallback.
    Timeout 20 seconds.
    """
    temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    temp_wav.close()

    # 1. PyAV: in-process decoding to 16kHz mono WAV (fast, no subprocess)
    try:
        import av
        in_container = av.open(ogg_path)
        in_stream = in_container.streams.audio[0]
        resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)

        with wave.open(temp_wav.name, 'wb') as out_wav:
            out_wav.setnchannels(1)
            out_wav.setsampwidth(2)
            out_wav.setframerate(16000)
            for frame in in_container.decode(in_stream):
                for resampled in resampler.resample(frame):
                    out_wav.writeframes(resampled.to_ndarray().tobytes())
        return temp_wav.name
    except Exception as e:
        logger.warning(f"PyAV conversion failed: {e}. Trying ffmpeg fallback.")

    # 2. ffmpeg fallback
    ffmpeg_bin = os.getenv("FFMPEG_PATH", "ffmpeg")
    cmd = [
        ffmpeg_bin,
        "-y",
        "-i", ogg_path,
        "-ar", "16000",
        "-ac", "1",
        "-f", "wav",
        temp_wav.name
    ]

    try:
        subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20,
            check=True
        )
        return temp_wav.name
    except Exception as e:
        if os.path.exists(temp_wav.name):
            try:
                os.remove(temp_wav.name)
            except OSError:
                pass
        raise RuntimeError(f"Audio conversion failed via PyAV and ffmpeg: {e}")


def preprocess_audio(audio_np: np.ndarray, sample_rate: int = 16000) -> np.ndarray:
    """
    Trims leading and trailing silence (energy threshold 0.01 / ~ -40dB)
    and normalises loudness (peak normalize to 0.90 / -1 dBFS).
    """
    energy = np.abs(audio_np)
    non_silent = np.where(energy > 0.01)[0]
    if len(non_silent) > 0:
        margin = int(0.1 * sample_rate)  # 100ms
        start_idx = max(0, non_silent[0] - margin)
        end_idx = min(len(audio_np), non_silent[-1] + margin)
        audio_np = audio_np[start_idx:end_idx]

    peak = np.max(np.abs(audio_np))
    if peak > 1e-4:
        audio_np = (audio_np / peak) * 0.90
    return audio_np


def check_voice_confidence(
    text: str,
    avg_logprob: float,
    no_speech_prob: float,
    temperature: float = 0.0
) -> bool:
    """
    Returns True if transcript passes confidence criteria:
    - avg_logprob >= -1.0
    - no_speech_prob <= 0.5
    - temperature <= 0.4
    - text contains at least 3 words
    - characters strictly within Tamil, Latin, digits, whitespace, and basic punctuation
    """
    if not text or len(text.strip().split()) < 3:
        return False
    if avg_logprob < -1.0:
        return False
    if no_speech_prob > 0.5:
        return False
    if temperature > 0.4:
        return False

    # Check for foreign scripts (Cyrillic, Arabic, Hangul, Kana, Hanzi, etc.)
    for ch in text:
        code = ord(ch)
        if 0x0B80 <= code <= 0x0BFF:  # Tamil
            continue
        if 0x0020 <= code <= 0x007E or 0x00A0 <= code <= 0x00FF:  # Latin & Punctuation
            continue
        if ch in ("\n", "\r", "\t"):
            continue
        return False

    return True


def transcribe_with_metadata(
    ogg_path: str,
    language_hint: str = "ta",
    delete_source: bool = True
) -> Dict[str, Any]:
    """
    Transcribes a voice note with audio preprocessing and confidence gate.
    Limits audio length to 1.0s <= duration <= 60.0s.
    Deletes temporary WAV and optionally source OGG in finally block.
    """
    wav_path: Optional[str] = None
    try:
        # Step 1: Convert OGG to 16 kHz mono WAV
        wav_path = convert_ogg_to_wav(ogg_path)

        # Step 2: Check audio duration limit
        duration = get_audio_duration_wave(wav_path)
        if duration < MIN_AUDIO_DURATION_SECONDS:
            raise ValueError(f"Audio duration ({duration:.2f}s) is under minimum allowed {MIN_AUDIO_DURATION_SECONDS}s.")
        if duration > MAX_AUDIO_DURATION_SECONDS:
            raise ValueError(f"Audio duration ({duration:.1f}s) exceeds maximum allowed {MAX_AUDIO_DURATION_SECONDS}s.")

        # Step 3: Read and Preprocess Audio
        with wave.open(wav_path, "rb") as wf:
            raw = wf.readframes(wf.getnframes())
            audio_np = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

        audio_np = preprocess_audio(audio_np)

        # Step 4: Transcribe (optimized: beam_size=1, temperature=0, 10 threads, vad_filter=True)
        model = _get_whisper_model()
        segments, _info = model.transcribe(
            audio_np,
            language=language_hint,
            beam_size=1,
            temperature=0,
            vad_filter=True,
            condition_on_previous_text=False
        )

        segs = list(segments)
        transcription_text = " ".join([segment.text.strip() for segment in segs]).strip()

        avg_lp = float(np.mean([s.avg_logprob for s in segs])) if segs else -99.0
        nsp = float(np.mean([s.no_speech_prob for s in segs])) if segs else 1.0

        confidence_passed = check_voice_confidence(
            text=transcription_text,
            avg_logprob=avg_lp,
            no_speech_prob=nsp,
            temperature=0.0
        )

        return {
            "text": transcription_text,
            "confidence_passed": confidence_passed,
            "avg_logprob": avg_lp,
            "no_speech_prob": nsp,
            "duration": duration,
            "words": len(transcription_text.split())
        }

    finally:
        if wav_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except OSError:
                pass
        if delete_source and ogg_path and os.path.exists(ogg_path):
            try:
                os.remove(ogg_path)
            except OSError:
                pass


def transcribe(ogg_path: str, language_hint: str = "ta", delete_source: bool = True) -> str:
    """Backwards-compatible convenience wrapper returning plain text."""
    res = transcribe_with_metadata(ogg_path, language_hint=language_hint, delete_source=delete_source)
    return res["text"]
