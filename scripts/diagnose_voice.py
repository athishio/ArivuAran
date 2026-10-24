import os
import sys
import time
import wave
import statistics
import subprocess
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import speech

def get_cpu_load():
    try:
        out = subprocess.check_output(
            ["powershell", "-Command", "(Get-CimInstance Win32_Processor).LoadPercentage"],
            text=True
        ).strip()
        return f"{out}%"
    except Exception:
        return "N/A"

print("======================================================================")
print("VOICE DIAGNOSIS: TEMPERATURE, LOGPROB & BEAM COMPARISON")
print("======================================================================")
print(f"Initial CPU Load: {get_cpu_load()}")

# Load model via speech._get_whisper_model()
t0 = time.perf_counter()
model = speech._get_whisper_model()
load_time = time.perf_counter() - t0
print(f"Whisper model loaded in {load_time:.2f}s (small, cpu, int8, threads=4)")

def load_audio_np(ogg_path: str):
    wav_path = speech.convert_ogg_to_wav(ogg_path)
    try:
        with wave.open(wav_path, "rb") as wf:
            raw = wf.readframes(wf.getnframes())
            audio_np = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        return audio_np
    finally:
        if os.path.exists(wav_path):
            os.remove(wav_path)

# Pre-load all audio arrays
clips = ["Audio-1.ogg", "Audio-2.ogg", "Audio-3.ogg", "Audio-4.ogg"]
audio_arrays = {}
for clip_name in clips:
    clip_path = os.path.join(WORKSPACE_ROOT, "data", "audio", clip_name)
    audio_arrays[clip_name] = load_audio_np(clip_path)

# 1. Temperature and avg_logprob per segment for Audio-1 and Audio-3
print("\n" + "=" * 70)
print("1. TEMPERATURE & AVG_LOGPROB ANALYSIS (CURRENT DEFAULTS, beam_size=5, language='ta')")
print("=" * 70)

for clip_name in ["Audio-1.ogg", "Audio-3.ogg"]:
    audio_np = audio_arrays[clip_name]
    segments, info = model.transcribe(audio_np, language="ta", beam_size=5)
    print(f"\n--- {clip_name} ---")
    print(f"Detected language: {info.language} (prob: {info.language_probability:.2f}), duration: {info.duration:.2f}s")
    seg_list = list(segments)
    for i, seg in enumerate(seg_list):
        print(f"  Segment {i+1} [{seg.start:.2f}s - {seg.end:.2f}s]:")
        print(f"    Text: {seg.text}")
        print(f"    Temperature: {seg.temperature}")
        print(f"    Avg Logprob: {seg.avg_logprob:.4f}")
        print(f"    Compression ratio: {seg.compression_ratio:.2f}")
        print(f"    No speech prob: {seg.no_speech_prob:.4f}")

# 2. Compare beam_size=5 against beam_size=1 (vad_filter=True, condition_on_previous_text=False)
print("\n" + "=" * 70)
print("2. BENCHMARK: BEAM_SIZE=5 (CURRENT) vs BEAM_SIZE=1 (VAD=True, CONDITION=False)")
print("=" * 70)

results = {}

for clip_name in clips:
    audio_np = audio_arrays[clip_name]
    results[clip_name] = {}
    print(f"\nTesting {clip_name}...")

    # CONFIG A: Current defaults (beam_size=5, language="ta")
    # Warmup
    list(model.transcribe(audio_np, language="ta", beam_size=5)[0])
    times_a = []
    text_a = ""
    for run in range(3):
        t_start = time.perf_counter()
        segs, _ = model.transcribe(audio_np, language="ta", beam_size=5)
        text_a = " ".join(s.text.strip() for s in segs)
        dur = time.perf_counter() - t_start
        times_a.append(dur)
    median_a = statistics.median(times_a)
    results[clip_name]["config_a"] = {
        "times": times_a,
        "median": median_a,
        "transcript": text_a.strip()
    }
    print(f"  Config A (beam=5): runs={[round(t, 2) for t in times_a]}, median={median_a:.2f}s")

    # CONFIG B: beam_size=1, vad_filter=True, condition_on_previous_text=False, language="ta"
    # Warmup
    list(model.transcribe(
        audio_np,
        language="ta",
        beam_size=1,
        vad_filter=True,
        condition_on_previous_text=False
    )[0])
    times_b = []
    text_b = ""
    for run in range(3):
        t_start = time.perf_counter()
        segs, _ = model.transcribe(
            audio_np,
            language="ta",
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False
        )
        text_b = " ".join(s.text.strip() for s in segs)
        dur = time.perf_counter() - t_start
        times_b.append(dur)
    median_b = statistics.median(times_b)
    results[clip_name]["config_b"] = {
        "times": times_b,
        "median": median_b,
        "transcript": text_b.strip()
    }
    print(f"  Config B (beam=1, vad=True, cond=False): runs={[round(t, 2) for t in times_b]}, median={median_b:.2f}s")

print("\n" + "=" * 70)
print("FINAL COMPARISON TABLE")
print("=" * 70)
for clip_name in clips:
    res = results[clip_name]
    med_a = res["config_a"]["median"]
    med_b = res["config_b"]["median"]
    speedup = med_a / med_b if med_b > 0 else 0
    print(f"\n{clip_name}:")
    print(f"  Config A Median : {med_a:.2f}s")
    print(f"  Config A Transcript: {res['config_a']['transcript']}")
    print(f"  Config B Median : {med_b:.2f}s ({speedup:.1f}x speedup)")
    print(f"  Config B Transcript: {res['config_b']['transcript']}")

print(f"\nFinal CPU Load: {get_cpu_load()}")
