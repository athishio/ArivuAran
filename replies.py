"""
Tamil reply templates and UI generators for Arivaran.
Plain spoken-style Tamil for easy understanding by all users.
All user-facing text is kept strictly in this file.
"""

from typing import Dict, Any, List
from config import BOT_NAME_EN, BOT_NAME_TA, BOT_NAME_TA_GEN

# Rule reason explanations in clear, spoken-style Tamil
REASONS: Dict[str, str] = {
    "urgency_pressure": "உடனடியாக செய்ய வேண்டும் என்று அவசரப்படுத்தி பயமுறுத்துகிறது.",
    "asks_sensitive_credentials": "ரகசிய OTP, PIN அல்லது கடவுச்சொல்லை கேட்கிறது (வங்கிகள் ஒருபோதும் இதை கேட்காது).",
    "suspicious_link_shortener": "உண்மையான முகவரியை மறைக்கும் சந்தேகத்திற்குரிய லிங்க் (Shortener) உள்ளது.",
    "brand_typosquatting": "வங்கி அல்லது அரசு இணையதளம் போல் போலியாக உருவாக்கப்பட்ட போலி லிங்க் உள்ளது.",
    "account_block_kyc_threat": "கணக்கு முடக்கப்படும் அல்லது KYC அப்டேட் செய்ய வேண்டும் என்று அச்சுறுத்துகிறது.",
    "prize_lottery_cashback": "நம்பமுடியாத பரிசு, லாட்டரி அல்லது கேஷ்பேக் ஆசை காட்டுகிறது.",
    "install_malicious_app": "மொபைலை கட்டுப்படுத்தும் ஆபத்தான ஆப் (APK / AnyDesk) டவுன்லோட் செய்ய சொல்கிறது.",
    "advance_fee_or_upi_collect": "பணம் திரும்பப் பெற அல்லது பரிசு பெற முன்பணம்/UPI அப்ரூவல் கேட்கிறது.",
    "fake_job_part_time": "வீட்டிலிருந்தே எளிய வேலை என்று கூறி டெலிகிராம்/வாட்ஸ்அப்பில் தொடர்புகொள்ள சொல்கிறது.",
    "digital_arrest_impersonation": "போலீஸ், சிபிஐ அல்லது சுங்கத்துறை அதிகாரி போல் மிரட்டுகிறது (டிஜிட்டல் அரெஸ்ட் மோசடி).",
    "electricity_bill_scam": "மின்சாரம் துண்டிக்கப்படும் என்று போலியாக பயமுறுத்தி போன் செய்ய சொல்கிறது.",
    "mixed_script_tricks": "கண்டுபிடிப்பதை தவிர்க்க எழுத்துக்களை மாற்றி தந்திரமாக எழுதப்பட்டுள்ளது.",
    "allowlisted_source": "அங்கீகரிக்கப்பட்ட அதிகாரப்பூர்வ நிறுவனம் அல்லது இணையதளத்திலிருந்து வந்ததாக தெரிகிறது."
}


