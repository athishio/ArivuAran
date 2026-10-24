# ARIVUARAN (அறிவுஅரண்) — Telegram Bot & Offline Test Bench
**Team INEVITABLE | Viksitthon 2026**

ARIVUARAN is a voice-first, bilingual (Tamil & Indian English) cybersecurity assistant designed to safeguard everyday citizens against digital, SMS, and financial scams.

Operating on **100% deterministic code** with **zero LLM hallucinations**, Arivaran analyzes messages, links, audio notes, and screenshots in under **50 milliseconds** while upholding strict **zero-knowledge privacy guarantees**.

---

## 🚀 Core Features

- **Instant Deterministic Engine:** Hard & soft heuristics score lookalike domains, phishing shorteners, urgent demands, fake KYC blocks, and digital arrest threats without external LLM calls.
- **Bilingual Conversational Experience:** First-message language selection (`[தமிழ்]` / `[English]`) with complete coverage across text, buttons, and voice responses.
- **Voice-First Accessibility:** Generates high-quality spoken voice clips (ta-IN-PallaviNeural & en-IN-NeerjaNeural) capped between 10 to 20 seconds.
- **Strict Privacy Architecture:** Stores **never** message text, transcripts, phone numbers, or OTPs. Database records only salted SHA-256 chat hashes, rounded timestamps, and signal codes. Session memory auto-expires after 30 minutes.
- **Multi-Modal Input:** Supports text forwards, voice notes (local Faster-Whisper), screenshots (Tesseract OCR), and button interactions.
- **Offline / Local Console:** Full-featured FastAPI local test bench (`http://127.0.0.1:8000`) for presentations, evaluations, or fallback when internet is unavailable.

---

## 🛠️ System Requirements & Prerequisite Binaries

The following system binaries must be installed on your operating system (they are external executables, not pip packages):

1. **Tesseract OCR (v5.0+):**
   - Required for screenshot OCR. Must include both Tamil (`tam`) and English (`eng`) language training data (`tessdata`).
   - Default Windows location: `C:\Program Files\Tesseract-OCR\tesseract.exe` (configurable in `.env` via `TESSERACT_CMD`).
2. **FFmpeg / PyAV:**
   - Used for transcoding audio notes and encoding OGG/Opus voice notes.
   - Configure `FFMPEG_PATH` in `.env` or rely on the built-in PyAV `libopus` encoder.
3. **Python 3.11 or 3.12** in an isolated virtual environment (`.venv`).

---

## 📦 Installation & Setup

```bash
# 1. Clone repository and navigate to workspace
cd E:\Arivaran

# 2. Activate virtual environment
.venv\Scripts\activate

# 3. Install pinned Python dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
```

Open `.env` and fill in your variables:
```ini
BOT_TOKEN=8860136312:AAH...
SALT=your_custom_secret_salt_string_2026
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
FFMPEG_PATH=ffmpeg
DEMO_MODE=true
TTS_RATE=-10%
USE_CLASSIFIER=false
```

---

## 🚦 System Preflight Verification

Before launching the bot or demo, run the diagnostic preflight checklist:

```bash
python scripts/preflight.py
```

Expected output:
```text
======================================================================
ARIVUARAN (அறிவுஅரண்) SYSTEM PREFLIGHT CHECKLIST
======================================================================
  ✅ [PASS]         Internet Connectivity          : Connected
  ✅ [PASS]         Telegram Bot Token             : Token formatted correctly
  ✅ [PASS]         Faster-Whisper Model Cache     : Cached model(s) found
  ✅ [PASS]         Tesseract OCR (tam + eng)      : Installed (tam + eng)
  ✅ [PASS]         Audio Encoding (ffmpeg / PyAV) : PyAV available with libopus + ogg
  ✅ [PASS]         Audio Cache Completeness       : Pre-cached clips present
  ✅ [PASS]         SQLite Database Writable       : Database writable
  ⚠️ [OPTIONAL]    ML Text Classifier             : Optional classifier
======================================================================
🎉 ALL CRITICAL PREREQUISITES VERIFIED! Bot is ready for launch.
======================================================================
```

