import os
import sys
import time
import wave
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')
os.environ['HF_HUB_OFFLINE'] = '1'
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import faster_whisper
import speech

model_path = r'C:\Users\athis\.cache\huggingface\hub\models--Systran--faster-whisper-small\snapshots\536b0662742c02347bc0e980a01041f333bce120'

def preprocess_audio(audio_np, sample_rate=16000):
    duration = len(audio_np) / float(sample_rate)
    if duration < 1.0:
        raise ValueError(f'Audio too short ({duration:.2f}s < 1.0s)')
    if duration > 60.0:
        raise ValueError(f'Audio too long ({duration:.2f}s > 60.0s)')
    
    # 1. Trim leading and trailing silence
    energy = np.abs(audio_np)
    non_silent = np.where(energy > 0.01)[0]
    if len(non_silent) > 0:
        margin = int(0.1 * sample_rate)
        start_idx = max(0, non_silent[0] - margin)
        end_idx = min(len(audio_np), non_silent[-1] + margin)
        audio_np = audio_np[start_idx:end_idx]
    
    # 2. Normalise loudness
    peak = np.max(np.abs(audio_np))
    if peak > 1e-4:
        audio_np = (audio_np / peak) * 0.90
        
    return audio_np

print("======================================================================", flush=True)
print("STEP 1: PIPELINE FIXES BENCHMARK (beam 1 vs beam 5, temp 0, 10 threads)", flush=True)
print("======================================================================", flush=True)

# Warm model once
t0 = time.perf_counter()
model = faster_whisper.WhisperModel(model_path, device='cpu', compute_type='int8', cpu_threads=10)
print(f"Warm model load time: {time.perf_counter() - t0:.3f} s", flush=True)

clips = ["Audio-1.ogg", "Audio-2.ogg", "Audio-3.ogg", "Audio-4.ogg"]
audio_dir = os.path.join(WORKSPACE_ROOT, "data", "audio")

preprocessed_audios = {}
for clip in clips:
    clip_path = os.path.join(audio_dir, clip)
    wav_path = speech.convert_ogg_to_wav(clip_path)
    with wave.open(wav_path, "rb") as wf:
        raw_bytes = wf.readframes(wf.getnframes())
        audio_np = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    if os.path.exists(wav_path):
        os.remove(wav_path)
    preprocessed_audios[clip] = preprocess_audio(audio_np)

print("\n--- BENCHMARK: BEAM_SIZE = 1 ---", flush=True)
for clip in clips:
    audio_np = preprocessed_audios[clip]
    t0 = time.perf_counter()
    segments, info = model.transcribe(
        audio_np,
        language="ta",
        beam_size=1,
        temperature=0,
        vad_filter=True,
        condition_on_previous_text=False
    )
    segs = list(segments)
    dt = time.perf_counter() - t0
    txt = " ".join(s.text.strip() for s in segs)
    avg_lp = np.mean([s.avg_logprob for s in segs]) if segs else -99.0
    nsp = np.mean([s.no_speech_prob for s in segs]) if segs else 1.0
    words = len(txt.split())
    print(f"{clip}: time={dt:.3f}s | words={words} | avg_lp={avg_lp:.3f} | no_speech={nsp:.3f}", flush=True)
    print(f"   text: {txt}", flush=True)

print("\n--- BENCHMARK: BEAM_SIZE = 5 ---", flush=True)
for clip in clips:
    audio_np = preprocessed_audios[clip]
    t0 = time.perf_counter()
    segments, info = model.transcribe(
        audio_np,
        language="ta",
        beam_size=5,
        temperature=0,
        vad_filter=True,
        condition_on_previous_text=False
    )
    segs = list(segments)
    dt = time.perf_counter() - t0
    txt = " ".join(s.text.strip() for s in segs)
    avg_lp = np.mean([s.avg_logprob for s in segs]) if segs else -99.0
    nsp = np.mean([s.no_speech_prob for s in segs]) if segs else 1.0
    words = len(txt.split())
    print(f"{clip}: time={dt:.3f}s | words={words} | avg_lp={avg_lp:.3f} | no_speech={nsp:.3f}", flush=True)
    print(f"   text: {txt}", flush=True)

print("\nSTEP 1 BENCHMARK COMPLETE.", flush=True)
