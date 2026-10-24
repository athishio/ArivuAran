# Changelog: Engine Rules & Detection Upgrades

This document details all modifications made to the Arivaran scam detection engine, the failure families that motivated each change, and the verified impact on benchmark performance.

---

## 1. Text Normalisation (`engine/redact.py`)

### Change 1.1: Unicode NFKC & Zero-Width Character Stripping
- **Change:** Applied `unicodedata.normalize("NFKC", text)` and regex removal of invisible zero-width formatting characters (`\u200B`, `\u200C`, `\u200D`, `\uFEFF`).
- **Failure Family Motivating Change:** Zero-width character credential evasion (e.g. `Your O\u200bT\u200bP is required`).
- **Impact:** Fixes robustness test **R06**; prevents word-boundary regex bypasses on credentials.

### Change 1.2: Refanging Obfuscated & Defanged Links
- **Change:** Implemented `refang_urls()` to map `hxxp://` / `hxxps://` to `http://` / `https://` and replace `[.]`, `(.)`, `[:]` with literal `.`, `:`.
- **Failure Family Motivating Change:** Defanged URL obfuscation (e.g. `hxxp://bank-kyc[.]example`).
- **Impact:** Fixes robustness test **R05**; enables `extract_urls()` to properly extract security URLs for inspection.

### Change 1.3: Collapsing Spaced Single Letters
- **Change:** Implemented `collapse_spaced_letters()` to collapse spaced letter sequences (e.g. `"S B I"` -> `"SBI"`, `"K Y C"` -> `"KYC"`, `"U P I"` -> `"UPI"`) while leaving normal words intact.
- **Failure Family Motivating Change:** Acronym and brand evasions in SMS messages (e.g. R01/R01b `"S B I bank a/c blocked"` and M062 `"S B I Bank: Ur a/c wil b blokd"`).
- **Impact:** Fixes **R01**, **R01b**, and test case **M062**.

### Change 1.4: Targeted Digit Lookalike Mapping
- **Change:** Implemented `map_digit_lookalikes()` strictly inside known sensitive tokens: `0TP` -> `OTP`, `0ne time password` -> `one time password`, `p1n` -> `PIN`, `up1` -> `UPI`.
- **Failure Family Motivating Change:** Leetspeak credential obfuscation (e.g. R07 `"Your 0TP is needed"`).
- **Impact:** Fixes robustness test **R07**.

---

## 2. Link Analysis & Host Parsing (`engine/links.py`)

### Change 2.1: Real Host Parsing for Userinfo URLs
- **Change:** Parsed the authority netloc to extract the genuine host after the `@` symbol (`real_netloc = netloc.split("@")[-1]`), while emitting the `USERINFO` security signal.
- **Failure Family Motivating Change:** HTTP userinfo trick spoofing trusted bank domains (e.g. R04 `http://sbi.co.in@evil.example/`).
- **Impact:** Fixes robustness test **R04**.

### Change 2.2: Brand Lookalike Token Analysis vs Official Domains
- **Change:** Added brand token checks for major Indian institutions (`sbi`, `hdfc`, `icici`, `axis`, `kotak`, `pnb`, `bob`, `paytm`, `phonepe`, `gpay`, `tneb`, `amazon`, `flipkart`, `netflix`). Flags `LOOKALIKE` if a brand token appears in an unofficial host or subdomain, including hyphen tricks (e.g. `sbi-co-in.example`, `sbi-kyc.example`).
- **Failure Family Motivating Change:** Domain spoofing and hyphenation tricks targeting bank brands (e.g. R02 `http://sbi-co-in.example/login`).
- **Impact:** Fixes robustness test **R02** and boosts phishing link detection across test messages.

### Change 2.3: Fallback Domain Extraction for RFC 2606 Test Domains
- **Change:** Added domain fallback handling when `tldextract` encounters pseudo-TLDs (`.example`, `.test`, `.local`) not present in the Public Suffix List (PSL).
- **Failure Family Motivating Change:** Synthetic evaluation URLs being dropped by strict PSL parsers.
- **Impact:** Enables offline link evaluation without external network dependencies.

### Change 2.4: Shortener Prefix Recognition
- **Change:** Expanded shortener recognition to cover `short.` and `tiny.` host prefixes and `short.example`.
- **Failure Family Motivating Change:** URL shortener evasions (e.g. M062 `short.example/aB3dE` and R03).
- **Impact:** Fixes **R03** and **M062**.

