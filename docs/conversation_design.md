# Conversation Design (Deliverable 1)

STATUS OF ALL TAMIL TEXT: needs native review.
Name placeholders: {BOT_NAME_TA} = அறிவுஅரண், {BOT_NAME_TA_GEN} = அறிவுஅரணின், {BOT_NAME_EN} = ARIVUARAN (from config.py).

## 0. Design rules

1. Fixed intents only. A user message (typed, or voice turned into text by Whisper) is matched to an intent ID by keyword substring matching. Do not use `\b` for Tamil.
2. Replies come from templates only. No LLM, no free-form advice.
3. If two intents match or none match, show buttons instead of guessing (F_UNKNOWN).
4. Session memory holds only the verdict, scam type and signal codes, never message text. Deleted after 30 minutes.
5. TTS rules. Each reply is spoken as written, after removing emoji and bullets and applying these replacements:

| Written | Spoken (TTS) |
|---|---|
| 1930 | ஒன்று ஒன்பது மூன்று பூஜ்யம் |
| cybercrime.gov.in | சைபர் கிரைம் டாட் ஜிஓவி டாட் இன் |
| OTP | ஓ டி பி |
| PIN | பின் |
| UPI | யூ பி ஐ |
| KYC | கே ஒய் சி |
| AnyDesk | எனிடெஸ்க் |

6. Never say "Safe". Never promise money will come back. Never give legal or financial advice.
7. For the "no red flags" verdict use the info icon or a white circle, never a green tick.

---

## 1. Verdict messages (VERDICT_*)

Slots: {reason1}, {reason2}, {reason3} come from the reason library (section 2), maximum 3.

| ID | Bot reply (Tamil) | English gloss |
|---|---|---|
| V_SCAM | ⚠️ **இது மோசடி போல் உள்ளது.**<br>காரணங்கள்:<br>1. {reason1}<br>2. {reason2}<br>செய்ய வேண்டியவை:<br>• லிங்கைத் தொடாதீர்கள்.<br>• OTP, PIN யாரிடமும் சொல்லாதீர்கள்.<br>• சந்தேகம் இருந்தால் உங்கள் வங்கியின் அதிகாரப்பூர்வ எண்ணை அழையுங்கள்.<br>மேலும் கேட்க: "ஏன்?" / "என்ன செய்வது?" | This looks like a scam. Reasons. Do: don't touch the link; never share OTP/PIN; call your bank's official number. You can ask "why?" / "what to do?" |
| V_SUSPICIOUS | 🟡 **இது சந்தேகத்துக்குரியது.**<br>இது மோசடியா என்று என்னால் உறுதியாகச் சொல்ல முடியவில்லை.<br>காரணங்கள்:<br>1. {reason1}<br>2. {reason2}<br>லிங்கைத் திறக்க வேண்டாம். உங்கள் வங்கியின் செயலியில் அல்லது அதிகாரப்பூர்வ இணையதளத்தில் நீங்களே பாருங்கள். OTP, PIN யாரிடமும் சொல்லாதீர்கள். | This is suspicious. I can't be sure. Reasons. Don't open the link; check in your bank's app or official site yourself. Never share OTP/PIN. |
| V_NOFLAG | ℹ️ **இதில் எச்சரிக்கை அறிகுறிகள் எதுவும் கிடைக்கவில்லை.**<br>ஆனால் இது பாதுகாப்பானது என்று அர்த்தம் இல்லை. தெரியாத எண்ணிலிருந்து வந்தால் கவனமாக இருங்கள். OTP, PIN யாரிடமும் சொல்லாதீர்கள். | No red flags found. That does not mean it is safe. Be careful if the number is unknown. Never share OTP/PIN. |
| V_UNREADABLE | உங்கள் செய்தியைப் படிக்க முடியவில்லை. தயவுசெய்து மீண்டும் அனுப்புங்கள் அல்லது செய்தியை எழுத்தில் ஒட்டுங்கள். | I couldn't read your message. Please resend or paste the text. |

---

## 2. Reason library (fixed strings)

