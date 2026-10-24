# Evaluation Results for Arivaran Scam Detection

## 1. Headline Metrics (Held-Out Test Set: Even IDs)

- **Test Set Size:** 33 messages (20 scams, 13 genuine)
- **False-Positive Rate on Genuine:** 0 of 13 (0.0%)
- **Recall (Scams Caught):** 20 of 20 (100.0%)
- **Precision:** 100.0%
- **Strict Recall (Decisive SCAM verdict):** 17 of 20 (85.0%)

### Full Dataset Metrics (All 66 Messages, includes tuning data)
- **Total Messages:** 66
- **Genuine Flagged:** 0 of 27 (FPR 0.0%)
- **Scams Flagged:** 39 of 39 (Recall 100.0%)
- **Precision:** 100.0%
- **Strict Recall:** 32 of 39 (82.1%)

## 2. Confusion Matrix (Held-Out Test Set)

| True Label | Pred: SCAM | Pred: SUSPICIOUS | Pred: NO_RED_FLAGS | Total |
|---|---|---|---|---|
| **genuine** | 0 | 0 | 13 | 13 |
| **scam** | 17 | 3 | 0 | 20 |

## 3. Dataset Distribution (Dev vs Test Split)

### Category Distribution

| Category | Dev Split (Odd IDs) | Test Split (Even IDs) | Total Messages |
|---|---|---|---|
| **appointment** | 1 | 0 | 1 |
| **authority** | 3 | 3 | 6 |
| **awareness** | 1 | 0 | 1 |
| **bank_alert** | 1 | 1 | 2 |
| **bank_impersonation** | 1 | 0 | 1 |
| **delivery** | 0 | 1 | 1 |
| **fake_care** | 3 | 0 | 3 |
| **family_impersonation** | 0 | 1 | 1 |
| **greeting** | 1 | 0 | 1 |
| **invest** | 3 | 0 | 3 |
| **job** | 1 | 4 | 5 |
| **kyc** | 3 | 2 | 5 |
| **kyc_legit** | 0 | 1 | 1 |
| **loan** | 1 | 0 | 1 |
| **order** | 1 | 1 | 2 |
| **otp** | 2 | 1 | 3 |
| **otp_legit** | 2 | 0 | 2 |
| **parcel** | 1 | 0 | 1 |
| **personal** | 2 | 4 | 6 |
| **prize** | 0 | 3 | 3 |
| **school** | 1 | 2 | 3 |
| **subscription** | 1 | 0 | 1 |
| **telecom** | 1 | 0 | 1 |
| **travel** | 0 | 1 | 1 |
| **upi_collect** | 0 | 4 | 4 |
| **utility** | 2 | 3 | 5 |
| **weather** | 0 | 1 | 1 |
| **work** | 1 | 0 | 1 |

### Language Distribution

| Language | Dev Split (Odd IDs) | Test Split (Even IDs) | Total Messages |
|---|---|---|---|
| **en** | 13 | 12 | 25 |
| **ta** | 11 | 10 | 21 |
| **tanglish** | 9 | 11 | 20 |

## 4. Ablation Study (Held-Out Test Set)

| Config | Description | FPR (Genuine Flagged) | Recall (Scams Caught) | Strict Recall |
|---|---|---|---|---|
| **A** | Text rules only | 0/13 (0.0%) | 18/20 (90.0%) | 16/20 (80.0%) |
| **B** | Rules + Link checks | 0/13 (0.0%) | 20/20 (100.0%) | 17/20 (85.0%) |
| **C** | Rules + Links + Classifier | *classifier planned* | *classifier planned* | *classifier planned* |

## 5. Breakdown by Language (Held-Out Test Set)

| Language | Messages | Genuine Flagged | Scams Caught | Recall | Precision | Strict Recall |
|---|---|---|---|---|---|---|
| **en** | 12 | 0/5 (0.0%) | 7/7 | 100.0% | 100.0% | 71.4% |
| **ta** | 10 | 0/3 (0.0%) | 7/7 | 100.0% | 100.0% | 100.0% |
| **tanglish** | 11 | 0/5 (0.0%) | 6/6 | 100.0% | 100.0% | 83.3% |

