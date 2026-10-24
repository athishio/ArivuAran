"""
Data-only module defining rule constants, patterns, keywords, and allowlists.
Covers English, Tamil, and Tanglish variants.
"""

import re
from dataclasses import dataclass
from typing import List, Pattern

@dataclass(frozen=True)
class RuleDefinition:
    id: str
    points: int
    reason_key: str
    description: str
    patterns: List[Pattern]
    negative_patterns: List[Pattern] = None  # If any negative pattern matches, rule won't fire


# =====================================================================
# ALLOWLIST DATA
# =====================================================================
# Official Indian banking and government domains (must match exact or true suffix)
ALLOWLISTED_DOMAINS = [
    "sbi.co.in",
    "onlinesbi.sbi",
    "hdfcbank.com",
    "icicibank.com",
    "axisbank.com",
    "kotak.com",
    "bankofbaroda.in",
    "pnbindia.in",
    "canarabank.com",
    "unionbankofindia.co.in",
    "indianbank.in",
    "iob.in",
    "idfcfirstbank.com",
    "indusind.com",
    "gov.in",
    "nic.in",
    "cybercrime.gov.in",
    "incometax.gov.in",
    "uidai.gov.in",
    "epfindia.gov.in",
    "indiapost.gov.in",
]

# Official SMS sender ID prefixes (e.g. AD-HDFCBK, VK-SBIINB)
ALLOWLISTED_SMS_HEADERS = [
    "HDFCBK", "SBIINB", "SBIPSG", "ICICIB", "AXISBK", "KOTAKB",
    "BOBTXN", "PNBSMS", "CANBNK", "UNIONB", "INDBNK", "IOBTXN",
    "EPFOHO", "AADHAR", "ITDEPT", "CBICIN", "VODAFO", "AIRTEL", "JIOINF"
]

# Known URL shortener domains
SHORTENER_DOMAINS = [
    "bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "rb.gy",
    "shorturl.at", "tiny.cc", "ow.ly", "buff.ly", "goo.gl", "bit.do", "t.me"
]

# Targeted brand keywords for typosquatting / mimicry checks
BRAND_KEYWORDS = [
    "sbi", "hdfc", "icici", "axis", "kotak", "yono", "bob", "pnb",
    "tneb", "paytm", "gpay", "phonepe", "pan", "kyc", "aadhaar", "ebill"
]

SUSPICIOUS_TLDS = [
    ".xyz", ".top", ".club", ".buzz", ".work", ".site", ".online",
    ".vip", ".monster", ".fit", ".rest", ".live", ".cc"
]


