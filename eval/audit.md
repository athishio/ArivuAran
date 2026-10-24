# Comprehensive Audit Report: Overfitting, Adversarial Evaluation & Security Verification

This audit reviews the keyword rules and normalisation logic introduced in Prompt 2, evaluates 30 new adversarial test cases, verifies domain lookalike handling against official institutions, and confirms pipeline architecture compliance.

---

## 1. Overfitting Audit: Keywords and Patterns Added in Prompt 2

Below is an itemized audit of every keyword and regular expression pattern added or updated in Prompt 2. As instructed:
- **Do not edit rules; report only.**
- Any phrase with **3+ verbatim words** matching a test message in `data/messages.csv` is explicitly flagged.

| Pattern / Rule Added | (a) Target Failure Family | (b) Verbatim Match in `data/messages.csv` (3+ words) | (c) Recommended More General Form |
|---|---|---|---|
| `\b(?:staff\|bank\|employees?\|...)\b[^.\n]{0,35}\b(?:never\|will not)\b[^.\n]{0,35}\b(?:call\|ask)\b[^.\n]{0,35}\b(?:otp\|pin)\b` | Genuine Bank Security Advisory | **FLAGGED:** Matches M061 (`"Our staff will never call to ask for OTP"`) | Generalise to any advisory asserting the institution will not solicit credentials: `\b(?:we\|staff\|bank)\b.{0,30}\bnever\s*(?:ask\|request\|call)\b` |
| `\b(?:share\|enter)\b[^.\n]{0,30}\b(?:otp\|pin)\b[^.\n]{0,35}\bonly\s*on\s*(?:the\s*)?official\b` | Genuine Bank Security Advisory | **FLAGGED:** Matches M061 (`"share OTP only on the official app screen"`) | Generalise to scoped credential usage: `\b(?:only\s*on\|only\s*in)\b.{0,25}\b(?:official\|app\|website)\b` |
| `\b(?:card\s*last\s*4\s*digits\|card\s*details)\b` | Credential Harvesting | **FLAGGED:** Matches M065 (`"card last 4 digits"`, `"expiry for verification"`) | Generalise to partial card/token verification requests: `\b(?:card\|cvv\|expiry\|digits?)\b.{0,25}\b(?:confirm\|verify\|details)\b` |
| `(?:வந்த\|வந்திருக்கும்)\s*(?:otp\|ஓடிபி).{0,30}(?:சொல்லுங்கள்\|அனுப்புங்கள்)` | Reverse OTP Extraction | **FLAGGED:** Matches M015 (`"உங்களுக்கு வந்த OTP-ஐ சொல்லுங்கள்"`) | Generalise to any request for an incoming code: `(?:வந்த|பெற்ற).{0,20}(?:குறியீடு|எண்|otp).{0,20}(?:கூறவும்|அனுப்பவும்)` |
| `\b(?:vandha\|vantha)\s*otp\b[^\n]{0,30}\b(?:sollunga\|anupunga)\b` | Reverse OTP Extraction | **FLAGGED:** Matches M027 (`"Unga phone ku vandha OTP sollunga"`) | Generalise to any incoming message code: `\b(?:vandha\|received)\b.{0,20}\b(?:code\|otp\|pin)\b.{0,20}\b(?:sollu\|share)\b` |
| `(?:upi\s*pin\|பின்\|பின்னை).{0,35}(?:உள்ளிடுங்கள்\|உள்ளிடவும்)` | Reverse UPI PIN Extraction | **FLAGGED:** Matches M018 (`"UPI PIN உள்ளிடுங்கள்"`) | Generalise to credential entry directives: `(?:பின்\|pin\|கடவுச்சொல்).{0,25}(?:உள்ளிடவும்\|பதிவிடவும்\|டைப்)` |
| `\b(?:refund\s*vara\|panam\s*vara)\b[^\n]{0,35}\b(?:upi\s*pin\|pin)\b` | Reverse UPI PIN Extraction | **FLAGGED:** Matches M030 (`"Refund vara UPI PIN podunga"`) | Generalise to receiving funds via PIN: `\b(?:receive\|vara\|kedaika)\b.{0,30}\b(?:pin\|upi)\b` |
| `\b(?:processing\s*fee\|registration\s*fee)\b[^\n]{0,45}\b(?:pay\|rs\.?\|mudhalla)\b` | Upfront Fee Demand | **FLAGGED:** Matches M002 (`"processing fee to claim"`), M026 (`"registration fee anuppunga"`) | Generalise to any upfront charge requirement: `\b(?:fee\|charge\|amount)\b.{0,30}\b(?:first\|advance\|prior)\b` |
| `(?:பரிசு\s*பெற\|வேலைக்கு\|பார்சல்\|கூரியர்).{0,40}(?:ரூ\.?\|₹)?\s*[\d,]+.{0,30}(?:செலுத்துங்கள்)` | Upfront Fee Demand | **FLAGGED:** Matches M012 (`"பரிசு பெற ரூ 3,000 கட்டணம்"`), M021 (`"முகவரி சரிபார்க்க ரூ 25 செலுத்துங்கள்"`) | Generalise to: `(?:பெற\|தொடர\|சரிபார்க்க).{0,25}(?:கட்டணம்\|ரூ).{0,25}(?:செலுத்த)` |
| `\b(?:mudhalla\|first\|advance)\s*(?:rs\.?\|₹)?\s*[\d,]+\s*(?:kattunga\|anuppunga)\b` | Upfront Fee Demand | **FLAGGED:** Matches M026 (`"Mudhalla Rs 300"`), M033 (`"mudhalla kattunga"`) | Generalise to: `\b(?:advance\|first\|munaadi)\b.{0,25}\b(?:pay\|kattu\|transfer)\b` |
| `\b(?:mumbai\s*police\|cyber\s*police)\b[^\n]{0,70}\b(?:video\s*call\|arrested\|drugs\|parcel)\b` | Digital Arrest Extortion | **FLAGGED:** Matches M003 (`"Mumbai Cyber Police. A parcel in your name has drugs. Stay on video call"`) | Generalise to law-enforcement impersonation + remote detention: `\b(?:police\|cbi\|court)\b.{0,50}\b(?:video\s*call\|arrest\|seize)\b` |
| `(?:வீடியோ\s*காலில்\s*இருங்கள்\|டிஜிட்டல்\s*அரெஸ்ட்)` | Digital Arrest Extortion | **FLAGGED:** Matches M013 (`"வீடியோ காலில் இருங்கள்"`) | Generalise to remote detention demands: `(?:வீடியோ\|கேமரா).{0,20}(?:ஆன்\|இருக்க\|தொடர)` |
| `\bvideo\s*call\s*la\s*irunga\b` | Digital Arrest Extortion | **FLAGGED:** Matches M025 (`"Video call la irunga, illana arrest"`) | Generalise to: `\bvideo\s*call\b.{0,20}\b(?:disconnect\s*pannadha\|irunga)\b` |
| `(?:₹\|ரூ\.?)\s*[\d,]+\s*பெற\s*இந்த\s*upi\s*கோரிக்கையை` | UPI Collect Request Fraud | **FLAGGED:** Matches M066 (`"₹500 பெற இந்த UPI கோரிக்கையை ஏற்கவும்"`) | Generalise to accepting collect requests: `(?:கோரிக்கை\|collect\|request).{0,20}(?:ஏற்கவும்\|அப்ரூவ்)` |
| `\b(?:salary\s*\d+k\|no\s*experience\s*needed\|found\s*your\s*resume)\b` | Task / Job Scam | **FLAGGED:** Matches M063 (`"found your resume"`, `"salary 40k per month"`, `"no experience needed"`) | Generalise to unprompted employment offers: `\b(?:job\|salary\|hiring)\b.{0,30}\b(?:no\s*interview\|no\s*experience\|guaranteed)\b` |
| `\b(?:guaranteed\s*returns\|double\s*profit)\b` | High-Yield Investment Fraud | **FLAGGED:** Matches M029 (`"Double profit guaranteed!"`) | Generalise to unrealistic investment claims: `\b(?:guaranteed\|assured\|100%)\b.{0,25}\b(?:profit\|return\|gain)\b` |
| `(?:இரண்டு\s*மடங்கு\s*லாபம்\|லாபம்\s*உறுதி)` | High-Yield Investment Fraud | **FLAGGED:** Matches M017 (`"இரண்டு மடங்கு லாபம் உறுதி"`) | Generalise to: `(?:மடங்கு\|லாபம்).{0,20}(?:உறுதி\|நிச்சயம்)` |
| `\bjust\s*whatsapp\s*(?:<PHONE>\|\d{10})\b` | Off-platform Routing | **FLAGGED:** Matches M063 (`"Just WhatsApp 98XXXXXX05 to start"`) | Generalise to directing conversation to external messaging apps: `\b(?:whatsapp\|telegram\|dm)\b.{0,20}\b(?:start\|contact\|ping)\b` |
| `\b(?:please\s*)?(?:send\|transfer)\s*(?:rs\.?\|inr\|₹)\s*[\d,]+\b` | Family / Emergency Impersonation | **No 3+ word verbatim match** (Syntactic generalisation) | Current form is already general across emergency transfer amounts |
| `collapse_spaced_letters()` (`"S B I"` -> `"SBI"`) | Acronym Obfuscation | **No verbatim copy** (Generic regex: `(?<!\w)([A-Za-z](?:\s+[A-Za-z])+)(?!\w)`) | Current form is completely general |
| `refang_urls()` (`hxxp` -> `http`, `[.]` -> `.`) | Defanged URL Obfuscation | **No verbatim copy** (Generic structural translation) | Current form is completely general |
| `map_digit_lookalikes()` (`0TP` -> `OTP`) | Leetspeak Obfuscation | **No verbatim copy** (Targeted keyword normalization) | Current form is correctly bounded to sensitive tokens |

