"""
PII Redaction and Structural Feature Extraction for ArivuAran.
Protects sensitive user data (Cards, Aadhaar, Phone, PAN, UPI, Account Numbers)
and extracts structural features prior to scoring.
"""

import re
import unicodedata
from typing import List, Dict, Any, Tuple

# URL extraction pattern matching explicit schemes or domain/path constructs
URL_RE = re.compile(
    r"(?i)\b(?:https?://|www\.)[^\s<>\"']+"
    r"|\b[a-z0-9][a-z0-9\-]{0,62}(?:\.[a-z0-9\-]{2,63})+(?:/[^\s<>\"']*)?"
)

# Currency and numerical pattern guard (prevents 'Rs.500', 're.1', 'no.5' being flagged as URLs)
CURRENCY_OR_NUMBER_GUARD = re.compile(
    r"(?i)^(?:rs|inr|re|no|vol|sec|act|dr|mr|mrs|prof)\.\d+$"
)

# Indian PII detection patterns
PII: List[Tuple[str, re.Pattern]] = [
    ("CARD", re.compile(r"(?<!\d)(?:\d[ -]?){13,16}(?!\d)")),
    ("AADHAAR", re.compile(r"(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)")),
    ("PHONE", re.compile(r"(?<!\d)(?:\+?91[ -]?)?[6-9]\d{9}(?!\d)")),
    ("PAN", re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")),
    ("UPI", re.compile(r"\b[\w.\-]{2,}@[A-Za-z]{2,}\b")),
    ("ACCOUNT", re.compile(r"(?<!\d)\d{9,18}(?!\d)")),
]

# Quick OTP-like number pattern (4-8 standalone digits)
OTP_CANDIDATE_RE = re.compile(r"(?<!\d)\d{4,8}(?!\d)")


def refang_urls(text: str) -> str:
    """Refangs obfuscated/defanged URLs (e.g., hxxp -> http, [.] -> .)."""
    t = re.sub(r"(?i)\bhxxp(s?)://", r"http\1://", text)
    t = re.sub(r"\[\.\]|\(\.\)", ".", t)
    t = re.sub(r"\[:\]|\(:\)", ":", t)
    return t


def collapse_spaced_letters(text: str) -> str:
    """Collapses spaced single letters into words: 'S B I' -> 'SBI', 'K Y C' -> 'KYC'."""
    return re.sub(
        r"(?<![A-Za-z0-9])([A-Za-z](?:\s+[A-Za-z])+)(?![A-Za-z0-9])",
        lambda m: re.sub(r"\s+", "", m.group(0)),
        text
    )


def map_digit_lookalikes(text: str) -> str:
    """Maps common digit lookalikes only inside known keywords (e.g. 0TP -> OTP)."""
    t = re.sub(r"(?i)\b0tp\b", "OTP", text)
    t = re.sub(r"(?i)\b0ne\s*time\s*passw[0o]rd\b", "one time password", t)
    t = re.sub(r"(?i)\bp1n\b", "PIN", t)
    t = re.sub(r"(?i)\bup1\b", "UPI", t)
    t = re.sub(r"(?i)\bky0\b", "KYC", t)
    return t


def normalize_input(text: str) -> str:
    """
    Applies full text normalisation per specification:
    1. Unicode NFKC
    2. Remove zero-width characters (U+200B, U+200C, U+200D, U+FEFF)
    3. Refang obfuscated links (hxxp -> http, [.] -> .)
    4. Collapse spaced single letters ('S B I' -> 'SBI')
    5. Map common digit lookalikes inside known keywords ('0TP' -> 'OTP')
    6. Normalize whitespace
    """
    if not text:
        return ""
    text = text[:2000]
    # Unicode NFKC
    text = unicodedata.normalize("NFKC", text)
    # Remove zero-width, joiners, bidi formatting, and invisible characters (U+200B-U+200F, U+202A-U+202E, U+2060, U+FEFF, U+00AD)
    text = re.sub(r"[\u200B-\u200F\u202A-\u202E\u2060\uFEFF\u00AD]", "", text)
    # Refang links
    text = refang_urls(text)
    # Collapse spaced single letters
    text = collapse_spaced_letters(text)
    # Map digit lookalikes inside known keywords
    text = map_digit_lookalikes(text)
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_urls(text: str) -> List[str]:
    """
    Extracts valid URLs from text, stripping trailing punctuation.
    Guards against currency/abbreviation false matches like 'Rs.500'.
    """
    if not text:
        return []

    cleaned = normalize_input(text)
    urls = []
    for m in URL_RE.finditer(cleaned):
        raw = m.group(0).rstrip(".,);]:'\"")
        # Exclude currency expressions like Rs.500 or No.10
        if CURRENCY_OR_NUMBER_GUARD.match(raw):
            continue
        # Exclude pure number extensions e.g. 1.2
        if re.fullmatch(r"\d+\.\d+", raw):
            continue
        urls.append(raw)
    return urls


def redact(text: str) -> str:
    """
    Redacts personal identifiable information (Cards, Aadhaar, Phone, PAN, UPI, Account)
    while strictly protecting extracted URLs from being corrupted by PII regexes.
    """
    if not text:
        return ""

    t = normalize_input(text)

    # 1. Stash URLs with temporary placeholders so PII regexes don't touch them
    held: Dict[str, str] = {}

    def stash(m: re.Match) -> str:
        raw = m.group(0)
        # If it's a currency token like Rs.500, don't treat it as a URL
        if CURRENCY_OR_NUMBER_GUARD.match(raw.rstrip(".,);]")):
            return raw
        key = f"§URL{len(held)}§"
        held[key] = raw
        return key

    t = URL_RE.sub(stash, t)

    # 2. Apply PII redactions
    for label, rx in PII:
        t = rx.sub(f"<{label}>", t)

    # 3. Restore stashed URLs
    for k, v in held.items():
        t = t.replace(k, v)

    return t


def extract_features(text: str) -> Dict[str, Any]:
    """
    Extracts structural features from the raw message before scoring:
    - Candidate URLs
    - Presence of phone numbers
    - Presence of OTP-like numeric codes
    - Message length
    """
    cleaned = normalize_input(text)
    urls = extract_urls(cleaned)
    has_phone = bool(re.search(r"(?<!\d)(?:\+?91[ -]?)?[6-9]\d{9}(?!\d)", cleaned))
    has_otp = bool(OTP_CANDIDATE_RE.search(cleaned))

    return {
        "urls": urls,
        "has_phone": has_phone,
        "has_otp_candidate": has_otp,
        "length": len(cleaned)
    }