| Code | Tamil | English gloss |
|---|---|---|
| R_URGENT | "உடனே", "இன்றே" என்று அவசரப்படுத்துகிறது. | It rushes you ("immediately", "today"). |
| R_OTP | OTP / PIN கேட்கிறது. | It asks for OTP/PIN. |
| R_LINK_SHORT | சுருக்கப்பட்ட லிங்க் உள்ளது. உண்மையான இணையதளம் மறைந்துள்ளது. | Shortened link hides the real site. |
| R_LINK_LOOK | லிங்க் வங்கியின் பெயரைப் போல் தோன்றுகிறது, ஆனால் உண்மையான முகவரி வேறு. | Link imitates a bank name but the real address differs. |
| R_KNOWN_BAD | இந்த லிங்க் மோசடி பட்டியலில் உள்ளது. | The link is on a known-bad list. |
| R_KYC | KYC புதுப்பிக்காவிட்டால் கணக்கு முடங்கும் என்று பயமுறுத்துகிறது. | Threatens account block unless KYC is updated. |
| R_PRIZE | பரிசு / லாட்டரி வென்றதாகச் சொல்கிறது. | Claims you won a prize/lottery. |
| R_FEE_FIRST | முதலில் பணம் அல்லது கட்டணம் கட்டச் சொல்கிறது. | Asks you to pay a fee first. |
| R_AUTHORITY | போலீஸ் / அதிகாரி என்று சொல்லி பயமுறுத்துகிறது. | Pretends to be police/officer and threatens. |
| R_APP | ஒரு செயலியை நிறுவச் சொல்கிறது. | Asks you to install an app. |
| R_JOB | வேலைக்காக முன்பணம் கேட்கிறது அல்லது எளிய வேலைக்கு அதிக பணம் தருவதாகச் சொல்கிறது. | Asks money for a job or promises high pay for easy tasks. |
| R_INVEST | உறுதியான அதிக லாபம் தருவதாகச் சொல்கிறது. | Promises guaranteed high returns. |
| R_UPI_COLLECT | பணம் "பெற" PIN போடச் சொல்கிறது. | Asks for PIN to "receive" money. |
| R_PHONE | செய்தியில் உள்ள எண்ணை அழைக்கச் சொல்கிறது. | Tells you to call a number in the message. |

---

## 3. Follow-up intents (after a verdict)

Keywords are examples. Add more after testing.

