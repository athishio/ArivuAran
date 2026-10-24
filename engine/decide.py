"""
Decision Engine and Verdict Computation for ArivuAran.
Computes final verdict (SCAM, SUSPICIOUS, NO_RED_FLAGS) deterministically.
Maps fired signals to plain Tamil explanations.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Set, Any

from .redact import extract_urls, redact, extract_features
from .links import analyse_url, Signal
from .rules import evaluate_text_rules

# Tamil explanation templates mapped from signal codes
REASON_TEMPLATES_TA: Dict[str, str] = {
    "ASK_SENSITIVE": "வங்கிகள் SMS மூலம் OTP, PIN அல்லது கடவுச்சொல்லைக் கேட்காது.",
    "PIN_REQUEST": "பணம் பெறவோ அல்லது சரிபார்க்கவோ UPI PIN உள்ளிடுமாறு கேட்பது மோசடி.",
    "FEE_FIRST": "பரிசு, வேலை அல்லது கடனுக்கு முன்பணமாக கட்டணம் செலுத்தச் சொல்வது மோசடி.",
    "DIGITAL_ARREST": "வீடியோ காலில் மிரட்டி டிஜிட்டல் அரெஸ்ட் செய்வது சைபர் மோசடி.",
    "KYC_UPDATE": "வங்கிகள் SMS வழியாக அவசர KYC விவரங்களைக் கேட்காது.",
    "LOOKALIKE": "இந்த இணைய முகவரி வங்கியின் உண்மையான முகவரி அல்ல.",
    "BRAND_MISMATCH": "செய்தியில் கூறப்படும் நிறுவனமும் லிங்க்கின் முகவரியும் பொருந்தவில்லை.",
    "THREAT": "கணக்கு முடக்கப்படும் அல்லது நடவடிக்கை எடுக்கப்படும் என்று அவசரப்படுத்தி பயமுறுத்துகிறது.",
    "URGENCY": "உடனடியாக செய்ய வேண்டும் என்று அவசரப்படுத்துகிறது.",
    "PRIZE": "நீங்கள் பங்கேற்காத பரிசு, லாட்டரி அல்லது கேஷ்பேக் ஆசை காட்டுகிறது.",
    "AUTHORITY": "போலீஸ், CBI போன்ற பெயரில் மிரட்டி பணம் கேட்பது மோசடி.",
    "REMOTE_ACCESS": "AnyDesk, APK போன்ற ஆபத்தான செயலிகளை நிறுவச் சொல்கிறது.",
    "PAYMENT_PUSH": "பணம் பெற UPI பின்னை உள்ளிடச் சொல்வது மோசடி தந்திரம்.",
    "JOB_TASK": "எளிய பகுதிநேர வேலை அல்லது யூடியூப் லைக் மூலம் அதிக வருமானம் தருவதாக ஆசை காட்டுகிறது.",
    "INVEST": "உறுதியான அதிக லாபம் தருவதாகக் கூறி பணத்தை ஈர்க்க முயற்சிக்கிறது.",
    "SHORTENER": "இணைப்பு சுருக்கப்பட்டுள்ளது; உண்மையான முகவரி மறைக்கப்பட்டுள்ளது.",
    "KNOWN_BAD": "இந்த இணைப்பு மோசடி இணைப்புகளின் பட்டியலில் உள்ளது.",
    "IP_HOST": "பாதுகாப்பான இணைய முகவரிக்கு பதிலாக நேரடி IP எண் பயன்படுத்தப்பட்டுள்ளது.",
    "PUNYCODE": "போலி எழுத்துக்களைக் கொண்ட ஏமாற்று இணைய முகவரி.",
    "USERINFO": "உண்மையான தளத்தை மறைக்கும் தந்திரமான முகவரி வடிவம்.",
    "CALLBACK": "அங்கீகரிக்கப்படாத தனிநபர் தொலைபேசி எண்ணை அழைக்கச் சொல்கிறது.",
}

# Signal Classification Policy Table
# HARD signals: Can give SCAM alone
HARD_SIGNALS: Set[str] = {
    "ASK_SENSITIVE",     # OTP, card, CVV, password credentials requested
    "PIN_REQUEST",      # Explicit PIN entry/demand (e.g. enter UPI PIN)
    "PAYMENT_PUSH",     # Collect request, enter UPI PIN to receive money, scan QR to receive
    "FEE_FIRST",        # Upfront fee/charges demanded for prize/loan/job/parcel
    "REMOTE_ACCESS",    # Install AnyDesk, TeamViewer, QuickSupport, or .apk
    "DIGITAL_ARREST",   # Authority + arrest / video-call / drugs threat
    "KNOWN_BAD",        # Verified malicious URL
    "LOOKALIKE",        # Bank/brand domain spoofing/lookalike link
    "USERINFO",         # User-info @ trick obfuscating host
    "PUNYCODE",         # Punycode homograph attack
    "IP_HOST",          # Direct IP address host
}

# SOFT signals: Need at least one other signal before the message is flagged.
# A KYC word alone, or urgency alone, or any single soft signal must not flag a message.
SOFT_SIGNALS: Set[str] = {
    "KYC_UPDATE",
    "THREAT",
    "URGENCY",
    "SHORTENER",
    "CALLBACK",
    "PRIZE",
    "JOB_TASK",
    "INVEST",
    "AUTHORITY",
    "RISKY_TLD",
    "NO_HTTPS",
    "MANY_SUBDOMAINS",
    "BRAND_MISMATCH",
}

# Mitigating signals: Legitimate bank transaction or OTP delivery notices
MITIGATING_SIGNALS: Set[str] = {
    "OTP_DELIVERY",
    "TXN_ALERT",
    "DELIVERY_ALERT",
}

# Link-derived signals
LINK_SIGNALS: Set[str] = {
    "LOOKALIKE",
    "KNOWN_BAD",
    "IP_HOST",
    "PUNYCODE",
    "USERINFO",
    "SHORTENER",
    "RISKY_TLD",
    "NO_HTTPS",
    "MANY_SUBDOMAINS",
    "BRAND_MISMATCH",
}


def suppress_ask_sensitive_if_otp_delivery(
    signals: List[Signal],
    has_links: bool = False,
    hard_scam: bool = False
) -> List[Signal]:
    """
    Suppresses ASK_SENSITIVE when genuine OTP delivery notice is detected:
    - If OTP_DELIVERY fires (a code/number is being delivered plus a "do not share" warning),
      the message has NO links, and ASK_SENSITIVE is the only hard signal,
      then ASK_SENSITIVE is suppressed.
    - If any other hard signal, any link, or any soft signal such as URGENCY/KYC/THREAT is also present,
      do NOT suppress.
    """
    codes: Set[str] = {s.code for s in signals}
    message_has_links = has_links or bool(codes & LINK_SIGNALS)

    if "OTP_DELIVERY" in codes and not message_has_links:
        hard_codes = (codes & HARD_SIGNALS) | ({"HARD_SCAM"} if hard_scam else set())
        soft_codes = codes & SOFT_SIGNALS
        if hard_codes == {"ASK_SENSITIVE"} and not soft_codes:
            return [s for s in signals if s.code != "ASK_SENSITIVE"]

    return signals

NEXT_STEP_SCAM_TA = "இணைப்பைத் திறக்க வேண்டாம். OTP, PIN யாரிடமும் சொல்ல வேண்டாம். வங்கியின் அதிகாரப்பூர்வ செயலி அல்லது எண்ணில் சரிபார்க்கவும்."
NEXT_STEP_NO_RED_FLAGS_TA = "எச்சரிக்கை அறிகுறி இல்லை. ஆனாலும் OTP, PIN யாரிடமும் பகிர வேண்டாம்."


@dataclass
class AnalysisResult:
    verdict: str                  # "SCAM" | "SUSPICIOUS" | "NO_RED_FLAGS"
    score: int                    # Numeric total score
    signals: List[Signal]         # List of fired signals
    reasons_ta: List[str]         # Top Tamil reason explanations (max 3)
    next_step_ta: str             # Actionable guidance in Tamil
    redacted_text: str            # Clean text with PII removed
    urls: List[str]               # Extracted URLs
    is_hard_scam: bool = False    # True if triggered by hard-kill rule


def decide(
    signals: List[Signal],
    hard_scam: bool = False,
    scam_at: int = 5,
    suspicious_at: int = 2,
    has_links: bool = False
) -> Tuple[str, int]:
    """
    Computes verdict based on signal classification policy:
    1. HARD signals alone give SCAM.
    2. Mitigating signals (without hard signals) give NO_RED_FLAGS.
    3. Single SOFT signal alone NEVER flags (NO_RED_FLAGS).
    4. Two or more SOFT signals flag as SUSPICIOUS or SCAM based on count/score.
    """
    signals = suppress_ask_sensitive_if_otp_delivery(signals, has_links=has_links, hard_scam=hard_scam)
    score = sum(s.points for s in signals)
    codes: Set[str] = {s.code for s in signals}

    # 1. HARD signals policy: Can give SCAM alone
    has_hard = hard_scam or bool(codes & HARD_SIGNALS)
    if has_hard:
        return "SCAM", max(score, 5)

    # 2. Mitigating signals policy (genuine alerts without hard scam signs)
    if bool(codes & MITIGATING_SIGNALS):
        return "NO_RED_FLAGS", min(score, 0)

    # 3. SOFT signals policy
    soft_codes = codes & SOFT_SIGNALS

    # Rule C: A KYC word alone, or urgency alone, or any single soft signal
    # must not flag a message. Soft signals need at least one other signal.
    if len(soft_codes) <= 1:
        return "NO_RED_FLAGS", score

    # Multiple soft signals present
    # If 3 or more distinct soft signals OR score >= 5 -> SCAM
    if len(soft_codes) >= 3 or score >= scam_at:
        return "SCAM", score

    # Exactly 2 soft signals with score in [2, 4] -> SUSPICIOUS
    return "SUSPICIOUS", score


def analyse(text: str) -> AnalysisResult:
    """
    Master pipeline: Feature extraction -> PII Redaction -> Link Analysis -> Text Rules -> Decision.
    """
    if not text or not text.strip():
        return AnalysisResult(
            verdict="NO_RED_FLAGS",
            score=0,
            signals=[],
            reasons_ta=[],
            next_step_ta=NEXT_STEP_NO_RED_FLAGS_TA,
            redacted_text="",
            urls=[],
            is_hard_scam=False
        )

    # 1. Structural feature & URL extraction from raw text
    features = extract_features(text)
    urls = features["urls"]

    # 2. Redact PII (Aadhaar, Phone, Card, PAN, UPI, Account)
    redacted_text = redact(text)

    # 3. Analyze URLs
    all_signals: List[Signal] = []
    for u in urls:
        url_signals = analyse_url(u, text_lower=text.lower())
        all_signals.extend(url_signals)

    # 4. Evaluate Text Rules on redacted text (with mitigating signals if no URL)
    text_signals = evaluate_text_rules(
        redacted_text=redacted_text,
        raw_text=text,
        urls=urls
    )
    all_signals.extend(text_signals)

    # Suppress ASK_SENSITIVE if genuine OTP delivery notice without links/soft signals
    has_links = bool(urls)
    all_signals = suppress_ask_sensitive_if_otp_delivery(all_signals, has_links=has_links)

    # 5. Decide Verdict
    verdict, total_score = decide(all_signals, has_links=has_links)

    # 6. Extract up to 3 distinct Tamil reasons
    reasons_ta: List[str] = []
    seen_reasons: Set[str] = set()

    # Prioritize higher-weighted signals for explanation
    sorted_signals = sorted(all_signals, key=lambda s: s.points, reverse=True)
    for s in sorted_signals:
        if s.points <= 0:
            continue
        explanation = REASON_TEMPLATES_TA.get(s.code)
        if explanation and explanation not in seen_reasons:
            reasons_ta.append(explanation)
            seen_reasons.add(explanation)
        if len(reasons_ta) >= 3:
            break

    # 7. Next step guidance
    next_step = NEXT_STEP_NO_RED_FLAGS_TA if verdict == "NO_RED_FLAGS" else NEXT_STEP_SCAM_TA

    return AnalysisResult(
        verdict=verdict,
        score=total_score,
        signals=all_signals,
        reasons_ta=reasons_ta,
        next_step_ta=next_step,
        redacted_text=redacted_text,
        urls=urls,
        is_hard_scam=("LOOKALIKE" in {s.code for s in all_signals} and bool({s.code for s in all_signals} & {"THREAT", "URGENCY", "ASK_SENSITIVE", "KYC_UPDATE"}))
    )


def analyze(text: str, config: str = "B") -> Dict[str, Any]:
    """
    Exposes verdict engine for evaluation harness with configuration support:
    - Config A: Text rules only (no URL analysis)
    - Config B: Full Engine (Text rules + URL analysis)
    - Config C: Rules + links + classifier (Not implemented / planned)
    Returns:
        {verdict: "SCAM"|"SUSPICIOUS"|"NO_RED_FLAGS", scam_type: Optional[str], signals: List[str]}
    """
    if config == "C":
        raise NotImplementedError("Config C (classifier) is not implemented (planned)")

    if not text or not text.strip():
        return {
            "verdict": "NO_RED_FLAGS",
            "scam_type": None,
            "signals": []
        }

    # 1. PII Redaction
    redacted_text = redact(text)

    # 2. Extract URLs only if enabled in config
    urls = extract_urls(text) if config == "B" else []

    all_signals: List[Signal] = []
    if config == "B":
        for u in urls:
            url_signals = analyse_url(u, text_lower=text.lower())
            all_signals.extend(url_signals)

    # 3. Evaluate Text Rules
    text_signals = evaluate_text_rules(
        redacted_text=redacted_text,
        raw_text=text,
        urls=urls
    )
    all_signals.extend(text_signals)

    # Suppress ASK_SENSITIVE if genuine OTP delivery notice without links/soft signals
    has_links = bool(extract_urls(text))
    all_signals = suppress_ask_sensitive_if_otp_delivery(all_signals, has_links=has_links)

    # 4. Compute Verdict
    verdict, total_score = decide(all_signals, has_links=has_links)

    # 5. Extract dominant scam_type
    scam_type = None
    if verdict in ("SCAM", "SUSPICIOUS") and all_signals:
        positive_sigs = [s for s in all_signals if s.points > 0]
        if positive_sigs:
            top_sig = max(positive_sigs, key=lambda s: s.points)
            scam_type = top_sig.code.lower()

    return {
        "verdict": verdict,
        "scam_type": scam_type,
        "signals": [s.code for s in all_signals]
    }