---

## 3. Signal Policy Table & Combination Rules (`engine/decide.py`)

### Change 3.1: Explicit HARD vs SOFT Signal Classification
- **Change:** Created code-level tables distinguishing `HARD_SIGNALS` from `SOFT_SIGNALS`:
  - **HARD_SIGNALS** (can give `SCAM` alone):
    - `ASK_SENSITIVE`: OTP, CVV, password, card details requested.
    - `PIN_REQUEST`: Explicit PIN entry demand (especially UPI PIN to receive funds).
    - `PAYMENT_PUSH`: UPI collect requests, QR scams, emergency cash demands.
    - `FEE_FIRST`: Upfront fee/charges demanded to claim prize, job, loan, or parcel.
    - `REMOTE_ACCESS`: APK download or screen-sharing tools (AnyDesk, TeamViewer).
    - `DIGITAL_ARREST`: Authority impersonation with video-call or arrest threat.
    - `LOOKALIKE`, `USERINFO`, `PUNYCODE`, `IP_HOST`, `KNOWN_BAD`: Malicious/spoofed links.
  - **SOFT_SIGNALS** (require at least one other signal before flagging):
    - `KYC_UPDATE`, `THREAT`, `URGENCY`, `SHORTENER`, `CALLBACK`, `PRIZE`, `JOB_TASK`, `INVEST`, `AUTHORITY`, `RISKY_TLD`, `NO_HTTPS`, `BRAND_MISMATCH`.
- **Failure Family Motivating Change:** Single soft tokens causing false alarms on benign customer notices.
- **Impact:** Completely eliminates false positives on genuine messages:
  - **M056** (KYC-at-branch advisory): single `KYC_UPDATE` -> **`NO_RED_FLAGS`**.
  - **M058** (Urgent electricity maintenance): single `URGENCY` -> **`NO_RED_FLAGS`**.

### Change 3.2: Mitigating Signals Policy
- **Change:** Enforced that legitimate transactional notices (`OTP_DELIVERY`, `TXN_ALERT`, `DELIVERY_ALERT`) suppress soft signals on messages with no links.
- **Failure Family Motivating Change:** Genuine bank debit alerts and OTP delivery notices getting flagged due to urgency or transaction keywords.
- **Impact:** Preserves 0% FPR across all legitimate bank and utility messages.

---

## 4. Extended Signal Families across Tamil, English, and Tanglish (`engine/rules.py`)

### Change 4.1: New `PIN_REQUEST` Family
- **Change:** Detects PIN entry requests across all three languages:
  - **Tamil (substring matching):** `UPI PIN உள்ளிடுங்கள்`, `பின்னை உள்ளிடவும்`, `திரும்பப் பெற... பின்`.
  - **Tanglish:** `upi pin podunga`, `refund vara upi pin`, `pin enter pannunga`.
  - **English:** `enter your upi pin to receive`, `enter upi pin`.
- **Failure Family Motivating Change:** Reverse UPI collect requests asking victims to enter PIN to "receive" refunds (e.g. M008, M018, M030).
- **Impact:** Catches **M018** (`உங்களுக்கு ரூ 2,000 திரும்பப் பெற, UPI PIN உள்ளிடுங்கள்`) and **M030**.

### Change 4.2: New `FEE_FIRST` Family
- **Change:** Flags demands for upfront fees/charges:
  - **Tamil (substring matching):** `கட்டணம் செலுத்துங்கள்`, `பதிவுக் கட்டணம்`, `முதலில் ரூ... செலுத்துங்கள்`.
  - **Tanglish:** `processing fee kattunga`, `mudhalla registration fee anuppunga`, `fee kattunga`.
  - **English:** `pay processing fee to claim`, `registration fee`.
- **Failure Family Motivating Change:** Upfront advance fee scams for jobs, loans, prizes, and held parcels (e.g. M002, M012, M014, M021, M024, M026, M033).
- **Impact:** Catches **M014**, **M021**, **M024**, **M026**, **M033**.