---

## 🎙️ Audio Pre-Generation Pipeline

To operate completely offline during presentations and minimize latency, pre-generate all spoken audio clips:

```bash
python scripts/pregen_audio.py
```

This populates `cache/audio/` with SHA-256 keyed OGG/Opus and MP3 clips for every response ID in `data/replies.json` for both Tamil and English.

---

## 🖥️ Running the Application

### Option A: Telegram Bot (Long Polling)
Runs directly without requiring public webhooks, domains, or ngrok tunnels:
```bash
python bot.py
```

### Option B: Local Web Console (127.0.0.1 Backup)
Runs the standalone local browser console for live evaluation and demo resilience:
```bash
python console.py
```
Open **`http://127.0.0.1:8000`** in any browser. Features live audio playback, demo canned message buttons, and instant language switching.

---

## 🤖 Active Telegram Commands

The bot supports the following live commands:

| Command | Description (English) | விளக்கம் (Tamil) |
| :--- | :--- | :--- |
| `/start` | Start {BOT_NAME_EN} & welcome advisory | தொடக்கம் & குறள் 421 வழிகாட்டல் |
| `/help` | List active commands | கட்டளைகளின் பட்டியல் |
| `/language` | Select language (alias: `/lang`) | மொழி தேர்வு (தமிழ் / English) |
| `/privacy` | Zero-knowledge privacy guarantees | தனியுரிமை கொள்கை |
| `/stats` | Live detection statistics | நேரலை புள்ளிவிவரங்கள் |
| `/delete` | Clear session memory & saved language | நினைவகத்தை அழி |
| `/demo` | Canned demo test cases *(when `DEMO_MODE=true`)* | மாதிரி சோதனைகள் |

### BotFather Setup Text
Copy and paste the following into [@BotFather](https://t.me/BotFather) under `/setcommands`:
```text
start - தொடக்கம் / Start bot
help - கட்டளைகள் / Help
language - மொழி தேர்வு / Select language
privacy - தனியுரிமை / Privacy policy
stats - நேரலை புள்ளிவிவரங்கள் / Live stats
delete - நினைவகத்தை அழி / Clear session
demo - மாதிரி சோதனைகள் / Demo test cases
```

---

## ⚖️ TTS Providers & Licensing Disclosure

- **Primary Provider (`edge-tts`):**
  Uses the open-source `edge-tts` library to interface with Microsoft's neural cloud voices (`ta-IN-PallaviNeural` and `en-IN-NeerjaNeural`). **Notice:** `edge-tts` is unofficial, terms unverified (source repository: https://github.com/rany2/edge-tts). It wraps public speech endpoints without an enterprise SLA.
- **Fallback Provider (`gTTS`):**
  If `edge-tts` times out or fails (8-second timeout), the engine falls back to `gTTS` (v2.5.4). **Notice:** `gTTS` is unofficial, terms unverified (source repository: https://github.com/pndurette/gTTS). It connects to Google Translate's web endpoint and is not an enterprise Google Cloud Text-to-Speech service.
- **Offline Fallback:**
  If network connectivity is lost entirely, the bot gracefully falls back to pre-cached audio or text-only responses with zero crash.

---

## 🔒 Known Limitations

1. **Deterministic Scope:** The heuristic engine is tuned for scam and phishing patterns commonly observed in SMS, WhatsApp forwards, and voice notes. It is not designed for parsing lengthy PDF contracts.
2. **OCR Dependency:** Screenshot verification accuracy depends on image clarity, lighting, and Tesseract font rendering.
3. **No Direct Complaint Filing:** Arivaran is an advisory assistant and does not file official police FIRs or cybercrime complaints on behalf of citizens. It guides users directly to dial **1930** or visit [cybercrime.gov.in](https://cybercrime.gov.in).