# =====================================================================
# RULE DEFINITIONS
# =====================================================================
RULES: List[RuleDefinition] = [
    RuleDefinition(
        id="R01",
        points=15,
        reason_key="urgency_pressure",
        description="Creates panic or urgent time pressure to act immediately",
        patterns=[
            re.compile(r"(?i)\b(immediately|within\s*24\s*(?:hours|hrs)|urgent|urgently|expires\s*today|act\s*now|last\s*chance)\b"),
            re.compile(r"(உடனடியாக|இன்றே|உடனே|24\s*மணி\s*நேரத்திற்குள்|இறுதி\s*வாய்ப்பு)"),
            re.compile(r"(?i)\b(udane|udaney|indrey|inre|24\s*mani\s*nerathil|urgent\s*aa)\b"),
        ]
    ),
    RuleDefinition(
        id="R02",
        points=35,
        reason_key="asks_sensitive_credentials",
        description="Asks to provide, share, or enter OTP, PIN, CVV, or passwords",
        patterns=[
            re.compile(r"(?i)\b(?:share|send|enter|submit|provide|tell|reply\s*with)\b[^\n\.\,]{0,80}\b(?:otp|one\s*time\s*password|cvv|atm\s*pin|upi\s*pin|netbanking\s*password|(?:16\s*digit\s*)?card\s*number)\b"),
            re.compile(r"(?i)\b(?:otp|pin|cvv|password|card\s*number)\b[^\n\.\,]{0,80}\b(?:share|send|kudunga|anupunga|sollunga|enter\s*pannunga)\b"),
            re.compile(r"(ஓடிபி|பின்|சிவிவி|கடவுச்சொல்|பாஸ்வேர்ட்|OTP|PIN|CVV).{0,40}(பகிரவும்|அனுப்பவும்|சொல்லவும்|பதிவிடவும்|சமர்ப்பிக்கவும்)"),
        ],
        # Negative patterns: Do NOT trigger R02 if the message warns the user NEVER/DO NOT share OTP
        negative_patterns=[
            re.compile(r"(?i)\b(do\s*not\s*share|never\s*share|strictly\s*confidential|not\s*shared\s*with\s*anyone|don'?t\s*share|share\s*pannatheenga)\b"),
            re.compile(r"(யாருடனும்\s*பகிர\s*வேண்டாம்|பகிராதீர்கள்|தெரிவிக்க\s*வேண்டாம்|கூற\s*வேண்டாம்)"),
        ]
    ),
    RuleDefinition(
        id="R03",
        points=20,
        reason_key="suspicious_link_shortener",
        description="Contains URL shortener or bare IP address",
        patterns=[
            re.compile(r"(?:https?://)?(?:www\.)?(?:" + "|".join(re.escape(d) for d in SHORTENER_DOMAINS) + r")/[^\s]+", re.IGNORECASE),
            re.compile(r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::\d+)?(?:/[^\s]*)?", re.IGNORECASE),
        ]
    ),
    RuleDefinition(
        id="R04",
        points=25,
        reason_key="brand_typosquatting",
        description="Domain mimics official brands or banks using suspicious TLDs or hyphens",
        patterns=[
            re.compile(r"https?://[a-zA-Z0-9.\-]*(?:sbi|hdfc|icici|yono|tneb|phonepe)[a-zA-Z0-9.\-]*(?:" + "|".join(re.escape(tld) for tld in SUSPICIOUS_TLDS) + r")(?:/[^\s]*)?", re.IGNORECASE),
            re.compile(r"https?://(?:www\.)?[a-zA-Z0-9\-]+-(?:kyc|update|login|verification|support)\.[a-zA-Z]{2,}(?:/[^\s]*)?", re.IGNORECASE),
        ]
    ),
    RuleDefinition(
        id="R05",
        points=25,
        reason_key="account_block_kyc_threat",
        description="Threatens account suspension, deactivation, or uncompleted KYC/PAN",
        patterns=[
            re.compile(r"(?i)\b(?:account|pan|debit\s*card|sim|service)\b[^\n\.\,]{0,40}\b(?:blocked|suspended|deactivated|terminated|closed|expired)\b"),
            re.compile(r"(?i)\b(?:complete|update|submit)\s*(?:your\s*)?(?:kyc|pan\s*card|aadhaar)\b"),
            re.compile(r"(வங்கி\s*கணக்கு|அக்கவுண்ட்|பான்\s*கார்டு|சிம்\s*கார்டு|ஆதார்).{0,40}(முடக்கப்படும்|நிறுத்தப்படும்|பிளாக்\s*செய்யப்படும்|இணைக்கப்படவில்லை|இணைக்கவும்)"),
            re.compile(r"(கேஒய்சி|kyc).{0,30}(புதுப்பிக்கவும்|முடிக்கவும்|செய்யாவிடில்)"),
            re.compile(r"(?i)\b(?:pan|aadhaar|account)\b[^\n]{0,40}\b(?:link\s*aagala|link\s*pannalana|not\s*linked|block\s*aagum|kyc\s*update)\b"),
        ]
    ),
    RuleDefinition(
        id="R06",
        points=25,
        reason_key="prize_lottery_cashback",
        description="Promises fake prizes, lottery winnings, KBC awards, or unexpected cashback",
        patterns=[
            re.compile(r"(?i)\b(congratulations|you\s*have\s*won|lottery|lucky\s*draw|kbc|cashback|refund|reward\s*points)\b"),
            re.compile(r"(வாழ்த்துகள்|பரிசு|வென்றுள்ளீர்கள்|வெல்லும்|லக்கி\s*டிரா|கே\.பி\.சி|பணப்பரிசு|குலுக்கலில்|ரீஃபண்ட்)"),
            re.compile(r"(?i)\b(ungalluku\s*parisu|prize\s*adichurukku|lottery\s*la\s*jeichiteenga)\b"),
        ]
    ),
    RuleDefinition(
        id="R07",
        points=30,
        reason_key="install_malicious_app",
        description="Asks to download APK files or install remote screen-sharing tools",
        patterns=[
            re.compile(r"(?i)\b(\.apk\b|anydesk|teamviewer|rustdesk|quicksupport|screen\s*share\s*app)\b"),
            re.compile(r"(செயலியை\s*பதிவிறக்கம்|ஆப்\s*டவுன்லோட்|இன்ஸ்டால்\s*செய்யவும்)"),
            re.compile(r"(?i)\b(intha\s*app\s*download|apk\s*install\s*pannunga)\b"),
        ]
    ),
    RuleDefinition(
        id="R08",
        points=25,
        reason_key="advance_fee_or_upi_collect",
        description="Asks for upfront fee, advance payment for refunds, or UPI collect request",
        patterns=[
            re.compile(r"(?i)\b(?:pay|send|transfer)\b[^\n\.\,]{0,60}\b(?:processing\s*fee|registration\s*fee|advance|to\s*receive\s*refund|fine|penalty|money)\b"),
            re.compile(r"(?i)\b(?:approve|accept)\s*(?:the\s*)?upi\s*collect\b|upi\s*collect(?:\s*request)?"),
            re.compile(r"(கட்டணம்\s*செலுத்தவும்|பதிவு\s*கட்டண|கட்டணமாக|பணம்\s*அனுப்பினால்|முன்பணம்|செலுத்தி\s*பதிவு|அப்ரூவ்\s*செய்யவும்)"),
            re.compile(r"(?i)\b(advance\s*panam|registration\s*fees\s*kudunga|upi\s*collect\s*approve\s*pannunga)\b"),
        ]
    ),
    RuleDefinition(
        id="R09",
        points=40,
        reason_key="fake_job_part_time",
        description="Offers work-from-home/part-time earning redirecting to Telegram or WhatsApp",
        patterns=[
            re.compile(r"(?i)\b(?:part\s*time\s*job|work\s*from\s*home|daily\s*(?:rs\s*)?\d+|income|like\s*youtube\s*videos)\b[^\n]{0,100}\b(?:telegram|whatsapp|t\.me|wa\.me)\b"),
            re.compile(r"(பகுதிநேர\s*வேலை|வீட்டிலிருந்தே|தினசரி\s*வருமானம்|கூகிள்\s*ரேட்டிங்).{0,100}(?:சம்பாதிக்கலாம்|வேலை).{0,100}(டெலிகிராம்|வாட்ஸ்அப்|telegram|t\.me)"),
            re.compile(r"(?i)\b(?:part\s*time\s*job|daily\s*(?:rs\s*)?\d+\s*sambathikalam)\b.{0,80}(?:telegram|whatsapp|t\.me)\b"),
        ]
    ),
    RuleDefinition(
        id="R10",
        points=60,
        reason_key="digital_arrest_impersonation",
        description="Impersonates Police, CBI, Customs, TRAI, or courier (Digital Arrest scam)",
        patterns=[
            re.compile(r"(?i)\b(cbi|crime\s*branch|mumbai\s*police|delhi\s*police|customs\s*officer|trai|narcotics|digital\s*arrest)\b"),
            re.compile(r"(?i)\b(?:fedex|dhl|courier)\s*(?:parcel|package)\s*(?:seized|contains\s*drugs|illegal|detained)\b"),
            re.compile(r"(சைபர்\s*கிரைம்|சிபிஐ|காவல்\s*துறை|சுங்கத்துறை|டிஜிட்டல்\s*(?:கைது|அரெஸ்ட்)|போதைப்பொருள்|சட்டவிரோத\s*பார்சல்)"),
            re.compile(r"(?i)\b(?:digital\s*arrest|police\s*case\s*aagum|courier.*drugs|illegal\s*weapons)\b"),
        ]
    ),
    RuleDefinition(
        id="R11",
        points=45,
        reason_key="electricity_bill_scam",
        description="TNEB / Electricity disconnection threat demanding immediate phone contact",
        patterns=[
            re.compile(r"(?i)\b(?:tneb|electricity\s*bill|power\s*supply)\b[^\n]{0,80}\b(?:disconnected|cut\s*tonight|power\s*off|power\s*cut)\b"),
            re.compile(r"(மின்சாரம்\s*துண்டிக்கப்படும்|மின்\s*இணைப்பு\s*துண்டிக்கப்படும்|TNEB).{0,80}(தொடர்பு\s*கொள்ளவும்|அழைக்கவும்|bill\s*pending|\d{10})"),
            re.compile(r"(?i)\b(?:power\s*cut\s*aagum|current\s*cut\s*aagum|tneb\s*(?:officer\s*)?call\s*pannunga)\b"),
        ]
    ),
    RuleDefinition(
        id="R12",
        points=10,
        reason_key="mixed_script_tricks",
        description="Uses suspicious mixed Latin/Cyrillic lookalikes embedded inside words",
        patterns=[
            re.compile(r"(?:[a-zA-Z][\u0B80-\u0BFF]+[a-zA-Z]|[\u0B80-\u0BFF][a-zA-Z]+[\u0B80-\u0BFF])"),
            re.compile(r"\b[sS][bB][iI][0-9oO\-_]+[a-zA-Z0-9]*\b"),
        ]
    ),
]