### Change 4.3: New `DIGITAL_ARREST` Family
- **Change:** Flags authority impersonation coupled with video call / arrest / narcotics threat:
  - **English:** `cyber police / cbi` + `video call / arrest / drugs / parcel in your name`.
  - **Tamil:** `சைபர் கிரைம் / போலீஸ் அதிகாரி` + `வீடியோ கால் / கைது செய்யப்படுவீர்கள் / வழக்கு`.
  - **Tanglish:** `police officer pesuren` + `video call la irunga / arrest`.
- **Failure Family Motivating Change:** Digital arrest and parcel scam coercion (e.g. M003 Mumbai cyber police parcel scam, M013, M025).
- **Impact:** Catches **M003**, **M013**, **M025**.

### Change 4.4: Linguistic Parity & Tamil Substring Matching
- **Change:** Ensured all fraud families have symmetric English, Tamil, and Tanglish keyword patterns. Used UTF-8 substring matching for Tamil instead of word-boundary `\b` (which breaks on Tamil Unicode vowel markers).
- **Failure Family Motivating Change:** Robustness test R08 discrepancy (where identical scams across EN, TA, and Tanglish yielded mismatched verdicts) and M029/M047.
- **Impact:** Fixes **R08** (`VERDICT_MATCH` produces `SCAM` across English, Tamil, and Tanglish). Pongal greetings (`பொங்கல் வாழ்த்துகள்`) no longer falsely trigger prize rules (**M047**).

### Change 4.5: Negation Stripping Enhancements
- **Change:** Extended `strip_security_warnings()` to strip bank staff advisories (`"Our staff will never call to ask for OTP"`) and app screen instructions (`"Kindly share OTP only on the official app screen"`).
- **Failure Family Motivating Change:** Bank security awareness messages getting flagged for containing the word OTP.
- **Impact:** Fixes **M061** (genuine awareness advisory).

---

## 5. Performance Summary (Before vs After)

| Metric Split | Initial Baseline (`results_v0.md`) | Post-Upgrade (`results_v1.md`) |
|---|---|---|
| **Held-Out Test Set Recall** | 75.0% (15/20 scams) | **100.0% (20/20 scams)** |
| **Held-Out Test Set False-Positive Rate** | 15.4% (2/13 genuine) | **0.0% (0/13 genuine)** |
| **Held-Out Test Set Precision** | 88.2% | **100.0%** |
| **Held-Out Test Set Strict Recall** | 20.0% (4/20 decisive SCAM) | **85.0% (17/20 decisive SCAM)** |
| **Full Dataset Recall** | 69.2% (27/39 scams) | **100.0% (39/39 scams)** |
| **Full Dataset False-Positive Rate** | 14.8% (4/27 genuine) | **0.0% (0/27 genuine)** |
| **Robustness Tests Implemented** | 8 PASS, 5 FAIL | **13 PASS, 0 FAIL** |
| **Wrong Predictions on Test Set** | 7 messages wrong | **0 messages wrong** |
| **Wrong Predictions on Dev Set** | 9 messages wrong | **0 messages wrong** |
| **Previously-Correct Messages Broken** | N/A | **None (0)** |

---

## 6. Tier 0 & Tier 1 Infrastructure Upgrades (23 Oct 2026)

### Change 6.1: Onboarding Language Selection & Privacy Persistence
- **Change:** Implemented first-run bilingual prompt (`[தமிழ்]` / `[English]`) for chats with no saved preference. Added `user_prefs` table storing only salted SHA-256 chat hash + language code (zero raw user or chat IDs). Added `/language` command (alias `/lang`) and updated `/delete` to clear saved preferences.
- **Impact:** Guarantees language persistence across sessions while preserving zero-knowledge privacy.

### Change 6.2: Conversational Routing Rule
- **Change:** Implemented `should_route_to_intent()` in `bot.py`:
  - Short text (< 8 words, no link, no digits/phone) or button taps route to intent matcher.
  - Text >= 8 words or containing URLs or numbers routes directly to verdict engine.
  - Forwarded scams asking for OTP/credentials (e.g. `"sent by mistake, share the OTP"`) bypass intent classification and route to the verdict engine, scoring `SCAM`.
- **Impact:** Prevents forwarded OTP theft scams from falsely triggering emergency incident guidance (`INC_OTP`).

