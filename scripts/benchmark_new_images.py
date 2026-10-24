"""
scripts/benchmark_new_images.py
Evaluates the two new screenshots in data/images/ (Ss-5.jpeg and Ss-6.jpeg).
1. OCR (tam+eng) 3 times per file with exact latency timings and script detection.
2. Real pipeline analysis (engine.analyse) printing verdict, scam type, and signals.
3. Compares against manifest if present, else reports NO ACCURACY CLAIM (NOT VERIFIED).
4. Repeats OCR with network disabled.
"""

import os
import sys
import time
import socket
import unicodedata
from PIL import Image
import pytesseract

sys.stdout.reconfigure(encoding="utf-8")

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import config
from engine import analyze, analyse
from engine.redact import normalize_input

NEW_FILES = ["Ss-5.jpeg", "Ss-6.jpeg"]
IMAGES_DIR = os.path.join(WORKSPACE_ROOT, "data", "images")
MANIFEST_PATH = os.path.join(IMAGES_DIR, "manifest.csv")


def is_tamil_script(text: str) -> bool:
    """Returns True if text contains Tamil Unicode block characters (\u0B80-\u0BFF)."""
    return any("\u0B80" <= c <= "\u0BFF" for c in text)


def run_benchmark(offline_mode: bool = False):
    header = "OFFLINE TEST (Internet Off)" if offline_mode else "ONLINE RUN (Real Pipeline)"
    print("\n" + "=" * 80)
    print(f"BENCHMARK: {header}")
    print("=" * 80)

    # Check manifest
    has_manifest = os.path.exists(MANIFEST_PATH)
    manifest_entries = {}
    if has_manifest:
        import csv
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                manifest_entries[row.get("filename", "")] = row

    print(f"Manifest status: {'FOUND' if has_manifest else 'NOT FOUND'}")
    if not has_manifest:
        print(">> NOTICE: No manifest exists for these files -> NO ACCURACY CLAIM (NOT VERIFIED). <<\n")

    results = {}

    for fname in NEW_FILES:
        fpath = os.path.join(IMAGES_DIR, fname)
        if not os.path.exists(fpath):
            print(f"File {fname} not found!")
            continue

        timings = []
        raw_text = ""
        for i in range(1, 4):
            t0 = time.perf_counter()
            img = Image.open(fpath)
            raw_text = pytesseract.image_to_string(img, lang="tam+eng")
            t1 = time.perf_counter()
            timings.append((t1 - t0) * 1000.0)

        # Detect script
        has_tamil = is_tamil_script(raw_text)
        script_desc = "Tamil script (தமிழ்)" if has_tamil else "Latin / English script"

        # Zero-width character inspection
        zw_chars = [f"U+{ord(c):04X}" for c in raw_text if ord(c) in (0x200B, 0x200C, 0x200D, 0x200E, 0x200F, 0x2060, 0xFEFF, 0x00AD)]

        # Zero-width stripping and real pipeline evaluation
        cleaned_text = normalize_input(raw_text)
        analysis_res = analyse(cleaned_text)

        # Scam type determination
        scam_type = "None"
        if analysis_res.signals:
            pos_signals = [s for s in analysis_res.signals if s.points > 0]
            if pos_signals:
                top_sig = max(pos_signals, key=lambda s: s.points)
                scam_type = top_sig.code.lower()

        results[fname] = {
            "timings_ms": timings,
            "median_ms": sorted(timings)[1],
            "script": script_desc,
            "has_tamil": has_tamil,
            "zw_count": len(zw_chars),
            "raw_text": raw_text,
            "verdict": analysis_res.verdict,
            "score": analysis_res.score,
            "scam_type": scam_type,
            "signals": [s.code for s in analysis_res.signals]
        }

        print(f"--- File: {fname} ---")
        print(f"File size: {os.path.getsize(fpath)} bytes")
        print(f"Timings (3 runs): {timings[0]:.1f}ms, {timings[1]:.1f}ms, {timings[2]:.1f}ms | Median: {sorted(timings)[1]:.1f}ms")
        print(f"Script detected: {script_desc}")
        print(f"Zero-width characters stripped: {len(zw_chars)} ({', '.join(set(zw_chars)) if zw_chars else 'None'})")
        print("Raw OCR Output (Exact):")
        print("-" * 50)
        print(raw_text.strip() if raw_text.strip() else "[NO TEXT EXTRACTED]")
        print("-" * 50)
        print(f"Pipeline Verdict : {analysis_res.verdict}")
        print(f"Pipeline Score   : {analysis_res.score}")
        print(f"Scam Type        : {scam_type}")
        print(f"Signal Codes     : {[s.code for s in analysis_res.signals]}")
        if has_manifest and fname in manifest_entries:
            print(f"Manifest Ground Truth: {manifest_entries[fname]}")
        else:
            print("Accuracy Claim   : NOT VERIFIED (No manifest entry)")
        print()

    return results


def run_offline():
    # Block network socket calls to guarantee offline execution
    orig_socket = socket.socket
    def blocked_socket(*args, **kwargs):
        raise OSError("Network disabled for offline verification")

    socket.socket = blocked_socket
    try:
        run_benchmark(offline_mode=True)
    finally:
        socket.socket = orig_socket


if __name__ == "__main__":
    run_benchmark(offline_mode=False)
    run_offline()