| ID | User says (Tamil / Tanglish) | Bot reply (Tamil) | English gloss |
|---|---|---|---|
| F_CLICK | "இந்த லிங்கை கிளிக் பண்ணலாமா?" / "link open pannalama?" / "click pannalaama" | **If Scam or Suspicious:** வேண்டாம். லிங்கைத் திறக்காதீர்கள்.<br>**If No red flags:** எச்சரிக்கை அறிகுறி இல்லை, ஆனால் உறுதி இல்லை. தெரியாத லிங்கில் OTP, PIN கொடுக்காதீர்கள். | No, don't open it. / No red flags, but not certain. Never give OTP/PIN on unknown links. |
| F_NAME | "இது என்ன மோசடி?" / "idhu enna scam?" / "scam peru enna" | இது "{scam_type_ta}" வகை மோசடி. தெரிந்துகொள்ள "கற்றுக்கொள்" என்று சொல்லுங்கள். | This is a "{type}" scam. Say "learn" to know more. |
| F_WHY | "ஏன் மோசடி?" / "yen scam?" / "why" / "reason sollunga" | காரணங்கள் மீண்டும்:<br>{reason list} | Reasons again. |
| F_TODO | "இப்போ என்ன பண்ணணும்?" / "ippo enna pannanum" / "what to do" | லிங்கைத் தொடாதீர்கள். பதில் அனுப்ப வேண்டாம். OTP, PIN சொல்லாதீர்கள். சந்தேகம் இருந்தால் வங்கியின் அதிகாரப்பூர்வ எண்ணை அழையுங்கள். | Don't touch the link, don't reply, don't share OTP/PIN, call your bank's official number. |
| F_REPLY | "பதில் அனுப்பலாமா?" / "reply pannalama" | வேண்டாம். பதில் அனுப்பினால் உங்கள் எண் செயலில் உள்ளது என்று அவர்களுக்குத் தெரியும். எண்ணை block செய்யலாம். | No. Replying tells them your number is active. You may block the number. |
| F_CALLNUM | "இந்த நம்பருக்கு கூப்பிடலாமா?" / "intha number ku call pannalama" | வேண்டாம். செய்தியில் உள்ள எண்ணை அழைக்காதீர்கள். உங்கள் வங்கி அட்டையில் அல்லது அதிகாரப்பூர்வ இணையதளத்தில் உள்ள எண்ணை மட்டும் அழையுங்கள். | Don't call the number in the message; use the number on your card or official site. |
| F_FROMBANK | "இது என் வங்கியிலிருந்து வந்ததா?" / "bank la irundhu vandhucha" | அனுப்பியவர் யார் என்று என்னால் உறுதிப்படுத்த முடியாது. உங்கள் வங்கியின் செயலியில் நீங்களே சரிபாருங்கள். | I can't confirm who sent it. Check in your bank's app yourself. |
| F_SAFE | "இது safe-ஆ?" / "safe aa?" / "nambalaama" | "பாதுகாப்பானது" என்று நான் சொல்ல மாட்டேன். {verdict sentence}. OTP, PIN யாரிடமும் சொல்லாதீர்கள். | I won't say "safe". {verdict}. Never share OTP/PIN. |
| F_REPORT | "எப்படி புகார் செய்வது?" / "complaint epdi kodukurathu" / "report panna" | பணம் போயிருந்தால் உடனே 1930-ஐ அழையுங்கள். இணையத்தில் cybercrime.gov.in-ல் புகார் செய்யலாம். புகாரை நான் பதிவு செய்ய மாட்டேன்; நீங்களே செய்ய வேண்டும். செய்திகளை அழிக்காமல் வைத்திருங்கள். | If money is lost call 1930; report on cybercrime.gov.in. I don't file complaints; keep the messages. |
| F_SHARE | "குடும்பத்துக்கு அனுப்பணும்" / "amma ku anuppanum" / "share" | உங்கள் குடும்பத்துக்கு எச்சரிக்கை அட்டை தயார் செய்கிறேன். அனுப்புவதா வேண்டாமா என்பது உங்கள் விருப்பம். | I'll make a warning card. Whether to forward is your choice. |
| F_LEARN | "கற்றுக்கொள்" / "idha pathi sollunga" / "teach me" | (plays the teach-mode lesson for the scam type, section 5) | |
| F_REPEAT | "மறுபடி சொல்லுங்க" / "marubadi sollunga" / "repeat" | (replays the last reply; offers a slower voice) | |
| F_WRONG | "தப்பா சொல்றீங்க" / "thappa solreenga" / "wrong" | மன்னிக்கவும். நான் தவறு செய்திருக்கலாம். உங்கள் செய்தியை அனுப்பாமல், இந்த முடிவு தவறு என்று மட்டும் பதிவு செய்கிறேன். பதிவு செய்யலாமா? [ஆம்] [வேண்டாம்] | Sorry, I may be wrong. I'll record only that this verdict was wrong, without your message. OK? |
| F_PRIVACY | "என் தகவல் சேமிக்கிறீங்களா?" / "en message save pannuveengala" | உங்கள் செய்தி, எண், OTP எதையும் நான் சேமிப்பதில்லை. மோசடி வகை, நேரம் போன்ற பெயர் இல்லாத எண்ணிக்கை மட்டும் சேமிக்கப்படும். | I don't store your message, number or OTP. Only anonymous counts (type, time). |
| F_UNKNOWN | (anything else) | மன்னிக்கவும், புரியவில்லை. கீழே உள்ள பொத்தான்களில் ஒன்றைத் தேர்ந்தெடுங்கள். | Sorry, didn't understand. Pick a button. |

---

## 4. "I already..." cases (INC_*)

Calm tone, 3 to 4 short steps, never promise a refund, the bot files nothing.

