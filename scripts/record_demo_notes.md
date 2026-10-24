# ARIVUARAN (அறிவுஅரண்) — Demo Screen-Recording Guide
**Team INEVITABLE | Viksitthon 2026**

This document provides exact step-by-step instructions to record a flawless 2-to-3 minute backup demonstration video of Arivaran, both via Telegram and via the offline local console (`http://127.0.0.1:8000`).

---

## 1. Setup & Environment Checklist

1. **Resolution & Display:**
   - Screen resolution: 1920×1080 (1080p).
   - Browser: Google Chrome or Microsoft Edge in Dark Mode.
   - Browser zoom: 110%–125% for high readability of Tamil fonts.
   - Tool: Windows Game Bar (`Win + Alt + R`) or OBS Studio (Canvas: 1920×1080, 60fps).
2. **Audio Setup:**
   - Microphone: USB microphone or clear headset.
   - System Audio: Enabled so TTS voice playback is clearly captured in the video.
3. **Services Running:**
   - Terminal 1: `.venv\Scripts\python console.py` (Local console at `http://127.0.0.1:8000`).
   - Terminal 2: `.venv\Scripts\python bot.py` (Telegram bot long-polling, if Telegram is tested).

---

## 2. Video Script & Recording Walkthrough (3 Minutes)

### Section A: Introduction (0:00 - 0:30)
- **Visual:** Browser showing `http://127.0.0.1:8000`.
- **Narration:**
  > "Hello everyone. This is Team INEVITABLE presenting ARIVUARAN (அறிவுஅரண்) — a voice-first cybersecurity guardian built for rural and non-English-literate citizens.
  > Arivaran operates on 100% deterministic code with zero LLM hallucinations, ensuring instant verdicts under 50 milliseconds while preserving absolute privacy."

### Section B: Demo Case 1 — Fake SBI KYC Phishing (0:30 - 1:10)
- **Action:** Click the sample chip **`1. SBI KYC`**.
- **Message:** `"Your SBI account is blocked. Update KYC immediately at http://sbi-kyc-verify.xyz"`
- **Action:** Click **"சரிபார் (Analyze)"**.
- **Visual:**
  - Red badge `🔴 மோசடி (SCAM)` appears instantly.
  - Fired signals: `SHORTENER` / `LOOKALIKE_DOMAIN` / `URGENT_DEMAND`.
  - HTML warning explanation with Thirukkural guidance.
- **Audio:** Click the HTML5 audio player.
  - **Hear:** Pallavi Neural voice speaking Tamil summary:
    *"இது மோசடி போல் உள்ளது. காரணங்கள்: ஒன்று, இது போலியான அல்லது சந்தேகத்திற்குரிய இணையதள முகவரி..."*
  - **Highlight:** Voice duration is exactly ~14 seconds, clean, clear, and reassuring.

### Section C: Demo Case 2 — "Sent by Mistake" OTP Scam (1:10 - 1:45)
- **Action:** Click sample chip **`2. OTP Mistake`**.
- **Message:** `"Urgent: I accidentally sent an OTP to your phone by mistake, please share the OTP"`
- **Action:** Click **"சரிபார் (Analyze)"**.
- **Highlight:**
  > "Notice how our routing rule works: even though this message mentions OTP, it is recognized as a forwarded scam attempting credential theft, NOT an incident report. The bot immediately flags it as a SCAM with `ASK_SENSITIVE` and advises the user to never share their OTP."

### Section D: Demo Case 3 — Digital Arrest Impersonation (1:45 - 2:20)
- **Action:** Click sample chip **`3. Digital Arrest`**.
- **Message:** `"This is CBI officer Sharma. Digital arrest warrant issued. Transfer money immediately or police will arrive."`
- **Action:** Click **"சரிபார் (Analyze)"**.
- **Visual & Audio:**
  - Highlights `POLICE_IMPERSONATION` and `URGENT_DEMAND`.
  - Clear advice: Law enforcement never places citizens under 'digital arrest' or demands money over phone.
  - Guides user to dial **1930** (National Cyber Crime Helpline).

### Section E: Language Toggle & Telegram Bot Demo (2:20 - 3:00)
- **Action:** Click the **"English"** toggle button at the top of the console.
- **Visual:** UI translates to English. Re-analyze Case 1.
- **Audio:** Play the voice note — hears **en-IN-NeerjaNeural** speaking Indian English.
- **Switch to Telegram Window (Optional Backup):**
  - Show Telegram chat with `/demo` command.
  - Tap button `[1. SBI KYC Link]`.
  - Show the verdict card and the Telegram voice note with the waveform.
- **Closing Statement:**
  > "Arivaran stores zero message text, zero phone numbers, and operates completely offline with pre-cached audio. Arivaran — protecting everyday citizens against cyber fraud."