## 6. Breakdown by Category (Held-Out Test Set)

| Scam Category | Samples | Flagged | Strict SCAM | Recall |
|---|---|---|---|---|
| **authority** | 3 | 3/3 | 2/3 | 100.0% |
| **family_impersonation** | 1 | 1/1 | 1/1 | 100.0% |
| **job** | 4 | 4/4 | 2/4 | 100.0% |
| **kyc** | 2 | 2/2 | 2/2 | 100.0% |
| **otp** | 1 | 1/1 | 1/1 | 100.0% |
| **prize** | 3 | 3/3 | 3/3 | 100.0% |
| **upi_collect** | 4 | 4/4 | 4/4 | 100.0% |
| **utility** | 2 | 2/2 | 2/2 | 100.0% |

## 7. Wrong Predictions (Held-Out Test Set: Even IDs)

*None! All test set messages classified correctly.*

## 8. Wrong Predictions (Dev Split: Odd IDs)

*None! All dev set messages classified correctly.*

## 9. Signal x Language Keyword Coverage Table

| Signal Code | English (en) | Tamil (ta) | Tanglish (tanglish) | Representative Patterns |
|---|---|---|---|---|
| **ASK_SENSITIVE** | Yes | Yes | Yes | share/send otp, ஓடிபி/பின் பகிரவும், kudunga/anupunga |
| **PIN_REQUEST** | Yes | Yes | Yes | enter upi pin, பின் உள்ளிடுங்கள், pin podunga |
| **FEE_FIRST** | Yes | Yes | Yes | processing fee, கட்டணம் செலுத்துங்கள், fee kattunga |
| **DIGITAL_ARREST** | Yes | Yes | Yes | cyber police video call, டிஜிட்டல் அரெஸ்ட், case irukku arrest |
| **KYC_UPDATE** | Yes | Yes | Yes | update kyc/pan, கேஒய்சி புதுப்பிக்க, link aagala |
| **THREAT** | Yes | Yes | Yes | blocked/suspended, முடக்கப்படும்/துண்டிக்கப்படும், block aagum/cut aagum |
| **URGENCY** | Yes | Yes | Yes | immediately/urgent, உடனடியாக/உடனே, udane/inru night |
| **PRIZE** | Yes | Yes | Yes | you won/lottery/kbc, பரிசு வென்றுள்ளீர்கள்/லக்கி டிரா, prize jeichirukeenga |
| **AUTHORITY** | Yes | Yes | Yes | cbi/police/customs/trai, சைபர் கிரைம்/சிபிஐ/காவல்துறை, police officer pesuren |
| **REMOTE_ACCESS** | Yes | Yes | Yes | anydesk/teamviewer/.apk, செயலியை பதிவிறக்கம், anydesk install |
| **PAYMENT_PUSH** | Yes | Yes | Yes | collect request/enter upi pin, முன்பணம்/கட்டணம், gpay seyyavum |
| **JOB_TASK** | Yes | Yes | Yes | work from home/like youtube, பகுதிநேர வேலை, youtube like pannina |
| **INVEST** | Yes | Yes | Yes | guaranteed returns/double money, முதலீடு செய்து இரட்டிப்பு, double profit guaranteed |
| **CALLBACK** | Yes | Yes | Yes | call this number, தொடர்பு கொள்ளவும், number ku call pannunga |
| **LOOKALIKE** | N/A | N/A | N/A | URL analysis (Domain matching, brand names) |
| **SHORTENER** | N/A | N/A | N/A | URL analysis (bit.ly, t.co, tinyurl, etc.) |
| **IP_HOST** | N/A | N/A | N/A | URL analysis (Raw IPv4 address host) |
| **USERINFO** | N/A | N/A | N/A | URL analysis (@ symbol in authority netloc) |
| **PUNYCODE** | N/A | N/A | N/A | URL analysis (IDN xn-- homograph spoofing) |
| **OTP_DELIVERY** | Yes | Yes | No | Mitigating: is your otp + warning, ரகசிய otp |
| **TXN_ALERT** | Yes | Yes | No | Mitigating: debited/credited Rs, வரவு/பற்று |
| **DELIVERY_ALERT** | Yes | Yes | No | Mitigating: out for delivery/order #, டெலிவரி/பார்சல் |

