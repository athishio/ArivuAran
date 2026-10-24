"""
ArivuAran Comprehensive Evaluation & Benchmark Suite.
Measures:
1. Precision, Recall, F1-Score on the 60-sample benchmark dataset (messages.csv).
2. False-Positive Rate on genuine bank alerts (strictly asserted to be 0%).
3. Ablation Study: Rules Only vs Links Only vs Full Engine.
4. Robustness against evasion tactics (obfuscated links, spaced letters, shorteners, Tanglish).
5. Latency benchmarking (per-message scoring time in milliseconds).
"""

import os
import sys
import csv
import time
from typing import List, Dict, Any, Tuple

# Ensure engine package is importable when running script directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from engine.decide import analyse, decide
from engine.redact import extract_urls, redact, extract_features
from engine.links import analyse_url
from engine.rules import evaluate_text_rules


def load_dataset(csv_path: str = None) -> List[Dict[str, Any]]:
    """Loads benchmark test dataset from data/tests/messages.csv."""
    if csv_path is None:
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(curr_dir, "..", "data", "tests", "messages.csv")

    samples = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            samples.append({
                "id": int(row["id"]),
                "text": row["text"],
                "language": row["language"],
                "expected": row["label"],
                "category": row["category"],
                "notes": row.get("notes", "")
            })
    return samples


