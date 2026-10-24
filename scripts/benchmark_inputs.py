"""
Phase 2.1 Real Input Benchmarks for ArivuAran.
Runs OCR on data/images/ and STT on data/audio/.
Measures 3 runs per file with exact latency timings and raw outputs.
Checks for human-authored manifest.csv (never creates or edits one).
"""

import os
import sys
import time
import shutil
import tempfile
from typing import Dict, List, Optional
from PIL import Image
import pytesseract

sys.stdout.reconfigure(encoding="utf-8")

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import config
import speech

AUDIO_DIR = os.path.join(WORKSPACE_ROOT, "data", "audio")
IMAGES_DIR = os.path.join(WORKSPACE_ROOT, "data", "images")


def benchmark_images():
    manifest_path = os.path.join(IMAGES_DIR, "manifest.csv")
    has_manifest = os.path.exists(manifest_path)
    manifest_data = {}
    if has_manifest:
        import csv
        with open(manifest_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                manifest_data[row.get("filename", "")] = row.get("ground_truth", "")

    print("\n" + "=" * 80)
    print("PHASE 2.1: OCR BENCHMARK ON REAL SCREENSHOTS (Tesseract tam+eng)")
    print("=" * 80)
    print(f"Manifest status: {'FOUND' if has_manifest else 'NOT FOUND (Reporting raw outputs with NO ACCURACY CLAIM)'}")

    image_files = sorted([f for f in os.listdir(IMAGES_DIR) if f.lower().endswith((".jpeg", ".jpg", ".png"))])

    ocr_results = {}
    for img_name in image_files:
        img_path = os.path.join(IMAGES_DIR, img_name)
        timings = []
        raw_output = ""
        for run_idx in range(1, 4):
            t0 = time.perf_counter()
            img = Image.open(img_path)
            raw_output = pytesseract.image_to_string(img, lang="tam+eng")
            t1 = time.perf_counter()
            timings.append((t1 - t0) * 1000.0)

        ocr_results[img_name] = {
            "timings_ms": timings,
            "avg_ms": sum(timings) / len(timings),
            "output": raw_output
        }

        print(f"\n--- File: {img_name} ---")
        print(f"Timings (3 runs): {timings[0]:.1f}ms, {timings[1]:.1f}ms, {timings[2]:.1f}ms | Avg: {sum(timings)/len(timings):.1f}ms")
        print("Raw OCR Output:")
        print("-" * 40)
        print(raw_output.strip() if raw_output.strip() else "[NO TEXT EXTRACTED]")
        print("-" * 40)
        if has_manifest:
            gt = manifest_data.get(img_name, "[NOT IN MANIFEST]")
            print(f"Ground Truth: {gt}")

    return ocr_results


def benchmark_audio():
    manifest_path = os.path.join(AUDIO_DIR, "manifest.csv")
    has_manifest = os.path.exists(manifest_path)
    manifest_data = {}
    if has_manifest:
        import csv
        with open(manifest_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                manifest_data[row.get("filename", "")] = row.get("ground_truth", "")

    print("\n" + "=" * 80)
    print("PHASE 2.1: STT BENCHMARK ON REAL AUDIO (faster-whisper small)")
    print("=" * 80)
    print(f"Manifest status: {'FOUND' if has_manifest else 'NOT FOUND (Reporting raw outputs with NO ACCURACY CLAIM)'}")

    audio_files = sorted([f for f in os.listdir(AUDIO_DIR) if f.lower().endswith((".ogg", ".wav", ".mp3"))])

    stt_results = {}
    for aud_name in audio_files:
        src_path = os.path.join(AUDIO_DIR, aud_name)
        timings = []
        raw_output = ""
        for run_idx in range(1, 4):
            # Safe temporary copy to protect source audio from deletion
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
                shutil.copyfile(src_path, tmp.name)
                tmp_copy = tmp.name

            t0 = time.perf_counter()
            raw_output = speech.transcribe(tmp_copy, language_hint="ta")
            t1 = time.perf_counter()
            timings.append((t1 - t0) * 1000.0)

        stt_results[aud_name] = {
            "timings_ms": timings,
            "avg_ms": sum(timings) / len(timings),
            "output": raw_output
        }

        print(f"\n--- File: {aud_name} ---")
        print(f"Timings (3 runs): {timings[0]:.1f}ms, {timings[1]:.1f}ms, {timings[2]:.1f}ms | Avg: {sum(timings)/len(timings):.1f}ms")
        print("Raw STT Output:")
        print("-" * 40)
        print(raw_output.strip() if raw_output.strip() else "[NO SPEECH DETECTED]")
        print("-" * 40)
        if has_manifest:
            gt = manifest_data.get(aud_name, "[NOT IN MANIFEST]")
            print(f"Ground Truth: {gt}")

    return stt_results


if __name__ == "__main__":
    ocr_res = benchmark_images()
    stt_res = benchmark_audio()
