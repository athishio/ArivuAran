"""
Local Console Web Page for ArivuAran (127.0.0.1 only).
Provides a browser-based UI for scam verification with audio playback and language toggle.
Uses the exact same deterministic engine and TTS pipeline as the Telegram bot.
Enables demo continuation even if Telegram is blocked or network is restricted.
"""

import os
import sys
import html
from typing import Optional
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

WORKSPACE_ROOT = os.path.dirname(os.path.abspath(__file__))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import config
import db
import tts
import bot
from engine.decide import analyse

app = FastAPI(title="ArivuAran Local Console", docs_url=None, redoc_url=None)

CACHE_AUDIO_DIR = os.path.join(WORKSPACE_ROOT, "cache", "audio")
os.makedirs(CACHE_AUDIO_DIR, exist_ok=True)


DEMO_SAMPLES = {
    "kyc": "Your SBI account is blocked. Update KYC immediately at http://sbi-kyc-verify.xyz",
    "otp_mistake": "Urgent: I accidentally sent an OTP to your phone by mistake, please share the OTP",
    "digital_arrest": "This is CBI officer Sharma. Digital arrest warrant issued. Transfer money immediately or police will arrive.",
    "upi_collect": "Paytm: Collect request Rs 5000 approved. Click link to receive money.",
    "job_task": "Simple part time job work from home. Daily 5000 like youtube videos contact t.me/task_scam",
}


@app.get("/audio/{filename}")
async def get_audio(filename: str):
    """Serves synthesized / cached audio clips."""
    safe_name = os.path.basename(filename)
    path = os.path.join(CACHE_AUDIO_DIR, safe_name)
    if os.path.exists(path):
        media_type = "audio/ogg" if safe_name.endswith(".ogg") else "audio/mpeg"
        return FileResponse(path, media_type=media_type)
    return HTMLResponse("Audio file not found", status_code=404)


@app.get("/", response_class=HTMLResponse)
async def get_console(lang: str = "ta"):
    return render_page(lang=lang, input_text="", result=None)


@app.post("/analyze", response_class=HTMLResponse)
async def post_analyze(text: str = Form(...), lang: str = Form("ta")):
    clean_text = text.strip()
    if not clean_text:
        return render_page(lang=lang, input_text="", result=None)

    # Deterministic analysis (< 1ms)
    analysis = analyse(clean_text)

    # Build reply text and follow-up
    reply_text = bot.build_verdict_reply(analysis, lang=lang)
    followup_text, buttons = bot.build_followup_message(analysis.verdict, lang=lang)

    # Synthesize verdict voice (cached)
    signals = [s.code for s in analysis.signals]
    voice_res = await tts.synthesize_verdict_voice(
        verdict=analysis.verdict,
        signals=signals,
        lang=lang
    )

    audio_url = None
    audio_dur = None
    if voice_res:
        v_path, dur = voice_res
        if v_path and os.path.exists(v_path):
            audio_url = f"/audio/{os.path.basename(v_path)}"
            audio_dur = dur

    result_data = {
        "verdict": analysis.verdict,
        "score": analysis.score,
        "signals": analysis.signals,
        "reply_text": reply_text,
        "followup_text": followup_text,
        "buttons": buttons,
        "audio_url": audio_url,
        "audio_dur": audio_dur,
    }

    return render_page(lang=lang, input_text=clean_text, result=result_data)


