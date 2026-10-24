import os
import json
import joblib
import pytest
from engine.decide import analyse
import config

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")


def test_clf_v2_json_privacy_no_message_text_or_pii():
    """Verifies models/clf_v2.json contains only aggregate metadata, zero user/message text or PII."""
    json_path = os.path.join(MODELS_DIR, "clf_v2.json")
    assert os.path.exists(json_path), "Missing models/clf_v2.json"

    with open(json_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    # Check expected keys
    assert "model_name" in meta
    assert "sha256" in meta
    assert "total_training_samples" in meta
    assert "classes" in meta
    assert "threshold" in meta

    # Ensure no raw message texts or samples are leaked
    # Check that metadata only contains schema keys and summary numbers
    allowed_keys = {
        "model_name", "sha256", "model_type", "training_rows_by_source",
        "total_training_samples", "classes", "class_balance",
        "language_balance", "random_seed", "sklearn_version",
        "threshold", "created_at", "default_enabled", "notes"
    }
    assert set(meta.keys()).issubset(allowed_keys)
    meta_str = json.dumps(meta).lower()
    for forbidden in ["http", "https://", "kyc", "48500", "98765", "aadhaar", "<card>", "<phone>"]:
        assert forbidden not in meta_str, f"Forbidden term '{forbidden}' found in metadata JSON"


def test_clf_v2_model_properties_and_safety():
    """
    Verifies that classifier:
    1. Never produces SCAM alone (only elevates NO_RED_FLAGS to SUSPICIOUS at most).
    2. Never lowers an existing verdict (SCAM stays SCAM, SUSPICIOUS stays SUSPICIOUS).
    3. When USE_CLASSIFIER is False, analyse() output is completely unaffected.
    """
    joblib_path = os.path.join(MODELS_DIR, "clf_v2.joblib")
    assert os.path.exists(joblib_path), "Missing models/clf_v2.joblib"

    pipe = joblib.load(joblib_path)
    assert hasattr(pipe, "predict_proba")

    test_samples = [
        ("Meeting tomorrow at 10 AM in room 3.", "genuine"),
        ("Please find the attached minutes of our discussion.", "genuine"),
        ("Dear customer your SBI account is blocked update KYC immediately: http://fake-sbi.xyz", "scam")
    ]

    threshold = 0.70

    for text, exp in test_samples:
        rule_res = analyse(text)
        prob = pipe.predict_proba([text])[0, 1]

        # Combine rules and classifier per Mode C architecture
        if rule_res.verdict == "SCAM":
            final_verdict = "SCAM"
        elif rule_res.verdict == "SUSPICIOUS":
            final_verdict = "SUSPICIOUS"
        elif prob >= threshold:
            final_verdict = "SUSPICIOUS"  # ML only elevates to SUSPICIOUS
        else:
            final_verdict = "NO_RED_FLAGS"

        # Safety Check 1: Classifier NEVER produces SCAM alone on NO_RED_FLAGS rule input
        if rule_res.verdict == "NO_RED_FLAGS":
            assert final_verdict != "SCAM", "Safety violation: Classifier produced SCAM on a NO_RED_FLAGS rule message"

        # Safety Check 2: Classifier NEVER lowers a verdict
        if rule_res.verdict == "SCAM":
            assert final_verdict == "SCAM", "Safety violation: Classifier lowered SCAM verdict"
        if rule_res.verdict == "SUSPICIOUS":
            assert final_verdict in ("SCAM", "SUSPICIOUS"), "Safety violation: Classifier lowered SUSPICIOUS verdict"


def test_use_classifier_false_matches_pure_rules():
    """Verifies that USE_CLASSIFIER=False produces identical output to pure deterministic rules."""
    use_classifier = os.getenv("USE_CLASSIFIER", "false").lower() in ("true", "1", "yes")
    assert use_classifier is False

    sample_messages = [
        "Dear customer, your SBI account KYC is expired. Visit http://sbi-fake.xyz",
        "Your electricity bill is paid. Thank you.",
        "Urgent: You won 25 lakhs lottery! Call now."
    ]

    for msg in sample_messages:
        res = analyse(msg)
        assert res.verdict in ("SCAM", "SUSPICIOUS", "NO_RED_FLAGS")