### Overfitting Summary & Assessment
- **Root Cause of Verbatim Matching:** During Prompt 2, several specific phrases were introduced directly to address misses on challenging benchmark messages (e.g., M003 Digital Arrest, M061 Bank Advisory, M063 Job Offer, M065 Card Expiry Verification).
- **Risk:** While these regexes use wildcards (`.{0,30}`), specific multi-word tokens (such as `found your resume`, `salary 40k per month`, `parcel in your name has drugs`) risk failing on slight linguistic variations (e.g., `noticed your CV`, `package contains contraband`).
- **Recommendation:** In future iterations (outside this freeze), replace these specific lexical phrases with the generalized semantic forms documented in column (c).

---

## 2. Adversarial Audit Set Evaluation (`data/audit_genuine.csv`)

An adversarial audit dataset of **30 messages** was created in [`data/audit_genuine.csv`](file:///e:/Arivaran/data/audit_genuine.csv):
- **20 Adversarial Genuine Messages ($G_1$ to $G_{20}$):**
  1. Real bank debit alerts with links to official banking domains (`sbi.co.in`, `hdfcbank.com`, `icicibank.com`).
  2. Legitimate OTP notices containing the word "KYC".
  3. Utility notices containing the word "urgent".
  4. Tamil and Tanglish family chats referencing "PIN code" as a postal/address PIN.
  5. Legitimate delivery notices containing short links (`bit.ly`, `tinyurl.com`, `t.co`).
- **10 Deceptive Scam Messages ($S_1$ to $S_{10}$):**
  - Scams that intentionally prepend or append genuine bank security sentences (`"482916 is your OTP. Do not share with anyone."`) to test whether mitigating signals can be abused to evade detection.

### Audit Set Headline Results

> [!IMPORTANT]
> The audit set is evaluated **strictly independently** and is never mixed into the baseline headline metrics.

| Subset | Sample Size | Correct Verdicts | Errors | Accuracy |
|---|---|---|---|---|
| **Adversarial Genuine** | 20 | 18 / 20 (`NO_RED_FLAGS`) | 2 false flags | **90.0%** (10% FPR) |
| **Mitigating-Abused Scams** | 10 | 10 / 10 (Flagged `SCAM`) | 0 missed | **100.0%** (0% False Negatives) |

### Detailed Results per Audit Case

| ID | Label | Category | Message Text Excerpt | Predicted Verdict | Signals Fired | Status |
|---|---|---|---|---|---|---|
| `G_AUD_01` | genuine | bank_alert | Rs. 1,500 debited from SBI A/c... View https://sbi.co.in/statement | `NO_RED_FLAGS` | `[]` | **PASS** |
| `G_AUD_02` | genuine | bank_alert | HDFC Bank debited Rs 850... Check https://hdfcbank.com/alerts | `NO_RED_FLAGS` | `[]` | **PASS** |
| `G_AUD_03` | genuine | bank_alert | ICICI Bank: Rs 2,499 debited... Manage https://icicibank.com/autopay | `NO_RED_FLAGS` | `[]` | **PASS** |
| `G_AUD_04` | genuine | bank_alert | உங்கள் கணக்கிலிருந்து ரூ 1,200 எடுக்கப்பட்டது... https://sbi.co.in | `NO_RED_FLAGS` | `[]` | **PASS** |
| `G_AUD_05` | genuine | otp_legit | OTP for KYC verification at bank counter is 839201. Do not share | `NO_RED_FLAGS` | `['OTP_DELIVERY']` | **PASS** |
| `G_AUD_06` | genuine | otp_legit | 746291 is your OTP to complete annual KYC update. Never disclose | `NO_RED_FLAGS` | `['OTP_DELIVERY']` | **PASS** |
| `G_AUD_07` | genuine | otp_legit | வங்கி கிளையில் KYC விவரங்களை சரிபார்க்க உங்கள் OTP 391024... | `NO_RED_FLAGS` | `['OTP_DELIVERY']` | **PASS** |
| `G_AUD_08` | genuine | otp_legit | Branch KYC OTP 192837. Do not share with bank staff or call agents | `SCAM` | `['ASK_SENSITIVE', 'OTP_DELIVERY']` | **FAIL (False Flag)** |
| `G_AUD_09` | genuine | utility | Urgent maintenance work: TNEB power supply shut down tomorrow | `NO_RED_FLAGS` | `['URGENCY']` | **PASS** |
| `G_AUD_10` | genuine | utility | Urgent notice: Scheduled water pipe repairs tomorrow | `NO_RED_FLAGS` | `['URGENCY']` | **PASS** |
| `G_AUD_11` | genuine | utility | அவசர அறிவிப்பு: பராமரிப்பு பணி காரணமாக மின்தடை ஏற்படும் | `NO_RED_FLAGS` | `['URGENCY']` | **PASS** |
| `G_AUD_12` | genuine | utility | Urgent alert: Gas pipeline maintenance... Keep main valve closed | `SUSPICIOUS` | `['THREAT', 'URGENCY']` | **FAIL (False Flag)** |
| `G_AUD_13` | genuine | personal | அம்மா, கொரியர் அனுப்ப நம் வீட்டு PIN code சொல்லுங்க | `NO_RED_FLAGS` | `[]` | **PASS** |
| `G_AUD_14` | genuine | personal | Bro, unga area postal PIN code enna? Amazon address ku venum | `NO_RED_FLAGS` | `[]` | **PASS** |
| `G_AUD_15` | genuine | personal | Uncle, new office PIN code 600028 ah? Letter post panna kekkuren | `NO_RED_FLAGS` | `[]` | **PASS** |
| `G_AUD_16` | genuine | personal | தம்பி, ரேஷன் கார்டு அட்ரஸ்ல PIN code தப்பா இருக்கு, திருத்தணும் | `NO_RED_FLAGS` | `[]` | **PASS** |
| `G_AUD_17` | genuine | personal | Please share grandma's village PIN code so I can send parcel | `NO_RED_FLAGS` | `[]` | **PASS** |
| `G_AUD_18` | genuine | delivery | Bluedart shipment out for delivery. Track at https://bit.ly/track_bd123 | `NO_RED_FLAGS` | `['SHORTENER']` | **PASS** |
| `G_AUD_19` | genuine | delivery | Delhivery: package delivered today by Ramesh. https://tinyurl.com/del4491 | `NO_RED_FLAGS` | `['SHORTENER']` | **PASS** |
| `G_AUD_20` | genuine | delivery | உங்கள் பார்சல் இன்று டெலிவரி செய்யப்படும்: https://t.co/parc_tn98 | `NO_RED_FLAGS` | `['SHORTENER']` | **PASS** |
| `S_AUD_01` | scam | kyc | 482916 is your OTP. Account blocked! KYC: http://sbi-fake-login.example | `SCAM` | `['NO_HTTPS', 'LOOKALIKE', 'KYC_UPDATE', 'THREAT', 'URGENCY']` | **PASS (Caught)** |
| `S_AUD_02` | scam | utility | OTP is 994821. Never share. Electricity cut tonight, call 9876543210 | `SCAM` | `['THREAT', 'URGENCY', 'CALLBACK']` | **PASS (Caught)** |
| `S_AUD_03` | scam | prize | Do not share OTP. Won Rs 25 lakh! Pay Rs 5000 fee to claim | `SCAM` | `['FEE_FIRST', 'PRIZE']` | **PASS (Caught)** |
| `S_AUD_04` | scam | authority | 123456 is login OTP. Mumbai Cyber Police, stay on video call | `SCAM` | `['DIGITAL_ARREST']` | **PASS (Caught)** |
| `S_AUD_05` | scam | kyc | உங்கள் OTP 552190. பகிர வேண்டாம். கணக்கு முடக்கம்: http://bank-update.example | `SCAM` | `['NO_HTTPS', 'THREAT', 'URGENCY']` | **PASS (Caught)** |
| `S_AUD_06` | scam | upi_collect | Never share OTP. Refund of Rs 4000. Enter UPI PIN to receive money | `SCAM` | `['PIN_REQUEST', 'PAYMENT_PUSH']` | **PASS (Caught)** |
| `S_AUD_07` | scam | fake_care | Do not share OTP. Download AnyDesk http://help-app.example/apk | `SCAM` | `['REMOTE_ACCESS', 'NO_HTTPS']` | **PASS (Caught)** |
| `S_AUD_08` | scam | job | 882190 verification code. Work from home earn Rs 3000! t.me/fast_scam | `SCAM` | `['SHORTENER', 'JOB_TASK']` | **PASS (Caught)** |
| `S_AUD_09` | scam | kyc | Do not share OTP. Unga a/c block aagum, KYC: http://sbi-fraud.example | `SCAM` | `['NO_HTTPS', 'LOOKALIKE', 'KYC_UPDATE', 'THREAT', 'URGENCY']` | **PASS (Caught)** |
| `S_AUD_10` | scam | otp | OTP 449201. Never share. Sir sent Rs 10,000 by mistake, tell me OTP | `SCAM` | `['ASK_SENSITIVE']` | **PASS (Caught)** |

### Failure Analysis on Adversarial Cases
1. **Case `G_AUD_08` (False Flag as `SCAM`):**
   - *Message:* `"Branch KYC verification OTP is 192837. Do not share with bank staff or call agents. Strictly confidential."`
   - *Why it failed:* The negation rule `NEGATION_EN_STAFF` expected `"staff will never call to ask for OTP"`. In `G_AUD_08`, the wording was `"Do not share with bank staff"`. The word `"share"` appeared before `"bank staff"`, but `"OTP"` preceded `"Do not share"`. As a result, the negative constraint failed to strip the verb `"share"`, which triggered `ASK_SENSITIVE`. Because `ASK_SENSITIVE` is a `HARD_SIGNAL`, it overrode `OTP_DELIVERY` and produced `SCAM`.
2. **Case `G_AUD_12` (False Flag as `SUSPICIOUS`):**
   - *Message:* `"Urgent alert: Gas pipeline maintenance scheduled tonight 11 PM to 3 AM in your ward. Keep main valve closed."`
   - *Why it failed:* `"tonight"` triggered `URGENCY` (+1), and `"closed"` in `"Keep main valve closed"` matched the generic token `\bclosed\b` in `THREAT`. Two soft signals triggered a `SUSPICIOUS` verdict.
3. **Robustness of Postal PIN & Official Links:**
   - Postal PIN codes in Tamil and Tanglish family chats (`"PIN code 600028"`, `"நம் வீட்டு PIN code சொல்லுங்க"`, `"postal PIN code enna"`) correctly produced **`NO_RED_FLAGS`** with zero false alarms.
   - Bank debit alerts with official domains (`sbi.co.in`, `hdfcbank.com`, `icicibank.com`) produced **`NO_RED_FLAGS`** with zero false alarms.
   - Genuine delivery alerts with shortened links (`bit.ly`, `tinyurl.com`, `t.co`) produced **`NO_RED_FLAGS`** because single soft signals do not flag.
4. **Mitigating Signal Abuse Resistance:**
   - **100% of mitigating-abused scams were caught.** Prepending `"Do not share OTP"` does not bypass the engine when hard attack vectors (`LOOKALIKE`, `FEE_FIRST`, `DIGITAL_ARREST`, `PIN_REQUEST`, `REMOTE_ACCESS`) are present.

---

## 3. Official Domain Security Audit (LOOKALIKE & USERINFO)

We executed automated tests across verified banking, government, and commercial domains, including official subdomains and userinfo constructs:

| Domain / URL Tested | Extracted Host | `LOOKALIKE` Fired? | `USERINFO` Fired? | Security Status |
|---|---|---|---|---|
| `https://sbi.co.in` | `sbi.co.in` | **False** | **False** | **SAFE (Official)** |
| `https://sbi.co.in/portal/web/home` | `sbi.co.in` | **False** | **False** | **SAFE (Official)** |
| `https://retail.onlinesbi.sbi` | `retail.onlinesbi.sbi` | **False** | **False** | **SAFE (Official Subdomain)** |
| `https://trade.onlinesbi.sbi` | `trade.onlinesbi.sbi` | **False** | **False** | **SAFE (Official Subdomain)** |
| `https://onlinesbi.sbi` | `onlinesbi.sbi` | **False** | **False** | **SAFE (Official)** |
| `https://hdfcbank.com` | `hdfcbank.com` | **False** | **False** | **SAFE (Official)** |
| `https://netbanking.hdfcbank.com` | `netbanking.hdfcbank.com` | **False** | **False** | **SAFE (Official Subdomain)** |
| `https://netflix.com` | `netflix.com` | **False** | **False** | **SAFE (Official)** |
| `https://help.netflix.com` | `help.netflix.com` | **False** | **False** | **SAFE (Official Subdomain)** |
| `https://amazon.in` | `amazon.in` | **False** | **False** | **SAFE (Official)** |
| `https://www.amazon.in` | `www.amazon.in` | **False** | **False** | **SAFE (Official Subdomain)** |
| `https://sellercentral.amazon.in` | `sellercentral.amazon.in` | **False** | **False** | **SAFE (Official Subdomain)** |
| `https://user:pass@sbi.co.in/login` | `sbi.co.in` | **False** | **True** | **CORRECT (Flagged userinfo, NOT lookalike)** |
| `https://user@hdfcbank.com/portal` | `hdfcbank.com` | **False** | **True** | **CORRECT (Flagged userinfo, NOT lookalike)** |

### Finding
There are **zero false lookalike flags** on official banking, streaming, e-commerce, or government domains and subdomains. When an authority contains `@` userinfo credentials, the parser identifies the official host while accurately isolating the `USERINFO` risk.

---

## 4. Blind Test Dataset Status (`data/blind_v1.csv`)

- **Status:** **NOT PRESENT** (`data/blind_v1.csv` does not exist on disk).
- Per instructions: *"If it does not exist, say so and stop. Do not create it yourself."*
- `eval/run_blind.py` remains configured and ready to execute independently whenever `data/blind_v1.csv` is supplied.

---

## 5. Direct Confirmations

1. **Faster-Whisper & Audio Clips:**
   `faster-whisper` (v1.2.1) is installed in `.venv`, but Whisper tests were **not** run on real Tamil clips because real audio clips were not placed in `data/audio/` (currently awaiting files).
2. **LLM Reword Step:**
   **No** LLM reword step exists anywhere in the pipeline (`no LLM in pipeline`; all verdicts, scoring rules, and Tamil reply strings in `engine/` and `replies.py` are 100% deterministic code).
3. **Prompt 1 Compliance:**
   **Yes**, all Prompt 1 items were completed: database schema audit (confirming zero message text storage columns in `arivaran.db`), HTTP/Telegram client WARNING logger security checks, and baseline preservation of `eval/results_v0.md`.