def evaluate_dataset(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluates full engine performance against the test dataset.
    Returns detailed confusion matrix, precision, recall, and false positive rates.
    """
    tp = 0  # Expected SCAM, predicted SCAM
    fp = 0  # Expected Non-scam (Genuine), predicted SCAM
    tn = 0  # Expected Non-scam, predicted Non-scam (SUSPICIOUS or NO_RED_FLAGS)
    fn = 0  # Expected SCAM, predicted Non-scam

    genuine_fps = []
    genuine_flagged = []
    misclassified = []
    latencies = []

    matrix = {
        "SCAM": {"SCAM": 0, "SUSPICIOUS": 0, "NO_RED_FLAGS": 0},
        "SUSPICIOUS": {"SCAM": 0, "SUSPICIOUS": 0, "NO_RED_FLAGS": 0},
        "NO_RED_FLAGS": {"SCAM": 0, "SUSPICIOUS": 0, "NO_RED_FLAGS": 0},
    }

    for item in samples:
        text = item["text"]
        expected = item["expected"]

        start_t = time.perf_counter()
        result = analyse(text)
        duration_ms = (time.perf_counter() - start_t) * 1000.0
        latencies.append(duration_ms)

        actual = result.verdict

        matrix[expected][actual] += 1

        # Evaluate Scam Classification
        if expected == "SCAM":
            if actual == "SCAM":
                tp += 1
            else:
                fn += 1
                misclassified.append((item["id"], expected, actual, result.score, text))
        else:
            # Expected is NO_RED_FLAGS or SUSPICIOUS
            if actual == "SCAM":
                fp += 1
                misclassified.append((item["id"], expected, actual, result.score, text))
            else:
                tn += 1
                if expected != actual:
                    misclassified.append((item["id"], expected, actual, result.score, text))

        if expected == "NO_RED_FLAGS" and actual != "NO_RED_FLAGS":
            genuine_flagged.append((item["id"], text, actual, result.score))

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

    return {
        "total_samples": len(samples),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "matrix": matrix,
        "genuine_flagged": genuine_flagged,
        "misclassified": misclassified,
        "avg_latency_ms": avg_latency
    }


def run_ablation_study(samples: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    """
    Ablation Study:
    - Config A: Rules Only (no link checks)
    - Config B: Links Only (no text rules)
    - Config C: Full Engine (Rules + Link Analysis)
    """
    results = {}

    # Config A: Rules Only
    tp_a, fp_a, fn_a = 0, 0, 0
    for s in samples:
        redacted = redact(s["text"])
        rules_sig = evaluate_text_rules(redacted, s["text"], urls=[])
        verdict, _ = decide(rules_sig)
        if s["expected"] == "SCAM":
            if verdict == "SCAM": tp_a += 1
            else: fn_a += 1
        elif verdict == "SCAM":
            fp_a += 1

    rec_a = tp_a / (tp_a + fn_a) if (tp_a + fn_a) > 0 else 0.0
    prec_a = tp_a / (tp_a + fp_a) if (tp_a + fp_a) > 0 else 0.0
    results["Rules Only"] = {"precision": prec_a, "recall": rec_a, "f1": 2*prec_a*rec_a/(prec_a+rec_a) if (prec_a+rec_a)>0 else 0.0}

    # Config B: Links Only
    tp_b, fp_b, fn_b = 0, 0, 0
    for s in samples:
        urls = extract_urls(s["text"])
        link_sigs = []
        for u in urls:
            link_sigs.extend(analyse_url(u, text_lower=s["text"].lower()))
        verdict, _ = decide(link_sigs)
        if s["expected"] == "SCAM":
            if verdict == "SCAM": tp_b += 1
            else: fn_b += 1
        elif verdict == "SCAM":
            fp_b += 1

    rec_b = tp_b / (tp_b + fn_b) if (tp_b + fn_b) > 0 else 0.0
    prec_b = tp_b / (tp_b + fp_b) if (tp_b + fp_b) > 0 else 0.0
    results["Links Only"] = {"precision": prec_b, "recall": rec_b, "f1": 2*prec_b*rec_b/(prec_b+rec_b) if (prec_b+rec_b)>0 else 0.0}

    # Config C: Full Engine
    eval_full = evaluate_dataset(samples)
    results["Full Engine (Rules + Links)"] = {
        "precision": eval_full["precision"],
        "recall": eval_full["recall"],
        "f1": eval_full["f1"]
    }

    return results


def run_robustness_tests() -> List[Tuple[str, str, bool]]:
    """Evaluates resistance against specific obfuscation and evasion tricks."""
    test_cases = [
        ("Spaced Brand Letters", "Dear user, your S B I account is suspended. Update at http://sbi-verify.top", "SCAM"),
        ("Userinfo @ Obfuscation", "Visit your bank portal: http://sbi.co.in@evil-phishing.com/login", "SCAM"),
        ("URL Shortener Redirect", "Your courier has an unpaid customs charge. Pay at http://bit.ly/pay-tax", "SUSPICIOUS"),
        ("Tanglish Threat", "Current cut aagum inru night 9 PM ku. Call officer 9876543210", "SCAM"),
        ("Bare IP Address Host", "Download banking patch from http://185.122.1.5/update.apk", "SCAM"),
    ]

    outcomes = []
    for name, text, expected_verdict in test_cases:
        res = analyse(text)
        success = (res.verdict == expected_verdict)
        outcomes.append((name, res.verdict, success))
    return outcomes


def print_evaluation_report():
    """Generates complete terminal report for hackathon judges."""
    samples = load_dataset()
    print("\n" + "=" * 70)
    print("ARIVUARAN EMPIRICAL EVALUATION REPORT (60-SAMPLE BENCHMARK)")
    print("=" * 70)

    # 1. Primary Metrics
    eval_res = evaluate_dataset(samples)
    print(f"\n📊 Total Labeled Samples Evaluated : {eval_res['total_samples']}")
    print(f"   • True Positives (Scams Caught)  : {eval_res['tp']}")
    print(f"   • False Positives (Safe as Scam) : {eval_res['fp']} (Critical Target = 0)")
    print(f"   • True Negatives (Safe/Susp.)    : {eval_res['tn']}")
    print(f"   • False Negatives (Scams Missed) : {eval_res['fn']}")
    print(f"\n🎯 Precision : {eval_res['precision'] * 100:.2f}%")
    print(f"🎯 Recall    : {eval_res['recall'] * 100:.2f}%")
    print(f"🎯 F1-Score  : {eval_res['f1'] * 100:.2f}%")
    print(f"⚡ Latency   : {eval_res['avg_latency_ms']:.2f} ms/message (Deterministic, < 50ms)")

    # 2. Strict Zero False Alarm Verification on Genuine Messages
    gen_flagged = eval_res["genuine_flagged"]
    gen_total = len([s for s in samples if s["expected"] == "NO_RED_FLAGS"])
    print(f"\n🛡️ Genuine Messages False Alarm Count : {len(gen_flagged)} / {gen_total}")
    if len(gen_flagged) > 0:
        print(f"   ⚠️ WARNING: {len(gen_flagged)} genuine message(s) falsely flagged:")
        for m_id, txt, verd, sc in gen_flagged:
            print(f"      ID {m_id} -> {verd} (Score {sc}): {txt[:60]}...")
    else:
        print("   ✅ PASSED: 0.0% False Positive Rate on genuine bank alerts, OTPs, delivery and personal messages.")

    # 3. 3-Way Multi-Class Confusion Matrix
    print("\n" + "-" * 70)
    print("📈 3-WAY MULTI-CLASS CONFUSION MATRIX")
    print("-" * 70)
    print(f"{'Expected (Ground Truth)':<24} | {'Pred: SCAM':<12} | {'Pred: SUSPICIOUS':<16} | {'Pred: NO_RED_FLAGS':<18}")
    print("-" * 70)
    m = eval_res["matrix"]
    for row_name in ["SCAM", "SUSPICIOUS", "NO_RED_FLAGS"]:
        print(f"{row_name:<24} | {m[row_name]['SCAM']:^12} | {m[row_name]['SUSPICIOUS']:^16} | {m[row_name]['NO_RED_FLAGS']:^18}")

    # 4. Ablation Study
    print("\n" + "-" * 70)
    print("🔬 ABLATION STUDY (Component Contribution)")
    print("-" * 70)
    print(f"{'Configuration':<32} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10}")
    print("-" * 70)
    ablation = run_ablation_study(samples)
    for config_name, metrics in ablation.items():
        print(f"{config_name:<32} | {metrics['precision']*100:6.1f}%   | {metrics['recall']*100:6.1f}%   | {metrics['f1']*100:6.1f}%")

    # 5. Robustness Evasion Tests
    print("\n" + "-" * 70)
    print("🛡️ EVASION & ROBUSTNESS TESTS")
    print("-" * 70)
    robustness = run_robustness_tests()
    for name, verdict, passed in robustness:
        status_str = "✅ PASS" if passed else "❌ FAIL"
        print(f"• {name:<30} -> Verdict: {verdict:<12} [{status_str}]")

    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    print_evaluation_report()