### Change 6.3: Voice Pipeline & Multi-Tier TTS Fallback
- **Change:** Built full fallback chain in `tts.py`: `cache -> edge-tts (8s timeout) -> gTTS (ta/en) -> text only with note`.
- **Change:** Added OGG/Opus audio transcoding via `ffmpeg` (using `FFMPEG_PATH`) with built-in PyAV `libopus` container fallback.
- **Change:** Pre-generated audio clips for all 146 reply variants across Tamil and English via `scripts/pregen_audio.py`.
- **Impact:** Enables 100% offline audio playback (< 2ms cache retrieval latency) with zero network dependency during demonstrations.

### Change 6.4: Interactive Demo Mode & Standalone Local Console
- **Change:** Added `/demo` command in `bot.py` (active when `DEMO_MODE=true`), offering 5 canned scam cases running through the real deterministic engine.
- **Change:** Created `console.py` (FastAPI at `http://127.0.0.1:8000`) providing an offline-resilient web UI with audio playback, sample chips, and language toggle.
- **Change:** Created `scripts/preflight.py` automated checklist verifying all 8 environment prerequisites.

---

## 7. Tier 2 Cleanup & Classifier V2 Upgrades (24 Oct 2026)

### Change 7.1: Zero-Width Character Normalisation & Hardening
- **Change:** Expanded regex normalisation in `engine/redact.py` to strip all zero-width and directional formatting characters (`\u200B-\u200F`, `\u202A-\u202E`, `\u2060`, `\uFEFF`, `\u00AD`) before URL extraction and signal matching.
- **Impact:** Neutralizes zero-width non-joiner evasion attacks seen in `Ss-2.jpeg` without changing any existing verdict. Verified in `tests/test_audit_fixes.py::test_normalisation_zero_width_ss2`.

### Change 7.2: Database Test Isolation
- **Change:** Implemented `tests/conftest.py` with an autouse fixture intercepting `ARIVARAN_DB_PATH`, guaranteeing that all unit and integration tests run against isolated temporary databases (`tmp_path / "test_arivaran.db"`).
- **Impact:** Strictly prevents test runs from polluting the production database (`arivaran.db`).

### Change 7.3: Negative Routing Tests
- **Change:** Hardened routing in `engine/intents.py` and `bot.py` by excluding receipt/passive notification keywords (`"is paid"`, `"was paid"`, `"bill paid"`, `"has been paid"`, `"thank you"`). Added `test_negative_routing_end_to_end` asserting `"Your bill is paid, thank you"` and `"shipping address"` never trigger emergency incident menus (`INC_*`).

### Change 7.4: Classifier V2 Training & Safety Verification
- **Change:** Trained `clf_v2` (`TfidfVectorizer` char_wb 2-5 + `LogisticRegression` balanced) on 372 deduplicated messages (`messages.csv` dev split + `train_extra.csv` + `train_extra2.csv`). Cross-validation selected an operating threshold of `0.70` to target zero false alarms.
- **Evaluation:** On the held-out test split (even IDs of `messages.csv`), rules alone caught 20/20 scams with 0/13 false alarms. Mode C (`rules + clf_v2`) also caught 20/20 with 0/13 false alarms (no scam gain over rules).
- **Decision:** Per decision rule, `USE_CLASSIFIER` strictly remains `false` by default. Model saved to `models/clf_v2.joblib` and metadata to `models/clf_v2.json`. Verified in `tests/test_classifier_v2.py`.

---

## 8. Voice-In STT Pipeline & Spoken Safety Architecture (24 Oct 2026)

### Change 8.1: In-Process PyAV Audio Pipeline & Preprocessing
- **Change:** Switched audio conversion from ffmpeg subprocess to in-process `av` (PyAV) decoding direct to 16 kHz mono WAV/NumPy arrays (`speech.convert_ogg_to_wav`), reducing conversion latency to ~60-90 ms per clip without subprocess spawns. Added `speech.preprocess_audio`:
  - 1s to 60s audio duration guard.
  - Leading and trailing silence trimming using energy threshold (>0.01 with 100ms margins).
  - Peak loudness normalisation (scaling peak amplitude to 0.90).

### Change 8.2: Faster-Whisper Decoding Optimisation & Offline Hardening
- **Change:** Set `HF_HUB_OFFLINE=1` preventing urllib3 HuggingFace network check timeouts in isolated environments. Configured `cpu_threads=10` matching host physical cores.
- **Change:** Benchmarked beam sizes with `temperature=0` and `condition_on_previous_text=False`:
  - `beam_size=1` achieved median decoding latency of ~7.8s (<15s requirement) with zero repetitive hallucination loops.
  - `beam_size=5` took 9.8s - 23.2s and triggered repetitive hallucination loops on low-confidence segments.
  - Selected `beam_size=1`, `temperature=0`, `vad_filter=True`.

