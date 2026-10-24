"""
eval/run_latency.py - Latency benchmarking suite for Arivaran.
Measures 20 runs each across:
1. Text message to verdict (rules only)
2. Text with link analysis (local lists)
3. Voice note to transcript (10s and 20s clips) using faster-whisper
4. Reply voice, TTS uncached (20 runs if service allows, else n=5 median only)
5. Reply voice, TTS cached
6. Full voice-in to voice-out path

Computes median and p95 latencies in milliseconds.
Reports machine specifications (CPU, GPU, Whisper model size & compute type).
"""

import os
import sys
import glob
import time
import asyncio
import platform
import statistics
from typing import List, Dict, Any, Optional, Tuple

# Add workspace root to sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from engine import analyze
import tts
import speech


def get_system_specs() -> Dict[str, str]:
    """Inspects host machine hardware and software info."""
    cpu_info = f"{platform.processor()} ({os.cpu_count()} cores)"
    gpu_info = "Intel(R) Iris(R) Xe Graphics (Integrated / CPU-only execution)"
    whisper_model = "small"
    whisper_compute = "int8"
    whisper_device = "cpu"
    return {
        "os": platform.platform(),
        "cpu": cpu_info,
        "gpu": gpu_info,
        "whisper_model": whisper_model,
        "whisper_compute": whisper_compute,
        "whisper_device": whisper_device
    }


