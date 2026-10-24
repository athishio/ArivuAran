"""
Deterministic Text Rules and Mitigating Signal Evaluation for ArivuAran.
Covers English, Tamil, and Tanglish fraud patterns.
Applies negation stripping to prevent genuine bank security warnings from triggering false positives.
"""

import re
from typing import List, Dict, Any
from .links import Signal

# Negation and Security Warning Stripping Patterns
# Genuine bank alerts say "Do not share OTP" or "Our staff will never call to ask for OTP"
NEGATION_EN = re.compile(
    r"\b(?:do not|don'?t|dont|never|not|should not|kindly)\b[^.\n]{0,45}\b(?:share|disclose|give|tell)\b[^.\n]{0,35}\b(?:otp|pin|cvv|password)\b[^.\n]*",
    re.IGNORECASE
)
NEGATION_EN_STAFF = re.compile(
    r"\b(?:staff|bank|employees?|representative|official)\b[^.\n]{0,35}\b(?:never|will not|wont)\b[^.\n]{0,35}\b(?:call|ask|request)\b[^.\n]{0,35}\b(?:otp|pin|cvv|password)\b[^.\n]*",
    re.IGNORECASE
)
NEGATION_EN_SCREEN = re.compile(
    r"\b(?:share|enter)\b[^.\n]{0,30}\b(?:otp|pin)\b[^.\n]{0,35}\bonly\s*on\s*(?:the\s*)?official\b[^.\n]*",
    re.IGNORECASE
)
NEGATION_TA = re.compile(
    r"(?:யாருடனும்\s*பகிர\s*வேண்டாம்|பகிராதீர்கள்|தெரிவிக்க\s*வேண்டாம்|கூற\s*வேண்டாம்|பகிராதீர்)"
)
NEGATION_TANGLISH = re.compile(
    r"(?:share\s*pannatheenga|yarukum\s*sollatheenga|kuduka\s*koodadhu)"
)


def strip_security_warnings(text: str) -> str:
    """Strips legitimate bank advisory warnings like 'Never share your OTP' before rule checks."""
    t = NEGATION_EN.sub(" ", text)
    t = NEGATION_EN_STAFF.sub(" ", t)
    t = NEGATION_EN_SCREEN.sub(" ", t)
    t = NEGATION_TA.sub(" ", t)
    t = NEGATION_TANGLISH.sub(" ", t)
    return t


