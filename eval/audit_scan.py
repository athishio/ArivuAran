import sys
import io
import csv
import re

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('data/messages.csv', encoding='utf-8') as f:
    messages = [(r['id'], r['text'].lower()) for r in csv.DictReader(f)]

# Detailed rules and patterns added or modified in Prompt 2
patterns_to_audit = [
    # 1. Negation
    {
        "pattern": r"\b(?:staff|bank|employees?|representative|official)\b[^.\n]{0,35}\b(?:never|will not|wont)\b[^.\n]{0,35}\b(?:call|ask|request)\b",
        "description": "Staff never calls to ask for OTP/PIN",
        "family": "Genuine Bank Security Advisory",
        "keywords": ["staff will never call to ask for otp"]
    },
    {
        "pattern": r"\b(?:share|enter)\b[^.\n]{0,30}\b(?:otp|pin)\b[^.\n]{0,35}\bonly\s*on\s*(?:the\s*)?official\b",
        "description": "Share OTP only on official app",
        "family": "Genuine Bank Security Advisory",
        "keywords": ["share otp only on the official"]
    },
    # 2. ASK_SENSITIVE
    {
        "pattern": r"\b(?:card\s*last\s*4\s*digits|card\s*details)\b",
        "description": "Confirm card last 4 digits / expiry",
        "family": "Credential Harvesting",
        "keywords": ["card last 4 digits", "confirm your card", "expiry for verification"]
    },
    {
        "pattern": r"(?:வந்த|வந்திருக்கும்|வந்த\s*ரகசிய)\s*(?:otp|ஓடிபி).{0,30}(?:சொல்லுங்கள்|சொல்லவும்|அனுப்புங்கள்|பகிரவும்)",
        "description": "Tamil asking for received OTP",
        "family": "Reverse OTP Extraction",
        "keywords": ["வந்த otp சொல்லுங்கள்", "வந்த otp-ஐ சொல்லுங்கள்"]
    },
    {
        "pattern": r"\b(?:vandha|vantha)\s*otp\b[^\n]{0,30}\b(?:sollunga|anupunga|kudunga)\b",
        "description": "Tanglish asking for received OTP",
        "family": "Reverse OTP Extraction",
        "keywords": ["vandha otp sollunga"]
    },
    # 3. PIN_REQUEST
    {
        "pattern": r"(?:upi\s*pin|பின்|பின்னை|பின்\s*எண்).{0,35}(?:உள்ளிடுங்கள்|உள்ளிடவும்)",
        "description": "Tamil enter UPI PIN to receive money",
        "family": "Reverse UPI PIN Extraction",
        "keywords": ["upi pin உள்ளிடுங்கள்", "திரும்பப் பெற upi pin"]
    },
    {
        "pattern": r"\b(?:refund\s*vara|panam\s*vara|amount\s*vara)\b[^\n]{0,35}\b(?:upi\s*pin|pin)\b",
        "description": "Tanglish UPI PIN for refund",
        "family": "Reverse UPI PIN Extraction",
        "keywords": ["refund vara upi pin", "upi pin podunga"]
    },
    # 4. FEE_FIRST
    {
        "pattern": r"\b(?:processing\s*fee|registration\s*fee|advance\s*fee|claim\s*fee)\b",
        "description": "Advance fee / processing fee",
        "family": "Upfront Fee Demand",
        "keywords": ["processing fee to claim", "registration fee anuppunga", "fee kattunga"]
    },
    {
        "pattern": r"(?:பரிசு\s*பெற|வேலைக்கு|பார்சல்|கூரியர்|முகவரி\s*சரிபார்க்க).{0,40}(?:ரூ\.?|₹)?\s*[\d,]+.{0,30}(?:செலுத்துங்கள்|செலுத்தவும்|கட்டவும்)",
        "description": "Tamil fee demand for parcel/prize",
        "family": "Upfront Fee Demand",
        "keywords": ["பரிசு பெற ரூ", "முகவரி சரிபார்க்க ரூ", "பதிவுக் கட்டணம் செலுத்துங்கள்"]
    },
    {
        "pattern": r"\b(?:mudhalla|first|advance)\s*(?:rs\.?|₹)?\s*[\d,]+\s*(?:kattunga|anuppunga|pay\s*pannunga)\b",
        "description": "Tanglish advance payment demand",
        "family": "Upfront Fee Demand",
        "keywords": ["mudhalla rs 300", "mudhalla kattunga"]
    },
    # 5. DIGITAL_ARREST
    {
        "pattern": r"\b(?:cbi|crime\s*branch|mumbai\s*police|delhi\s*police|cyber\s*police|customs\s*officer|trai|narcotics)\b[^\n]{0,70}\b(?:video\s*call|arrested|arrest|warrant|drugs|illegal|parcel\s*in\s*your\s*name)\b",
        "description": "Digital arrest coercion with authority + video call / drugs",
        "family": "Digital Arrest Extortion",
        "keywords": ["mumbai cyber police", "parcel in your name has drugs", "stay on video call"]
    },
    {
        "pattern": r"(?:வீடியோ\s*காலில்\s*இருங்கள்|டிஜிட்டல்\s*அரெஸ்ட்)",
        "description": "Tamil stay on video call",
        "family": "Digital Arrest Extortion",
        "keywords": ["வீடியோ காலில் இருங்கள்"]
    },
    {
        "pattern": r"\bvideo\s*call\s*la\s*irunga\b",
        "description": "Tanglish stay on video call",
        "family": "Digital Arrest Extortion",
        "keywords": ["video call la irunga"]
    },
    # 6. PAYMENT_PUSH
    {
        "pattern": r"(?:₹|ரூ\.?)\s*[\d,]+\s*பெற\s*இந்த\s*upi\s*கோரிக்கையை",
        "description": "Tamil accept UPI request to receive money",
        "family": "UPI Collect Request Fraud",
        "keywords": ["பெற இந்த upi கோரிக்கையை ஏற்கவும்"]
    },
    {
        "pattern": r"\b(?:please\s*)?(?:send|transfer)\s*(?:rs\.?|inr|₹)\s*[\d,]+\b",
        "description": "Emergency cash transfer demand",
        "family": "Family Impersonation / Emergency Fraud",
        "keywords": ["please send rs 15000"]
    },
    # 7. JOB_TASK
    {
        "pattern": r"\b(?:salary\s*\d+k|no\s*experience\s*needed|found\s*your\s*resume)\b",
        "description": "Unsolicited job offer tokens",
        "family": "Task / Job Scam",
        "keywords": ["salary 40k per month", "no experience needed", "found your resume"]
    },
    # 8. INVEST
    {
        "pattern": r"\b(?:guaranteed\s*returns|double\s*(?:your\s*)?money|double\s*profit|vip\s*stock)\b",
        "description": "Guaranteed profit / double return tokens",
        "family": "High-Yield Investment Fraud",
        "keywords": ["guaranteed 200 return", "double profit guaranteed"]
    },
    {
        "pattern": r"(?:இரண்டு\s*மடங்கு\s*லாபம்|லாபம்\s*உறுதி)",
        "description": "Tamil double profit guaranteed",
        "family": "High-Yield Investment Fraud",
        "keywords": ["இரண்டு மடங்கு லாபம் உறுதி"]
    },
    # 9. CALLBACK
    {
        "pattern": r"\bjust\s*whatsapp\s*(?:<PHONE>|\d{10}|[6-9]\d[Xx*]{6}\d{2})\b",
        "description": "WhatsApp contact directive",
        "family": "Unsolicited Communication / Off-platform Routing",
        "keywords": ["just whatsapp"]
    }
]

print(f"{'Audit Item':<35} {'Family':<30} {'Matched In messages.csv':<35}")
print("-" * 105)

for item in patterns_to_audit:
    matches = []
    for kw in item["keywords"]:
        for mid, text in messages:
            if kw.lower() in text:
                matches.append((mid, kw))
    
    match_str = ", ".join([f"{m[0]} ('{m[1]}')" for m in matches]) if matches else "None (General pattern)"
    print(f"{item['description']:<35} {item['family']:<30} {match_str:<35}")