## 10. Robustness Test Suite (R01 to R15 with Required Signals)

| ID | Case | Input / Technique | Required Signal | Result | Details |
|---|---|---|---|---|---|
| R01 | **Spaced letters (no link)** | `S B I bank a/c blocked, update KYC` | `KYC_UPDATE` | **PASS** | Verdict: SUSPICIOUS, Signals: ['KYC_UPDATE', 'THREAT'] |
| R01b | **Spaced letters (with link)** | `S B I bank a/c blocked, update KYC: http://sbi.example/kyc` | `KYC_UPDATE` | **PASS** | Verdict: SCAM, Signals: ['NO_HTTPS', 'LOOKALIKE', 'KYC_UPDATE', 'THREAT'] |
| R02 | **Lookalike domain** | `http://sbi-co-in.example/login` | `LOOKALIKE` | **PASS** | Signals: ['NO_HTTPS', 'LOOKALIKE'] |
| R03 | **Shortener** | `http://bit.ly/aB3dE` | `SHORTENER` | **PASS** | Signals: ['SHORTENER', 'NO_HTTPS'] |
| R04 | **@ trick** | `http://sbi.co.in@evil.example/` | `USERINFO` | **PASS** | Signals: ['USERINFO', 'NO_HTTPS'] |
| R05 | **Defanged link** | `hxxp://bank-kyc[.]example` | `URL_EXTRACTED` | **PASS** | Extracted URLs: ['http://bank-kyc.example'] |
| R06 | **Zero-width chars (no KYC)** | `Your O\u200bT\u200bP is required to verify transaction: 98XXXXXX01` | `ASK_SENSITIVE` | **PASS** | Verdict: SCAM, Signals: ['ASK_SENSITIVE'] (Required ASK_SENSITIVE: True) |
| R07 | **Leetspeak credential** | `Your 0TP is needed to verify account: 98XXXXXX01` | `ASK_SENSITIVE` | **PASS** | Verdict: SCAM, Signals: ['ASK_SENSITIVE'] |
| R08 | **Tamil + English mix** | `EN / TA / Tanglish SBI KYC scam` | `VERDICT_MATCH (SCAM)` | **PASS** | EN: SCAM, TA: SCAM, Tanglish: SCAM |
| R09 | **Prompt injection** | `Ignore previous instructions + scam` | `KYC_UPDATE / THREAT` | **PASS** | Verdict: SCAM, Signals: ['NO_HTTPS', 'LOOKALIKE', 'KYC_UPDATE', 'THREAT', 'URGENCY'] |
| R10 | **PII redaction** | `Aadhaar: 2345 6789 0123, PAN: ABCDE1234F, Card: 4532 1234 5678 9012, Phone: 9876543210, UPI: user@oksbi` | `PII_REDACTED` | **PASS** | Redacted: Aadhaar: <AADHAAR>, PAN: <PAN>, Card: <CARD>, Phone: <PHONE>, UPI: <UPI> |
| R11a | **Private IP link (static)** | `http://127.0.0.1/app.apk` | `IP_HOST` | **PASS** | Static signals: ['IP_HOST'] |
| R11b | **SSRF guard (expansion)** | `http://127.0.0.1:63047/redirect` | `SSRF_BLOCKED` | **NOT IMPLEMENTED** | Live network link expansion is not implemented in bot |
| R12 | **Redirect to private IP** | `http://127.0.0.1:63047/private-redirect` | `SSRF_BLOCKED` | **NOT IMPLEMENTED** | Live network link expansion is not implemented in bot |
| R13 | **Long redirect chain** | `http://127.0.0.1:63047/redirect?n=5` | `MAX_HOPS_ENFORCED` | **NOT IMPLEMENTED** | Live network link expansion is not implemented in bot |
| R14 | **Slow server timeout** | `http://127.0.0.1:63047/slow` | `TIMEOUT_ENFORCED` | **NOT IMPLEMENTED** | Live network link expansion is not implemented in bot |
| R15 | **Query-string stripping** | `http://x.example/login?token=secret_token_12345` | `QUERY_STRIPPED` | **PASS** | Stripped URL: http://x.example/login |