def evaluate_text_rules(
    redacted_text: str,
    raw_text: str,
    urls: List[str]
) -> List[Signal]:
    """
    Evaluates text against deterministic fraud rules across English, Tamil, and Tanglish.
    Returns a list of fired Signal objects with associated points.
    """
    signals: List[Signal] = []
    text_lower = redacted_text.lower()
    raw_lower = raw_text.lower()

    # Strip legitimate bank security warnings for credential check
    text_for_sensitive = strip_security_warnings(text_lower)

    # 1. ASK_SENSITIVE (+3, HARD): Requests OTP, CVV, password, card details/expiry
    ask_sensitive_patterns = [
        # English:
        r"\b(?:share|send|enter|submit|provide|tell|reply\s*with|give|confirm)\b[^\n\.]{0,50}\b(?:otp|one\s*time\s*password|cvv|atm\s*pin|upi\s*pin|card\s*number|card\s*last\s*4\s*digits|password|expiry)\b",
        r"\b(?:otp|one\s*time\s*password|cvv|password|card\s*number|card\s*last\s*4\s*digits|card\s*details)\b[^\n\.]{0,50}\b(?:is\s*(?:needed|required|mandatory)|share|send|tell|give|provide|confirm|verify|needed|required)\b",
        r"\b(?:confirm|verify)\s*your\s*card\b",
        # Tamil (substring matching):
        r"(?:ஓடிபி|சிவிவி|கடவுச்சொல்|பாஸ்வேர்ட்|கார்டு\s*எண்).{0,40}(?:பகிரவும்|அனுப்பவும்|சொல்லவும்|பதிவிடவும்|சமர்ப்பிக்கவும்|தேவை|உள்ளிடவும்|தரவும்|கூறவும்|சொல்லுங்கள்|அனுப்புங்கள்)",
        r"(?:otp|cvv|password).{0,35}(?:சமர்ப்பிக்கவும்|சொல்லவும்|அனுப்பவும்|பதிவிடவும்|பகிரவும்|சொல்லுங்கள்|அனுப்புங்கள்|தேவை|உள்ளிடவும்)",
        r"(?:வந்த|வந்திருக்கும்|வந்த\s*ரகசிய)\s*(?:otp|ஓடிபி).{0,30}(?:சொல்லுங்கள்|சொல்லவும்|அனுப்புங்கள்|பகிரவும்)",
        # Tanglish:
        r"\b(?:otp|cvv|password)\b[^\n]{0,40}\b(?:share|send|kudunga|anupunga|sollunga|thevai|podunga|type\s*pannunga|confirm\s*pannunga)\b",
        r"\b(?:kudunga|anupunga|sollunga|enter\s*pannunga|share\s*pannunga)\b[^\n]{0,40}\b(?:otp|cvv|password)\b",
        r"\b(?:vandha|vantha)\s*otp\b[^\n]{0,30}\b(?:sollunga|anupunga|kudunga)\b",
    ]
    if any(re.search(pat, text_for_sensitive, re.IGNORECASE) for pat in ask_sensitive_patterns):
        signals.append(Signal("ASK_SENSITIVE", 3, "credential_request"))

    # 2. PIN_REQUEST (+3, HARD): Asking to enter or share PIN (especially UPI PIN to receive money)
    pin_request_patterns = [
        # English:
        r"\b(?:enter|share|type|submit|provide|put)\s*(?:your\s*)?(?:upi\s*pin|atm\s*pin|pin)\b",
        r"\b(?:upi\s*pin|atm\s*pin|pin)\b[^\n\.]{0,35}\b(?:to\s*receive|to\s*get|to\s*claim|is\s*needed|is\s*required|enter|share)\b",
        # Tamil:
        r"(?:upi\s*pin|பின்|பின்னை|பின்\s*எண்).{0,35}(?:உள்ளிடுங்கள்|உள்ளிடவும்|பதிவிடவும்|பகிரவும்|அனுப்பவும்|பதிவு\s*செய்யவும்)",
        r"(?:பெற|திரும்பப்\s*பெற|வர).{0,35}(?:upi\s*pin|பின்|பின்னை).{0,35}(?:உள்ளிடுங்கள்|உள்ளிடவும்)",
        # Tanglish:
        r"\b(?:upi\s*pin|pin)\b[^\n]{0,35}\b(?:podunga|enter\s*pannunga|type\s*pannunga|kudunga|anuppunga)\b",
        r"\b(?:refund\s*vara|panam\s*vara|amount\s*vara)\b[^\n]{0,35}\b(?:upi\s*pin|pin)\b",
    ]
    if any(re.search(pat, text_for_sensitive, re.IGNORECASE) for pat in pin_request_patterns):
        signals.append(Signal("PIN_REQUEST", 3, "pin_entry_request"))

    # 3. FEE_FIRST (+3, HARD): Upfront fee/charges demanded to claim prize, job, loan, courier, etc.
    fee_first_patterns = [
        # English:
        r"\b(?:pay|deposit|send|transfer)\s*(?:rs\.?|inr|₹)?\s*[\d,]+\s*(?:as\s*)?(?:fee|charges?|processing|registration|advance|token|tax)\b",
        r"\b(?:processing\s*fee|registration\s*fee|advance\s*fee|claim\s*fee|courier\s*fee|delivery\s*fee|verification\s*fee)\b[^\n]{0,45}\b(?:pay|deposit|rs\.?|₹|mudhalla)\b",
        r"\b(?:fee|charges?)\b[^\n]{0,30}\b(?:to\s*claim|to\s*receive|to\s*clear|to\s*start|to\s*verify)\b",
        # Tamil:
        r"(?:கட்டணம்|பதிவுக்\s*கட்டணம்|முன்பணம்|செயலாக்கக்\s*கட்டணம்|வரி).{0,35}(?:செலுத்தவும்|செலுத்துங்கள்|கட்டவும்|அனுப்பவும்)",
        r"(?:செலுத்தவும்|செலுத்துங்கள்|கட்டவும்).{0,35}(?:ரூ\.?|₹)\s*[\d,]+",
        r"(?:ரூ\.?|₹)\s*[\d,]+.{0,25}(?:கட்டணம்|பதிவுக்\s*கட்டணம்|செலுத்துங்கள்|செலுத்தவும்)",
        r"(?:பரிசு\s*பெற|வேலைக்கு|பார்சல்|கூரியர்|முகவரி\s*சரிபார்க்க).{0,40}(?:ரூ\.?|₹)?\s*[\d,]+.{0,30}(?:செலுத்துங்கள்|செலுத்தவும்|கட்டவும்)",
        # Tanglish:
        r"\b(?:processing\s*fee|registration\s*fee|advance\s*fee|courier\s*fee|claim\s*fee)\b[^\n]{0,40}\b(?:kattunga|anuppunga|pay\s*pannunga)\b",
        r"\b(?:mudhalla|first|advance)\s*(?:rs\.?|₹)?\s*[\d,]+\s*(?:kattunga|anuppunga|pay\s*pannunga|registration\s*fee)\b",
        r"\b(?:claim\s*panna|amount\s*vara)\b[^\n]{0,40}\b(?:fee\s*kattunga|pay\s*pannunga|fee\b)",
    ]
    if any(re.search(pat, text_lower, re.IGNORECASE) for pat in fee_first_patterns):
        signals.append(Signal("FEE_FIRST", 3, "upfront_fee_demanded"))

    # 4. DIGITAL_ARREST (+4, HARD): Authority impersonation with arrest, video call, or narcotics threat
    digital_arrest_patterns = [
        # English:
        r"\b(?:cbi|crime\s*branch|mumbai\s*police|delhi\s*police|cyber\s*police|customs\s*officer|trai|narcotics)\b[^\n]{0,70}\b(?:video\s*call|arrested|arrest|warrant|drugs|illegal|parcel\s*in\s*your\s*name|clear\s*the\s*case)\b",
        r"\b(?:stay\s*on\s*video\s*call|digital\s*arrest)\b",
        # Tamil:
        r"(?:சைபர்\s*கிரைம்|சிபிஐ|காவல்துறை|காவல்\s*துறை|போலீஸ்\s*அதிகாரி).{0,70}(?:வீடியோ\s*கால்|கைது\s*செய்யப்படுவீர்கள்|கைது|வழக்கு|போதைப்பொருள்|டிஜிட்டல்\s*கைது)",
        r"(?:வீடியோ\s*காலில்\s*இருங்கள்|டிஜிட்டல்\s*அரெஸ்ட்)",
        # Tanglish:
        r"\b(?:police\s*officer|cyber\s*crime|cbi)\b[^\n]{0,60}\b(?:video\s*call|arrest|case\s*irukku)\b",
        r"\bvideo\s*call\s*la\s*irunga\b",
    ]
    if any(re.search(pat, text_lower, re.IGNORECASE) for pat in digital_arrest_patterns):
        signals.append(Signal("DIGITAL_ARREST", 4, "digital_arrest_threat"))

    # 5. PAYMENT_PUSH (+3, HARD): Collect request, scan QR to receive, accept UPI collect, emergency cash demand
    payment_push_patterns = [
        # English:
        r"\b(?:collect\s*request|approve\s*(?:the\s*)?upi|enter\s*upi\s*pin\s*to\s*receive|scan\s*qr\s*to\s*receive|accept\s*(?:the\s*)?request)\b",
        r"\b(?:accept|approve)\s*(?:this\s*)?(?:collect\s*request|upi\s*request)\b",
        r"\b(?:please\s*)?(?:send|transfer)\s*(?:rs\.?|inr|₹)\s*[\d,]+\b",
        # Tamil:
        r"(?:upi\s*collect|upi\s*கோரிக்கையை\s*ஏற்கவும்|பணம்\s*பெற.{0,30}கோரிக்கையை|அப்ரூவ்\s*செய்யவும்)",
        r"(?:₹|ரூ\.?)\s*[\d,]+\s*பெற\s*இந்த\s*upi\s*கோரிக்கையை",
        # Tanglish:
        r"\b(?:collect\s*request\s*accept|refund\s*vara\s*upi|request\s*accept\s*pannunga)\b",
        r"\b(?:gpay|phonepe|paytm)\s*(?:collect|request|send\s*money)\b",
    ]
    if any(re.search(pat, text_lower, re.IGNORECASE) for pat in payment_push_patterns):
        signals.append(Signal("PAYMENT_PUSH", 3, "payment_push_or_collect"))

    # 6. REMOTE_ACCESS (+3, HARD): AnyDesk, TeamViewer, QuickSupport, RustDesk, screen share, APK install
    remote_patterns = [
        # English:
        r"\b(?:anydesk|teamviewer|rustdesk|quicksupport|screen\s*share)\b",
        r"\.apk\b",
        # Tamil:
        r"(?:செயலியை\s*பதிவிறக்கம்|ஆப்\s*டவுன்லோட்|இன்ஸ்டால்\s*செய்யவும்)",
        # Tanglish:
        r"\b(?:anydesk|teamviewer|quicksupport)\s*install\b",
    ]
    if any(re.search(pat, text_lower, re.IGNORECASE) for pat in remote_patterns):
        signals.append(Signal("REMOTE_ACCESS", 3, "remote_access_or_apk"))

    # 7. KYC_UPDATE (+2, SOFT): update, verify or renew KYC, PAN, Aadhaar
    kyc_patterns = [
        # English:
        r"\b(?:update|verify|renew|link|complete|updt)\s*(?:your\s*)?(?:kyc|pan|aadhaar)\b",
        r"\b(?:kyc|pan|aadhaar)\b[^\n]{0,35}\b(?:update|verify|renew|expired|pending|suspended|deactivated|link\s*aagala|not\s*linked|updt)\b",
        # Tamil:
        r"(?:கேஒய்சி|kyc|பான்|ஆதார்).{0,35}(?:புதுப்பிக்க|புதுப்பிக்கவும்|முடிக்கவும்|இணைக்க|இணைக்கப்படவில்லை|காலாவதியாகிவிட்டது|செய்யாவிடில்)",
        # Tanglish:
        r"\b(?:kyc|pan|aadhaar)\b[^\n]{0,35}\b(?:update\s*pannunga|link\s*pannunga|link\s*aagala|expired|block\s*aagum)\b",
    ]
    if any(re.search(pat, text_lower, re.IGNORECASE) for pat in kyc_patterns):
        signals.append(Signal("KYC_UPDATE", 2, "kyc_pan_update"))

    # 8. THREAT (+2, SOFT): blocked, suspended, frozen, disconnected, arrest, legal action, power cut
    threat_patterns = [
        # English:
        r"\b(?:blocked|suspended|frozen|disconnected|disconnection|sim\s*disconnection|terminated|closed|deactivated|legal\s*action|arrest|warrant|power\s*cut|expired|blokd|wil\s*b\s*blokd)\b",
        # Tamil:
        r"(?:முடக்கப்படும்|முடக்கப்பட்டுள்ளது|முடக்கம்|முடங்கும்|நிறுத்தப்படும்|நிறுத்தப்பட்டுள்ளது|துண்டிக்கப்படும்|துண்டிக்கப்பட்டது|தடைசெய்யப்படும்|மின்\s*இணைப்பு\s*துண்டிக்கப்படும்)",
        # Tanglish:
        r"\b(?:block\s*aagum|cut\s*aagum|freeze\s*aagum|current\s*cut|sim\s*cut|aayiduchu|block\s*aayiduchu)\b",
    ]
    if any(re.search(pat, text_lower, re.IGNORECASE) for pat in threat_patterns):
        signals.append(Signal("THREAT", 2, "threat_or_suspension"))

    # 9. URGENCY (+1, SOFT): today, immediately, urgent, within N hours, last chance, limited seats
    urgency_patterns = [
        # English:
        r"\b(?:immediately|within\s*\d+\s*(?:hours|hrs)|urgent|urgently|expires\s*today|act\s*now|last\s*chance|tonight|limited\s*seats|invest\s*today)\b",
        # Tamil:
        r"(?:உடனடியாக|உடனே|இன்றே|இன்றுக்குள்|இன்று\s*இரவு|24\s*மணி\s*நேரத்திற்குள்|இறுதி\s*வாய்ப்பு|இடங்கள்\s*குறைவு)",
        # Tanglish:
        r"\b(?:inru\s*night|inniku\s*night|inre|udane|seekiram|today\s*kulla|urgent\s*ah|limited\s*seats)\b",
    ]
    if any(re.search(pat, text_lower, re.IGNORECASE) for pat in urgency_patterns):
        signals.append(Signal("URGENCY", 1, "urgency_pressure"))

    # 10. PRIZE (+2, SOFT): you won, lottery, lucky draw, reward, cashback
    prize_patterns = [
        # English:
        r"\b(?:you\s*(?:have\s*)?won|won\s*(?:rs\.?|₹)?\s*[\d,]+|lottery|lucky\s*draw|kbc|cashback|reward\s*points)\b",
        # Tamil (never matching plain 'வாழ்த்துகள்' alone):
        r"(?:பரிசு\s*வென்றுள்ளீர்கள்|ரூ\.?\s*[\d,]+\s*பரிசு|லக்கி\s*டிரா|கே\.பி\.சி|பணப்பரிசு|குலுக்கலில்\s*பரிசு|தேர்ந்தெடுக்கப்பட்டீர்கள்)",
        # Tanglish:
        r"\b(?:prize\s*jeichirukeenga|lottery\s*adichirukku|gift\s*vandhurukku|prize\s*won)\b",
    ]
    if any(re.search(pat, text_lower, re.IGNORECASE) for pat in prize_patterns):
        signals.append(Signal("PRIZE", 2, "prize_or_lottery"))

    # 11. AUTHORITY (+1, SOFT): CBI, police, TRAI, customs, court, bank manager
    authority_patterns = [
        # English:
        r"\b(?:cbi|crime\s*branch|mumbai\s*police|delhi\s*police|customs|trai|narcotics|police\s*officer|bank\s*manager|trai\s*officer)\b",
        # Tamil:
        r"(?:சைபர்\s*கிரைம்|சிபிஐ|காவல்துறை|காவல்\s*துறை|சுங்கத்துறை|போதைப்பொருள்|வங்கி\s*மேலாளர்|சட்டவிரோத\s*செயலில்)",
        # Tanglish:
        r"\b(?:police\s*officer|cyber\s*crime|cbi|trai\s*officer)\b",
    ]
    if any(re.search(pat, text_lower, re.IGNORECASE) for pat in authority_patterns):
        signals.append(Signal("AUTHORITY", 1, "authority_impersonation"))

    # 12. JOB_TASK (+2, SOFT): part-time job, per-day earnings, like and subscribe tasks
    job_patterns = [
        # English:
        r"\b(?:part\s*time\s*job|work\s*from\s*home|daily\s*(?:income|salary|earning|rs\s*\d+)|like\s*youtube\s*videos|earn\s*rs|salary\s*\d+k|no\s*experience\s*needed|found\s*your\s*resume)\b",
        # Tamil:
        r"(?:பகுதிநேர\s*வேலை|வீட்டிலிருந்தே\s*வேலை|தினசரி\s*வருமானம்|கூகிள்\s*ரேட்டிங்|தினம்\s*ரூ\.?\s*[\d,]+\s*சம்பாதிக்கலாம்)",
        # Tanglish:
        r"\b(?:part\s*time\s*job|work\s*from\s*home|daily\s*rs|youtube\s*like\s*pannina)\b",
    ]
    if any(re.search(pat, text_lower, re.IGNORECASE) for pat in job_patterns):
        signals.append(Signal("JOB_TASK", 2, "job_or_task_scam"))

    # 13. INVEST (+2, SOFT): guaranteed returns, double your money, VIP stock tips
    invest_patterns = [
        # English:
        r"\b(?:guaranteed\s*returns|double\s*(?:your\s*)?money|double\s*profit|vip\s*stock|trading\s*tips|crypto\s*profit)\b",
        # Tamil:
        r"(?:உறுதியான\s*வருமானம்|முதலீடு\s*செய்து\s*இரட்டிப்பு|இரண்டு\s*மடங்கு\s*லாபம்|லாபம்\s*உறுதி)",
        # Tanglish:
        r"\b(?:double\s*profit|profit\s*guaranteed|double\s*returns?)\b",
    ]
    if any(re.search(pat, text_lower, re.IGNORECASE) for pat in invest_patterns):
        signals.append(Signal("INVEST", 2, "investment_or_trading_scam"))

    # 14. CALLBACK (+1, SOFT): 'call this number' with a mobile number or contact officer
    callback_patterns = [
        # English:
        r"\b(?:call|contact|dial|whatsapp)\b[^\n]{0,35}\b(?:<PHONE>|\d{10}|[6-9]\d[Xx*]{6}\d{2})\b",
        r"\bjust\s*whatsapp\s*(?:<PHONE>|\d{10}|[6-9]\d[Xx*]{6}\d{2})\b",
        # Tamil:
        r"(?:<PHONE>|\d{10}|[6-9]\d[Xx*]{6}\d{2})[^\n]{0,35}(?:தொடர்பு\s*கொள்ளவும்|அழைக்கவும்|பேசவும்|அழைக்க)",
        r"(?:தொடர்பு\s*கொள்ளவும்|அழைக்கவும்|தொடர்புகொள்ள)\s*[:\-]?\s*(?:<PHONE>|\d{10}|[6-9]\d[Xx*]{6}\d{2})",
        r"(?:உடனே\s*அழைக்கவும்|இந்த\s*எண்ணை\s*அழைக்கவும்)",
        # Tanglish:
        r"\b(?:call\s*pannunga|contact\s*pannunga|whatsapp\s*pannunga)\b",
    ]
    if any(re.search(pat, text_lower, re.IGNORECASE) for pat in callback_patterns):
        signals.append(Signal("CALLBACK", 1, "callback_instruction"))

    # =================================================================
    # MITIGATING SIGNALS (Only apply when message contains NO URL or verified safe URL)
    # =================================================================
    if not urls:
        # OTP_DELIVERY (-3): Genuine OTP delivered for user's transaction/login with security warning
        # Example: "123456 is your OTP for login. Do not share it with anyone."
        is_otp_delivery = bool(
            re.search(r"\b(?:\d{4,8}|[A-Z0-9]{6})\b[^\n]{0,35}\b(?:is\s*your\s*(?:secret\s*)?otp|is\s*the\s*otp|verification\s*code)\b", raw_lower)
            or re.search(r"\botp\s*(?:is|for\s*transaction)\b[^\n]{0,35}\b\d{4,8}\b", raw_lower)
            or re.search(r"(?:உங்கள்\s*ஆதார்\s*சரிபார்ப்பு\s*குறியீடு|ரகசிய\s*otp)", raw_lower)
        )
        has_security_warning = bool(
            re.search(r"\b(?:do\s*not\s*share|never\s*share|strictly\s*confidential)\b", raw_lower)
            or re.search(r"(?:யாருடனும்\s*பகிர\s*வேண்டாம்|பகிராதீர்கள்)", raw_lower)
        )
        if is_otp_delivery and has_security_warning:
            signals.append(Signal("OTP_DELIVERY", -3, "genuine_otp_with_warning"))

        # TXN_ALERT (-2): Debit or credit alert without links
        # Example: "Rs.500 debited from A/c XX1234"
        is_txn_alert = bool(
            re.search(r"\b(?:debited|credited|withdrawn|deposited|transfer(?:red)?)\b", raw_lower)
            and re.search(r"(?:rs\.?|inr|₹|ரூ\.?)\s*[\d,]+", raw_lower)
        )
        if is_txn_alert:
            signals.append(Signal("TXN_ALERT", -2, "legitimate_bank_alert"))

        # DELIVERY_ALERT (-2): Legitimate delivery and transit tracking updates with no links
        is_delivery_alert = bool(
            re.search(r"\b(?:delivery\s*pin|ride\s*pin|order\s*#?\d+|out\s*for\s*delivery|delivered|delivery\s*partner|picked\s*up)\b", raw_lower)
            or re.search(r"(?:டெலிவரி|பார்சல்|ஆர்டர்\s*எண்|டெலிவரி\s*பார்ட்னர்)", raw_lower)
        )
        if is_delivery_alert and not is_otp_delivery:
            signals.append(Signal("DELIVERY_ALERT", -2, "legitimate_delivery_alert"))

    return signals
