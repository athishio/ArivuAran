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

print("======================================================================", flush=True)
print("STEP 0: VOICE-IN BASELINE DIAGNOSIS ON REAL CLIPS", flush=True)
print("======================================================================", flush=True)

# 1. Model Lifecycle & Configuration
print("Model Lifecycle: Created once as global singleton (lazy-loaded/startup)", flush=True)
print("Model Name: faster-whisper small (Systran/faster-whisper-small)", flush=True)
print("Device: cpu", flush=True)
print("Compute Type: int8", flush=True)
print("CPU Threads Used: 4 (baseline)", flush=True)
print("Beam Size: 5 (baseline)", flush=True)
print("VAD Filter: True", flush=True)
print("Language Passed: ta", flush=True)

model_path = r'C:\Users\athis\.cache\huggingface\hub\models--Systran--faster-whisper-small\snapshots\536b0662742c02347bc0e980a01041f333bce120'
t0 = time.perf_counter()
model = faster_whisper.WhisperModel(model_path, device='cpu', compute_type='int8', cpu_threads=4)
model_load_time = time.perf_counter() - t0
print(f"Model Load Time: {model_load_time:.3f} s", flush=True)

clips = ["Audio-1.ogg", "Audio-2.ogg", "Audio-3.ogg", "Audio-4.ogg"]
audio_dir = os.path.join(WORKSPACE_ROOT, "data", "audio")

for clip in clips:
    clip_path = os.path.join(audio_dir, clip)
    if not os.path.exists(clip_path):
        print(f"File not found: {clip}", flush=True)
        continue

    # Audio Conversion
    t_conv_start = time.perf_counter()
    wav_path = speech.convert_ogg_to_wav(clip_path)
    conv_time = time.perf_counter() - t_conv_start

    with wave.open(wav_path, "rb") as wf:
        n_frames = wf.getnframes()
        sample_rate = wf.getframerate()
        duration = n_frames / float(sample_rate)
        raw_bytes = wf.readframes(n_frames)
        audio_np = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0

    if os.path.exists(wav_path):
        try:
            os.remove(wav_path)
        except OSError:
            pass

    # Decoding (Baseline: beam_size=5, default temperature fallbacks, vad_filter=True, language="ta")
    t_dec_start = time.perf_counter()
    segments, info = model.transcribe(
        audio_np,
        language="ta",
        beam_size=5,
        vad_filter=True
    )
    transcript = " ".join(s.text.strip() for s in segments).strip()
    decode_time = time.perf_counter() - t_dec_start

    total_time = conv_time + decode_time

    print(f"\n--- {clip} ---", flush=True)
    print(f"Audio Duration:      {duration:.2f} s", flush=True)
    print(f"Audio Conversion:    {conv_time * 1000.0:.2f} ms ({conv_time:.3f} s)", flush=True)
    print(f"Decoding Time:       {decode_time:.3f} s", flush=True)
    print(f"Total Processing:    {total_time:.3f} s", flush=True)
    print(f"Exact Transcript:    {transcript}", flush=True)

print("\n======================================================================", flush=True)
print("DIAGNOSIS COMPLETE", flush=True)
