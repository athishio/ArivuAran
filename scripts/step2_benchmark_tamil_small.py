import os
import sys
import time
import wave
import statistics
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')
os.environ['HF_HUB_OFFLINE'] = '1'

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import faster_whisper
import speech
from engine.voice_norm import normalise_voice_transcript
from engine.decide import analyse

print("======================================================================")
print("TAMIL SMALL MODEL TRIAL BENCHMARK (OFFLINE)")
print("======================================================================")

# Paths
path_model_a = r"C:\Users\athis\.cache\huggingface\hub\models--Systran--faster-whisper-small\snapshots\536b0662742c02347bc0e980a01041f333bce120"
path_model_b = os.path.join(WORKSPACE_ROOT, "models", "whisper-tamil-small-ct2")

print(f"Loading Model A (Standard small): {path_model_a}")
t0 = time.perf_counter()
model_a = faster_whisper.WhisperModel(path_model_a, device='cpu', compute_type='int8', cpu_threads=10)
print(f"Model A loaded in {time.perf_counter() - t0:.3f} s")

print(f"Loading Model B (Tamil small ct2): {path_model_b}")
t0 = time.perf_counter()
model_b = faster_whisper.WhisperModel(path_model_b, device='cpu', compute_type='int8', cpu_threads=10)
print(f"Model B loaded in {time.perf_counter() - t0:.3f} s (OFFLINE SUCCESS)")

clips = ["Audio-1.ogg", "Audio-2.ogg", "Audio-3.ogg", "Audio-4.ogg"]
audio_dir = os.path.join(WORKSPACE_ROOT, "data", "audio")

# Load and preprocess all clips
preprocessed_audios = {}
for clip in clips:
    clip_path = os.path.join(audio_dir, clip)
    wav_path = speech.convert_ogg_to_wav(clip_path)
    with wave.open(wav_path, "rb") as wf:
        raw_bytes = wf.readframes(wf.getnframes())
        audio_np = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    if os.path.exists(wav_path):
        os.remove(wav_path)
    preprocessed_audios[clip] = speech.preprocess_audio(audio_np)

print("\n--- RUNNING 3 RUNS PER CLIP FOR MEDIAN LATENCY ---")

def benchmark_model(model, model_name):
    results = {}
    for clip in clips:
        audio_np = preprocessed_audios[clip]
        durations = []
        last_transcript = ""
        last_avg_lp = 0.0
        
        for r in range(3):
            t_start = time.perf_counter()
            segments, info = model.transcribe(
                audio_np,
                language="ta",
                beam_size=1,
                temperature=0,
                vad_filter=True,
                condition_on_previous_text=False
            )
            segs = list(segments)
            dur = time.perf_counter() - t_start
            durations.append(dur)
            last_transcript = " ".join(s.text.strip() for s in segs).strip()
            last_avg_lp = float(np.mean([s.avg_logprob for s in segs])) if segs else -99.0
            
        med_lat = statistics.median(durations)
        results[clip] = {
            "latency": med_lat,
            "transcript": last_transcript,
            "avg_logprob": last_avg_lp,
            "runs": durations
        }
        print(f"[{model_name}] {clip}: median={med_lat:.3f}s (runs={[round(d, 3) for d in durations]}), avg_lp={last_avg_lp:.3f}")
    return results

print("\nBenchmarking Model A (Standard small)...")
results_a = benchmark_model(model_a, "Model A")

print("\nBenchmarking Model B (Tamil small)...")
results_b = benchmark_model(model_b, "Model B")

print("\n======================================================================")
print("SIDE-BY-SIDE TRANSCRIPT COMPARISON & REVIEW TABLE")
print("======================================================================")
for clip in clips:
    ra = results_a[clip]
    rb = results_b[clip]
    print(f"\nCLIP: {clip}")
    print(f"  Model A (Current Small):")
    print(f"    Latency:     {ra['latency']:.3f} s")
    print(f"    Avg Logprob: {ra['avg_logprob']:.3f}")
    print(f"    Transcript:  {ra['transcript']}")
    print(f"  Model B (Tamil Small - vasista22):")
    print(f"    Latency:     {rb['latency']:.3f} s")
    print(f"    Avg Logprob: {rb['avg_logprob']:.3f}")
    print(f"    Transcript:  {rb['transcript']}")

print("\n======================================================================")
print("ENGINE VERDICTS (DESCRIPTIVE ONLY)")
print("======================================================================")
for clip in clips:
    for m_label, m_res in [("Model A (Standard Small)", results_a[clip]), ("Model B (Tamil Small)", results_b[clip])]:
        raw_text = m_res["transcript"]
        norm_text = normalise_voice_transcript(raw_text)
        analysis = analyse(norm_text)
        sigs = [f"{s.code}(+{s.points})" for s in analysis.signals]
        sig_str = ", ".join(sigs) if sigs else "NONE"
        print(f"\n[{m_label}] - {clip}:")
        print(f"  Raw:        {raw_text}")
        print(f"  Normalised: {norm_text}")
        print(f"  Verdict:    {analysis.verdict} (Score: {analysis.score}, Signals: {sig_str})")
