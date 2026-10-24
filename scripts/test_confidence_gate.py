import os
import sys
import wave
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import speech

def has_invalid_characters(text: str) -> bool:
    """Checks if text contains characters outside Tamil, Latin, digits, whitespace, and punctuation."""
    import unicodedata
    for ch in text:
        # Check Tamil block
        if '\u0B80' <= ch <= '\u0BFF':
            continue
        # Check Latin
        if ('a' <= ch <= 'z') or ('A' <= ch <= 'Z'):
            continue
        # Check digits
        if '0' <= ch <= '9':
            continue
        # Check whitespace
        if ch.isspace():
            continue
        # Check punctuation or symbol
        cat = unicodedata.category(ch)
        if cat.startswith(('P', 'S')):  # Punctuation or Symbol
            continue
        if ch in ('\u200c', '\u200d', '\u200b', '\ufeff'):
            continue
        # Any other character category (e.g. Other Letters 'Lo' from Cyrillic, Hangul, CJK, etc.)
        return True
    return False

def check_confidence_gate(segments, full_text):
    """
    Returns (passed: bool, reasons: list)
    Fail if:
    - avg_logprob < -1.0
    - no_speech_prob > 0.5
    - final temperature > 0.4
    - text contains characters outside Tamil, Latin, digits, and punctuation
    """
    reasons = []
    
    # 1. Foreign characters check
    if has_invalid_characters(full_text):
        reasons.append("Contains characters outside Tamil, Latin, digits, punctuation")
        
    for i, seg in enumerate(segments):
        if seg.avg_logprob < -1.0:
            reasons.append(f"Segment {i+1} avg_logprob {seg.avg_logprob:.4f} < -1.0")
        if seg.no_speech_prob > 0.5:
            reasons.append(f"Segment {i+1} no_speech_prob {seg.no_speech_prob:.4f} > 0.5")
        if seg.temperature > 0.4:
            reasons.append(f"Segment {i+1} temperature {seg.temperature:.2f} > 0.4")
            
    passed = len(reasons) == 0
    return passed, reasons

model = speech._get_whisper_model()
clips = ["Audio-1.ogg", "Audio-2.ogg", "Audio-3.ogg", "Audio-4.ogg"]

print("======================================================================")
print("CONFIDENCE GATE EVALUATION ON 4 AUDIO CLIPS")
print("======================================================================")

passed_count = 0
for clip_name in clips:
    clip_path = os.path.join(WORKSPACE_ROOT, "data", "audio", clip_name)
    wav_path = speech.convert_ogg_to_wav(clip_path)
    try:
        with wave.open(wav_path, "rb") as wf:
            raw = wf.readframes(wf.getnframes())
            audio_np = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)
            
    segments, info = model.transcribe(audio_np, language="ta", beam_size=5)
    seg_list = list(segments)
    full_text = " ".join(s.text.strip() for s in seg_list)
    
    passed, reasons = check_confidence_gate(seg_list, full_text)
    if passed:
        passed_count += 1
        status = "PASSED"
    else:
        status = "FAILED"
        
    print(f"\n{clip_name}: {status}")
    print(f"  Duration: {info.duration:.2f}s")
    print(f"  Full Text: {full_text}")
    for i, s in enumerate(seg_list):
        print(f"  Seg {i+1}: temp={s.temperature:.2f}, avg_logprob={s.avg_logprob:.4f}, no_speech_prob={s.no_speech_prob:.4f}")
    if reasons:
        print(f"  Rejection Reasons: {reasons}")

print("\n" + "=" * 70)
print(f"CONFIDENCE GATE RESULT: {passed_count} / {len(clips)} CLIPS PASSED")
print("======================================================================")