| ID | User says (Tamil / Tanglish) | Bot reply (Tamil) | English gloss |
|---|---|---|---|
| INC_OTP | "OTP சொல்லிட்டேன்" / "otp sollitten" / "otp share panniten" | பதற வேண்டாம். இப்போது இதைச் செய்யுங்கள்:<br>1. உங்கள் வங்கியின் அதிகாரப்பூர்வ உதவி எண்ணை உடனே அழைத்து, நடந்ததைச் சொல்லுங்கள். அட்டை / UPI-ஐ நிறுத்த முடியுமா என்று கேளுங்கள்.<br>2. பணம் போயிருந்தால் உடனே 1930-ஐ அழையுங்கள்.<br>3. செய்திகளையும் திரைப்பிடிப்புகளையும் அழிக்காதீர்கள். | Don't panic. 1) Call your bank's official helpline, ask if card/UPI can be stopped. 2) If money is gone, call 1930. 3) Keep messages and screenshots. |
| INC_LINK | "லிங்க் கிளிக் பண்ணிட்டேன்" / "link click panniten" | இதுவரை பணம் போகவில்லை என்றால் பதற வேண்டாம்.<br>1. அந்தப் பக்கத்தில் எதுவும் உள்ளிடாதீர்கள். மூடிவிடுங்கள்.<br>2. OTP, PIN, கடவுச்சொல் உள்ளிட்டிருந்தால் வங்கியின் அதிகாரப்பூர்வ எண்ணை அழையுங்கள்.<br>3. பணம் போயிருந்தால் 1930. | If no money lost, don't panic. 1) Close the page, enter nothing. 2) If you typed OTP/PIN/password, call your bank. 3) If money is gone, 1930. |
| INC_ANYDESK | "AnyDesk போட்டுட்டேன்" / "anydesk install panniten" / "remote app install panniten" | இது ஆபத்தானது. உடனே செய்யுங்கள்:<br>1. இணையத்தை அணையுங்கள் (Wi-Fi, மொபைல் டேட்டா).<br>2. அந்தச் செயலியை மூடி, நீக்குங்கள்.<br>3. வங்கி செயலிகளைத் திறக்காதீர்கள்.<br>4. முடிந்தால் வேறு போனிலிருந்து வங்கியின் அதிகாரப்பூர்வ எண்ணையும் 1930-ஐயும் அழையுங்கள். | Dangerous. 1) Turn off internet. 2) Close and delete the app. 3) Don't open banking apps. 4) If possible, from another phone call your bank and 1930. |
| INC_PAID | "பணம் அனுப்பிட்டேன்" / "panam anuppiten" / "paisa pochu" / "paid" | நேரம் மிக முக்கியம். உடனே:<br>1. 1930-ஐ அழையுங்கள்.<br>2. உங்கள் வங்கியின் அதிகாரப்பூர்வ உதவி எண்ணிலும் தெரிவியுங்கள்.<br>3. பிறகு cybercrime.gov.in-ல் புகார் செய்யலாம்.<br>4. பணப் பரிமாற்ற விவரம், செய்திகள், திரைப்பிடிப்புகளை அழிக்காமல் வைத்திருங்கள்.<br>பணம் திரும்பக் கிடைக்கும் என்று என்னால் உறுதி சொல்ல முடியாது. | Time matters. 1) Call 1930. 2) Tell your bank's official helpline. 3) Then report at cybercrime.gov.in. 4) Keep records. I can't promise a refund. |
| INC_CARD | "கார்டு நம்பர் சொல்லிட்டேன்" / "card details kuduthuten" / "pin sollitten" | உடனே உங்கள் வங்கியின் அதிகாரப்பூர்வ எண்ணை அழைத்து, அட்டையை நிறுத்தச் சொல்லுங்கள். பணம் போயிருந்தால் 1930-ஐ அழையுங்கள். செய்திகளை அழிக்காதீர்கள். | Call your bank now, ask to stop the card. If money is gone, call 1930. Keep messages. |

Rule: if the user types paid / OTP shared / AnyDesk / card details at any time, even without a prior verdict, jump to the matching INC_* reply.

---

## 5. Teach mode (about 20 seconds of audio each)

