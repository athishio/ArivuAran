# Project Status & Comprehensive Feature Ledger

**Project:** ARIVUARAN (அறிவுஅரண்)  
**Team:** INEVITABLE (Viksitthon 2026)  
**Updated:** 2026-10-24T03:22:00+05:30  
**Current Mode:** Production Hardened & Code Frozen (`USE_CLASSIFIER=false`)

---

## 1. Feature Status Matrix

| Feature | Status | Evidence File | Command / Test |
|---|---|---|---|
| **Text Verdicts** | **BUILT+TESTED** | `engine/decide.py`, `engine/scoring.py` | `pytest tests/test_engine.py` |
| **Both-Language Replies** | **BUILT+TESTED** | `data/replies.json`, `replies.py` | `pytest tests/test_audit_fixes.py::test_both_language_coverage_and_prohibited_words` |
| **Language Selection** | **BUILT+TESTED** | `bot.py`, `db.py` | `pytest tests/test_audit_fixes.py::test_first_run_language_prompt_and_flow` |
| **Routing Engine** | **BUILT+TESTED** | `engine/intents.py`, `bot.py` | `pytest tests/test_audit_fixes.py::test_routing_rule_short_intent_vs_verdict` |
| **INC Incident Flows** | **BUILT+TESTED** | `engine/intents.py`, `data/replies.json` | `pytest tests/test_intents.py` |
| **Interactive Buttons** | **BUILT+TESTED** | `telegram_io.py`, `bot.py` | `pytest tests/test_telegram.py::test_send_buttons` |
| **Session Expiry (30 min)** | **BUILT+TESTED** | `engine/intents.py` | `pytest tests/test_intents.py::test_session_expiry_30_minutes` |
| **Privacy Audit** | **BUILT+TESTED** | `eval/check_privacy.py`, `db.py` | `python eval/check_privacy.py` |
| **TTS + Cache + Fallbacks** | **BUILT+TESTED** | `tts.py`, `cache/audio/` | `pytest tests/test_tts_fallbacks.py` |
| **Pregenerated Audio** | **BUILT+TESTED** | `scripts/pregen_audio.py`, `cache/audio/` | `python scripts/pregen_audio.py` |
| **Demo Mode** | **BUILT+TESTED** | `bot.py`, `config.py` | `pytest tests/test_audit_fixes.py::test_demo_mode_command_and_canned_execution` |
| **Console Page** | **BUILT+TESTED** | `console.py`, `preview.html` | `python console.py` |
| **Preflight Check** | **BUILT+TESTED** | `scripts/preflight.py` | `python scripts/preflight.py` |
| **Voice Upload Retry** | **BUILT+TESTED** | `telegram_io.py` | `pytest tests/test_audit_fixes.py::test_voice_send_timeout_retry_and_fallback` |
| **Family Share Card** | **BUILT+TESTED** | `card_renderer.py` | `pytest tests/test_audit_fixes.py::test_family_card_html_and_png` |
| **Teach Mode** | **BUILT+TESTED** | `data/replies.json` (`T_*`) | `pytest tests/test_intents.py` |
| **Review Loop** | **BUILT+TESTED** | `bot.py`, `db.py` (`log_feedback`) | `pytest tests/test_telegram.py::test_buttons_inc_menu_and_cases` |
| **Live Stats Command** | **BUILT+TESTED** | `bot.py`, `db.py` (`get_stats`) | `pytest tests/test_telegram.py::test_commands` |
| **ML Text Classifier (clf_v1)** | **BUILT, OFF: 5 of 13 false positives on the held-out split, 73 training rows** | `models/clf_v1.joblib`, `models/clf_v1.json` | `python scripts/train_classifier.py` |
| **ML Text Classifier (clf_v2)** | **BUILT, OFF: zero gain over rules on held-out split (20/20 caught by rules alone), 372 training rows, threshold 0.70** | `models/clf_v2.joblib`, `models/clf_v2.json` | `python scripts/train_classifier_v2.py` |
| **Voice-In STT** | **BUILT NOT VERIFIED (unverified manifest)** | `speech.py`, `data/audio/manifest.csv` | `python scripts/eval_manifest.py` |
| **Screenshot OCR** | **BUILT NOT VERIFIED: no manifest** | `eval/ocr_raw_Ss-*.txt`, `data/images/` | `python scripts/verify_ocr_full.py` |
| **Fuzzy Matching (rapidfuzz)** | **NOT BUILT** | N/A | Excluded from requirements.txt; rules frozen |
| **Known-Bad Link Feeds** | **NOT BUILT** | N/A | Excluded; rules frozen |
| **WhatsApp Channel** | **PLANNED** | Architecture spec only | Non-goal for current release |
| **IVR / Phone Call** | **PLANNED** | Architecture spec only | Non-goal for current release |
| **Bhashini Integration** | **PLANNED** | Architecture spec only | Non-goal for current release |
| **LLM (any kind)** | **PLANNED** | Architecture spec only | Explicitly prohibited; deterministic rules only |

