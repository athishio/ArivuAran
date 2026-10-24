"""
Unit tests for Intent Classifier, Follow-up Dialogues, Emergency INC Cases, and Session Expiry.
Tests verify:
1. At least 5 unique custom phrasings per intent across Tamil, English, and Tanglish.
2. Emergency INC_* priorities fire without prior verdict.
3. Unrecognized input maps to F_UNKNOWN.
4. Verdict-dependent follow-ups require prior verdict and handle session expiration (30 mins).
"""

import os
import sys
import time
import pytest

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from engine.intents import (
    classify_intent,
    resolve_intent_response,
    SessionStore,
    INC_KEYWORDS,
    FOLLOWUP_KEYWORDS
)

# ---------------------------------------------------------------------------
# Custom Test Phrasings (Own phrasings, NOT copies from design doc)
# ---------------------------------------------------------------------------
INTENT_TEST_SAMPLES = {
    # Emergency INC_*
    "INC_OTP": [
        "நான் அவங்களுக்கு OTP சொல்லிட்டேன் என்ன பண்றது",
        "i already shared otp with the caller",
        "ayyo na otp share panniten bro",
        "i sent otp by mistake",
        "enoda secret otp kuduthuten",
    ],
    "INC_LINK": [
        "அந்த மோசடி லிங்க் ஓபன் பண்ணிட்டேன்",
        "i mistakenly clicked the link",
        "antha link kulla poiten enna aagum",
        "opened link sent in message",
        "naan antha link click paniten",
    ],
    "INC_ANYDESK": [
        "அவங்க சொன்னபடி செயலியை டவுன்லோட் செய்தேன்",
        "i downloaded apk file they told",
        "avan sonnan nu anydesk pottuten",
        "installed remote app on my mobile",
        "ayyo anydesk download panniten",
    ],
    "INC_PAID": [
        "நான் ஏற்கனவே பணம் கட்டிட்டேன்",
        "money gone from my account already",
        "gpay la panam kattiten",
        "already paid the fee",
        "ayyo kaasu anupiten bro",
    ],
    "INC_CARD": [
        "என் ஏடிஎம் கார்டு பின் சொல்லிட்டேன்",
        "i gave card details on call",
        "debit card number sollitten ippo enna panrathu",
        "entered card details on the site",
        "cvv solliten bayama irukku",
    ],

    # Follow-ups F_*
    "F_CLICK": [
        "இந்த லிங்க் ஓபன் பண்ணலாமா சொல்லுங்க",
        "can i open this link safely",
        "intha link click pannalama bro",
        "should i click to check",
        "link thirakkalama vendama",
    ],
    "F_NAME": [
        "இது என்ன வகை மோசடினு சொல்லுங்க",
        "what type of scam is this exactly",
        "idhu enna scam category",
        "tell me the name of the scam",
        "enna fraud idhu explain pannu",
    ],
    "F_WHY": [
        "இது ஏன் மோசடி என்று விளக்கம் கொடுங்கள்",
        "why is it a scam tell me",
        "ethukku scam nu solreenga",
        "what is the reason for suspicion",
        "reason sollunga please",
    ],
    "F_TODO": [
        "இப்போ நான் அடுத்து என்ன செய்ய வேண்டும்",
        "what should i do right now",
        "ippo enna seiyanum advise pannunga",
        "what action to take next",
        "aduthu enna pannanum சொல்லுங்க",
    ],
    "F_REPLY": [
        "அந்த மெசேஜ்க்கு பதில் சொல்லலாமா",
        "can i reply back to them",
        "avanukku message anuppalama",
        "should i reply to this sender",
        "badhil anuppalama vendama",
    ],
    "F_CALLNUM": [
        "மெசேஜ்ல இருக்கிற நம்பருக்கு போன் பண்ணலாமா",
        "can i call this number directly",
        "intha number ku call pannalama bro",
        "shall i dial this number once",
        "phone pannalama en a/c ku",
    ],
    "F_FROMBANK": [
        "இது நிஜமாவே வங்கியிலிருந்து வந்ததா",
        "is this from my bank actually",
        "sbi bank la irundhu vandhucha idhu",
        "did bank send this message to me",
        "bank message thaana confirm pannunga",
    ],
    "F_SAFE": [
        "இந்த செய்தி உண்மையானதா நான் நம்பலாமா",
        "is this safe to proceed",
        "idhu safe aa bro sollu",
        "can i trust this message completely",
        "nambalaama vendama",
    ],
    "F_REPORT": [
        "சைபர் கிரைம் புகார் செய்வது எப்படி",
        "how to report this fraud online",
        "complaint epdi kodukurathu சொல்லுங்க",
        "where to complain against this scam",
        "police complaint epdi pannanum",
    ],
    "F_SHARE": [
        "எங்க அம்மாவுக்கு இந்த எச்சரிக்கையை அனுப்பணும்",
        "send to family warning card",
        "amma ku anuppanum card kudunga",
        "share with parents for safety",
        "family ku share panna card venum",
    ],
    "F_LEARN": [
        "இதை பற்றி சொல்லுங்க விவரமா",
        "teach me more about this fraud",
        "idha pathi sollunga kathukuren",
        "want to learn how this works",
        "kattrukol mode open pannunga",
    ],
    "F_REPEAT": [
        "கடைசியா சொன்னதை மறுபடி சொல்லுங்க",
        "repeat please what you said",
        "marubadi sollunga keka mudila",
        "say once more slowly",
        "thirumba sollunga please",
    ],
    "F_WRONG": [
        "நீங்க சொல்வது தவறான முடிவு",
        "you are wrong about this message",
        "thappa solreenga ithu bank sms",
        "this is wrong result",
        "thappa irukku unga result",
    ],
    "F_PRIVACY": [
        "என் தகவல் சேமிக்கிறீங்களா ரகசியம் காக்கப்படுமா",
        "do you save my data or otp",
        "en message save pannuveengala bro",
        "is my data stored anywhere",
        "details store aaguma server la",
    ],
}


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("intent_id,phrasings", INTENT_TEST_SAMPLES.items())
def test_intent_phrasings_detection(intent_id, phrasings):
    """Test that at least 5 distinct phrasings per intent classify accurately."""
    assert len(phrasings) >= 5
    for phrase in phrasings:
        detected = classify_intent(phrase)
        assert detected == intent_id, f"Failed for phrase '{phrase}': expected {intent_id}, got {detected}"


