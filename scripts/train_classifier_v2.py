import os
import sys
import csv
import json
import time
import hashlib
import statistics
import joblib
import numpy as np
from collections import Counter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold
import sklearn

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from engine.redact import redact
from engine.decide import analyse

MODELS_DIR = os.path.join(WORKSPACE_ROOT, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

def text_hash(t: str) -> str:
    clean = redact(t).strip().lower()
    return hashlib.sha256(clean.encode('utf-8')).hexdigest()

print("======================================================================")
print("ARIVUARAN CLASSIFIER V2 TRAINING & EVALUATION PIPELINE")
print("======================================================================")

# 1. Load Protected Held-Out Sets (for contamination check & final evaluation)
held_out_even = []
even_hashes = set()
with open(os.path.join(WORKSPACE_ROOT, "data", "messages.csv"), "r", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        mid = r["id"].strip()
        num = int(mid.replace("M", ""))
        if num % 2 == 0:
            h = text_hash(r["text"])
            even_hashes.add(h)
            held_out_even.append({
                "id": mid,
                "text": r["text"],
                "clean_text": redact(r["text"]),
                "language": r["language"].strip(),
                "label": r["label"].strip().lower(),
                "hash": h
            })

audit_genuine = []
audit_hashes = set()
with open(os.path.join(WORKSPACE_ROOT, "data", "audit_genuine.csv"), "r", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        h = text_hash(r["text"])
        audit_hashes.add(h)
        audit_genuine.append({
            "id": r["id"].strip(),
            "text": r["text"],
            "clean_text": redact(r["text"]),
            "language": r.get("language", "unknown").strip(),
            "label": "genuine",
            "hash": h
        })

print(f"Protected held-out sets loaded:")
print(f"  - messages.csv (even split): {len(held_out_even)} rows")
print(f"  - audit_genuine.csv: {len(audit_genuine)} rows")

# 2. Load Training Candidates
sources = [
    ("messages_dev", os.path.join(WORKSPACE_ROOT, "data", "messages.csv"), "dev"),
    ("train_extra", os.path.join(WORKSPACE_ROOT, "data", "train_extra.csv"), "all"),
    ("train_extra2", os.path.join(WORKSPACE_ROOT, "data", "train_extra2.csv"), "all")
]

raw_candidates = []
for src_name, path, mode in sources:
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            if mode == "dev":
                mid = r["id"].strip()
                num = int(mid.replace("M", ""))
                if num % 2 == 0:
                    continue
            raw_candidates.append({
                "source": src_name,
                "id": r["id"].strip(),
                "text": r["text"],
                "language": r.get("language", "unknown").strip(),
                "label": r["label"].strip().lower(),
            })

print(f"\nRaw training candidates loaded: {len(raw_candidates)}")
for src_name, _, _ in sources:
    c_src = [r for r in raw_candidates if r["source"] == src_name]
    print(f"  - {src_name}: {len(c_src)} rows (scam: {sum(1 for r in c_src if r['label'] == 'scam')}, genuine: {sum(1 for r in c_src if r['label'] == 'genuine')})")

# 3. Deduplication and Contamination Filtering
seen_hashes = set()
training_data = []
dropped_internal_dup = 0
dropped_even_match = 0
dropped_audit_match = 0

for r in raw_candidates:
    h = text_hash(r["text"])
    clean = redact(r["text"])
    
    # Check contamination
    if h in even_hashes:
        dropped_even_match += 1
        continue
    if h in audit_hashes:
        dropped_audit_match += 1
        continue
    if h in seen_hashes:
        dropped_internal_dup += 1
        continue
        
    seen_hashes.add(h)
    training_data.append({
        **r,
        "clean_text": clean,
        "hash": h
    })

print(f"\nData Filtering Results:")
print(f"  - Dropped internal exact duplicates: {dropped_internal_dup}")
print(f"  - Dropped matches to messages.csv even split: {dropped_even_match}")
print(f"  - Dropped matches to audit_genuine.csv: {dropped_audit_match}")
print(f"  - Final clean deduplicated training samples: {len(training_data)}")

if len(training_data) < 150:
    print(f"WARNING: TOTAL TRAINING ROWS ({len(training_data)}) IS UNDER 150 ROWS!")
else:
    print(f"TOTAL TRAINING ROWS ({len(training_data)}) EXCEEDS 150 ROWS (VALID DATASET).")

# Class and language balance
src_counts = Counter(r["source"] for r in training_data)
lang_counts = Counter(r["language"] for r in training_data)
label_counts = Counter(r["label"] for r in training_data)
print(f"\nTraining Set Composition:")
print(f"  - By Source: {dict(src_counts)}")
print(f"  - By Language: {dict(lang_counts)}")
print(f"  - By Label: {dict(label_counts)}")

# 4. Cross-Validation on Training Data Only
X_clean = [r["clean_text"] for r in training_data]
y = np.array([1 if r["label"] == "scam" else 0 for r in training_data])
strat_keys = [f"{r['language']}_{r['label']}" for r in training_data]

cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

threshold_candidates = [0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95]
cv_results = {th: {"false_alarms": 0, "scams_caught": 0, "total_scams": 0, "total_genuine": 0, "fa_by_lang": Counter()} for th in threshold_candidates}

for fold, (train_idx, val_idx) in enumerate(cv.split(X_clean, strat_keys)):
    X_tr = [X_clean[i] for i in train_idx]
    y_tr = y[train_idx]
    X_val = [X_clean[i] for i in val_idx]
    y_val = y[val_idx]
    val_meta = [training_data[i] for i in val_idx]
    
    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True)),
        ("clf", LogisticRegression(class_weight="balanced", C=1.0, max_iter=1000, random_state=42))
    ])
    pipe.fit(X_tr, y_tr)
    probs = pipe.predict_proba(X_val)[:, 1]
    
    for th in threshold_candidates:
        preds = (probs >= th).astype(int)
        for p, true_y, meta in zip(preds, y_val, val_meta):
            if true_y == 1:
                cv_results[th]["total_scams"] += 1
                if p == 1:
                    cv_results[th]["scams_caught"] += 1
            else:
                cv_results[th]["total_genuine"] += 1
                if p == 1:
                    cv_results[th]["false_alarms"] += 1
                    cv_results[th]["fa_by_lang"][meta["language"]] += 1