---

## 2. Benchmark & Evaluation Results

- **Held-Out Test Set (even split of messages.csv, n=33):**
  - Scams Caught: **20 of 20 (100.0% Recall)**
  - Genuine False Alarms: **0 of 13 (0.0% False Positive Rate)**
- **AI-Written Blind Evaluation Result (`data/blind_v1.csv`):**
  - **10 of 15 scams caught, 0 of 15 false alarms, n=30, AI-written, not independent**
  - Single run completed and permanently frozen.
- **Audit Genuine Evaluation (`data/audit_genuine.csv`, n=30):**
  - 11 of 30 flagged as SUSPICIOUS by rules due to unverified bank-style urgency keywords in genuine notifications.
  - Adding `clf_v2` produced 0 new false alarms at threshold 0.70, but caught 0 additional scams.

---

## 3. Known False Negatives & Under-Called Cases

- **`Ss-4.jpeg` (India Post parcel scam):**
  - Content: `India Post: Your parcel 1P88213907 is held at Chennai hub due to incomplete address. Pay Rs 25 redelivery fee within 12 hours or it will be returned and destroyed: http://indiapost-redelivery.example/pay`
  - Current Verdict: `SUSPICIOUS` (Score: 2, Signals: `['NO_HTTPS', 'URGENCY']`).
  - Analysis: Did not trigger `FEE_FIRST` because "redelivery fee" was not matched by advance fee regex. Under-called as SUSPICIOUS rather than SCAM. Engine rules frozen.

---

## 4. Tamil Review Items (`needs_native_review`)
Listed in detail in `docs/tamil_review_items.md`:
1. `பூஜ்ஜியம்` vs `சைபர்` for spoken digit 0 in `1930`.
2. `"மேலும் என்ன தெரிந்துகொள்ள வேண்டும்?"` post-verdict follow-up phrasing.
3. `அறிவுஅரண்` vs `அறிவு அரண்` spacing/declension.
4. Incident colloquialisms (`INC_OTP`, `INC_LINK`, `INC_ANYDESK`, `INC_PAID`, `INC_CARD`).
5. Thirukkural 421 translation & attribution.
6. `S_VOICE_RETRY` & `S_VOICE_NO_VERDICT`: Tamil strings pending native review; English shown to users until reviewed.

---

## 5. Voice Manifest & STT Evaluation (`data/audio/manifest.csv`)

`data/audio/manifest.csv` contains 4 real clips. All rows are explicitly marked `verified: no` with speaker notes citing uncorrected speech, cut-off audio, and colloquial wording. Voice-in status remains **BUILT NOT VERIFIED (unverified manifest)** and `VOICE_IN_ENABLED = False`.

### 5.1 Empirical Evaluation Against `manifest.csv`
- **Audio-1.ogg (11.2s, describes message; contains non-Tamil letter; needs speaker correction):**
  - Reference: `எனக்கு ஒரு பட்டியிலிருந்து ஒரு குறுஞ்செய்து வந்திருக்கு அந்த குறுஞ்செய்து வந்து அந்த லிக்கைத் தொடல்லனா என் அக்கோண்ட் பிடிக்கும் அப்படிச் சொல்லிட்டு போட்டுருக்கேன் இது ஸ்கேம் குறுञ்செய்தா இல்லையா?`
  - Reference Engine Verdict: `NO_RED_FLAGS` (Score: 0, Signals: NONE)
  - Model A (`faster-whisper-small`): WER = 72.7%, CER = 40.0% | Latency: 5.335s | Verdict: `NO_RED_FLAGS`
  - Model B (`whisper-tamil-small-ct2`): WER = 77.3%, CER = 52.3% | Latency: 3.848s | Verdict: `NO_RED_FLAGS`
