"""
Unit Test Suite for ArivuAran Detection Engine (Step 1 & Step 2).
Verifies:
1. Fake KYC SMS scores SCAM.
2. Genuine OTP with security warning is NOT flagged (NO_RED_FLAGS).
3. 'Rs.500' is NOT treated as a domain name.
4. PII Redaction correctly masks cards, Aadhaar, PAN, phones, and accounts without corrupting URLs.
5. Tamil keywords and combining vowel marks behave properly without \b regex traps.
"""

import os
import sys
import pytest

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from engine.redact import redact, extract_urls, extract_features
from engine.links import analyse_url, Signal
from engine.rules import evaluate_text_rules
from engine.decide import decide, analyse, AnalysisResult


# =====================================================================
# CORE SPECIFICATION TESTS
# =====================================================================

def test_fake_kyc_sms_scores_scam():
    """
    Test case requested by user:
    'Dear customer, your SBI account will be blocked today. Update KYC immediately: http://sbi-kyc-verify.xyz'
    Must score SCAM.
    """
    sms = "Dear customer, your SBI account will be blocked today. Update KYC immediately: http://sbi-kyc-verify.xyz"
    result = analyse(sms)

    assert result.verdict == "SCAM"
    assert result.score >= 5
    codes = {s.code for s in result.signals}

    # Verify fired signals
    assert "LOOKALIKE" in codes or "RISKY_TLD" in codes
    assert "KYC_UPDATE" in codes
    assert "THREAT" in codes
    assert "URGENCY" in codes

    # Verify Tamil explanations generated
    assert len(result.reasons_ta) > 0
    assert "இணைப்பைத் திறக்க வேண்டாம்" in result.next_step_ta


def test_genuine_otp_is_not_flagged():
    """
    Test case requested by user:
    '123456 is your OTP for login. Do not share it with anyone.'
    Must NOT be flagged (Verdict = NO_RED_FLAGS).
    """
    sms = "123456 is your OTP for login. Do not share it with anyone."
    result = analyse(sms)

    assert result.verdict == "NO_RED_FLAGS"
    assert result.score <= 0
    codes = {s.code for s in result.signals}
    # ASK_SENSITIVE must NOT fire because warning was stripped
    assert "ASK_SENSITIVE" not in codes
    # OTP_DELIVERY mitigating signal fires
    assert "OTP_DELIVERY" in codes


def test_currency_rs_500_not_treated_as_domain():
    """
    Test case requested by user:
    'Rs.500 debited from your a/c' must NOT treat 'Rs.500' as a domain.
    """
    text = "Dear customer, Rs.500 debited from your a/c ending 1234."
    urls = extract_urls(text)
    assert len(urls) == 0, f"Expected 0 URLs, but found: {urls}"

    # Also test analyse_url directly on 'Rs.500'
    signals = analyse_url("Rs.500")
    assert len(signals) == 0

    result = analyse(text)
    assert result.verdict == "NO_RED_FLAGS"


# =====================================================================
# PII REDACTION TESTS
# =====================================================================

def test_pii_redaction():
    """Verifies sensitive data is redacted while protecting URLs."""
    raw = (
        "My Aadhaar is 4532 8912 3456, PAN is ABCDE1234F, phone is +91 9840123456, "
        "UPI is testuser@oksbi, card is 4111 2222 3333 4444. "
        "Check details at https://sbi.co.in/login"
    )
    redacted = redact(raw)

    # Sensitive values must be replaced
    assert "4532 8912 3456" not in redacted
    assert "<AADHAAR>" in redacted
    assert "ABCDE1234F" not in redacted
    assert "<PAN>" in redacted
    assert "9840123456" not in redacted
    assert "<PHONE>" in redacted
    assert "testuser@oksbi" not in redacted
    assert "<UPI>" in redacted
    assert "4111 2222 3333 4444" not in redacted
    assert "<CARD>" in redacted

    # Legitimate URL must be preserved intact
    assert "https://sbi.co.in/login" in redacted


# =====================================================================
# TAMIL PHRASING & SCRIPT TESTS
# =====================================================================

def test_tamil_threat_and_urgency():
    """Verifies Tamil keywords match cleanly despite combining vowel marks."""
    tamil_scam = (
        "உங்கள் வங்கி கணக்கு இன்றுடன் முடக்கப்படும். "
        "உடனடியாக உங்கள் பான் கார்டு மற்றும் OTP விவரங்களை புதுப்பிக்கவும்: http://sbi-kyc.top"
    )
    result = analyse(tamil_scam)
    assert result.verdict == "SCAM"
    codes = {s.code for s in result.signals}
    assert "THREAT" in codes
    assert "URGENCY" in codes
    assert "KYC_UPDATE" in codes
    assert "LOOKALIKE" in codes


def test_tamil_genuine_warning_not_flagged():
    """Verifies Tamil genuine security advisory doesn't trigger ASK_SENSITIVE."""
    tamil_genuine = "வங்கி எச்சரிக்கை: உங்கள் OTP எண்ணை யாருடனும் பகிர வேண்டாம். எஸ்பிஐ வங்கி."
    result = analyse(tamil_genuine)
    assert result.verdict == "NO_RED_FLAGS"
    codes = {s.code for s in result.signals}
    assert "ASK_SENSITIVE" not in codes


# =====================================================================
# LINK ANALYSIS TESTS
# =====================================================================

def test_raw_ip_and_punycode():
    """Verifies raw IP hosts and Punycode spoofing are flagged."""
    ip_url = "http://192.168.1.1/app.apk"
    ip_sigs = analyse_url(ip_url)
    assert any(s.code == "IP_HOST" for s in ip_sigs)

    puny_url = "http://xn--sbi-9ha.com/login"
    puny_sigs = analyse_url(puny_url)
    assert any(s.code == "PUNYCODE" for s in puny_sigs)


def test_official_domains_not_lookalike():
    """Verifies official bank domains like sbi.co.in or tneb.gov.in are never marked LOOKALIKE."""
    sigs = analyse_url("https://sbi.co.in/portal", text_lower="sbi notice")
    assert not any(s.code == "LOOKALIKE" for s in sigs)
    assert not any(s.code == "BRAND_MISMATCH" for s in sigs)
