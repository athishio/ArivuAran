# Evaluation Results for Arivaran Scam Detection

## 1. Headline Metrics (Held-Out Test Set: Even IDs)

- **Test Set Size:** 33 messages (20 scams, 13 genuine)
- **False-Positive Rate on Genuine:** 2 of 13 (15.4%)
- **Recall (Scams Caught):** 15 of 20 (75.0%)
- **Precision:** 88.2%
- **Strict Recall (Decisive SCAM verdict):** 4 of 20 (20.0%)

### Full Dataset Metrics (All 66 Messages, includes tuning data)
- **Total Messages:** 66
- **Genuine Flagged:** 4 of 27 (FPR 14.8%)
- **Scams Flagged:** 27 of 39 (Recall 69.2%)
- **Precision:** 87.1%
- **Strict Recall:** 7 of 39 (17.9%)

## 2. Confusion Matrix (Held-Out Test Set)

| True Label | Pred: SCAM | Pred: SUSPICIOUS | Pred: NO_RED_FLAGS | Total |
|---|---|---|---|---|
| **genuine** | 0 | 2 | 11 | 13 |
| **scam** | 4 | 11 | 5 | 20 |

## 3. Ablation Study (Held-Out Test Set)

| Config | Description | FPR (Genuine Flagged) | Recall (Scams Caught) | Strict Recall |
|---|---|---|---|---|
| **A** | Text rules only | 2/13 (15.4%) | 15/20 (75.0%) | 2/20 (10.0%) |
| **B** | Rules + Link checks | 2/13 (15.4%) | 15/20 (75.0%) | 4/20 (20.0%) |
| **C** | Rules + Links + Classifier | *classifier planned* | *classifier planned* | *classifier planned* |

## 4. Breakdown by Language (Held-Out Test Set)

| Language | Messages | Genuine Flagged | Scams Caught | Recall | Precision | Strict Recall |
|---|---|---|---|---|---|---|
| **en** | 12 | 2/5 (40.0%) | 6/7 | 85.7% | 75.0% | 28.6% |
| **ta** | 10 | 0/3 (0.0%) | 4/7 | 57.1% | 100.0% | 14.3% |
| **tanglish** | 11 | 0/5 (0.0%) | 5/6 | 83.3% | 100.0% | 16.7% |

## 5. Breakdown by Category (Held-Out Test Set)

| Scam Category | Samples | Flagged | Strict SCAM | Recall |
|---|---|---|---|---|
| **authority** | 3 | 3/3 | 0/3 | 100.0% |
| **family_impersonation** | 1 | 1/1 | 0/1 | 100.0% |
| **job** | 4 | 3/4 | 2/4 | 75.0% |
| **kyc** | 2 | 1/2 | 1/2 | 50.0% |
| **otp** | 1 | 1/1 | 0/1 | 100.0% |
| **prize** | 3 | 2/3 | 0/3 | 66.7% |
| **upi_collect** | 4 | 2/4 | 1/4 | 50.0% |
| **utility** | 2 | 2/2 | 0/2 | 100.0% |

## 6. Wrong Predictions (Held-Out Test Set)

| ID | Expected | Predicted | Signals Fired | Text |
|---|---|---|---|---|
| M014 | scam | NO_RED_FLAGS | None | வீட்டிலிருந்தே வேலை. தினம் ரூ 2,000 சம்பாதிக்கலாம். முதலில் ரூ 500 பதிவுக் கட்டணம் செலுத்துங்கள். |
| M018 | scam | NO_RED_FLAGS | None | உங்களுக்கு ரூ 2,000 திரும்பப் பெற, UPI PIN உள்ளிடுங்கள். |
| M024 | scam | NO_RED_FLAGS | None | Congrats! Neenga 5 lakh prize jeichirukeenga. Claim panna Rs 2000 fee kattunga. |
| M056 | genuine | SUSPICIOUS | KYC_UPDATE | Dear customer, please complete your KYC at your nearest branch with original ID documents. No link or call needed. |
| M058 | genuine | SUSPICIOUS | URGENCY | Urgent: Your electricity supply will be interrupted tomorrow 10 AM to 2 PM for maintenance in Sulur area. |
| M062 | scam | NO_RED_FLAGS | None | S B I Bank: Ur a/c wil b blokd. Updt PAN now at short.example/aB3dE |
| M066 | scam | NO_RED_FLAGS | None | நீங்கள் தேர்ந்தெடுக்கப்பட்டீர்கள்! ₹500 பெற இந்த UPI கோரிக்கையை ஏற்கவும். |

## 7. Robustness Test Suite (R01 to R15)

