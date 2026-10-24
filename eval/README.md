# Arivaran Evaluation Harness

Deterministic, reproducible evaluation and benchmark suite for Arivaran's scam detection bot.

## Single Command to Run Everything

```bash
python eval/run_all.py
```
*(Or inside virtualenv on Windows / Git Bash:)*
```bash
./.venv/Scripts/python eval/run_all.py
```

---

## Tooling & Architecture

| File | Purpose |
|---|---|
| `data/messages.csv` | 66 synthetic test messages (odd ID = dev split, even ID = held-out test split). |
| `data/robustness.csv` | 15 targeted evasion, SSRF, and parser stress test cases (R01 to R15 with required signals). |
| `data/blind_v1.csv` | Optional blind test dataset evaluated independently (when provided). |
| `eval/results_v0.md` | Baseline snapshot of evaluation report before test suite upgrades (preserved permanently). |
| `eval/run_eval.py` | Accuracy evaluation, multi-class confusion matrix, FPR, precision, recall, strict recall, language/category breakdowns, dev vs test distribution, dev wrong predictions, and signal x language coverage matrix. |
| `eval/run_robustness.py` | Runs R01-R15 using an offline local fake HTTP server (`127.0.0.1`, random port) verifying required signals (R01/R01b, R06 zero-width without KYC, R11a/R11b, LLM pipeline check). |
| `eval/run_latency.py` | Measures median and p95 latencies across 20 runs (or n=5 fallback for uncached TTS), faster-whisper support, and system hardware specifications. |
| `eval/check_privacy.py` | DB schema dump (confirming no message text column), distinctive EN/TA sentence leak detection, PII leak audits, and HTTP/Telegram client WARNING logger verification. |
| `eval/run_blind.py` | Independent blind evaluation runner for `data/blind_v1.csv` with identical metrics. |
| `eval/run_all.py` | Master harness runner executing all 5 evaluation benchmarks in sequence. |
| `eval/results.md` | Auto-generated unified markdown report containing all tables and findings. |

---

## Evaluation Ground Rules Followed

1. **Deterministic Only:** No LLM or network heuristics decide verdicts. All decisions stem from deterministic rule scoring.
2. **Offline & Isolated:** No internet calls used for evaluation. Robustness tests use a local loopback server (`127.0.0.1`).
3. **Honest Reporting:** No invented metrics. Unimplemented modules (`faster-whisper`, Config C classifier, live redirect expander) are explicitly reported as `NOT IMPLEMENTED`.
4. **Synthetic Data Only:** All phone numbers, account numbers, and domains are synthetic (`.example`, fake prefixes).