def build_reply(result: Dict[str, Any]) -> str:
    """
    Builds the main Tamil verdict reply:
    - Verdict headline (Emoji + Tamil)
    - Up to 3 top reasons
    - Clear action line
    - Tool disclaimer
    """
    verdict = result.get("verdict", "LIKELY_SAFE")
    reasons = result.get("reasons", [])

    # Filter out allowlisted_source from reasons list when presenting scam risks
    risk_reasons = [r for r in reasons if r != "allowlisted_source"]

    # 1. Headline
    if verdict == "SCAM":
        headline = "🚨 <b>எச்சரிக்கை! இது ஒரு மோசடி (SCAM) செய்தி போல தெரிகிறது.</b>"
        action = "⛔ <b>நீங்கள் என்ன செய்ய வேண்டும்:</b>\n• எந்த லிங்க்கையும் தொடாதீர்கள் (Click செய்யாதீர்கள்).\n• OTP அல்லது வங்கி விவரங்களை ஒருபோதும் பகிராதீர்கள்.\n• இந்த செய்தியை உடனே டெலீட் செய்துவிடுங்கள்."
    elif verdict == "SUSPICIOUS":
        headline = "⚠️ <b>கவனம்! இது சந்தேகத்திற்குரிய (SUSPICIOUS) செய்தி.</b>"
        action = "🔍 <b>நீங்கள் என்ன செய்ய வேண்டும்:</b>\n• செய்தியில் உள்ள போன் நம்பரையோ லிங்க்கையோ நம்பாதீர்கள்.\n• உங்கள் ஏடிஎம் கார்டின் பின்புறம் உள்ள வங்கியின் அதிகாரப்பூர்வ உதவி எண்ணை மட்டும் அழைத்து சரிபார்க்கவும்."
    else:
        headline = "✅ <b>இதில் வெளிப்படையான ஆபத்து எதுவும் தெரியவில்லை (NO RED FLAGS FOUND).</b>"
        action = "💡 <b>நினைவில் கொள்க:</b>\n• இதில் உடனடி ஆபத்து அறிகுறிகள் இல்லை.\n• ஆனாலும் உங்கள் OTP அல்லது கடவுச்சொல்லை எப்போதும் யாருடனும் பகிராதீர்கள்."

    # 2. Reasons list (up to 3)
    reasons_text = ""
    if risk_reasons:
        reasons_text = "\n\n📌 <b>கண்டறியப்பட்ட காரணங்கள்:</b>\n"
        for idx, r_key in enumerate(risk_reasons[:3], 1):
            explanation = REASONS.get(r_key, "சந்தேகத்திற்குரிய வாசகங்கள் உள்ளன.")
            reasons_text += f"{idx}. {explanation}\n"

    # 3. Disclaimer
    disclaimer = "\nℹ️ <i>குறிப்பு: எந்த தொழில்நுட்ப கருவியும் 100% துல்லியமானது அல்ல. உங்கள் விழிப்புணர்வே சிறந்த பாதுகாப்பு.</i>"

    return f"{headline}{reasons_text}\n{action}{disclaimer}"


def build_buttons(verdict: str) -> List[Dict[str, str]]:
    """
    Builds up to 3 interactive reply buttons (titles strictly <= 20 chars).
    """
    return [
        {"id": "check_another", "title": "இன்னொன்று check"},
        {"id": "lost_money", "title": "பணம் இழந்துட்டேன்"},
        {"id": "wrong_result", "title": "தவறா?"}
    ]


def build_lost_money_flow() -> str:
    """
    Returns concise step-by-step emergency instructions and copyable dispute template.
    """
    return (
        "🚨 <b>பணம் இழந்துவிட்டீர்களா? பதறாதீர்கள்!</b>\n"
        "உடனடியாக இந்த 3 அவசர நடவடிக்கைகளை எடுங்கள்:\n\n"
        "1️⃣ <b>1930 எண்ணை உடனே அழையுங்கள்:</b>\n"
        "தேசிய சைபர் கிரைம் உதவி எண் <b>1930</b>-க்கு உடனே போன் செய்யுங்கள். (முதல் 2 முதல் 4 மணி நேரத்திற்குள் புகார் அளித்தால் பணத்தை முடக்கி மீட்க அதிக வாய்ப்பு உண்டு).\n\n"
        "2️⃣ <b>வங்கி கணக்கை பிளாக் செய்யுங்கள்:</b>\n"
        "உங்கள் வங்கியின் 24x7 அவசர உதவி எண்ணை அழைத்து, பணப்பரிவர்த்தனை நடந்த கார்டு / UPI / கணக்கை உடனடியாக தற்காலிகமாக பிளாக் செய்யச் சொல்லுங்கள்.\n\n"
        "3️⃣ <b>ஆன்லைன் புகார் பதிவு:</b>\n"
        "👉 <b>cybercrime.gov.in</b> இணையதளத்தில் UTR எண் மற்றும் ஸ்கிரீன்ஷாட்களுடன் உடனே புகார் பதிவு செய்யுங்கள்.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📋 <b>வங்கிக்கு அனுப்ப மாதிரி மின்னஞ்சல் (Tap to copy):</b>\n\n"
        "<code>Subject: Urgent - Fraudulent Transaction Dispute\n"
        "Dear Bank, a fraudulent transaction of Rs. [AMOUNT] occurred on [DATE] via UPI/Card (UTR: [TXN ID]). I did not authorize this. Please immediately freeze the beneficiary account and initiate dispute recovery under cyber fraud guidelines.</code>\n\n"
        "⚠️ <i>முக்கியம்: இழந்த பணத்தை மீட்டுத் தருகிறோம் என்று கட்டணம் கேட்கும் யாரையும் நம்பி மீண்டும் பணம் அனுப்பாதீர்கள்.</i>"
    )