| ID | Case | Input / Technique | Expected | Result | Details |
|---|---|---|---|---|---|
| R01 | **Spaced letters** | `S B I bank a/c blocked, update KYC: http://sbi.example/kyc` | Flagged | **PASS** | Verdict: SCAM, Signals: ['KYC_UPDATE', 'THREAT'] |
| R02 | **Lookalike domain** | `http://sbi-co-in.example/login` | Link flagged as lookalike | **FAIL** | Signals: [] |
| R03 | **Shortener** | `http://bit.ly/aB3dE` | Flagged as shortener | **PASS** | Signals: ['SHORTENER', 'NO_HTTPS'] |
| R04 | **@ trick** | `http://sbi.co.in@evil.example/` | Real host = evil.example | **FAIL** | Signals: [] |
| R05 | **Defanged link** | `hxxp://bank-kyc[.]example` | Treated as a link | **FAIL** | Extracted URLs: [] |
| R06 | **Zero-width characters** | `O\u200bT\u200bP in KYC scam` | Still detected | **PASS** | Verdict: SUSPICIOUS, Signals: ['KYC_UPDATE'] |
| R07 | **Leetspeak** | `0TP, K Y C update link` | Still detected | **FAIL** | Verdict: NO_RED_FLAGS, Signals: [] |
| R08 | **Tamil + English mix** | `EN / TA / Tanglish SBI KYC scam` | Same verdict | **FAIL** | EN: SCAM, TA: SUSPICIOUS, Tanglish: SCAM |
| R09 | **Prompt injection** | `Ignore previous instructions + scam` | Verdict unchanged (still flagged) | **PASS** | Verdict: SCAM, Signals: ['KYC_UPDATE', 'THREAT', 'URGENCY'] |
| R10 | **PII in message** | `Fake Aadhaar, PAN, Card, Phone, UPI` | Redacted before any log or storage | **PASS** | Redacted: Aadhaar: <AADHAAR>, PAN: <PAN>, Card: <CARD>, Phone: <PHONE>, UPI: <UPI> |
| R11 | **Private IP link** | `http://127.0.0.1/app.apk` | Expansion refused / Flagged as IP host | **PASS** | Detected as raw IP host statically: ['IP_HOST'] |
| R12 | **Redirect to private IP** | `http://127.0.0.1:62074/private-redirect` | Stopped (SSRF guard) | **NOT IMPLEMENTED** | Live network link expansion is not implemented in bot (offline static engine only) |
| R13 | **Long redirect chain** | `http://127.0.0.1:62074/redirect?n=5` | Stops at 3 hops | **NOT IMPLEMENTED** | Live network link expansion is not implemented in bot (offline static engine only) |
| R14 | **Slow server** | `http://127.0.0.1:62074/slow` | Times out at 3 s | **NOT IMPLEMENTED** | Live network link expansion is not implemented in bot (offline static engine only) |
| R15 | **Query-string stripping** | `http://x.example/login?token=secret_token_12345` | Query string removed before any external check | **PASS** | Stripped URL: http://x.example/login |


## 8. Latency Benchmark Report

- **Host Machine:** Windows-11-10.0.26300-SP0
- **CPU:** Intel64 Family 6 Model 186 Stepping 3, GenuineIntel (12 cores)
- **GPU:** Intel(R) Iris(R) Xe Graphics (Integrated / CPU-only)
- **Whisper Configuration:** small (CPU int8, defined in speech.py)

| Pipeline Path | Median Latency | p95 Latency | Benchmark Status |
|---|---|---|---|
| **Text message to verdict, rules only** | 0.10 ms | 7.32 ms | PASS |
| **Text with link analysis (local lists)** | 0.20 ms | 34.77 ms | PASS |
| **Voice note to transcript, 10 s clip** | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED (faster-whisper package not installed in environment) |
| **Voice note to transcript, 20 s clip** | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED (faster-whisper package not installed in environment) |
| **Reply voice, TTS cached** | 0.08 ms | 0.22 ms | PASS |
| **Reply voice, TTS uncached** | 4094.83 ms | 5227.40 ms | PASS (5 sample calls) |
| **Full voice-in to voice-out** | NOT IMPLEMENTED | NOT IMPLEMENTED | NOT IMPLEMENTED (Blocked by local Whisper dependency) |


## 9. Privacy & PII Leakage Audit

- **Overall Privacy Status:** **PASS**
- **Synthetic PII Tested:** AADHAAR, PAN, CARD, PHONE, UPI, ACCOUNT
- **Target Storage Inspected:** `arivaran.db` (SQLite audit log), system logs

| PII Entity Type | Synthetic Test Value | Target Redacted Tag | Audit Result |
|---|---|---|---|
| **AADHAAR** | `4321 8765 2109` | `<AADHAAR>` | **PASS (Zero Leaks)** |
| **PAN** | `ABCDE9876Z` | `<PAN>` | **PASS (Zero Leaks)** |
| **CARD** | `4111 2222 3333 4444` | `<CARD>` | **PASS (Zero Leaks)** |
| **PHONE** | `9123456780` | `<PHONE>` | **PASS (Zero Leaks)** |
| **UPI** | `victim_test@okaxis` | `<UPI>` | **PASS (Zero Leaks)** |
| **ACCOUNT** | `987654321098` | `<ACCOUNT>` | **PASS (Zero Leaks)** |

✅ **Privacy Audit Confirmed:** No raw Aadhaar, PAN, Card, Phone, UPI, or Account strings exist in any database table or log file.

