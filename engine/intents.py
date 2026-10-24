"""
Intent Classifier, Reason & Teach Mappings, and Session Manager for ArivuAran.
Deterministic intent mapping for follow-up and emergency queries.
Zero LLM, substring matching for Tamil/English/Tanglish, strict 30-minute in-memory sessions.
"""

import os
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Set

from config import BOT_NAME_EN, BOT_NAME_TA, BOT_NAME_TA_GEN

REPLIES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "replies.json")

# In-memory cached replies dictionary keyed by ID
_REPLIES_CACHE: Optional[Dict[str, Dict[str, Any]]] = None


def get_all_replies() -> Dict[str, Dict[str, Any]]:
    """Loads and caches data/replies_ta.json."""
    global _REPLIES_CACHE
    if _REPLIES_CACHE is None:
        with open(REPLIES_PATH, "r", encoding="utf-8") as f:
            entries = json.load(f)
            _REPLIES_CACHE = {e["id"]: e for e in entries}
    return _REPLIES_CACHE


def get_reply(reply_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves reply entry by ID."""
    return get_all_replies().get(reply_id)


def format_template(template: str, **kwargs) -> str:
    """Formats template safely with global bot names and custom slots."""
    params = {
        "BOT_NAME_TA": BOT_NAME_TA,
        "BOT_NAME_TA_GEN": BOT_NAME_TA_GEN,
        "BOT_NAME_EN": BOT_NAME_EN,
        **kwargs
    }
    # Replace known placeholders
    res = template
    for k, v in params.items():
        res = res.replace("{" + k + "}", str(v))
    return res


# =====================================================================
# 1. EMERGENCY INC_* INTENT KEYWORDS (Priority Rule)
# =====================================================================
INC_KEYWORDS: Dict[str, List[str]] = {
    "INC_OTP": [
        # Tamil
        "otp சொல்லிட்டேன்", "ஓடிபி சொல்லிட்டேன்", "otp குடுத்துட்டேன்",
        "otp பகிர்ந்தேன்", "otp கொடுத்துட்டேன்", "கடவுச்சொல் சொல்லிட்டேன்",
        # English
        "shared my otp", "gave otp", "told the otp", "i gave otp", "shared otp", "i sent otp", "told otp",
        # Tanglish
        "otp sollitten", "otp share panniten", "otp kuduthuten", "otp solliten", "otp share paniten", "otp anupiten"
    ],
    "INC_LINK": [
        # Tamil
        "லிங்க் கிளிக் பண்ணிட்டேன்", "லிங்க் திறந்தேன்", "இணைப்பை திறந்தேன்", "லிங்கை அமுக்கிட்டேன்", "லிங்க் ஓபன் பண்ணிட்டேன்",
        # English
        "clicked the link", "opened the link", "i clicked link", "clicked link", "opened link", "clicked phishing link",
        # Tanglish
        "link click panniten", "link open panniten", "link kulla poiten", "link click paniten", "link thiranthen", "link open panten"
    ],
    "INC_ANYDESK": [
        # Tamil
        "anydesk போட்டுட்டேன்", "செயலி நிறுவினேன்", "ஆப் ஏத்திட்டேன்", "anydesk ஏத்திட்டேன்", "செயலியை டவுன்லோட் செய்தேன்",
        # English
        "installed anydesk", "downloaded anydesk", "installed remote app", "downloaded apk", "installed apk", "installed teamviewer",
        # Tanglish
        "anydesk install panniten", "remote app install panniten", "anydesk pottuten", "app install panniten", "anydesk download panniten", "apk install panniten"
    ],
    "INC_PAID": [
        # Tamil
        "பணம் அனுப்பிட்டேன்", "பணம் போச்சு", "பணம் கட்டிட்டேன்", "காசு அனுப்பிட்டேன்", "பணம் செலுத்திட்டேன்",
        "ரூபாய் அனுப்பிட்டேன்", "அனுப்பிட்டேன்", "கட்டிட்டேன்", "செலுத்திட்டேன்",
        # English
        "i paid", "paid", "sent money", "transferred money", "money gone", "already paid", "sent the amount", "paid money",
        # Tanglish
        "panam anuppiten", "paisa pochu", "kaasu anupiten", "money send panniten", "panam kattiten", "amount anupiten", "anupiten"
    ],
    "INC_CARD": [
        # Tamil
        "கார்டு நம்பர் சொல்லிட்டேன்", "கார்டு விவரம் கொடுத்தேன்", "சிவிவி சொல்லிட்டேன்", "அட்டை எண் கொடுத்தேன்", "கார்டு பின் சொல்லிட்டேன்",
        # English
        "gave card details", "shared card number", "gave cvv", "entered card details", "shared card", "gave debit card", "shared credit card",
        # Tanglish
        "card details kuduthuten", "card number sollitten", "cvv solliten", "card details share panniten", "atm card number solliten"
    ],
}


# =====================================================================
# 2. FOLLOW-UP F_* INTENT KEYWORDS
# =====================================================================
FOLLOWUP_KEYWORDS: Dict[str, List[str]] = {
    "F_CLICK": [
        # Tamil
        "லிங்கை கிளிக் பண்ணலாமா", "லிங்க் திறக்கலாமா", "லிங்கை தொடலாமா", "லிங்க் ஓபன் பண்ணலாமா",
        # English
        "can i click the link", "can i open this link", "should i click", "is it okay to open link", "can i open link",
        # Tanglish
        "link open pannalama", "click pannalaama", "link click pannalama", "link thirakkalama", "link polaama"
    ],
    "F_NAME": [
        # Tamil
        "என்ன மோசடி", "மோசடி பெயர் என்ன", "என்ன வகை மோசடி", "என்ன பிராடு",
        # English
        "what scam is this", "what type of scam", "scam name", "what kind of scam is this", "name of the scam",
        # Tanglish
        "idhu enna scam", "scam peru enna", "enna scam idhu", "scam name enna", "enna fraud idhu"
    ],
    "F_WHY": [
        # Tamil
        "ஏன் மோசடி", "ஏன் அப்படி சொல்றீங்க", "காரணம் என்ன", "ஏன் சந்தேகமானது", "காரணம் சொல்லுங்க",
        # English
        "why is it a scam", "why scam", "what is the reason", "tell me why", "reason for this",
        # Tanglish
        "yen scam", "reason sollunga", "ethukku scam", "yen apdi solreenga", "reason enna"
    ],
    "F_TODO": [
        # Tamil
        "இப்போ என்ன பண்ணணும்", "என்ன செய்வது", "அடுத்து என்ன செய்ய வேண்டும்", "நான் என்ன செய்ய வேண்டும்",
        # English
        "what should i do", "what to do now", "what next", "how to proceed", "what action to take", "what to do",
        # Tanglish
        "ippo enna pannanum", "enna seiyanum", "aduthu enna pannanum", "ippo enna seivadhu"
    ],
    "F_REPLY": [
        # Tamil
        "பதில் அனுப்பலாமா", "மெசேஜ் அனுப்பலாமா", "ரிப்ளை பண்ணலாமா", "பதில் சொல்லலாமா",
        # English
        "can i reply", "should i reply to this", "can i respond", "shall i message them back", "can i send message back",
        # Tanglish
        "reply pannalama", "message anuppalama", "badhil anuppalama", "reply panlama", "response pannalama"
    ],
    "F_CALLNUM": [
        # Tamil
        "இந்த நம்பருக்கு கூப்பிடலாமா", "போன் பண்ணலாமா", "இந்த எண்ணை அழைக்கலாமா", "கால் செய்யலாமா",
        # English
        "can i call this number", "should i call them", "shall i dial this number", "can i phone them", "can i call back",
        # Tanglish
        "intha number ku call pannalama", "call pannalama", "phone pannalama", "dial pannalama", "call panlaama"
    ],
    "F_FROMBANK": [
        # Tamil
        "வங்கியிலிருந்து வந்ததா", "வங்கி தான் அனுப்புச்சா", "வங்கி செய்திதானா", "பேங்க்ல இருந்து வந்ததா",
        # English
        "is this from my bank", "did bank send this", "is it really from bank", "is this official bank message", "sent by my bank",
        # Tanglish
        "bank la irundhu vandhucha", "bank message thaana", "bank thaan anupucha", "bank lendhu vandhadha", "sbi la irundhu vandhucha"
    ],
    "F_SAFE": [
        # Tamil
        "safe-ஆ", "பாதுகாப்பானதா", "நம்பலாமா", "உண்மையானதா",
        # English
        "is this safe", "is it safe", "can i trust this", "is this genuine", "can i believe this",
        # Tanglish
        "safe aa", "nambalaama", "safe ah", "genuine ah", "trust pannalama"
    ],
    "F_REPORT": [
        # Tamil
        "எப்படி புகார் செய்வது", "புகார் கொடுக்கலாமா", "சைபர் கிரைம் புகார்", "போலீசில் புகார்", "புகார் செய்ய",
        # English
        "how to report", "how to complaint", "where to complain", "file cyber complaint", "report scam",
        # Tanglish
        "complaint epdi kodukurathu", "report panna", "complaint pannanum", "epdi report pandrathu", "police complaint epdi"
    ],
    "F_SHARE": [
        # Tamil
        "குடும்பத்துக்கு", "குடும்பத்திற்கு", "அம்மாவுக்கு", "குடும்ப அட்டை", "குடும்பத்தினர்",
        # English
        "send to family", "share with parents", "forward to family", "share card", "family warning", "share with family",
        # Tanglish
        "amma ku anuppanum", "kudumbathukku anupanum", "family ku share", "family share", "share pannanum", "family"
    ],
    "F_LEARN": [
        # Tamil
        "கற்றுக்கொள்", "இதை பற்றி சொல்லுங்க", "விளக்கமாக சொல்", "பயிற்சி கொடு",
        # English
        "teach me", "learn more", "tell me about this", "want to learn", "explain this scam",
        # Tanglish
        "idha pathi sollunga", "learn pannanum", "teach pannunga", "kattrukol", "katrukol"
    ],
    "F_REPEAT": [
        # Tamil
        "மறுபடி சொல்லுங்க", "மீண்டும் சொல்", "இன்னொரு முறை சொல்லுங்க", "திரும்ப சொல்லு",
        # English
        "repeat please", "say again", "tell me again", "repeat that", "say once more",
        # Tanglish
        "marubadi sollunga", "thirumba sollunga", "again sollunga", "once more sollunga"
    ],
    "F_WRONG": [
        # Tamil
        "தப்பா சொல்றீங்க", "தவறான முடிவு", "தப்பு", "நீ சொல்வது தவறு", "தப்பான தகவல்",
        # English
        "you are wrong", "this is wrong", "incorrect verdict", "wrong result", "not correct",
        # Tanglish
        "thappa solreenga", "wrong ah irukku", "thappu", "wrong verdict", "thappa irukku"
    ],
    "F_PRIVACY": [
        # Tamil
        "தகவல் சேமிக்கிறீங்களா", "விவரம் சேமிக்கப்படுமா", "ரகசியம் காக்கப்படுமா", "தனியுரிமை கொள்கை",
        # English
        "do you save my data", "is my data stored", "privacy policy", "do you store message", "my privacy",
        # Tanglish
        "en message save pannuveengala", "data save aaguma", "privacy enna", "details store aaguma", "privacy irukka"
    ],
}


def classify_intent(text: str) -> str:
    """
    Maps user text (typed or transcribed) to ONE intent ID using substring matching.
    Priority rule: text meaning 'I shared the OTP / clicked the link / installed AnyDesk / paid / gave card details'
    jumps to the matching INC_* reply, even with no prior verdict.
    If two intents match or none match, return F_UNKNOWN.
    """
    if not text or not text.strip():
        return "F_UNKNOWN"

    norm_text = text.lower().strip()

    # Step 1: Check emergency INC_* intents first (Priority Rule)
    is_passive_payment = any(p in norm_text for p in ["is paid", "was paid", "bill paid", "has been paid", "successfully paid", "thank you"])
    matched_inc: List[str] = []
    for intent_id, phrases in INC_KEYWORDS.items():
        if intent_id == "INC_PAID" and is_passive_payment:
            continue
        for phrase in phrases:
            # Substring matching (Never use \b on Tamil text)
            if phrase.lower() in norm_text:
                matched_inc.append(intent_id)
                break

    if len(matched_inc) == 1:
        return matched_inc[0]
    elif len(matched_inc) > 1:
        return "F_UNKNOWN"

    # Step 2: Check follow-up F_* intents
    matched_f: List[str] = []
    for intent_id, phrases in FOLLOWUP_KEYWORDS.items():
        for phrase in phrases:
            if phrase.lower() in norm_text:
                matched_f.append(intent_id)
                break

    if len(matched_f) == 1:
        return matched_f[0]

    # Zero or ambiguous matches default to F_UNKNOWN
    return "F_UNKNOWN"


# =====================================================================
# 3. SIGNAL TO REASON & SCAM TYPE TO TEACH MAPPINGS
# =====================================================================
SIGNAL_TO_REASON_ID: Dict[str, str] = {
    "URGENCY": "R_URGENT",
    "ASK_SENSITIVE": "R_OTP",
    "PIN_REQUEST": "R_UPI_COLLECT",
    "PAYMENT_PUSH": "R_UPI_COLLECT",
    "SHORTENER": "R_LINK_SHORT",
    "LOOKALIKE": "R_LINK_LOOK",
    "KNOWN_BAD": "R_KNOWN_BAD",
    "KYC_UPDATE": "R_KYC",
    "PRIZE": "R_PRIZE",
    "FEE_FIRST": "R_FEE_FIRST",
    "AUTHORITY": "R_AUTHORITY",
    "DIGITAL_ARREST": "R_AUTHORITY",
    "REMOTE_ACCESS": "R_APP",
    "JOB_TASK": "R_JOB",
    "INVEST": "R_INVEST",
    "CALLBACK": "R_PHONE",
    "USERINFO": "R_LINK_LOOK",
    "PUNYCODE": "R_LINK_LOOK",
    "IP_HOST": "R_LINK_LOOK",
    "BRAND_MISMATCH": "R_LINK_LOOK",
    "THREAT": "R_KYC",
}

SCAM_TYPE_TO_TEACH_ID: Dict[str, str] = {
    "kyc": "T_KYC",
    "otp": "T_OTP",
    "ask_sensitive": "T_OTP",
    "prize": "T_PRIZE",
    "authority": "T_AUTH",
    "digital_arrest": "T_AUTH",
    "job": "T_JOB",
    "job_task": "T_JOB",
    "invest": "T_INVEST",
    "upi_collect": "T_UPI",
    "pin_request": "T_UPI",
    "payment_push": "T_UPI",
    "fake_care": "T_CARE",
    "remote_access": "T_CARE",
}

SCAM_TYPE_TA_NAMES: Dict[str, str] = {
    "kyc": "KYC / வங்கி கணக்கு முடக்கம்",
    "otp": "OTP கோரிக்கை",
    "ask_sensitive": "ரகசிய விவரங்கள் கோரிக்கை",
    "prize": "பரிசு / லாட்டரி ஆசை",
    "authority": "போலீஸ் / அதிகாரி மிரட்டல்",
    "digital_arrest": "டிஜிட்டல் அரெஸ்ட் மிரட்டல்",
    "job": "பகுதிநேர வேலை வாய்ப்பு",
    "job_task": "டாஸ்க் / வீடியோ லைக் வேலை",
    "invest": "போலி முதலீடு / அதிக லாபம்",
    "upi_collect": "UPI பணம் பெறும் கோரிக்கை",
    "pin_request": "UPI PIN கோரிக்கை",
    "payment_push": "பணம் பெறும் கோரிக்கை",
    "fake_care": "போலி வாடிக்கையாளர் சேவை",
    "remote_access": "ஆபத்தான செயலி நிறுவல்",
    "unknown": "சந்தேகத்திற்கிடமான செய்தி",
}


# =====================================================================
# 4. IN-MEMORY SESSION STORE (Strict 30-minute Expiry)
# =====================================================================
@dataclass
class SessionData:
    verdict: Optional[str] = None          # "SCAM" | "SUSPICIOUS" | "NO_RED_FLAGS"
    scam_type: Optional[str] = None        # e.g. "kyc", "otp"
    signals: List[str] = field(default_factory=list) # Signal codes only (never user text)
    last_reply_id: Optional[str] = None    # ID of template reply sent
    last_reply_text: Optional[str] = None  # Template text sent (never raw user text)
    language: str = "ta"                   # "ta" | "en"
    updated_at: float = field(default_factory=time.time)

    def is_expired(self, max_age_seconds: float = 1800.0) -> bool:
        return (time.time() - self.updated_at) > max_age_seconds


class SessionStore:
    def __init__(self, max_age_seconds: float = 1800.0):
        self.max_age_seconds = max_age_seconds
        self._sessions: Dict[int, SessionData] = {}

    def get(self, chat_id: int) -> Optional[SessionData]:
        sess = self._sessions.get(chat_id)
        if sess is None:
            return None
        if sess.is_expired(self.max_age_seconds):
            del self._sessions[chat_id]
            return None
        return sess

    def update(
        self,
        chat_id: int,
        verdict: Optional[str] = None,
        scam_type: Optional[str] = None,
        signals: Optional[List[str]] = None,
        last_reply_id: Optional[str] = None,
        last_reply_text: Optional[str] = None,
        language: Optional[str] = None
    ) -> SessionData:
        sess = self._sessions.get(chat_id)
        if sess is None or sess.is_expired(self.max_age_seconds):
            sess = SessionData()
            self._sessions[chat_id] = sess

        if verdict is not None:
            sess.verdict = verdict
        if scam_type is not None:
            sess.scam_type = scam_type
        if signals is not None:
            sess.signals = list(signals)
        if last_reply_id is not None:
            sess.last_reply_id = last_reply_id
        if last_reply_text is not None:
            sess.last_reply_text = last_reply_text
        if language is not None:
            sess.language = language
        sess.updated_at = time.time()
        return sess

    def clear(self, chat_id: int) -> None:
        if chat_id in self._sessions:
            del self._sessions[chat_id]


# Global session manager instance
session_manager = SessionStore(max_age_seconds=1800.0)


# =====================================================================
# 5. INTENT RESOLUTION & TEMPLATE FORMATTER
# =====================================================================
VERDICT_DEPENDENT_INTENTS: Set[str] = {"F_CLICK", "F_NAME", "F_WHY", "F_SAFE"}


def resolve_intent_response(
    intent_id: str,
    chat_id: int,
    session_store: Optional[SessionStore] = None,
    lang: Optional[str] = None
) -> Tuple[str, str, Optional[str]]:
    """
    Resolves an intent ID into:
    (reply_id, formatted_reply_text, tts_text) per user language (ta or en).

    Follow-ups that need a verdict (F_CLICK, F_NAME, F_WHY, F_SAFE) ask the user
    to send a message first if there is no active session.
    """
    store = session_store or session_manager
    sess = store.get(chat_id)
    resolved_lang = lang or (sess.language if sess and sess.language else "ta")
    lang_key = "en" if resolved_lang == "en" else "ta"

    def _get_txt(entry) -> str:
        if not entry:
            return ""
        if lang_key == "en" and entry.get("en"):
            return entry["en"]
        ta_val = entry.get("ta", "")
        if ta_val and ta_val != "MISSING - ask the team":
            return ta_val
        return entry.get("en", "")

    def _get_tts(entry) -> Optional[str]:
        if not entry:
            return None
        if lang_key == "en" and entry.get("tts_en"):
            return entry["tts_en"]
        ta_tts = entry.get("tts_ta") or entry.get("tts_text")
        if ta_tts and ta_tts != "MISSING - ask the team":
            return ta_tts
        return entry.get("tts_en")

    # Emergency INC_* cases: jump directly regardless of verdict
    if intent_id in INC_KEYWORDS:
        entry = get_reply(intent_id)
        if entry:
            return intent_id, format_template(_get_txt(entry)), _get_tts(entry)

    # Follow-ups that need a verdict
    if intent_id in VERDICT_DEPENDENT_INTENTS:
        if sess is None or sess.verdict is None:
            need_entry = get_reply("F_NEED_VERDICT")
            default_need = "Please send the message you want to check first." if lang_key == "en" else "முதலில் நீங்கள் சரிபார்க்க விரும்பும் செய்தியை எனக்கு அனுப்புங்கள்."
            text = format_template(_get_txt(need_entry)) if need_entry else default_need
            return "F_NEED_VERDICT", text, _get_tts(need_entry) if need_entry else text

    # Handle specific intents
    if intent_id == "F_CLICK":
        if sess.verdict in ("SCAM", "SUSPICIOUS"):
            entry = get_reply("F_CLICK_SCAM")
        else:
            entry = get_reply("F_CLICK_NOFLAG")
        return intent_id, format_template(_get_txt(entry)), _get_tts(entry)

    elif intent_id == "F_NAME":
        entry = get_reply("F_NAME")
        st_key = (sess.scam_type or "").lower()
        if lang_key == "en":
            scam_type_label = st_key.replace("_", " ").title() if st_key else "Suspicious Message"
        else:
            scam_type_label = SCAM_TYPE_TA_NAMES.get(st_key, "சந்தேகத்திற்கிடமான செய்தி")
        text = format_template(_get_txt(entry), scam_type_ta=scam_type_label, scam_type=scam_type_label)
        tts_tmpl = _get_tts(entry) or text
        return intent_id, text, format_template(tts_tmpl, scam_type_ta=scam_type_label, scam_type=scam_type_label)

    elif intent_id == "F_WHY":
        entry = get_reply("F_WHY")
        reasons: List[str] = []
        for code in sess.signals:
            rid = SIGNAL_TO_REASON_ID.get(code)
            if rid:
                r_entry = get_reply(rid)
                if r_entry:
                    r_txt = (r_entry.get("en_gloss") or r_entry.get("en")) if lang_key == "en" else r_entry.get("ta")
                    if r_txt and r_txt not in reasons:
                        reasons.append(r_txt)
        if not reasons:
            reasons = ["No specific risk codes were registered."] if lang_key == "en" else ["தெளிவான காரணக் குறியீடுகள் எதுவும் பதிவு செய்யப்படவில்லை."]
        reason_list = "\n".join(f"{i+1}. {r}" for i, r in enumerate(reasons[:3]))
        text = format_template(_get_txt(entry), reason_list=reason_list)
        tts_tmpl = _get_tts(entry) or text
        return intent_id, text, format_template(tts_tmpl, reason_list=reason_list)

    elif intent_id == "F_SAFE":
        entry = get_reply("F_SAFE")
        if lang_key == "en":
            verdict_sentences = {
                "SCAM": "This looks like a scam.",
                "SUSPICIOUS": "This looks suspicious.",
                "NO_RED_FLAGS": "No red flags were found in this message."
            }
        else:
            verdict_sentences = {
                "SCAM": "இது மோசடி போல் உள்ளது.",
                "SUSPICIOUS": "இது சந்தேகத்துக்குரியது.",
                "NO_RED_FLAGS": "இதில் எச்சரிக்கை அறிகுறிகள் எதுவும் கிடைக்கவில்லை."
            }
        v_sent = verdict_sentences.get(sess.verdict, "")
        text = format_template(_get_txt(entry), verdict_sentence=v_sent)
        tts_tmpl = _get_tts(entry) or text
        return intent_id, text, format_template(tts_tmpl, verdict_sentence=v_sent)

    elif intent_id == "F_LEARN":
        scam_type = (sess.scam_type if sess else None) or "kyc"
        teach_id = SCAM_TYPE_TO_TEACH_ID.get(scam_type.lower())
        if teach_id and get_reply(teach_id):
            entry = get_reply(teach_id)
            return teach_id, format_template(_get_txt(entry)), _get_tts(entry)
        else:
            entry = get_reply("S_COMING_SOON")
            return "S_COMING_SOON", format_template(_get_txt(entry)), _get_tts(entry)

    elif intent_id == "F_REPEAT":
        if sess and sess.last_reply_text:
            return "F_REPEAT", sess.last_reply_text, sess.last_reply_text
        else:
            need_entry = get_reply("F_NEED_VERDICT")
            default_need = "Please send the message you want to check first." if lang_key == "en" else "முதலில் நீங்கள் சரிபார்க்க விரும்பும் செய்தியை எனக்கு அனுப்புங்கள்."
            text = format_template(_get_txt(need_entry)) if need_entry else default_need
            return "F_NEED_VERDICT", text, _get_tts(need_entry) if need_entry else text

    elif intent_id == "F_SHARE":
        entry = get_reply("SHARE_CARD_OFFER")
        return "SHARE_CARD_OFFER", format_template(_get_txt(entry)), _get_tts(entry)

    # Standard F_* intents (F_TODO, F_REPLY, F_CALLNUM, F_FROMBANK, F_REPORT, F_WRONG, F_PRIVACY, F_UNKNOWN)
    entry = get_reply(intent_id)
    if entry:
        return intent_id, format_template(_get_txt(entry)), _get_tts(entry)

    # Fallback to F_UNKNOWN
    unknown_entry = get_reply("F_UNKNOWN")
    return "F_UNKNOWN", format_template(_get_txt(unknown_entry)), _get_tts(unknown_entry)