print("\n" + "=" * 70)
print("5-FOLD STRATIFIED CROSS-VALIDATION THRESHOLD SEARCH")
print("=" * 70)
chosen_threshold = 0.50
for th in threshold_candidates:
    res = cv_results[th]
    fa = res["false_alarms"]
    scam_rec = res["scams_caught"] / res["total_scams"] * 100
    print(f"Threshold {th:0.2f} | False Alarms: {fa:>2} / {res['total_genuine']} | Scams Caught: {res['scams_caught']:>3} / {res['total_scams']} ({scam_rec:5.1f}%) | FA by Lang: {dict(res['fa_by_lang'])}")

# Choose lowest threshold with zero false alarms, or highest threshold if none has zero
zero_fa_th = [th for th in threshold_candidates if cv_results[th]["false_alarms"] == 0]
if zero_fa_th:
    chosen_threshold = min(zero_fa_th)
else:
    chosen_threshold = 0.95
print(f"\nChosen Operating Threshold targeting 0 False Alarms: {chosen_threshold:0.2f}")

# 5. Train Final Model on All Deduplicated Training Data
final_pipe = Pipeline([
    ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True)),
    ("clf", LogisticRegression(class_weight="balanced", C=1.0, max_iter=1000, random_state=42))
])
final_pipe.fit(X_clean, y)

# Save models/clf_v2.joblib
joblib_path = os.path.join(MODELS_DIR, "clf_v2.joblib")
joblib.dump(final_pipe, joblib_path)
with open(joblib_path, "rb") as f:
    joblib_sha256 = hashlib.sha256(f.read()).hexdigest()
