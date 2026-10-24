# ARIVUARAN (அறிவுஅரண்) — Tamil Content Review Items
Status: `needs_native_review`

This document records all Tamil strings, phonetics, and UI text elements that require review and sign-off by native Tamil speakers and domain reviewers.

---

### 1. Spoken Digit Zero in Helpline 1930
- **Current Spoken String:** `"ஒன்று ஒன்பது மூன்று பூஜ்ஜியம்"`
- **Phonetic Replacement Target:** `1930` $\rightarrow$ `ஒன்று ஒன்பது மூன்று பூஜ்ஜியம்`
- **Review Question:**
  - Standard formal Tamil uses `பூஜ்ஜியம்` (Poojjiyam).
  - Spoken / colloquial Tamil commonly uses `பூஜியம்` or `சைபர்` (Saibar).
  - *Recommendation:* Keep `பூஜ்ஜியம்` as the default for formal clarity while reviewing whether rural elders prefer `சைபர்`.

---

### 2. Post-Verdict Follow-Up Line
- **Current Tamil Text:** `"மேலும் என்ன தெரிந்துகொள்ள வேண்டும்?"`
- **Context:** Sent as the short follow-up prompt accompanying the interactive buttons (`[ஏன்?]`, `[என்ன செய்வது?]`, etc.) after every verdict.
- **Review Question:**
  - Check whether `"மேலும் என்ன தெரிந்துகொள்ள வேண்டும்?"` feels natural and welcoming.
  - Alternatives:
    - `"அடுத்து என்ன செய்ய வேண்டும்?"`
    - `"வேறு என்ன தகவல் வேண்டும்?"`

---

### 3. Bot Name Spelling & Declension
- **Nominative:** `அறிவுஅரண்` (ARIVUARAN)
- **Genitive / Possessive:** `அறிவுஅரணின்`
- **Review Question:**
  - Verify whether `அறிவுஅரண்` (single compound) or `அறிவு அரண்` (spaced) is preferred for branding and official communication.

---

### 4. Technical & Incident Terminology
| Key | Current Tamil String | Spoken TTS String | Alternative / Question |
| :--- | :--- | :--- | :--- |
| `INC_OTP` | `"OTP சொல்லிவிட்டேன்"` | `"ஓ டி பி சொல்லிவிட்டேன்"` | `"ஓடிபி கொடுத்துட்டேன்"` (colloquial) |
| `INC_LINK` | `"லிங்க் திறந்தேன்"` | `"லிங்க் திறந்தேன்"` | `"இணைப்பைத் திறந்தேன்"` (formal) vs `"லிங்க் ஓபன் பண்ணிட்டேன்"` (Tanglish) |
| `INC_ANYDESK` | `"செயலி நிறுவினேன்"` | `"செயலி நிறுவினேன்"` | `"ஆப் டவுன்லோட் பண்ணிட்டேன்"` / `"ரிமோட் ஆப் இன்ஸ்டால் பண்ணிட்டேன்"` |
| `INC_PAID` | `"பணம் அனுப்பினேன்"` | `"பணம் அனுப்பினேன்"` | `"காசு அனுப்பிட்டேன்"` / `"பணம் போச்சு"` |
| `INC_CARD` | `"கார்டு விவரம் கொடுத்தேன்"` | `"கார்டு விவரம் கொடுத்தேன்"` | `"அட்டை விவரம் பகிர்ந்தேன்"` |

---

### 5. Thirukkural 421 Text & Attribution
- **Couplet:**
  ```text
  அறிவற்றங் காக்கும் கருவி செறுவார்க்கும்
  உள்ளழிக்கல் ஆகா அரண்
  ```
- **Attribution:** `— குறள் 421`
- **Status:** **APPROVED & LOCKED** (Kept exactly as transmitted in classic Tamil literature).

---

### 6. Missing Tamil String: `F_NEED_VERDICT`
- **Current Tamil Text:** `"முதலில் நீங்கள் சரிபார்க்க விரும்பும் செய்தியை எனக்கு அனுப்புங்கள்."`
- **English Gloss:** `"Please send the message you want to check first."`
- **Source Status:** `MISSING - ask the team` in `data/replies_ta.json` (unspecified in original `docs/conversation_design.md`).
- **Context:** Sent when a user taps a follow-up button like `[ஏன்?]` (Why?) or `[பாதுகாப்பானதா?]` without having submitted any message for verdict analysis yet.
- **Review Question:**
  - Check whether this phrasing is natural and clear for rural users, or if `"முதலில் நீங்கள் சந்தேகப்படும் செய்தியை எனக்கு அனுப்புங்கள்."` is clearer.

---

### 7. Voice Retry Prompt (`S_VOICE_RETRY`)
- **Current Status:** `MISSING - ask the team` (shows English draft to Tamil users until reviewed).
- **English Draft:** `"I couldn't hear that clearly. Please record again or type the message as text."`
- **Context:** Sent when voice confidence is below threshold, speech contains unrecognised scripts, or voice note times out.
- **Review Question:**
  - Provide a natural Tamil translation for rural users asking them to record again in a quiet place or type the text.
  - Suggested draft: `"குரல் தெளிவாக கேட்கவில்லை. அமைதியான இடத்தில் மீண்டும் பதிவு செய்யவும் அல்லது செய்தியை தட்டச்சு செய்யவும்."`

---

### 8. Voice No Reassurance Warning (`S_VOICE_NO_VERDICT`)
- **Current Status:** `MISSING - ask the team` (shows English draft to Tamil users until reviewed).
- **English Draft:** `"I can't reliably check a spoken description. If you have the actual message, send it as text or a screenshot. If money or an OTP was involved, call 1930."`
- **Context:** Sent when a voice note has no explicit scam indicators. Voice notes are never given a `NO_RED_FLAGS` reassuring verdict.
- **Review Question:**
  - Provide an authentic Tamil translation that avoids giving false safety reassurance for spoken descriptions and directs user to 1930 / forwarding the original message.
  - Suggested draft: `"வாய்வழியாக விவரித்ததை வைத்து உறுதியாகக் கூற முடியாது. உண்மையான செய்தியை உரை அல்லது ஸ்கிரீன்ஷாட்டாக அனுப்பவும். பணம் அல்லது OTP சம்பந்தப்பட்டிருந்தால் உடனே 1930-ஐ அழைக்கவும்."`