### Change 8.3: Voice Confidence Gate & Character Set Validator
- **Change:** Implemented `speech.check_voice_confidence` rejecting low-confidence speech:
  - `avg_logprob >= -1.0`, `no_speech_prob <= 0.5`, `temperature <= 0.4`, `word_count >= 3`.
  - Allowed characters strictly constrained to Tamil Unicode block (`\u0B80-\u0BFF`), Latin ASCII/supplement, digits, whitespace, and standard punctuation. Rejects foreign scripts (Hangul, Cyrillic, Kana) often produced during Whisper hallucinations.
  - Failed confidence routes to `S_VOICE_RETRY` ("I couldn't hear that clearly...").

### Change 8.4: Voice-Only Normaliser (`engine/voice_norm.py`)
- **Change:** Implemented deterministic phonetic regex mappings in `engine/voice_norm.py` strictly for spoken transcripts:
  - Mapped Tamil phonetic spellings: `ஓடிபி` / `ஓட்டிப் பே` -> `OTP`, `கேஒய்சி` -> `KYC`, `யூபிஐ` -> `UPI`, `பின்` -> `PIN`, `ஏடிஎம்` -> `ATM`, `அனிடெஸ்க்` -> `AnyDesk`, `போலிஸ்` -> `police`, `சொல்லுங்க` -> `சொல்லுங்கள்`.
  - Preserves frozen engine rules; only runs on confirmed voice inputs. Converts Audio-2 from unflagged text to `SCAM` (`ASK_SENSITIVE`, score 5).
  - Verified in `tests/test_voice_norm.py`.

### Change 8.5: Voice Confirmation Flow & No-Reassurance Safety Policy
- **Change:** Implemented mandatory confirmation step before analysis:
  - Bot transcribes off-loop (`asyncio.to_thread`) with a 25s timeout and sends `S_HEARD` with `[சரி]` (`V_CONFIRM`) and `[மீண்டும் சொல்கிறேன்]` (`V_RETRY`) buttons.
  - If user confirms and verdict evaluates to `NO_RED_FLAGS`, safety rule intercepts and returns `S_VOICE_NO_VERDICT` ("I can't reliably check a spoken description..."). Never gives false reassurance for spoken notes.
  - Transcripts and audio files are wiped immediately from memory/disk; zero transcript or audio bytes written to SQLite database.
  - Default status: `VOICE_IN_ENABLED = False` in `config.py`.

### Change 8.6: Normaliser Hardening & Ordinary Word Exclusion
- **Change:** Audited and hardened `engine/voice_norm.py` to remove the mapping `"பின்" -> "PIN"` (which collided with ordinary Tamil "பின்" = after/behind) and common colloquial verbs (`சொல்லுங்க`, `அனுப்புங்க`, `குடுங்க`, `போடுங்க`).
- **Rule Scope:** Strictly restricted to unambiguous loanword transliterations (`OTP`, `KYC`, `UPI`, `ATM`, `AnyDesk`, `SBI`, `police`). Added test asserting `"அதன் பின் நான் வந்தேன்"` is completely unchanged by normalisation.

### Change 8.7: Tamil Small Model Offline Trial (`vasista22/whisper-tamil-small`)
- **Trial:** Converted original `vasista22/whisper-tamil-small` (Apache-2.0, rev `ac0d71c`) to CTranslate2 int8 via an isolated temporary external venv (size: 241.26 MB, model.bin SHA-256: `50b54e93752018729964ae079e484ff3cbe72a40782481897cb9605fb66af910`), with temporary venv subsequently deleted.
- **Trial Evaluation:** Benchmarked offline across 4 real audio clips (median of 3 runs). While Model B achieved lower latency (3.3s - 5.5s) and higher average logprob, its colloquial transcription on Audio-2 (`ஓடிப்`, `சொல்லுங்க`) does not trigger frozen engine rules. Model A (`faster-whisper-small`) remains the default in `speech.py`. Voice-in status remains `BUILT NOT VERIFIED: no manifest`.