def test_unknown_intent():
    """Unrecognized / unrelated inputs must map to F_UNKNOWN."""
    unknown_samples = [
        "what is the weather today in Madurai",
        "hello good morning bro",
        "cricket score update please",
        "how are you doing today",
        "சமையல் குறிப்பு சொல்லுங்க",
    ]
    for sample in unknown_samples:
        assert classify_intent(sample) == "F_UNKNOWN"


def test_emergency_inc_fires_without_prior_verdict():
    """Priority rule: INC_* fires immediately even when user has no prior session/verdict."""
    store = SessionStore(max_age_seconds=1800.0)
    chat_id = 999123

    # Ensure clean empty session
    assert store.get(chat_id) is None

    # User says emergency phrase
    intent = classify_intent("ayyo na otp share panniten bro")
    assert intent == "INC_OTP"

    reply_id, reply_text, _ = resolve_intent_response(intent, chat_id=chat_id, session_store=store)
    assert reply_id == "INC_OTP"
    assert "பதற வேண்டாம்" in reply_text
    assert "1930" in reply_text


def test_verdict_dependent_intents_require_prior_verdict():
    """Follow-ups (F_CLICK, F_NAME, F_WHY, F_SAFE) ask to send message first if no verdict exists."""
    store = SessionStore(max_age_seconds=1800.0)
    chat_id = 888456

    # Verify each verdict-dependent intent returns F_NEED_VERDICT when session is empty
    for intent_id in ["F_CLICK", "F_NAME", "F_WHY", "F_SAFE"]:
        reply_id, reply_text, _ = resolve_intent_response(intent_id, chat_id=chat_id, session_store=store)
        assert reply_id == "F_NEED_VERDICT"
        assert "செய்தியை எனக்கு அனுப்புங்கள்" in reply_text


def test_verdict_dependent_intents_with_active_verdict():
    """Follow-ups correctly adapt to the active session verdict and signals."""
    store = SessionStore(max_age_seconds=1800.0)
    chat_id = 777234

    # Setup active scam session
    store.update(
        chat_id=chat_id,
        verdict="SCAM",
        scam_type="kyc",
        signals=["KYC_UPDATE", "URGENCY", "LOOKALIKE"]
    )

    # 1. F_CLICK on SCAM -> F_CLICK_SCAM advice
    reply_id, reply_text, _ = resolve_intent_response("F_CLICK", chat_id=chat_id, session_store=store)
    assert reply_id == "F_CLICK"
    assert "லிங்கைத் திறக்காதீர்கள்" in reply_text

    # 2. F_NAME -> formats Tamil scam name
    reply_id, reply_text, _ = resolve_intent_response("F_NAME", chat_id=chat_id, session_store=store)
    assert reply_id == "F_NAME"
    assert "KYC" in reply_text

    # 3. F_WHY -> lists top reasons from signals
    reply_id, reply_text, _ = resolve_intent_response("F_WHY", chat_id=chat_id, session_store=store)
    assert reply_id == "F_WHY"
    assert "காரணங்கள் மீண்டும்" in reply_text

    # 4. F_SAFE -> affirms non-safe position
    reply_id, reply_text, _ = resolve_intent_response("F_SAFE", chat_id=chat_id, session_store=store)
    assert reply_id == "F_SAFE"
    assert '"பாதுகாப்பானது" என்று நான் சொல்ல மாட்டேன்' in reply_text


def test_session_expiry_30_minutes():
    """Session must expire after 30 minutes (1800s) and drop follow-up context."""
    store = SessionStore(max_age_seconds=1800.0)
    chat_id = 666789

    store.update(chat_id=chat_id, verdict="SCAM", scam_type="otp")
    sess = store.get(chat_id)
    assert sess is not None

    # Simulate 31 minutes passing
    sess.updated_at = time.time() - 1801.0

    # Getting expired session clears it and returns None
    assert store.get(chat_id) is None

    # Resolving verdict-dependent intent now requires sending message first
    reply_id, reply_text, _ = resolve_intent_response("F_CLICK", chat_id=chat_id, session_store=store)
    assert reply_id == "F_NEED_VERDICT"
