"""
Link and URL Analysis for ArivuAran.
Detects domain lookalikes, brand mismatches, URL shorteners, risky TLDs,
raw IP addresses, punycode spoofing, and HTTP links.
"""

import re
from urllib.parse import urlparse
from dataclasses import dataclass
from typing import List, Dict, Set, Any
import tldextract

@dataclass
class Signal:
    code: str
    points: int
    detail: str = ""


# High-risk TLDs commonly abused for fast-flux phishing campaigns
RISKY_TLDS: Set[str] = {
    "xyz", "top", "icu", "click", "link", "live", "vip", "cyou",
    "rest", "buzz", "work", "monster", "fit", "site", "online", "cc"
}

# Known URL shorteners and redirect services
SHORTENERS: Set[str] = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "cutt.ly",
    "rb.gy", "shorturl.at", "t.me", "wa.me", "tiny.cc", "ow.ly", "buff.ly", "bit.do",
    "short.example"
}

# Official Brand and Government Allowlist definitions
BRANDS: Dict[str, Dict[str, Any]] = {
    "sbi": {
        "keywords": ["sbi", "statebank", "yono"],
        "domains": {"sbi.co.in", "onlinesbi.sbi", "onlinesbi.com"}
    },
    "hdfc": {
        "keywords": ["hdfc", "hdfcbank"],
        "domains": {"hdfcbank.com"}
    },
    "icici": {
        "keywords": ["icici", "icicibank", "imobile"],
        "domains": {"icicibank.com"}
    },
    "axis": {
        "keywords": ["axis", "axisbank"],
        "domains": {"axisbank.com"}
    },
    "kotak": {
        "keywords": ["kotak", "kotakbank"],
        "domains": {"kotak.com"}
    },
    "pnb": {
        "keywords": ["pnb", "punjabnationalbank"],
        "domains": {"pnbindia.in"}
    },
    "bob": {
        "keywords": ["bob", "bankofbaroda"],
        "domains": {"bankofbaroda.in"}
    },
    "tneb": {
        "keywords": ["tneb", "tangedco"],
        "domains": {"tneb.gov.in", "tangedco.gov.in"}
    },
    "pan": {
        "keywords": ["pan", "incometax"],
        "domains": {"incometax.gov.in", "tin-nsdl.com", "utiitsl.com"}
    },
    "aadhaar": {
        "keywords": ["aadhaar", "uidai"],
        "domains": {"uidai.gov.in"}
    },
    "phonepe": {
        "keywords": ["phonepe"],
        "domains": {"phonepe.com"}
    },
    "paytm": {
        "keywords": ["paytm"],
        "domains": {"paytm.com"}
    },
    "gpay": {
        "keywords": ["gpay", "googlepay"],
        "domains": {"google.com", "pay.google.com"}
    },
    "amazon": {
        "keywords": ["amazon"],
        "domains": {"amazon.in", "amazon.com"}
    },
    "flipkart": {
        "keywords": ["flipkart"],
        "domains": {"flipkart.com"}
    },
    "netflix": {
        "keywords": ["netflix"],
        "domains": {"netflix.com"}
    }
}

# Official government/institutional domain suffixes
OFFICIAL_SUFFIXES: Set[str] = {"gov.in", "nic.in", "ac.in"}


def is_official_domain(host: str) -> bool:
    """Checks whether host belongs to verified banking or government domains."""
    host = host.lower()
    for brand, info in BRANDS.items():
        for d in info["domains"]:
            if host == d or host.endswith("." + d):
                return True
    for suff in OFFICIAL_SUFFIXES:
        if host.endswith("." + suff) or host == suff:
            return True
    return False


def analyse_url(raw: str, text_lower: str = "") -> List[Signal]:
    """
    Analyzes a candidate URL and returns security signals.
    Parses real host behind userinfo tricks and detects brand lookalike spoofing.
    """
    if not raw:
        return []

    sigs: List[Signal] = []
    had_scheme = bool(re.match(r"(?i)https?://", raw))
    parsed = urlparse(raw if had_scheme else "http://" + raw)

    # 1. Userinfo Trick (@ in netloc e.g. sbi.co.in@evil.example)
    # Parse real host: use the part after "@"
    netloc = parsed.netloc
    if "@" in netloc:
        sigs.append(Signal("USERINFO", 3, netloc))
        real_netloc = netloc.split("@")[-1]
    else:
        real_netloc = netloc

    host = (real_netloc.split(":")[0] if real_netloc else "").lower()
    if not host:
        return sigs

    # Guard against currency or numeric tokens
    if re.fullmatch(r"\d+\.\d+", host) or re.match(r"(?i)^(?:rs|inr|re|no)\.\d+$", host):
        return []

    # 2. Raw IPv4 address check
    if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host):
        sigs.append(Signal("IP_HOST", 3, host))
        return sigs

    # 3. Extract public suffix using tldextract with fallback
    ext = tldextract.extract(host)
    if ext.suffix:
        reg = f"{ext.domain}.{ext.suffix}".lower()
    else:
        parts = host.split(".")
        if len(parts) >= 2:
            reg = ".".join(parts[-2:])
        else:
            reg = host

    # 4. Known URL Shorteners
    if reg in SHORTENERS or host in SHORTENERS or host.startswith("short.") or host.startswith("tiny."):
        sigs.append(Signal("SHORTENER", 2, reg))

    # 5. Risky Top-Level Domains (TLDs)
    if ext.suffix:
        tld_candidate = ext.suffix.split(".")[-1]
        if tld_candidate in RISKY_TLDS:
            sigs.append(Signal("RISKY_TLD", 1, ext.suffix))

    # 6. Punycode Spoofing (IDN Homograph attack)
    if "xn--" in host:
        sigs.append(Signal("PUNYCODE", 3, host))

    # 7. Deep Subdomain Mimicry (> 3 subdomain labels)
    if ext.subdomain and len(ext.subdomain.split(".")) > 3:
        sigs.append(Signal("MANY_SUBDOMAINS", 1, ext.subdomain))

    # 8. Unencrypted HTTP scheme
    if had_scheme and parsed.scheme.lower() == "http":
        sigs.append(Signal("NO_HTTPS", 1))

    # 9. Brand Lookalike and Brand Mismatch Checks
    # Flag when a brand token appears in a host that is not an official domain or official subdomain
    for name, info in BRANDS.items():
        is_authentic = any(host == d or host.endswith("." + d) for d in info["domains"])
        if is_authentic:
            continue

        # Lookalike: Bank/Authority brand token inside an unofficial host/domain (e.g. sbi-co-in.example)
        if any(k in host for k in info["keywords"]):
            sigs.append(Signal("LOOKALIKE", 4, f"{name}: {host}"))
        # Brand Mismatch: Message text claims to be from a brand, but links to an unverified domain
        elif any(re.search(rf"\b{k}\b", text_lower) for k in info["keywords"]):
            sigs.append(Signal("BRAND_MISMATCH", 3, f"{name} vs {reg}"))

    return sigs
