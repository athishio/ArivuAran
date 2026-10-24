"""
Deterministic rule engine for scoring scam likelihood in Tamil/English/Tanglish text.
Pure functions, runs in under 50ms, no external LLM or network calls.
"""

import re
import unicodedata
from urllib.parse import urlparse
from typing import Dict, Any, List

from rules import (
    RULES,
    ALLOWLISTED_DOMAINS,
    ALLOWLISTED_SMS_HEADERS,
)

# Configurable Verdict Thresholds
SCAM_THRESHOLD = 60
SUSPICIOUS_THRESHOLD = 30

# Tamil to ASCII digit mapping
TAMIL_DIGITS_TRANS = str.maketrans("௦௧௨௩௪௫௬௭௮௯", "0123456789")

# Compiled extraction regexes
URL_REGEX = re.compile(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+", re.IGNORECASE)
PHONE_REGEX = re.compile(r"(?:\+91[\-\s]?)?[6-9]\d{9}\b")
UPI_REGEX = re.compile(r"[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}")
AMOUNT_REGEX = re.compile(r"(?:rs\.?|inr|₹|ரூ\.?|ரூபாய்)\s*[\d,]+(?:\.\d+)?|[\d,]+(?:\.\d+)?\s*(?:rs|inr|₹|ரூபாய்|ரூ)", re.IGNORECASE)
OTP_CODE_REGEX = re.compile(r"\b\d{4,8}\b")


def normalize_text(text: str) -> str:
    """
    Normalizes text for consistent analysis:
    - Truncates to 5000 chars
    - Unicode NFC normalization
    - Removes zero-width characters
    - Converts Tamil numerals to ASCII digits
    - Collapses whitespace
    """
    if not text:
        return ""

    # Truncate to 5000 chars
    text = text[:5000]

    # Unicode NFC normalization
    text = unicodedata.normalize("NFC", text)

    # Strip zero-width characters (ZWSP, ZWNJ, ZWJ, BOM, etc.)
    text = re.sub(r"[\u200B-\u200D\uFEFF]", "", text)

    # Convert Tamil numerals to ASCII digits
    text = text.translate(TAMIL_DIGITS_TRANS)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def extract_entities(text: str) -> Dict[str, List[str]]:
    """Extracts URLs, phone numbers, UPI IDs, amounts, and OTP candidate codes."""
    urls = URL_REGEX.findall(text)
    phones = PHONE_REGEX.findall(text)
    upis = UPI_REGEX.findall(text)
    amounts = AMOUNT_REGEX.findall(text)
    otps = OTP_CODE_REGEX.findall(text)

    return {
        "urls": urls,
        "phones": phones,
        "upis": upis,
        "amounts": amounts,
        "otps": otps,
    }


def is_domain_allowlisted(domain: str) -> bool:
    """Matches exact domain or true suffix (prevents sbi.co.in.evil.com)."""
    if not domain:
        return False
    domain = domain.lower()
    for allowed in ALLOWLISTED_DOMAINS:
        if domain == allowed or domain.endswith("." + allowed):
            return True
    return False


def check_allowlist(text: str, extracted_urls: List[str]) -> bool:
    """Checks if sender header or any extracted URL domain matches official allowlists."""
    # Check SMS Sender ID headers like AD-HDFCBK, AX-SBIINB
    for header in ALLOWLISTED_SMS_HEADERS:
        if re.search(rf"\b[A-Z]{{2}}-{header}\b", text, re.IGNORECASE) or header in text:
            return True

    # Check URL domains
    for raw_url in extracted_urls:
        if not raw_url.startswith(("http://", "https://")):
            raw_url = "http://" + raw_url
        try:
            parsed = urlparse(raw_url)
            hostname = parsed.hostname or ""
            if is_domain_allowlisted(hostname):
                return True
        except Exception:
            continue

    return False


def score_message(text: str) -> Dict[str, Any]:
    """
    Scores a message deterministically against scam detection rules.
    Returns:
    {
        "score": int (0-100),
        "verdict": "SCAM" | "SUSPICIOUS" | "LIKELY_SAFE",
        "fired_rules": [rule_id, ...],
        "reasons": [reason_key, ...]
    }
    """
    cleaned_text = normalize_text(text)
    if not cleaned_text:
        return {
            "score": 0,
            "verdict": "LIKELY_SAFE",
            "fired_rules": [],
            "reasons": []
        }

    entities = extract_entities(cleaned_text)
    fired_rules: List[str] = []
    reasons: List[str] = []
    total_points = 0

    # 1. Evaluate Rule Definitions
    for rule in RULES:
        # Check negative patterns first (e.g. "Do not share OTP" warning in legitimate bank SMS)
        if rule.negative_patterns:
            if any(neg.search(cleaned_text) for neg in rule.negative_patterns):
                continue

        # Check positive patterns
        if any(pat.search(cleaned_text) for pat in rule.patterns):
            fired_rules.append(rule.id)
            reasons.append(rule.reason_key)
            total_points += rule.points

    # 2. Allowlist Check
    # If the message source/domain is official, subtract points (never below 0)
    is_allowed = check_allowlist(cleaned_text, entities["urls"])
    if is_allowed:
        # Subtract allowlist deduction (e.g. -45 points)
        total_points = max(0, total_points - 45)
        reasons.append("allowlisted_source")

    # 3. Cap at 100
    final_score = min(100, max(0, total_points))

    # 4. Determine Verdict
    if final_score >= SCAM_THRESHOLD:
        verdict = "SCAM"
    elif final_score >= SUSPICIOUS_THRESHOLD:
        verdict = "SUSPICIOUS"
    else:
        verdict = "LIKELY_SAFE"

    return {
        "score": final_score,
        "verdict": verdict,
        "fired_rules": fired_rules,
        "reasons": reasons
    }