def build_welcome_message() -> str:
    """Tamil greeting explaining how to use the bot."""
    return (
        f"👋 <b>வணக்கம்! நான் {BOT_NAME_TA} ({BOT_NAME_EN}).</b>\n"
        "உங்கள் டிஜிட்டல் & வங்கி மோசடி தடுப்பு உதவியாளர் 🛡️\n\n"
        "உங்களுக்கு வந்த SMS, வாட்ஸ்அப் செய்தி அல்லது வாய்ஸ் மெசேஜை (Voice Note) அப்படியே எனக்கு பார்வர்ட் செய்யுங்கள்.\n\n"
        "⚡ <i>சில நொடிகளில் அது மோசடியா (Scam) என சரிபார்த்து தமிழில் எச்சரிக்கிறேன்!</i>"
    )


def build_rate_limit_message() -> str:
    """Tamil message when rate limit (20 checks/hr) is exceeded."""
    return (
        "⏳ <b>அளவுக்கு அதிகமான கோரிக்கைகள் வந்துள்ளன.</b>\n\n"
        "பாதுகாப்பு கருதி, ஒரு மணி நேரத்திற்கு 20 முறை மட்டுமே சரிபார்க்க முடியும். தயவுசெய்து சிறிது நேரம் கழித்து மீண்டும் முயற்சிக்கவும்."
    )


def build_audio_too_long_message() -> str:
    """Tamil message for voice notes longer than 60 seconds."""
    return (
        "⏱️ <b>வாய்ஸ் மெசேஜ் மிகவும் நீளமாக உள்ளது.</b>\n\n"
        "தயவுசெய்து 60 வினாடிகளுக்குள் இருக்கும் வாய்ஸ் மெசேஜை அனுப்பவும் அல்லது செய்தியை டைப் செய்து அனுப்பவும்."
    )


def build_audio_failed_message() -> str:
    """Tamil message when audio transcription is empty or fails."""
    return (
        "🎙️ <b>வாய்ஸ் மெசேஜை தெளிவாக கேட்க முடியவில்லை.</b>\n\n"
        "தயவுசெய்து சத்தம் இல்லாத இடத்தில் மீண்டும் பேசி அனுப்பவும் அல்லது செய்தியை டெக்ஸ்ட்டாக டைப் செய்து அனுப்பவும்."
    )


def build_feedback_received_message() -> str:
    """Tamil confirmation for reporting wrong result."""
    return (
        "🙏 <b>உங்கள் கருத்துக்கு நன்றி!</b>\n\n"
        f"இந்த முடிவை எங்கள் குழு மறுஆய்வு செய்து {BOT_NAME_TA_GEN} துல்லியத்தை மேலும் மேம்படுத்தும்."
    )


def build_check_another_prompt() -> str:
    """Prompt asking the user for their next message."""
    return "👍 <b>சரி! நீங்கள் சரிபார்க்க விரும்பும் அடுத்த செய்தி அல்லது வாய்ஸ் மெசேஜை எனக்கு பார்வர்ட் செய்யுங்கள்.</b>"