model_size_bytes = os.path.getsize(joblib_path)

# Save models/clf_v2.json (No message text!)
metadata_v2 = {
    "model_name": "clf_v2",
    "sha256": joblib_sha256,
    "model_type": "TfidfVectorizer(char_wb, 2-5) + LogisticRegression(balanced)",
    "training_rows_by_source": dict(src_counts),
    "total_training_samples": len(training_data),
    "classes": ["genuine", "scam"],
    "class_balance": dict(label_counts),
    "language_balance": dict(lang_counts),
    "random_seed": 42,
    "sklearn_version": sklearn.__version__,
    "threshold": chosen_threshold,
    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "default_enabled": False,
    "notes": "train_extra2.csv is AI-written and may share lexical style with synthetic benchmark test cases."
}
json_path = os.path.join(MODELS_DIR, "clf_v2.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(metadata_v2, f, indent=2)

print(f"\nSaved clf_v2:")
print(f"  - Model: {joblib_path} ({model_size_bytes / 1024:.1f} KB, SHA-256: {joblib_sha256})")
print(f"  - Metadata: {json_path}")

# Load clf_v1 for comparison
clf_v1_pipe = joblib.load(os.path.join(MODELS_DIR, "clf_v1.joblib"))

# 6. Evaluation: Mode A (Rules only), Mode B (Rules + clf_v1), Mode C (Rules + clf_v2)
def evaluate_modes(dataset, name=""):
    # Measure latency on 20 calls
    latencies = []
    
    results = {"A": {"scams": 0, "false_alarms": 0, "total_scam": 0, "total_genuine": 0, "fa_lang": Counter(), "scam_lang": Counter()},
               "B": {"scams": 0, "false_alarms": 0, "total_scam": 0, "total_genuine": 0, "fa_lang": Counter(), "scam_lang": Counter()},
               "C": {"scams": 0, "false_alarms": 0, "total_scam": 0, "total_genuine": 0, "fa_lang": Counter(), "scam_lang": Counter()}}
    
    changed_messages = []
    
    for r in dataset:
        true_label = r["label"]
        lang = r["language"]
        if true_label == "scam":
            for m in ("A", "B", "C"): results[m]["total_scam"] += 1
        else:
            for m in ("A", "B", "C"): results[m]["total_genuine"] += 1
            
        # Mode A: Rules only
        rule_res = analyse(r["text"])
        pred_a = "scam" if rule_res.verdict == "SCAM" else ("suspicious" if rule_res.verdict == "SUSPICIOUS" else "genuine")
        
        # Mode B: Rules + clf_v1 (prob >= 0.5 triggers suspicious if no flags)
        prob_b = clf_v1_pipe.predict_proba([r["clean_text"]])[0, 1]
        if pred_a == "scam":
            pred_b = "scam"
        elif pred_a == "suspicious":
            pred_b = "suspicious"
        elif prob_b >= 0.5:
            pred_b = "suspicious"
        else:
            pred_b = "genuine"
            
        # Mode C: Rules + clf_v2 (prob >= chosen_threshold triggers suspicious if no flags)
        t0 = time.perf_counter()
        prob_c = final_pipe.predict_proba([r["clean_text"]])[0, 1]
        latencies.append((time.perf_counter() - t0) * 1000.0)
        
        if pred_a == "scam":
            pred_c = "scam"
        elif pred_a == "suspicious":
            pred_c = "suspicious"
        elif prob_c >= chosen_threshold:
            pred_c = "suspicious"
        else:
            pred_c = "genuine"
            
        # Update metrics
        for mode_key, pred in [("A", pred_a), ("B", pred_b), ("C", pred_c)]:
            # We count a scam caught if verdict is SCAM or SUSPICIOUS
            is_caught = pred in ("scam", "suspicious")
            if true_label == "scam":
                if is_caught:
                    results[mode_key]["scams"] += 1
                    results[mode_key]["scam_lang"][lang] += 1
            else:
                if is_caught:
                    results[mode_key]["false_alarms"] += 1
                    results[mode_key]["fa_lang"][lang] += 1
                    
        if pred_a != pred_c or pred_b != pred_c:
            changed_messages.append({
                "id": r["id"],
                "true": true_label,
                "lang": lang,
                "mode_a": pred_a,
                "mode_b": pred_b,
                "mode_c": pred_c,
                "prob_v2": prob_c
            })
            
    median_lat = statistics.median(latencies[:20]) if len(latencies) >= 20 else 0.0
    return results, changed_messages, median_lat

print("\n" + "=" * 70)
print("EVALUATION ON HELD-OUT EVEN SPLIT (data/messages.csv)")
print("=" * 70)
res_even, changed_even, lat_even = evaluate_modes(held_out_even, "even_split")
for m, label_m in [("A", "Rules Only"), ("B", "Rules + clf_v1"), ("C", "Rules + clf_v2")]:
    r = res_even[m]
    print(f"Mode {m} ({label_m:<16}): Scams Caught: {r['scams']:>2}/{r['total_scam']} | Genuine False Alarms: {r['false_alarms']:>2}/{r['total_genuine']} (FA by lang: {dict(r['fa_lang'])})")

print(f"\nChanged verdicts on even split (Rules A vs clf_v2 C): {len(changed_even)}")
for c in changed_even:
    print(f"  ID: {c['id']} | True: {c['true']} | Lang: {c['lang']} | Rules: {c['mode_a']} -> clf_v2: {c['mode_c']} (p={c['prob_v2']:.3f})")

print("\n" + "=" * 70)
print("EVALUATION ON AUDIT GENUINE SET (data/audit_genuine.csv)")
print("=" * 70)
res_audit, changed_audit, lat_audit = evaluate_modes(audit_genuine, "audit_genuine")
for m, label_m in [("A", "Rules Only"), ("B", "Rules + clf_v1"), ("C", "Rules + clf_v2")]:
    r = res_audit[m]
    print(f"Mode {m} ({label_m:<16}): Genuine False Alarms: {r['false_alarms']:>2}/{r['total_genuine']} (FA by lang: {dict(r['fa_lang'])})")

print(f"\nChanged verdicts on audit_genuine (Rules A vs clf_v2 C): {len(changed_audit)}")
for c in changed_audit:
    print(f"  ID: {c['id']} | True: {c['true']} | Lang: {c['lang']} | Rules: {c['mode_a']} -> clf_v2: {c['mode_c']} (p={c['prob_v2']:.3f})")

# Latency and Size
print(f"\nInference Latency: median {lat_even:.2f} ms (n=20)")
print(f"Model Size: {model_size_bytes / 1024:.1f} KB")

# 7. Decision Rule Check
# enable clf_v2 only if genuine false alarms are 0 on both sets AND at least one more scam is caught than with rules alone.
fa_even_c = res_even["C"]["false_alarms"]
fa_audit_c = res_audit["C"]["false_alarms"]
scams_caught_a = res_even["A"]["scams"]
scams_caught_c = res_even["C"]["scams"]

print("\n" + "=" * 70)
print("DECISION RULE VERIFICATION")
print("=" * 70)
passed_zero_fa = (fa_even_c == 0 and fa_audit_c == 0)
passed_scam_gain = (scams_caught_c > scams_caught_a)
print(f"Zero False Alarms on both sets?: {passed_zero_fa} (Even FA: {fa_even_c}, Audit FA: {fa_audit_c})")
print(f"Caught more scams than rules alone?: {passed_scam_gain} (Rules: {scams_caught_a}, clf_v2: {scams_caught_c})")

if passed_zero_fa and passed_scam_gain:
    print("DECISION: PASSES DECISION CRITERIA. Awaiting user approval to switch on.")
else:
    print("DECISION: no improvement. USE_CLASSIFIER stays false.")