| ID | Scam type | Lesson text (Tamil, also the TTS) | English gloss |
|---|---|---|---|
| T_KYC | KYC / bank block | வங்கியிலிருந்து என்று சொல்லி, "KYC புதுப்பிக்காவிட்டால் கணக்கு முடங்கும்" என்று செய்தி வரும். அதில் ஒரு லிங்க் இருக்கும். அதைத் தொடாதீர்கள். லிங்க் மூலம் OTP, PIN கேட்டால் அது மோசடி. வங்கிக் கிளைக்குச் செல்லுங்கள் அல்லது வங்கி செயலியில் நீங்களே பாருங்கள். | "Bank" SMS says KYC pending, account will be blocked, with a link. Don't touch it. OTP/PIN via link = scam. Go to branch or check the app yourself. |
| T_OTP | OTP request | OTP என்பது உங்கள் பணத்தின் சாவி. வங்கி ஊழியர், கூரியர், யாராக இருந்தாலும் OTP கேட்டால் சொல்லாதீர்கள். "தவறுதலாக அனுப்பிவிட்டேன்" என்றும் கேட்பார்கள். சொன்னால் பணம் போகலாம். | OTP is the key to your money. Never tell anyone. They may say "sent by mistake". |
| T_PRIZE | Prize / lottery | "நீங்கள் பரிசு வென்றீர்கள்" என்று செய்தி வரும். பரிசு பெற முதலில் கட்டணம் அல்லது வரி கட்டச் சொல்வார்கள். நீங்கள் எந்தப் போட்டியிலும் கலந்துகொள்ளவில்லை என்றால், அது மோசடி. பணம் அனுப்பாதீர்கள். | "You won!" Then they ask for a fee. If you entered nothing, it's a scam. Send no money. |
| T_AUTH | Authority impersonation ("digital arrest") | போலீஸ் அல்லது அதிகாரி என்று போனில் அழைத்து, "உங்கள் மேல் வழக்கு" என்று பயமுறுத்தி, பணம் கேட்பார்கள். வீடியோ காலில் இருக்கச் சொல்வார்கள். பதற வேண்டாம். போனை வைத்துவிடுங்கள். குடும்பத்தாரிடம் சொல்லுங்கள். 1930-ஐ அழையுங்கள். | Callers pose as police, threaten, demand money, keep you on video call. Hang up, tell family, call 1930. |
| T_JOB | Job tasks | "வீட்டிலிருந்தே வேலை, வீடியோ லைக் செய்தால் பணம்" என்று செய்தி வரும். முதலில் சிறிய தொகை தருவார்கள். பிறகு "அதிக லாபத்துக்கு பணம் கட்டுங்கள்" என்பார்கள். வேலைக்காக முன்பணம் கேட்டால் நம்ப வேண்டாம். | "Work from home, like videos, get paid." Small payout first, then ask you to deposit. Don't trust upfront money for jobs. |
| T_INVEST | Investment tips | "இந்தப் பங்கில் போடுங்கள், இரட்டிப்பு லாபம்" என்று குழுக்களில் சொல்வார்கள். உறுதியான லாபம் என்று யாரும் சொல்ல முடியாது. அவசரப்படுத்தினால் நிறுத்துங்கள். பணம் போடும் முன் குடும்பத்தாரிடம் கேளுங்கள். | Groups promise doubled profit. No one can guarantee profit. If rushed, stop and ask family. |
| T_UPI | UPI collect request | UPI-ல் "பணம் பெற" என்று ஒரு கோரிக்கை வரும். PIN போட்டால் உங்கள் பணம் போகும். பணம் பெறுவதற்கு PIN தேவையில்லை. PIN கேட்டால் நிறுத்துங்கள். | A "request" arrives. Entering PIN sends your money. Receiving money needs no PIN. |
| T_CARE | Fake customer care | இணையத்தில் தேடி கிடைத்த வாடிக்கையாளர் சேவை எண் போலியாக இருக்கலாம். அவர்கள் AnyDesk போன்ற செயலியை நிறுவச் சொல்வார்கள். நிறுவ வேண்டாம். அதிகாரப்பூர்வ இணையதளம் அல்லது அட்டையில் உள்ள எண்ணை மட்டும் பயன்படுத்துங்கள். | Customer-care numbers found online may be fake. They ask you to install a remote app. Don't. Use the official site or card number. |

---

## 6. Family-share card (opt-in; the user taps and forwards)

Privacy rule: the card contains only the scam type and generic advice. No message text, no phone number, no user details. The bot never sends it to anyone else.

| Slot | Tamil | English gloss |
|---|---|---|
| Headline | ⚠️ மோசடி எச்சரிக்கை! | Scam warning! |
| Line 1 | இப்படி ஒரு செய்தி வந்தது: **{scam_type_ta}** | A message like this came: {type} |
| Line 2 | லிங்கைத் தொடாதீர்கள். OTP, PIN யாரிடமும் சொல்லாதீர்கள். | Don't touch links. Never share OTP/PIN. |
| Line 3 | பணம் போயிருந்தால் உடனே 1930. | If money is lost, call 1930 immediately. |
| Footer | {BOT_NAME_TA} ({BOT_NAME_EN}) | |

Short audio (about 10 seconds, TTS): "குடும்பத்தாருக்கு ஒரு எச்சரிக்கை. {scam_type_ta} என்ற மோசடி செய்தி வந்துள்ளது. லிங்கைத் தொடாதீர்கள். OTP, PIN யாரிடமும் சொல்லாதீர்கள். பணம் போயிருந்தால் ஒன்று ஒன்பது மூன்று பூஜ்யம்-ஐ அழையுங்கள்."

Caption for the forward: "இது உங்கள் பாதுகாப்புக்காக. தயவுசெய்து பாருங்கள் 🙏" (For your safety, please take a look.)

Bot message offering it: "இந்த எச்சரிக்கை அட்டையை உங்கள் குடும்பத்துக்கு அனுப்ப விரும்புகிறீர்களா? [அட்டையைப் பெறு] [வேண்டாம்]" (Want to send this warning card to family? [Get card] [No])