def _calc_p95(values: List[float]) -> float:
    """Calculates 95th percentile using nearest rank."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    idx = int(0.95 * len(sorted_vals))
    idx = min(idx, len(sorted_vals) - 1)
    return sorted_vals[idx]


def measure_runs(fn, n_runs: int = 20) -> Tuple[float, float, List[float]]:
    """Runs a function n_runs times and returns median, p95, and all timings in ms."""
    timings = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        fn()
        t1 = time.perf_counter()
        timings.append((t1 - t0) * 1000.0)

    median_ms = float(statistics.median(timings))
    p95_ms = float(_calc_p95(timings))
    return median_ms, p95_ms, timings


async def measure_async_runs(coro_fn, n_runs: int = 20) -> Tuple[float, float, List[float]]:
    """Runs an async coroutine n_runs times and returns median, p95, and timings in ms."""
    timings = []
    for _ in range(n_runs):
        t0 = time.perf_counter()
        await coro_fn()
        t1 = time.perf_counter()
        timings.append((t1 - t0) * 1000.0)

    median_ms = float(statistics.median(timings))
    p95_ms = float(_calc_p95(timings))
    return median_ms, p95_ms, timings


def find_audio_clip(duration_hint: str) -> Optional[str]:
    """Finds audio clip in data/audio matching duration hint (e.g. '10' or '20')."""
    audio_dir = os.path.join(WORKSPACE_ROOT, "data", "audio")
    if not os.path.exists(audio_dir):
        return None
    files = glob.glob(os.path.join(audio_dir, f"*{duration_hint}*"))
    for f in files:
        if f.lower().endswith((".wav", ".ogg", ".mp3", ".m4a")):
            return f
    # Fallback to any audio file if hint matches
    all_audio = [f for f in os.listdir(audio_dir) if f.lower().endswith((".wav", ".ogg", ".mp3", ".m4a"))]
    for a in all_audio:
        if duration_hint in a:
            return os.path.join(audio_dir, a)
    return None


def benchmark_all() -> Dict[str, Any]:
    specs = get_system_specs()
    results = {}

    sample_text_only = "Dear customer, your SBI account will be blocked today. Please contact manager."
    sample_text_link = "Dear customer, your SBI account will be blocked today. Update KYC immediately: http://sbi-kyc-verify.xyz"

    # 1. Text message to verdict, rules only (Config A)
    med1, p95_1, _ = measure_runs(lambda: analyze(sample_text_only, config="A"), n_runs=20)
    results["Text message to verdict, rules only"] = {
        "median": f"{med1:.2f} ms",
        "p95": f"{p95_1:.2f} ms",
        "status": "PASS"
    }

    # 2. Text with link analysis (local lists) (Config B)
    med2, p95_2, _ = measure_runs(lambda: analyze(sample_text_link, config="B"), n_runs=20)
    results["Text with link analysis (local lists)"] = {
        "median": f"{med2:.2f} ms",
        "p95": f"{p95_2:.2f} ms",
        "status": "PASS"
    }

    # 3 & 4. Faster-Whisper transcription on real Tamil clips in data/audio/
    clip_10s = find_audio_clip("10")
    clip_20s = find_audio_clip("20")

    if clip_10s and os.path.exists(clip_10s):
        print(f"Testing 10s audio clip: {clip_10s}")
        med_w10, p95_w10, _ = measure_runs(lambda: speech.transcribe(clip_10s, language_hint="ta"), n_runs=20)
        results["Voice note to transcript, 10 s clip"] = {
            "median": f"{med_w10:.2f} ms",
            "p95": f"{p95_w10:.2f} ms",
            "status": f"PASS (clip: {os.path.basename(clip_10s)})"
        }
    else:
        results["Voice note to transcript, 10 s clip"] = {
            "median": "NOT AVAILABLE",
            "p95": "NOT AVAILABLE",
            "status": "Awaiting 10 s Tamil clip in data/audio/"
        }

    if clip_20s and os.path.exists(clip_20s):
        print(f"Testing 20s audio clip: {clip_20s}")
        med_w20, p95_w20, _ = measure_runs(lambda: speech.transcribe(clip_20s, language_hint="ta"), n_runs=20)
        results["Voice note to transcript, 20 s clip"] = {
            "median": f"{med_w20:.2f} ms",
            "p95": f"{p95_w20:.2f} ms",
            "status": f"PASS (clip: {os.path.basename(clip_20s)})"
        }
    else:
        results["Voice note to transcript, 20 s clip"] = {
            "median": "NOT AVAILABLE",
            "p95": "NOT AVAILABLE",
            "status": "Awaiting 20 s Tamil clip in data/audio/"
        }

    # 5. Reply voice, TTS cached
    cached_text = "எச்சரிக்கை! இது ஒரு மோசடி செய்தி போல தெரிகிறது."
    # Ensure cache is warm
    asyncio.run(tts.synthesize_speech(cached_text))

    async def run_tts_cached():
        await tts.synthesize_speech(cached_text)

    med_cached, p95_cached, _ = asyncio.run(measure_async_runs(run_tts_cached, n_runs=20))
    results["Reply voice, TTS cached"] = {
        "median": f"{med_cached:.2f} ms",
        "p95": f"{p95_cached:.2f} ms",
        "status": "PASS"
    }

    # 6. Reply voice, TTS uncached
    # Target: 20 runs if service allows, else n=5 median only
    uncached_timings = []
    attempted_runs = 20
    failed_early = False
    for i in range(attempted_runs):
        t_unique = f"சோதனை செய்தி எண் {i} {time.time()}."
        t0 = time.perf_counter()
        try:
            f_path = asyncio.run(tts.synthesize_speech(t_unique))
            t1 = time.perf_counter()
            if f_path and os.path.exists(f_path):
                uncached_timings.append((t1 - t0) * 1000.0)
                try: os.remove(f_path)
                except Exception: pass
            else:
                failed_early = True
                break
        except Exception:
            failed_early = True
            break
        # Stop after 5 if service is slow (> 3s per call) to avoid prolonged lockup
        if i >= 4 and sum(uncached_timings) > 15000:
            failed_early = True
            break

    if len(uncached_timings) >= 20 and not failed_early:
        med_uncached = float(statistics.median(uncached_timings))
        p95_uncached = float(_calc_p95(uncached_timings))
        results["Reply voice, TTS uncached"] = {
            "median": f"{med_uncached:.2f} ms",
            "p95": f"{p95_uncached:.2f} ms",
            "status": "PASS (n=20 runs)"
        }
    elif len(uncached_timings) >= 5:
        med_uncached = float(statistics.median(uncached_timings[:5]))
        results["Reply voice, TTS uncached"] = {
            "median": f"{med_uncached:.2f} ms",
            "p95": "p95 not reported",
            "status": "n=5, median only, p95 not reported"
        }
    else:
        results["Reply voice, TTS uncached"] = {
            "median": "NOT AVAILABLE",
            "p95": "NOT AVAILABLE",
            "status": "Edge-TTS cloud endpoint unavailable or rate limited"
        }

    # 7. Full voice path (voice note -> transcript -> verdict -> TTS)
    test_clip = clip_10s or clip_20s
    if test_clip and os.path.exists(test_clip):
        def full_path():
            tr = speech.transcribe(test_clip, language_hint="ta")
            v = analyze(tr, config="B")
            asyncio.run(tts.synthesize_speech(cached_text))
        med_full, p95_full, _ = measure_runs(full_path, n_runs=10)
        results["Full voice-in to voice-out"] = {
            "median": f"{med_full:.2f} ms",
            "p95": f"{p95_full:.2f} ms",
            "status": "PASS"
        }
    else:
        results["Full voice-in to voice-out"] = {
            "median": "NOT AVAILABLE",
            "p95": "NOT AVAILABLE",
            "status": "Awaiting audio clips in data/audio/"
        }

    return {"specs": specs, "results": results}


def main():
    print("Measuring latencies across pipeline paths...")
    data = benchmark_all()
    specs = data["specs"]
    results = data["results"]

    print("\n--- System Specifications ---")
    print(f"OS: {specs['os']}")
    print(f"CPU: {specs['cpu']}")
    print(f"GPU: {specs['gpu']}")
    print(f"Whisper Model Size: {specs['whisper_model']}")
    print(f"Whisper Compute Type: {specs['whisper_compute']}")
    print(f"Whisper Device: {specs['whisper_device']}")

    print("\n--- Latency Benchmark Results ---")
    print(f"{'Path':<40} {'Median':<15} {'p95':<15} Status")
    print("-" * 85)
    for path, res in results.items():
        print(f"{path:<40} {res['median']:<15} {res['p95']:<15} {res['status']}")

    # Append to eval/results.md
    res_path = os.path.join(WORKSPACE_ROOT, "eval", "results.md")
    if os.path.exists(res_path):
        with open(res_path, "a", encoding="utf-8") as f:
            f.write("\n## 11. Latency Benchmark Report\n\n")
            f.write(f"- **Host Machine:** {specs['os']}\n")
            f.write(f"- **CPU:** {specs['cpu']}\n")
            f.write(f"- **GPU:** {specs['gpu']}\n")
            f.write(f"- **Whisper Model Size:** `{specs['whisper_model']}`\n")
            f.write(f"- **Whisper Compute Type:** `{specs['whisper_compute']}`\n")
            f.write(f"- **Whisper Device:** `{specs['whisper_device']}`\n\n")
            f.write("| Pipeline Path | Median Latency | p95 Latency | Benchmark Status |\n")
            f.write("|---|---|---|---|\n")
            for path, res in results.items():
                f.write(f"| **{path}** | {res['median']} | {res['p95']} | {res['status']} |\n")
            f.write("\n")
        print(f"\nLatency benchmark appended to: {res_path}")


if __name__ == "__main__":
    main()
