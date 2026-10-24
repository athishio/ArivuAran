"""
scripts/train_classifier.py - Trains optional TF-IDF + LogisticRegression classifier.
Trains ONLY on dev split of messages.csv (odd IDs) and data/train_extra.csv.
Held-out test split (even IDs of messages.csv) and blind_v1.csv are strictly excluded from training.
Saves model to models/clf_v1.joblib and models/clf_v1.json.
"""

import os
import sys
import csv
import json
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

MODELS_DIR = os.path.join(WORKSPACE_ROOT, "models")
os.makedirs(MODELS_DIR, exist_ok=True)


def load_training_data():
    texts = []
    labels = []  # 1 for scam, 0 for genuine

    # 1. messages.csv (Dev split ONLY: odd IDs)
    messages_path = os.path.join(WORKSPACE_ROOT, "data", "messages.csv")
    with open(messages_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            mid = row["id"].strip()
            num = int(mid.replace("M", ""))
            if num % 2 != 0:  # Dev split
                texts.append(row["text"])
                labels.append(1 if row["label"].strip().lower() == "scam" else 0)

    print(f"Loaded {len(texts)} dev messages from messages.csv (scam: {sum(labels)}, genuine: {len(labels)-sum(labels)})")

    # 2. train_extra.csv
    extra_path = os.path.join(WORKSPACE_ROOT, "data", "train_extra.csv")
    extra_count = 0
    if os.path.exists(extra_path):
        with open(extra_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                texts.append(row["text"])
                labels.append(1 if row["label"].strip().lower() == "scam" else 0)
                extra_count += 1
        print(f"Loaded {extra_count} messages from train_extra.csv")

    total_train = len(texts)
    print(f"Total training set size: {total_train} (WARNING: Under 150 rows: {total_train < 150})")
    return texts, labels


def train_and_save():
    texts, labels = load_training_data()

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 5),
            min_df=2,
            sublinear_tf=True
        )),
        ("clf", LogisticRegression(
            class_weight="balanced",
            C=1.0,
            max_iter=1000,
            random_state=42
        ))
    ])

    pipeline.fit(texts, labels)

    # Save joblib model
    joblib_path = os.path.join(MODELS_DIR, "clf_v1.joblib")
    joblib.dump(pipeline, joblib_path)
    print(f"Saved model pipeline to {joblib_path}")

    # Metadata
    metadata = {
        "model_type": "TfidfVectorizer(char_wb, 2-5) + LogisticRegression(balanced)",
        "training_samples": len(texts),
        "classes": ["genuine", "scam"],
        "class_balance": {
            "scam": sum(labels),
            "genuine": len(labels) - sum(labels)
        },
        "default_enabled": False
    }

    json_path = os.path.join(MODELS_DIR, "clf_v1.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"Saved model metadata to {json_path}")

    return pipeline


if __name__ == "__main__":
    train_and_save()
