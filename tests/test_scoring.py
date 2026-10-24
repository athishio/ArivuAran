"""
Scoring Rule Engine Test Suite.
Evaluates precision against 45+ labeled messages in English, Tamil, and Tanglish.
Strict assertion: No genuine bank alert or OTP is classified as SCAM.
"""

import os
import json
import pytest
from scoring import score_message


def load_samples():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    samples_path = os.path.join(current_dir, "samples.json")
    with open(samples_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_scoring_engine_performance():
    samples = load_samples()
    assert len(samples) >= 45, f"Expected at least 45 test samples, found {len(samples)}"

    # Confusion matrix counters
    # Positive = SCAM, Negative = LIKELY_SAFE / SUSPICIOUS
    tp = 0  # Expected SCAM, Predicted SCAM
    fp = 0  # Expected Genuine, Predicted SCAM
    tn = 0  # Expected Genuine, Predicted LIKELY_SAFE / SUSPICIOUS
    fn = 0  # Expected SCAM, Predicted LIKELY_SAFE

    misclassified = []
    genuine_classified_as_scam = []

    print("\n" + "=" * 65)
    print("ARIVARAN SCAM DETECTION BENCHMARK EVALUATION")
    print("=" * 65)

    for item in samples:
        sample_id = item["id"]
        group = item["group"]
        expected = item["expected_verdict"]
        text = item["text"]

        result = score_message(text)
        actual = result["verdict"]
        score = result["score"]
        fired = result["fired_rules"]

        # Track genuine messages classified as SCAM
        if group == "genuine" and actual == "SCAM":
            genuine_classified_as_scam.append({
                "id": sample_id,
                "text": text,
                "score": score,
                "fired_rules": fired
            })

        # Calculate binary metrics for SCAM classification
        if expected == "SCAM":
            if actual == "SCAM":
                tp += 1
            else:
                fn += 1
                misclassified.append((sample_id, expected, actual, score, fired, text))
        elif expected in ("LIKELY_SAFE", "SUSPICIOUS"):
            if actual == "SCAM":
                fp += 1
                misclassified.append((sample_id, expected, actual, score, fired, text))
            else:
                tn += 1
                if expected != actual:
                    # Minor boundary discrepancy (e.g. LIKELY_SAFE vs SUSPICIOUS)
                    misclassified.append((sample_id, expected, actual, score, fired, text))

    print("\n--- CONFUSION MATRIX (SCAM Detection) ---")
    print(f"True Positives  (Scam correctly flagged SCAM)      : {tp}")
    print(f"False Positives (Genuine mistakenly flagged SCAM)   : {fp}")
    print(f"True Negatives  (Non-scam flagged safe/suspicious)  : {tn}")
    print(f"False Negatives (Scam missed by system)             : {fn}")

    if misclassified:
        print(f"\n--- MISCLASSIFIED MESSAGES ({len(misclassified)}) ---")
        for m_id, exp, act, sc, rules, txt in misclassified:
            safe_txt = txt[:70].encode('ascii', errors='backslashreplace').decode('ascii')
            print(f"ID: {m_id:02d} | Expected: {exp:11s} | Got: {act:11s} | Score: {sc:3d} | Rules: {rules}")
            print(f"    Text: {safe_txt}...\n")

    # STRICT ASSERTION: Genuine bank alerts / OTPs must NEVER be classified as SCAM
    assert len(genuine_classified_as_scam) == 0, (
        f"Critical Failure: {len(genuine_classified_as_scam)} genuine message(s) classified as SCAM:\n"
        f"{genuine_classified_as_scam}"
    )

    # Scams correctly identified
    assert tp >= 15, f"Expected at least 15 true positive scams, got {tp}"
    assert fp == 0, f"Expected zero false positive scams on benchmark, got {fp}"


def test_empty_and_long_text():
    """Verifies edge cases: empty strings and truncation on long texts."""
    empty_result = score_message("")
    assert empty_result["verdict"] == "LIKELY_SAFE"
    assert empty_result["score"] == 0

    long_text = "வணக்கம் " * 2000  # > 5000 chars
    long_result = score_message(long_text)
    assert isinstance(long_result["score"], int)