"""
eval/run_eval.py - Evaluation harness for Arivaran scam detection.
Evaluates deterministic verdict engine on held-out test split and full dataset.
Includes:
- Dev vs Test category & language distribution tables
- Confusion matrix and metrics (FPR, recall, precision, strict recall)
- Ablation study (Config A vs B vs C)
- Language and category breakdowns
- Wrong predictions on held-out test split AND dev split
- Signal x Language coverage matrix
Outputs results to eval/results.md.
"""

import os
import sys
import csv
from typing import List, Dict, Any, Tuple
from collections import Counter

# Add workspace root to sys.path
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from engine import analyze


def load_dataset(csv_path: str) -> List[Dict[str, Any]]:
    """Loads messages.csv with UTF-8 encoding."""
    messages = []
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            msg_id = row["id"].strip()
            num_part = int(msg_id.replace("M", ""))
            split = "dev" if (num_part % 2 != 0) else "test"
            messages.append({
                "id": msg_id,
                "num": num_part,
                "split": split,
                "text": row["text"],
                "language": row["language"].strip().lower(),
                "label": row["label"].strip().lower(),
                "category": row["category"].strip().lower(),
                "notes": row.get("notes", "").strip()
            })
    return messages


def compute_metrics(
    samples: List[Dict[str, Any]],
    predictions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Computes confusion matrix, false-positive rate, recall, precision, and strict recall.
    flagged = verdict in {'SCAM', 'SUSPICIOUS'}
    """
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


def compute_distribution(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Computes category and language counts across dev and test splits."""
    dev_samples = [s for s in samples if s["split"] == "dev"]
    test_samples = [s for s in samples if s["split"] == "test"]

    dev_cats = Counter(s["category"] for s in dev_samples)
    test_cats = Counter(s["category"] for s in test_samples)
    all_cats = sorted(list(set(dev_cats.keys()) | set(test_cats.keys())))

    cat_rows = []
    for c in all_cats:
        d_cnt = dev_cats.get(c, 0)
        t_cnt = test_cats.get(c, 0)
        cat_rows.append({"category": c, "dev": d_cnt, "test": t_cnt, "total": d_cnt + t_cnt})

    dev_langs = Counter(s["language"] for s in dev_samples)
    test_langs = Counter(s["language"] for s in test_samples)
    all_langs = sorted(list(set(dev_langs.keys()) | set(test_langs.keys())))

    lang_rows = []
    for l in all_langs:
        d_cnt = dev_langs.get(l, 0)
        t_cnt = test_langs.get(l, 0)
        lang_rows.append({"language": l, "dev": d_cnt, "test": t_cnt, "total": d_cnt + t_cnt})

    return {"categories": cat_rows, "languages": lang_rows}


def compute_language_breakdown(samples: List[Dict[str, Any]], config: str = "B") -> List[Dict[str, Any]]:
    """Breakdown metrics by language (en, ta, tanglish)."""
    languages = sorted(list({s["language"] for s in samples}))
    breakdown = []
    for lang in languages:
        lang_samples = [s for s in samples if s["language"] == lang]
        preds = [analyze(s["text"], config=config) for s in lang_samples]
        m = compute_metrics(lang_samples, preds)
        breakdown.append({
            "language": lang,
            "total": len(lang_samples),
            "genuine": m["genuine_count"],
            "scams": m["scam_count"],
            "genuine_flagged": m["genuine_flagged"],
            "fpr": m["fpr"],
            "recall": m["recall"],
            "precision": m["precision"],
            "strict_recall": m["strict_recall"]
        })
    return breakdown


def compute_category_breakdown(samples: List[Dict[str, Any]], config: str = "B") -> List[Dict[str, Any]]:
    """Breakdown recall by category for scam messages."""
    scam_samples = [s for s in samples if s["label"] == "scam"]
    categories = sorted(list({s["category"] for s in scam_samples}))
    breakdown = []
    for cat in categories:
        cat_samples = [s for s in scam_samples if s["category"] == cat]
        preds = [analyze(s["text"], config=config) for s in cat_samples]
        m = compute_metrics(cat_samples, preds)
        breakdown.append({
            "category": cat,
            "total": len(cat_samples),
            "flagged": m["scams_flagged"],
            "strict": m["scams_strict"],
            "recall": m["recall"]
        })
    return breakdown


def run_ablation(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Runs ablation on Config A (rules only) and Config B (rules + links)."""
    preds_a = [analyze(s["text"], config="A") for s in samples]
    m_a = compute_metrics(samples, preds_a)

    preds_b = [analyze(s["text"], config="B") for s in samples]
    m_b = compute_metrics(samples, preds_b)

    return {
        "Config A": m_a,
        "Config B": m_b
    }


def get_signal_language_coverage() -> List[Dict[str, str]]:
    """
    Maps signal codes to keyword coverage across English, Tamil, and Tanglish
    based on engine/rules.py and engine/links.py.
    """
    return [
        {"code": "ASK_SENSITIVE", "en": "Yes", "ta": "Yes", "tanglish": "Yes", "detail": "share/send otp, ஓடிபி/பின் பகிரவும், kudunga/anupunga"},
        {"code": "PIN_REQUEST", "en": "Yes", "ta": "Yes", "tanglish": "Yes", "detail": "enter upi pin, பின் உள்ளிடுங்கள், pin podunga"},
        {"code": "FEE_FIRST", "en": "Yes", "ta": "Yes", "tanglish": "Yes", "detail": "processing fee, கட்டணம் செலுத்துங்கள், fee kattunga"},
        {"code": "DIGITAL_ARREST", "en": "Yes", "ta": "Yes", "tanglish": "Yes", "detail": "cyber police video call, டிஜிட்டல் அரெஸ்ட், case irukku arrest"},
        {"code": "KYC_UPDATE", "en": "Yes", "ta": "Yes", "tanglish": "Yes", "detail": "update kyc/pan, கேஒய்சி புதுப்பிக்க, link aagala"},
        {"code": "THREAT", "en": "Yes", "ta": "Yes", "tanglish": "Yes", "detail": "blocked/suspended, முடக்கப்படும்/துண்டிக்கப்படும், block aagum/cut aagum"},
        {"code": "URGENCY", "en": "Yes", "ta": "Yes", "tanglish": "Yes", "detail": "immediately/urgent, உடனடியாக/உடனே, udane/inru night"},
        {"code": "PRIZE", "en": "Yes", "ta": "Yes", "tanglish": "Yes", "detail": "you won/lottery/kbc, பரிசு வென்றுள்ளீர்கள்/லக்கி டிரா, prize jeichirukeenga"},
        {"code": "AUTHORITY", "en": "Yes", "ta": "Yes", "tanglish": "Yes", "detail": "cbi/police/customs/trai, சைபர் கிரைம்/சிபிஐ/காவல்துறை, police officer pesuren"},
        {"code": "REMOTE_ACCESS", "en": "Yes", "ta": "Yes", "tanglish": "Yes", "detail": "anydesk/teamviewer/.apk, செயலியை பதிவிறக்கம், anydesk install"},
        {"code": "PAYMENT_PUSH", "en": "Yes", "ta": "Yes", "tanglish": "Yes", "detail": "collect request/enter upi pin, முன்பணம்/கட்டணம், gpay seyyavum"},
        {"code": "JOB_TASK", "en": "Yes", "ta": "Yes", "tanglish": "Yes", "detail": "work from home/like youtube, பகுதிநேர வேலை, youtube like pannina"},
        {"code": "INVEST", "en": "Yes", "ta": "Yes", "tanglish": "Yes", "detail": "guaranteed returns/double money, முதலீடு செய்து இரட்டிப்பு, double profit guaranteed"},
        {"code": "CALLBACK", "en": "Yes", "ta": "Yes", "tanglish": "Yes", "detail": "call this number, தொடர்பு கொள்ளவும், number ku call pannunga"},
        {"code": "LOOKALIKE", "en": "N/A", "ta": "N/A", "tanglish": "N/A", "detail": "URL analysis (Domain matching, brand names)"},
        {"code": "SHORTENER", "en": "N/A", "ta": "N/A", "tanglish": "N/A", "detail": "URL analysis (bit.ly, t.co, tinyurl, etc.)"},
        {"code": "IP_HOST", "en": "N/A", "ta": "N/A", "tanglish": "N/A", "detail": "URL analysis (Raw IPv4 address host)"},
        {"code": "USERINFO", "en": "N/A", "ta": "N/A", "tanglish": "N/A", "detail": "URL analysis (@ symbol in authority netloc)"},
        {"code": "PUNYCODE", "en": "N/A", "ta": "N/A", "tanglish": "N/A", "detail": "URL analysis (IDN xn-- homograph spoofing)"},
        {"code": "OTP_DELIVERY", "en": "Yes", "ta": "Yes", "tanglish": "No", "detail": "Mitigating: is your otp + warning, ரகசிய otp"},
        {"code": "TXN_ALERT", "en": "Yes", "ta": "Yes", "tanglish": "No", "detail": "Mitigating: debited/credited Rs, வரவு/பற்று"},
        {"code": "DELIVERY_ALERT", "en": "Yes", "ta": "Yes", "tanglish": "No", "detail": "Mitigating: out for delivery/order #, டெலிவரி/பார்சல்"}
    ]


def generate_markdown_report(
    test_metrics: Dict[str, Any],
    dev_metrics: Dict[str, Any],
    all_metrics: Dict[str, Any],
    ablation_test: Dict[str, Any],
    lang_test: List[Dict[str, Any]],
    cat_test: List[Dict[str, Any]],
    dist: Dict[str, Any],
    sig_coverage: List[Dict[str, str]]
) -> str:
    """Formats all evaluation tables into comprehensive markdown format."""
    lines = []
    lines.append("# Evaluation Results for Arivaran Scam Detection")
    lines.append("")
    lines.append("## 1. Headline Metrics (Held-Out Test Set: Even IDs)")
    lines.append("")
    lines.append(f"- **Test Set Size:** {test_metrics['scam_count'] + test_metrics['genuine_count']} messages ({test_metrics['scam_count']} scams, {test_metrics['genuine_count']} genuine)")
    lines.append(f"- **False-Positive Rate on Genuine:** {test_metrics['genuine_flagged']} of {test_metrics['genuine_count']} ({test_metrics['fpr'] * 100:.1f}%)")
    lines.append(f"- **Recall (Scams Caught):** {test_metrics['scams_flagged']} of {test_metrics['scam_count']} ({test_metrics['recall'] * 100:.1f}%)")
    lines.append(f"- **Precision:** {test_metrics['precision'] * 100:.1f}%")
    lines.append(f"- **Strict Recall (Decisive SCAM verdict):** {test_metrics['scams_strict']} of {test_metrics['scam_count']} ({test_metrics['strict_recall'] * 100:.1f}%)")
    lines.append("")
    lines.append("### Full Dataset Metrics (All 66 Messages, includes tuning data)")
    lines.append(f"- **Total Messages:** {all_metrics['scam_count'] + all_metrics['genuine_count']}")
    lines.append(f"- **Genuine Flagged:** {all_metrics['genuine_flagged']} of {all_metrics['genuine_count']} (FPR {all_metrics['fpr'] * 100:.1f}%)")
    lines.append(f"- **Scams Flagged:** {all_metrics['scams_flagged']} of {all_metrics['scam_count']} (Recall {all_metrics['recall'] * 100:.1f}%)")
    lines.append(f"- **Precision:** {all_metrics['precision'] * 100:.1f}%")
    lines.append(f"- **Strict Recall:** {all_metrics['scams_strict']} of {all_metrics['scam_count']} ({all_metrics['strict_recall'] * 100:.1f}%)")
    lines.append("")

    lines.append("## 2. Confusion Matrix (Held-Out Test Set)")
    lines.append("")
    lines.append("| True Label | Pred: SCAM | Pred: SUSPICIOUS | Pred: NO_RED_FLAGS | Total |")
    lines.append("|---|---|---|---|---|")
    mat = test_metrics["matrix"]
    gen_tot = test_metrics["genuine_count"]
    scam_tot = test_metrics["scam_count"]
    lines.append(f"| **genuine** | {mat['genuine']['SCAM']} | {mat['genuine']['SUSPICIOUS']} | {mat['genuine']['NO_RED_FLAGS']} | {gen_tot} |")
    lines.append(f"| **scam** | {mat['scam']['SCAM']} | {mat['scam']['SUSPICIOUS']} | {mat['scam']['NO_RED_FLAGS']} | {scam_tot} |")
    lines.append("")

    lines.append("## 3. Dataset Distribution (Dev vs Test Split)")
    lines.append("")
    lines.append("### Category Distribution")
    lines.append("")
    lines.append("| Category | Dev Split (Odd IDs) | Test Split (Even IDs) | Total Messages |")
    lines.append("|---|---|---|---|")
    for r in dist["categories"]:
        lines.append(f"| **{r['category']}** | {r['dev']} | {r['test']} | {r['total']} |")
    lines.append("")

    lines.append("### Language Distribution")
    lines.append("")
    lines.append("| Language | Dev Split (Odd IDs) | Test Split (Even IDs) | Total Messages |")
    lines.append("|---|---|---|---|")
    for r in dist["languages"]:
        lines.append(f"| **{r['language']}** | {r['dev']} | {r['test']} | {r['total']} |")
    lines.append("")

    lines.append("## 4. Ablation Study (Held-Out Test Set)")
    lines.append("")
    lines.append("| Config | Description | FPR (Genuine Flagged) | Recall (Scams Caught) | Strict Recall |")
    lines.append("|---|---|---|---|---|")
    m_a = ablation_test["Config A"]
    m_b = ablation_test["Config B"]
    lines.append(f"| **A** | Text rules only | {m_a['genuine_flagged']}/{m_a['genuine_count']} ({m_a['fpr']*100:.1f}%) | {m_a['scams_flagged']}/{m_a['scam_count']} ({m_a['recall']*100:.1f}%) | {m_a['scams_strict']}/{m_a['scam_count']} ({m_a['strict_recall']*100:.1f}%) |")
    lines.append(f"| **B** | Rules + Link checks | {m_b['genuine_flagged']}/{m_b['genuine_count']} ({m_b['fpr']*100:.1f}%) | {m_b['scams_flagged']}/{m_b['scam_count']} ({m_b['recall']*100:.1f}%) | {m_b['scams_strict']}/{m_b['scam_count']} ({m_b['strict_recall']*100:.1f}%) |")
    lines.append("| **C** | Rules + Links + Classifier | *classifier planned* | *classifier planned* | *classifier planned* |")
    lines.append("")

    lines.append("## 5. Breakdown by Language (Held-Out Test Set)")
    lines.append("")
    lines.append("| Language | Messages | Genuine Flagged | Scams Caught | Recall | Precision | Strict Recall |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in lang_test:
        lines.append(f"| **{r['language']}** | {r['total']} | {r['genuine_flagged']}/{r['genuine']} ({r['fpr']*100:.1f}%) | {r['recall']*r['scams']:.0f}/{r['scams']} | {r['recall']*100:.1f}% | {r['precision']*100:.1f}% | {r['strict_recall']*100:.1f}% |")
    lines.append("")

    lines.append("## 6. Breakdown by Category (Held-Out Test Set)")
    lines.append("")
    lines.append("| Scam Category | Samples | Flagged | Strict SCAM | Recall |")
    lines.append("|---|---|---|---|---|")
    for r in cat_test:
        lines.append(f"| **{r['category']}** | {r['total']} | {r['flagged']}/{r['total']} | {r['strict']}/{r['total']} | {r['recall']*100:.1f}% |")
    lines.append("")

    lines.append("## 7. Wrong Predictions (Held-Out Test Set: Even IDs)")
    lines.append("")
    test_wrongs = test_metrics["wrong_predictions"]
    if not test_wrongs:
        lines.append("*None! All test set messages classified correctly.*")
    else:
        lines.append("| ID | Expected | Predicted | Signals Fired | Text |")
        lines.append("|---|---|---|---|---|")
        for w in test_wrongs:
            sig_str = ", ".join(w["signals"]) if w["signals"] else "None"
            safe_text = w["text"].replace("|", "\\|")
            lines.append(f"| {w['id']} | {w['expected']} | {w['predicted']} | {sig_str} | {safe_text} |")
    lines.append("")

    lines.append("## 8. Wrong Predictions (Dev Split: Odd IDs)")
    lines.append("")
    dev_wrongs = dev_metrics["wrong_predictions"]
    if not dev_wrongs:
        lines.append("*None! All dev set messages classified correctly.*")
    else:
        lines.append("| ID | Expected | Predicted | Signals Fired | Text |")
        lines.append("|---|---|---|---|---|")
        for w in dev_wrongs:
            sig_str = ", ".join(w["signals"]) if w["signals"] else "None"
            safe_text = w["text"].replace("|", "\\|")
            lines.append(f"| {w['id']} | {w['expected']} | {w['predicted']} | {sig_str} | {safe_text} |")
    lines.append("")

    lines.append("## 9. Signal x Language Keyword Coverage Table")
    lines.append("")
    lines.append("| Signal Code | English (en) | Tamil (ta) | Tanglish (tanglish) | Representative Patterns |")
    lines.append("|---|---|---|---|---|")
    for s in sig_coverage:
        lines.append(f"| **{s['code']}** | {s['en']} | {s['ta']} | {s['tanglish']} | {s['detail']} |")
    lines.append("")

    return "\n".join(lines)


def main():
    csv_path = os.path.join(WORKSPACE_ROOT, "data", "messages.csv")
    if not os.path.exists(csv_path):
        print(f"ERROR: Dataset file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)

    samples = load_dataset(csv_path)
    test_samples = [s for s in samples if s["split"] == "test"]
    dev_samples = [s for s in samples if s["split"] == "dev"]

    print(f"Loaded {len(samples)} messages ({len(dev_samples)} dev, {len(test_samples)} test)")

    # Run predictions on test split
    preds_test = [analyze(s["text"], config="B") for s in test_samples]
    test_metrics = compute_metrics(test_samples, preds_test)

    # Run predictions on dev split
    preds_dev = [analyze(s["text"], config="B") for s in dev_samples]
    dev_metrics = compute_metrics(dev_samples, preds_dev)

    # Run predictions on all data
    preds_all = [analyze(s["text"], config="B") for s in samples]
    all_metrics = compute_metrics(samples, preds_all)

    # Dataset distribution
    dist = compute_distribution(samples)

    # Ablation
    ablation_test = run_ablation(test_samples)

    # Breakdowns
    lang_test = compute_language_breakdown(test_samples, config="B")
    cat_test = compute_category_breakdown(test_samples, config="B")

    # Signal x language coverage
    sig_coverage = get_signal_language_coverage()

    report = generate_markdown_report(
        test_metrics=test_metrics,
        dev_metrics=dev_metrics,
        all_metrics=all_metrics,
        ablation_test=ablation_test,
        lang_test=lang_test,
        cat_test=cat_test,
        dist=dist,
        sig_coverage=sig_coverage
    )

    out_path = os.path.join(WORKSPACE_ROOT, "eval", "results.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"Evaluation report written to: {out_path}")


if __name__ == "__main__":
    main()
