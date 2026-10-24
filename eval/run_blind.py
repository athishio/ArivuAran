"""
eval/run_blind.py - Blind test runner for Arivaran scam detection.
Evaluates data/blind_v1.csv (when present) using the deterministic engine (Config B).
Reports identical metrics as run_eval.py into a separate "Blind test v1" section in eval/results.md.
"""

import os
import sys
import csv
from typing import List, Dict, Any

# Add workspace root to sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from engine import analyze


def load_blind_dataset(csv_path: str) -> List[Dict[str, Any]]:
    """Loads blind dataset with UTF-8 encoding."""
    messages = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, 1):
            msg_id = row.get("id", f"B{idx:03d}").strip()
            messages.append({
                "id": msg_id,
                "text": row["text"],
                "language": row.get("language", "unknown").strip().lower(),
                "label": row["label"].strip().lower(),
                "category": row.get("category", "unknown").strip().lower(),
                "notes": row.get("notes", "").strip()
            })
    return messages


def compute_metrics(
    samples: List[Dict[str, Any]],
    predictions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Computes confusion matrix, false-positive rate, recall, precision, and strict recall."""
    matrix = {
        "genuine": {"SCAM": 0, "SUSPICIOUS": 0, "NO_RED_FLAGS": 0},
        "scam": {"SCAM": 0, "SUSPICIOUS": 0, "NO_RED_FLAGS": 0}
    }

    scam_count = 0
    genuine_count = 0
    scams_flagged = 0
    scams_strict = 0
    genuine_flagged = 0
    total_flagged = 0

    wrong_predictions = []

    for s, p in zip(samples, predictions):
        true_label = s["label"]
        verdict = p["verdict"]
        matrix[true_label][verdict] += 1

        is_flagged = verdict in ("SCAM", "SUSPICIOUS")
        if is_flagged:
            total_flagged += 1

        if true_label == "scam":
            scam_count += 1
            if is_flagged:
                scams_flagged += 1
            if verdict == "SCAM":
                scams_strict += 1
            if not is_flagged:
                wrong_predictions.append({
                    "id": s["id"],
                    "text": s["text"],
                    "expected": true_label,
                    "predicted": verdict,
                    "signals": p["signals"]
                })
        else: # genuine
            genuine_count += 1
            if is_flagged:
                genuine_flagged += 1
                wrong_predictions.append({
                    "id": s["id"],
                    "text": s["text"],
                    "expected": true_label,
                    "predicted": verdict,
                    "signals": p["signals"]
                })

    fpr = (genuine_flagged / genuine_count) if genuine_count > 0 else 0.0
    recall = (scams_flagged / scam_count) if scam_count > 0 else 0.0
    precision = (scams_flagged / total_flagged) if total_flagged > 0 else 0.0
    strict_recall = (scams_strict / scam_count) if scam_count > 0 else 0.0

    return {
        "matrix": matrix,
        "scam_count": scam_count,
        "genuine_count": genuine_count,
        "total_flagged": total_flagged,
        "scams_flagged": scams_flagged,
        "scams_strict": scams_strict,
        "genuine_flagged": genuine_flagged,
        "fpr": fpr,
        "recall": recall,
        "precision": precision,
        "strict_recall": strict_recall,
        "wrong_predictions": wrong_predictions
    }


def main():
    blind_path = os.path.join(WORKSPACE_ROOT, "data", "blind_v1.csv")
    res_path = os.path.join(WORKSPACE_ROOT, "eval", "results.md")

    if not os.path.exists(blind_path):
        print(f"INFO: Blind test file not present: {blind_path}")
        print("Reporting 'Awaiting data/blind_v1.csv' in results.md.")
        if os.path.exists(res_path):
            with open(res_path, "a", encoding="utf-8") as f:
                f.write("\n## 13. Blind test v1\n\n")
                f.write("*Awaiting `data/blind_v1.csv` (file not yet provided).*\n")
        return

    print(f"Running blind test evaluation on: {blind_path}")
    samples = load_blind_dataset(blind_path)
    preds = [analyze(s["text"], config="B") for s in samples]
    m = compute_metrics(samples, preds)

    # Format report section
    lines = []
    lines.append("\n## 13. Blind test v1\n")
    lines.append(f"- **Total Blind Test Messages:** {len(samples)} ({m['scam_count']} scams, {m['genuine_count']} genuine)")
    lines.append(f"- **False-Positive Rate on Genuine:** {m['genuine_flagged']} of {m['genuine_count']} ({m['fpr']*100:.1f}%)")
    lines.append(f"- **Recall (Scams Caught):** {m['scams_flagged']} of {m['scam_count']} ({m['recall']*100:.1f}%)")
    lines.append(f"- **Precision:** {m['precision']*100:.1f}%")
    lines.append(f"- **Strict Recall:** {m['scams_strict']} of {m['scam_count']} ({m['strict_recall']*100:.1f}%)\n")

    lines.append("### Confusion Matrix (Blind test v1)\n")
    lines.append("| True Label | Pred: SCAM | Pred: SUSPICIOUS | Pred: NO_RED_FLAGS | Total |")
    lines.append("|---|---|---|---|---|")
    mat = m["matrix"]
    lines.append(f"| **genuine** | {mat['genuine']['SCAM']} | {mat['genuine']['SUSPICIOUS']} | {mat['genuine']['NO_RED_FLAGS']} | {m['genuine_count']} |")
    lines.append(f"| **scam** | {mat['scam']['SCAM']} | {mat['scam']['SUSPICIOUS']} | {mat['scam']['NO_RED_FLAGS']} | {m['scam_count']} |\n")

    lines.append("### Wrong Predictions (Blind test v1)\n")
    wrongs = m["wrong_predictions"]
    if not wrongs:
        lines.append("*None! All blind test messages classified correctly.*\n")
    else:
        lines.append("| ID | Expected | Predicted | Signals Fired | Text |")
        lines.append("|---|---|---|---|---|")
        for w in wrongs:
            sig_str = ", ".join(w["signals"]) if w["signals"] else "None"
            safe_text = w["text"].replace("|", "\\|")
            lines.append(f"| {w['id']} | {w['expected']} | {w['predicted']} | {sig_str} | {safe_text} |")
        lines.append("")

    report_text = "\n".join(lines)
    if os.path.exists(res_path):
        with open(res_path, "a", encoding="utf-8") as f:
            f.write(report_text)
    print(f"Blind test evaluation results appended to: {res_path}")


if __name__ == "__main__":
    main()