def render_page(lang: str, input_text: str, result: Optional[dict]) -> str:
    is_ta = lang == "ta"
    title_sub = "மோசடி சரிபார்ப்பு உள்ளூர் தளம்" if is_ta else "Deterministic Scam Verification Console"
    placeholder = "சந்தேகமான SMS, செய்தி அல்லது லிங்கை இங்கே ஒட்டவும்..." if is_ta else "Paste suspicious SMS, message or link here..."
    btn_analyze = "சரிபார் (Analyze)" if is_ta else "Analyze Message"
    sample_lbl = "மாதிரி செய்திகள் (Demo Samples):" if is_ta else "Quick Demo Samples:"

    res_html = ""
    if result:
        v = result["verdict"]
        score = result["score"]
        if v == "SCAM":
            badge_class = "badge-scam"
            badge_text = "🔴 மோசடி (SCAM)" if is_ta else "🔴 SCAM DETECTED"
        elif v == "SUSPICIOUS":
            badge_class = "badge-susp"
            badge_text = "🟡 சந்தேகத்துக்குரியது (SUSPICIOUS)" if is_ta else "🟡 SUSPICIOUS"
        else:
            badge_class = "badge-safe"
            badge_text = "ℹ️ எச்சரிக்கை அறிகுறி இல்லை" if is_ta else "ℹ️ NO RED FLAGS FOUND"

        sigs_html = "".join([f"<li><code>+{s.points} pts</code> <b>{html.escape(s.code)}</b>: {html.escape(s.detail)}</li>" for s in result["signals"]])

        audio_player = ""
        if result["audio_url"]:
            audio_player = f"""
            <div class="audio-box">
              <p>🔊 <b>குரல் விளக்கம் (Voice Summary)</b> [{result['audio_dur']:.1f}s]:</p>
              <audio controls autoplay src="{result['audio_url']}" style="width: 100%; margin-top: 8px;"></audio>
            </div>
            """

        btns_html = " ".join([f"<span class='btn-tag'>{html.escape(b['title'])}</span>" for b in result["buttons"]])

        res_html = f"""
        <div class="result-card">
          <div class="badge {badge_class}">{badge_text}</div>
          <p class="score-line">Score: <b>{score} pts</b></p>
          <div class="message-body">{result['reply_text']}</div>
          {audio_player}
          <div class="signals-box">
            <h4>கண்டறியப்பட்ட காரணங்கள் (Fired Signals):</h4>
            <ul>{sigs_html or '<li>None</li>'}</ul>
          </div>
          <div class="followup-box">
            <p><b>{html.escape(result['followup_text'])}</b></p>
            <div style="margin-top: 8px;">{btns_html}</div>
          </div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{config.BOT_NAME_TA} ({config.BOT_NAME_EN}) — Console</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil:wght@400;600;700&display=swap');
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Noto Sans Tamil', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0b1120;
    color: #f1f5f9;
    padding: 24px 16px;
    display: flex;
    justify-content: center;
  }}
  .container {{
    max-width: 720px;
    width: 100%;
  }}
  header {{
    text-align: center;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid #1e293b;
  }}
  .brand {{
    font-size: 26px;
    font-weight: 700;
    color: #38bdf8;
    letter-spacing: 0.5px;
  }}
  .sub {{
    font-size: 14px;
    color: #94a3b8;
    margin-top: 4px;
  }}
  .lang-toggle {{
    margin-top: 12px;
    display: flex;
    justify-content: center;
    gap: 8px;
  }}
  .lang-btn {{
    padding: 4px 12px;
    border-radius: 6px;
    font-size: 13px;
    text-decoration: none;
    border: 1px solid #334155;
    color: #94a3b8;
  }}
  .lang-btn.active {{
    background: #0284c7;
    color: #ffffff;
    border-color: #0284c7;
    font-weight: 600;
  }}
  .samples {{
    margin-bottom: 16px;
    font-size: 13px;
    color: #94a3b8;
  }}
  .sample-chip {{
    display: inline-block;
    background: #1e293b;
    color: #cbd5e1;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    margin: 4px 4px 0 0;
    cursor: pointer;
    border: 1px solid #334155;
  }}
  .sample-chip:hover {{ background: #334155; }}
  textarea {{
    width: 100%;
    height: 120px;
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 12px;
    color: #ffffff;
    font-size: 15px;
    font-family: inherit;
    resize: vertical;
  }}
  textarea:focus {{ outline: none; border-color: #38bdf8; }}
  .submit-btn {{
    width: 100%;
    margin-top: 12px;
    padding: 12px;
    background: #0284c7;
    border: none;
    border-radius: 8px;
    color: #ffffff;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
  }}
  .submit-btn:hover {{ background: #0369a1; }}
  .result-card {{
    margin-top: 24px;
    background: #111827;
    border: 1px solid #374151;
    border-radius: 12px;
    padding: 20px;
  }}
  .badge {{
    display: inline-block;
    padding: 6px 14px;
    border-radius: 6px;
    font-weight: 700;
    font-size: 14px;
    margin-bottom: 12px;
  }}
  .badge-scam {{ background: #7f1d1d; color: #fca5a5; border: 1px solid #ef4444; }}
  .badge-susp {{ background: #713f12; color: #fde047; border: 1px solid #eab308; }}
  .badge-safe {{ background: #1e293b; color: #93c5fd; border: 1px solid #3b82f6; }}
  .score-line {{ font-size: 13px; color: #94a3b8; margin-bottom: 12px; }}
  .message-body {{
    background: #1e293b;
    padding: 16px;
    border-radius: 8px;
    line-height: 1.6;
    font-size: 15px;
    white-space: pre-wrap;
    margin-bottom: 16px;
  }}
  .audio-box {{
    background: #0f172a;
    border: 1px solid #334155;
    padding: 14px;
    border-radius: 8px;
    margin-bottom: 16px;
  }}
  .signals-box {{
    background: #0f172a;
    padding: 12px;
    border-radius: 8px;
    font-size: 13px;
    color: #cbd5e1;
    margin-bottom: 16px;
  }}
  .signals-box ul {{ padding-left: 20px; margin-top: 6px; }}
  .followup-box {{
    border-top: 1px solid #374151;
    padding-top: 12px;
    font-size: 14px;
  }}
  .btn-tag {{
    display: inline-block;
    background: #374151;
    padding: 4px 10px;
    border-radius: 4px;
    font-size: 12px;
    margin-right: 6px;
    color: #e2e8f0;
  }}
</style>
<script>
  const samples = {json.dumps(DEMO_SAMPLES)};
  function setSample(k) {{
    document.getElementById('msgInput').value = samples[k];
  }}
</script>
</head>
<body>
<div class="container">
  <header>
    <div class="brand">{config.BOT_NAME_TA} ({config.BOT_NAME_EN})</div>
    <div class="sub">{title_sub} — 127.0.0.1 Offline Backup</div>
    <div class="lang-toggle">
      <a href="/?lang=ta" class="lang-btn {'active' if is_ta else ''}">தமிழ் (Tamil)</a>
      <a href="/?lang=en" class="lang-btn {'active' if not is_ta else ''}">English</a>
    </div>
  </header>

  <form method="post" action="/analyze">
    <input type="hidden" name="lang" value="{lang}">
    <div class="samples">
      <span>{sample_lbl}</span><br>
      <span class="sample-chip" onclick="setSample('kyc')">1. SBI KYC</span>
      <span class="sample-chip" onclick="setSample('otp_mistake')">2. OTP Mistake</span>
      <span class="sample-chip" onclick="setSample('digital_arrest')">3. Digital Arrest</span>
      <span class="sample-chip" onclick="setSample('upi_collect')">4. UPI Collect</span>
      <span class="sample-chip" onclick="setSample('job_task')">5. Job Task</span>
    </div>
    <textarea id="msgInput" name="text" placeholder="{placeholder}">{html.escape(input_text)}</textarea>
    <button type="submit" class="submit-btn">{btn_analyze}</button>
  </form>

  {res_html}
</div>
</body>
</html>
"""


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("console:app", host="127.0.0.1", port=8000, reload=False)