## 11. Latency Benchmark Report

- **Host Machine:** Windows-11-10.0.26300-SP0
- **CPU:** Intel64 Family 6 Model 186 Stepping 3, GenuineIntel (12 cores)
- **GPU:** Intel(R) Iris(R) Xe Graphics (Integrated / CPU-only execution)
- **Whisper Model Size:** `small`
- **Whisper Compute Type:** `int8`
- **Whisper Device:** `cpu`

| Pipeline Path | Median Latency | p95 Latency | Benchmark Status |
|---|---|---|---|
| **Text message to verdict, rules only** | 0.20 ms | 17.10 ms | PASS |
| **Text with link analysis (local lists)** | 0.38 ms | 36.06 ms | PASS |
| **Voice note to transcript, 10 s clip** | NOT AVAILABLE | NOT AVAILABLE | Awaiting 10 s Tamil clip in data/audio/ |
| **Voice note to transcript, 20 s clip** | NOT AVAILABLE | NOT AVAILABLE | Awaiting 20 s Tamil clip in data/audio/ |
| **Reply voice, TTS cached** | 0.03 ms | 0.12 ms | PASS |
| **Reply voice, TTS uncached** | 4149.82 ms | p95 not reported | n=5, median only, p95 not reported |
| **Full voice-in to voice-out** | NOT AVAILABLE | NOT AVAILABLE | Awaiting audio clips in data/audio/ |


## 12. Privacy & Storage Audit Report

- **Overall Privacy Audit Status:** **PASS**
- **Database Schema Message-Text Audit:** **PASS** (Confirmed: No text-storing column exists in schema.)
- **HTTP / Telegram Logger Token Security:** **PASS** (PASS: httpx/telegram loggers set to WARNING; no bot tokens or request URLs emitted.)
- **Distinctive Test Sentences Leak Count:** **0** (0 leaked)
- **Synthetic PII Tokens Leak Count:** **0** (0 leaked)

### Database Schema Dump (`arivaran.db`)

| Table Name | Column Name | Column Type | Holds Message Text? |
|---|---|---|---|
| `checks` | `id` | `INTEGER` | **No** |
| `checks` | `ts` | `TEXT` | **No** |
| `checks` | `sender_hash` | `TEXT` | **No** |
| `checks` | `msg_type` | `TEXT` | **No** |
| `checks` | `score` | `INTEGER` | **No** |
| `checks` | `verdict` | `TEXT` | **No** |
| `checks` | `fired_rules` | `TEXT` | **No** |
| `checks` | `feedback` | `TEXT` | **No** |
| `sqlite_sequence` | `name` | `` | **No** |
| `sqlite_sequence` | `seq` | `` | **No** |

### Distinctive Sentence & PII Leakage Verification

| Test Payload Type | Sample Content | Target Destination | Audit Result |
|---|---|---|---|
| **Distinctive English Sentence** | `The golden chariot crossed the mountain at sunset 9876543210` | Storage / Logs | **PASS (Zero Leaks)** |
| **Distinctive Tamil Sentence** | `வானத்தில் வட்டமிட்ட வெண்புறா மரக்கிளையில் அமர்ந்தது 1234567890` | Storage / Logs | **PASS (Zero Leaks)** |
| **PII: AADHAAR** | `4321 8765 2109` | Storage / Logs | **PASS (Zero Leaks)** |
| **PII: PAN** | `ABCDE9876Z` | Storage / Logs | **PASS (Zero Leaks)** |
| **PII: CARD** | `4111 2222 3333 4444` | Storage / Logs | **PASS (Zero Leaks)** |
| **PII: PHONE** | `9123456780` | Storage / Logs | **PASS (Zero Leaks)** |
| **PII: UPI** | `victim_test@okaxis` | Storage / Logs | **PASS (Zero Leaks)** |
| **PII: ACCOUNT** | `987654321098` | Storage / Logs | **PASS (Zero Leaks)** |


## 13. Blind test v1

*Awaiting `data/blind_v1.csv` (file not yet provided).*