- **Audio-2.ogg (20.8s, describes call; text cut off; needs speaker correction):**
  - Reference: `எனக்கு ஒரு கால் வந்துவிட்டது, அந்த கால்ல ஒரு பர்சன் நான் போலிஸ் இந்த மாதிரி உங்களுக்கு ஓட்டிப்பி வந்திருக்கோம் அந்த ஓட்டிப்பி நீங்கள் எனக்கு சொல்லுங்க இல்லையென்றால உங்கள் மேல ஒரு ராங் கேஸ் வயனாயிடும் நீங்க ஒரு வயன் கட்டுற மாதிரியாயிருக.`
  - Reference Engine Verdict: `NO_RED_FLAGS` (Score: 0, Signals: NONE)
  - Model A (`faster-whisper-small`): WER = 87.5%, CER = 54.0% | Latency: 9.339s | Verdict: `SCAM` (`ASK_SENSITIVE(+3)`)
  - Model B (`whisper-tamil-small-ct2`): WER = 75.0%, CER = 47.7% | Latency: 5.538s | Verdict: `NO_RED_FLAGS`
- **Audio-3.ogg (11.0s, describes link and 10k debit; unclear wording; needs speaker correction):**
  - Reference: `எனக்கு ஒரு என்பேன் ஏதோ மேசைக்கு வந்துச்சி ஏஸ்அம்ஸ்ல ஒரு லிக்கு அது தொட்டேன் என்று இருந்து பார்த்தான் பத்தாயர் வா டெபிட் தர்ந்து வருகிறது நான் என்ன பட்டுவது.`
  - Reference Engine Verdict: `NO_RED_FLAGS` (Score: 0, Signals: NONE)
  - Model A (`faster-whisper-small`): WER = 95.5%, CER = 68.6% | Latency: 4.961s | Verdict: `NO_RED_FLAGS`
  - Model B (`whisper-tamil-small-ct2`): WER = 86.4%, CER = 62.8% | Latency: 3.280s | Verdict: `NO_RED_FLAGS`
- **Audio-4.ogg (8.5s, describes link; asks if scam):**
  - Reference: `இந்த மாதிரி ஒரு லிங்க எதான் அனுப்பியுட்டு இன்டென்ச்சிப்புக்கு அந்த மாதிரி சேர சொல்றாங்க இது வந்து ஸ்கேமா இல்லையா.`
  - Reference Engine Verdict: `NO_RED_FLAGS` (Score: 0, Signals: NONE)
  - Model A (`faster-whisper-small`): WER = 66.7%, CER = 31.0% | Latency: 3.642s | Verdict: `NO_RED_FLAGS`
  - Model B (`whisper-tamil-small-ct2`): WER = 46.7%, CER = 15.0% | Latency: 3.609s | Verdict: `NO_RED_FLAGS`

### 5.2 Key Architectural Conclusions
1. **Safety Policy Validation:** All 4 reference texts in `manifest.csv` evaluate to `NO_RED_FLAGS` because victims narrate events second-hand. Giving `NO_RED_FLAGS` reassurance to spoken voice notes would create false security. The no-reassurance intercept (`S_VOICE_NO_VERDICT`: *"I can't reliably check a spoken description..."*) is essential.
2. **Model Selection:** Model A (`faster-whisper-small`) remains default in `speech.py`. Model B is faster and achieves lower WER on Audio-2, 3, 4, but outputs colloquial verb forms (`சொல்லுங்க`) that do not match frozen engine rules on Audio-2.
3. **Normaliser Hardening (`engine/voice_norm.py`):** Removed `"பின்" -> "PIN"` and common colloquial verbs (`சொல்லுங்க`, `அனுப்புங்க`, `குடுங்க`, `போடுங்க`). Only unambiguous loanword transliterations (`OTP`, `KYC`, `UPI`, `ATM`, `AnyDesk`, `SBI`, `police`) are retained. Verified that `"அதன் பின் நான் வந்தேன்"` is completely unchanged.
4. **Safety Status:** Reassurance rule strictly enforces `S_VOICE_NO_VERDICT` when benign. All voice interactions require explicit user button confirmation (`S_HEARD` -> `V_CONFIRM` / `V_RETRY`). Feature flag strictly disabled by default (`VOICE_IN_ENABLED = False`).