---

## 7. System messages and buttons

| ID | Tamil | English gloss |
|---|---|---|
| S_WELCOME | வணக்கம்! நான் {BOT_NAME_TA} ({BOT_NAME_EN}). சந்தேகமான SMS, லிங்க், படம் அல்லது குரல் செய்தியை எனக்கு அனுப்புங்கள். இது மோசடியா என்று தமிழில் சொல்கிறேன்.<br>அறிவற்றங் காக்கும் கருவி செறுவார்க்கும்<br>உள்ளழிக்கல் ஆகா அரண் — குறள் 421<br>OTP, PIN யாரிடமும் சொல்லாதீர்கள். | Hello! I'm {name}. Send me a suspicious SMS, link, image or voice note. Kural 421. Never share OTP/PIN. |
| S_HEARD | நான் கேட்டது: "{transcript}". சரியா? [சரி] [மீண்டும் சொல்கிறேன்] | I heard: "...". Correct? [Yes] [Say again] |
| S_OCR | படத்தில் நான் படித்தது:<br>"{ocr_text}"<br>சரியா? [சரி] [திருத்து] | Text I read from the image. Correct? [Yes] [Edit] |
| S_NOVOICE | குரலைப் புரிந்துகொள்ள முடியவில்லை. தயவுசெய்து மெதுவாக மீண்டும் சொல்லுங்கள் அல்லது எழுதுங்கள். | Couldn't understand audio. Please repeat slowly or type. |
| S_WORKING | சரிபார்க்கிறேன்… ஒரு நிமிடம். | Checking… one moment. |
| S_ERROR | மன்னிக்கவும், இப்போது சரிபார்க்க முடியவில்லை. சிறிது நேரம் கழித்து முயற்சிக்கவும். இதற்கிடையில்: லிங்கைத் தொடாதீர்கள், OTP சொல்லாதீர்கள். | Sorry, can't check now. Try later. Meanwhile don't touch the link, don't share OTP. |
| S_DISTRICT | உங்கள் மாவட்டத்தில் உள்ள மோசடிகள் பற்றி எச்சரிக்கை பெற விரும்புகிறீர்களா? உங்கள் மாவட்டத்தை மட்டும் சேமிப்போம், எண் அல்லது பெயர் அல்ல. [ஆம்] [வேண்டாம்] | Want alerts about scams in your district? We only store the district, not your number or name. |
| S_WRONG_OK | நன்றி. இந்த முடிவு தவறு என்று பதிவு செய்தேன். | Thanks. Recorded that this verdict was wrong. |
| S_FEEDBACK | 🙏 உங்கள் கருத்துக்கு நன்றி! இந்த முடிவை எங்கள் குழு மறுஆய்வு செய்து {BOT_NAME_TA_GEN} துல்லியத்தை மேலும் மேம்படுத்தும். | Thanks for your feedback. Our team will review this and improve accuracy. |
| S_COMING_SOON | இந்த வசதி விரைவில் வரும். | This feature is coming soon. |

Telegram buttons after a verdict: [ஏன்?] [என்ன செய்வது?] [கற்றுக்கொள்] [குடும்பத்துக்கு அனுப்பு] [நான் ஏற்கனவே…]
The last one opens a menu: OTP சொல்லிவிட்டேன் / லிங்க் திறந்தேன் / செயலி நிறுவினேன் / பணம் அனுப்பினேன் / கார்டு விவரம் கொடுத்தேன்

---

## 8. Open items (not verified)

- T_AUTH says only that callers who threaten and demand money look like scams. No legal claim is made about "digital arrest".
- INC_ANYDESK step order (delete the app vs keep evidence) needs a cyber-cell or police opinion.
- Confirm that 1930 and cybercrime.gov.in are still current before the demo.
- Bank advice is generic ("your bank's official number"). No bank numbers are listed.
- The name spellings அறிவுஅரண் and அறிவுஅரணின் need confirmation from a Tamil reviewer.

## 9. Native-review checklist

1. Is the tone respectful (the "நீங்கள்" form throughout)?
2. Are "மோசடி", "எச்சரிக்கை" and "திரைப்பிடிப்பு" natural for rural and elderly users, or would they say "ஸ்கிரீன்ஷாட்"?
3. Do the TTS replacements sound natural with the Pallavi and Valluvar voices?
4. Are the reasons short enough to listen to?
5. Does the Kural 421 text match the source exactly?