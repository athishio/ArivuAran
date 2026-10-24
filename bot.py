"""
ARIVUARAN Telegram Bot Entry Point & Handlers.
Long polling connection layer for Tamil scam detection bot.
Processes text, voice notes, and inline button callbacks.
Strictly deterministic, zero LLM, template-driven replies from data/replies_ta.json.
"""

import os
import sys
import re
import html
import time
import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional, Dict, List, Tuple
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

import telegram_io
import db
import speech
import tts
import card_renderer
import config
from config import BOT_NAME_EN, BOT_NAME_TA, BOT_NAME_TA_GEN
from engine.decide import analyse
from engine.intents import (
    classify_intent,
    resolve_intent_response,
    get_reply,
    format_template,
    session_manager,
    SIGNAL_TO_REASON_ID,
    SCAM_TYPE_TA_NAMES,
    SCAM_TYPE_EN_NAMES,
    INC_KEYWORDS,
    FOLLOWUP_KEYWORDS,
)

# Configure minimal logger
logger = logging.getLogger("arivuaran_telegram_bot")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# 1. Config & Validation
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
SALT = os.getenv("SALT")

missing_vars = []
if not BOT_TOKEN:
    missing_vars.append("BOT_TOKEN")
if not SALT:
    missing_vars.append("SALT")

if missing_vars:
    error_msg = f"Fatal Startup Error: Missing required environment variable(s): {', '.join(missing_vars)} in .env"
    logger.critical(error_msg)
    raise RuntimeError(error_msg)


DEMO_CASES: Dict[str, str] = {
    "DEMO_1_KYC": "Your SBI account is blocked. Update KYC immediately at http://sbi-kyc-verify.xyz",
    "DEMO_2_OTP": "Urgent: I accidentally sent an OTP to your phone by mistake, please share the OTP",
    "DEMO_3_ARREST": "This is CBI officer Sharma. Digital arrest warrant issued. Transfer money immediately or police will arrive.",
    "DEMO_4_UPI": "Paytm: Collect request Rs 5000 approved. Click link to receive money.",
    "DEMO_5_JOB": "Simple part time job work from home. Daily 5000 like youtube videos contact t.me/task_scam",
}


# In-memory Rate Limiting: 20 messages per minute per chat
RATE_LIMIT_MAX = 20
RATE_LIMIT_WINDOW = 60  # seconds
chat_request_timestamps: Dict[int, List[float]] = defaultdict(list)

# In-memory store for pending voice transcripts awaiting user confirmation
# chat_id -> (transcription_text, timestamp)
_pending_voice_transcripts: Dict[int, Tuple[str, float]] = {}


def check_rate_limit(chat_id: int) -> bool:
    """Returns True if chat is within limit (20 msgs / min), False if rate-limited."""
    now = time.time()
    timestamps = chat_request_timestamps[chat_id]
    timestamps = [ts for ts in timestamps if now - ts < RATE_LIMIT_WINDOW]
    chat_request_timestamps[chat_id] = timestamps

    if len(timestamps) >= RATE_LIMIT_MAX:
        return False

    timestamps.append(now)
    return True


def get_display_reasons(analysis, lang: str = "ta") -> List[str]:
    """Extracts up to 2 distinct reason texts for UI display."""
    reasons: List[str] = []
    for s in analysis.signals:
        rid = SIGNAL_TO_REASON_ID.get(s.code)
        if rid:
            r_entry = get_reply(rid)
            if r_entry:
                txt = r_entry.get("en_gloss" if lang == "en" else "ta")
                if txt and txt not in reasons:
                    reasons.append(txt)
    return reasons


def build_verdict_reply(analysis, lang: str = "ta") -> str:
    """Formats verdict reply strictly using Telegram HTML without buttons."""
    if lang == "en":
        reasons = get_display_reasons(analysis, lang="en")
        r1 = reasons[0] if len(reasons) > 0 else "Suspicious patterns detected."
        r2 = reasons[1] if len(reasons) > 1 else "Unverified sender details."

        if analysis.verdict == "SCAM":
            return (
                "⚠️ <b>This looks like a scam.</b>\n\n"
                f"Reasons:\n1. {html.escape(r1)}\n2. {html.escape(r2)}\n\n"
                "What to do:\n"
                "• Do not click or open the link.\n"
                "• Never share your OTP or PIN with anyone.\n"
                "• If in doubt, call your bank's official helpline."
            )
        elif analysis.verdict == "SUSPICIOUS":
            return (
                "🟡 <b>This looks suspicious.</b>\n"
                "I cannot confirm with certainty whether this is genuine.\n\n"
                f"Reasons:\n1. {html.escape(r1)}\n2. {html.escape(r2)}\n\n"
                "What to do:\n"
                "• Do not click or open any link.\n"
                "• Verify directly in your bank's official app or site.\n"
                "• Never share your OTP or PIN with anyone."
            )
        else:
            return (
                "ℹ️ <b>No red flags found in this message.</b>\n\n"
                "What to do:\n"
                "• This does not guarantee the message is safe.\n"
                "• Stay alert if it was sent by an unknown number.\n"
                "• Never share your OTP or PIN with anyone."
            )
    else:
        # Tamil (Strictly approved templates)
        reasons = get_display_reasons(analysis, lang="ta")
        r1 = reasons[0] if len(reasons) > 0 else "சந்தேகத்திற்கிடமான தந்திரங்கள் உள்ளன."
        r2 = reasons[1] if len(reasons) > 1 else "அங்கீகரிக்கப்படாத கோரிக்கைகள் உள்ளன."

        if analysis.verdict == "SCAM":
            return (
                "⚠️ <b>இது மோசடி போல் உள்ளது.</b>\n\n"
                f"காரணங்கள்:\n1. {html.escape(r1)}\n2. {html.escape(r2)}\n\n"
                "செய்ய வேண்டியவை:\n"
                "• லிங்கைத் தொடாதீர்கள்.\n"
                "• OTP, PIN யாரிடமும் சொல்லாதீர்கள்.\n"
                "• சந்தேகம் இருந்தால் உங்கள் வங்கியின் அதிகாரப்பூர்வ எண்ணை அழையுங்கள்."
            )
        elif analysis.verdict == "SUSPICIOUS":
            return (
                "🟡 <b>இது சந்தேகத்துக்குரியது.</b>\n"
                "இது மோசடியா என்று என்னால் உறுதியாகச் சொல்ல முடியவில்லை.\n\n"
                f"காரணங்கள்:\n1. {html.escape(r1)}\n2. {html.escape(r2)}\n\n"
                "செய்ய வேண்டியவை:\n"
                "• லிங்கைத் திறக்க வேண்டாம்.\n"
                "• உங்கள் வங்கியின் செயலியில் நீங்களே பாருங்கள்.\n"
                "• OTP, PIN யாரிடமும் சொல்லாதீர்கள்."
            )
        else:
            return (
                "ℹ️ <b>இதில் எச்சரிக்கை அறிகுறிகள் எதுவும் கிடைக்கவில்லை.</b>\n\n"
                "செய்ய வேண்டியவை:\n"
                "• இது பாதுகாப்பானது என்று அர்த்தம் இல்லை.\n"
                "• தெரியாத எண்ணிலிருந்து வந்தால் கவனமாக இருங்கள்.\n"
                "• OTP, PIN யாரிடமும் சொல்லாதீர்கள்."
            )


def build_followup_message(verdict: str, lang: str = "ta") -> Tuple[str, List[Dict[str, str]]]:
    """
    Returns (followup_text, buttons) for the post-verdict prompt.
    Does not repeat the verdict.
    If verdict is NO_RED_FLAGS, 'Why?' is omitted.
    """
    if lang == "en":
        text = "What would you like to know next?"
        if verdict == "NO_RED_FLAGS":
            buttons = [
                {"id": "F_TODO", "title": "What should I do?"},
                {"id": "F_LEARN", "title": "Learn"},
                {"id": "F_SHARE", "title": "Send to family"},
                {"id": "INC_MENU", "title": "I already..."},
            ]
        else:
            buttons = [
                {"id": "F_WHY", "title": "Why?"},
                {"id": "F_TODO", "title": "What should I do?"},
                {"id": "F_LEARN", "title": "Learn"},
                {"id": "F_SHARE", "title": "Send to family"},
                {"id": "INC_MENU", "title": "I already..."},
            ]
    else:
        text = "மேலும் என்ன தெரிந்துகொள்ள வேண்டும்?"
        if verdict == "NO_RED_FLAGS":
            buttons = [
                {"id": "F_TODO", "title": "என்ன செய்வது?"},
                {"id": "F_LEARN", "title": "கற்றுக்கொள்"},
                {"id": "F_SHARE", "title": "குடும்பத்துக்கு அனுப்பு"},
                {"id": "INC_MENU", "title": "நான் ஏற்கனவே..."},
            ]
        else:
            buttons = [
                {"id": "F_WHY", "title": "ஏன்?"},
                {"id": "F_TODO", "title": "என்ன செய்வது?"},
                {"id": "F_LEARN", "title": "கற்றுக்கொள்"},
                {"id": "F_SHARE", "title": "குடும்பத்துக்கு அனுப்பு"},
                {"id": "INC_MENU", "title": "நான் ஏற்கனவே..."},
            ]
    return text, buttons


def build_verdict_buttons() -> List[Dict[str, str]]:
    """Legacy helper for backwards compatibility."""
    return [
        {"id": "F_WHY", "title": "ஏன்?"},
        {"id": "F_TODO", "title": "என்ன செய்வது?"},
        {"id": "F_LEARN", "title": "கற்றுக்கொள்"},
        {"id": "F_SHARE", "title": "குடும்பத்துக்கு அனுப்பு"},
        {"id": "INC_MENU", "title": "நான் ஏற்கனவே..."},
    ]


def build_inc_menu_buttons(lang: str = "ta") -> List[Dict[str, str]]:
    """Returns the menu of 5 INC emergency incident cases."""
    if lang == "en":
        return [
            {"id": "INC_OTP", "title": "I gave OTP"},
            {"id": "INC_LINK", "title": "I opened link"},
            {"id": "INC_ANYDESK", "title": "I installed app"},
            {"id": "INC_PAID", "title": "I sent money"},
            {"id": "INC_CARD", "title": "I gave card details"},
        ]
    return [
        {"id": "INC_OTP", "title": "OTP சொல்லிவிட்டேன்"},
        {"id": "INC_LINK", "title": "லிங்க் திறந்தேன்"},
        {"id": "INC_ANYDESK", "title": "செயலி நிறுவினேன்"},
        {"id": "INC_PAID", "title": "பணம் அனுப்பினேன்"},
        {"id": "INC_CARD", "title": "கார்டு விவரம் கொடுத்தேன்"},
    ]


def should_route_to_intent(text: str) -> bool:
    """
    Routing rule:
    1. Forwarded scam indicators (asking to share/send OTP or claims of 'sent by mistake')
       must ALWAYS go to verdict engine, never to an intent.
    2. Short messages (< 10 words) matching an emergency incident (INC_*)
       (e.g. 'paid 5000', 'ரூ 5000 அனுப்பிட்டேன்', 'otp sollitten', 'I clicked the link')
       must route to INC_* even if they contain numbers/amounts.
    3. For other general follow-ups (F_*): must be short (< 8 words), have no link, and no digits.
    """
    if not text or not text.strip():
        return False

    norm = text.lower().strip()

    # Rule 1: Forwarded scam asking to share/forward OTP or claiming sent by mistake -> ALWAYS VERDICT
    if ("sent by mistake" in norm or "by mistake" in norm) and ("otp" in norm or "pin" in norm):
        return False
    if ("share" in norm or "send" in norm or "tell" in norm or "forward" in norm) and ("otp" in norm or "pin" in norm):
        # Exception: user reporting they shared ("shared my otp", "shared otp", "i sent otp", "told the otp")
        if not any(p in norm for p in ["shared my otp", "i shared", "i sent otp", "i gave otp", "told the otp", "shared otp"]):
            return False
    if "தவறுதலாக" in norm and ("otp" in norm or "ஓடிபி" in norm):
        return False
    if ("சொல்லுங்க" in norm or "அனுப்புங்க" in norm or "பகிரவும்" in norm) and ("otp" in norm or "ஓடிபி" in norm or "கடவுச்சொல்" in norm):
        return False

    # Check for links/URLs: any domain/URL goes to scam analysis engine
    if re.search(r"https?://|www\.|\b[a-zA-Z0-9-]+\.(?:com|org|in|net|info|top|xyz|apk|link|co)\b", text, re.IGNORECASE):
        return False

    words = text.split()

    # Rule 2: Emergency incident reports (INC_*) can contain amount digits (e.g. "paid 5000", "ரூ 5000 அனுப்பிட்டேன்")
    if len(words) < 10:
        cand_intent = classify_intent(text)
        if cand_intent in INC_KEYWORDS:
            return True

    # Rule 3: General follow-ups (F_*) must be < 8 words, have NO digits, and match a known intent
    if len(words) >= 8:
        return False
    if re.search(r"\d+", text):
        return False

    cand_intent = classify_intent(text)
    if cand_intent == "F_UNKNOWN":
        return False

    return True


# =====================================================================
# CORE INTEGRATION HOOK
# =====================================================================
async def handle_message(user_id: int, msg_type: str, content: Any, chat_id: Optional[int] = None) -> None:
    """
    CENTRAL INTEGRATION HOOK: Scoring, Rules, Replies, STT, and DB.
    Never stores raw message text, transcripts, or credentials in DB/logs.
    """
    effective_chat_id = chat_id or user_id
    masked_user = telegram_io.mask_id(user_id)
    timestamp = datetime.now(timezone.utc).isoformat()
    sender_hash = db.hash_sender(str(user_id))

    try:
        # 1. Check persistent language preference in DB or active session
        saved_lang = db.get_user_language(sender_hash)
        sess = session_manager.get(effective_chat_id)
        user_lang = (sess.language if sess and sess.language else None) or saved_lang

        # 2. Interactive Button Callback Handling
        if msg_type == "button":
            callback_id = str(content or "").strip()

            # Handle Bilingual Language Selection Buttons
            if callback_id in ("SET_LANG_TA", "SET_LANG_EN"):
                selected_lang = "ta" if callback_id == "SET_LANG_TA" else "en"
                db.set_user_language(sender_hash, selected_lang)
                session_manager.update(effective_chat_id, language=selected_lang)
                welcome_entry = get_reply("S_WELCOME")
                welcome_text = welcome_entry[selected_lang] if welcome_entry else "வணக்கம்!"
                await telegram_io.send_text(effective_chat_id, format_template(welcome_text))
                logger.info(f"[{timestamp}] msg_type='button' user_id={masked_user} action={callback_id}: SUCCESS")
                return

            # Handle Demo Case Buttons
            if callback_id in DEMO_CASES:
                canned_msg = DEMO_CASES[callback_id]
                # Run through the REAL pipeline with cached audio
                await handle_message(
                    user_id=user_id,
                    msg_type="text",
                    content=canned_msg,
                    chat_id=effective_chat_id
                )
                logger.info(f"[{timestamp}] msg_type='button' user_id={masked_user} action={callback_id} demo_run: SUCCESS")
                return

            if callback_id == "INC_MENU":
                # Open menu of 5 incident emergency options
                prompt_txt = "கீழே உள்ளவற்றில் நீங்கள் எதைச் செய்தீர்கள் என்று தேர்ந்தெடுக்கவும்:" if user_lang == "ta" else "Please select what happened:"
                await telegram_io.send_text(
                    effective_chat_id,
                    prompt_txt,
                    buttons=build_inc_menu_buttons(lang=user_lang)
                )
                logger.info(f"[{timestamp}] msg_type='button' user_id={masked_user} action=INC_MENU: SUCCESS")
                return

            elif callback_id in INC_KEYWORDS:
                # Emergency INC incident button
                reply_id, reply_text, _ = resolve_intent_response(
                    intent_id=callback_id,
                    chat_id=effective_chat_id,
                    session_store=session_manager,
                    lang=user_lang
                )
                await telegram_io.send_text(effective_chat_id, reply_text, buttons=build_inc_menu_buttons(lang=user_lang))
                logger.info(f"[{timestamp}] msg_type='button' user_id={masked_user} action={callback_id}: SUCCESS")
                return

            elif callback_id == "SHARE_CARD_GET":
                sess = session_manager.get(effective_chat_id)
                st_key = (sess.scam_type if sess else "")
                if not st_key:
                    # Fall back to latest database record if session expired or bot restarted
                    last_chk = db.get_last_check(sender_hash)
                    if last_chk and last_chk.get("fired_rules"):
                        st_key = str(last_chk["fired_rules"][0]).lower()
                    elif last_chk and last_chk.get("verdict"):
                        st_key = str(last_chk["verdict"]).lower()
                    else:
                        st_key = "unknown"

                scam_type_ta = SCAM_TYPE_TA_NAMES.get(st_key.lower()) or SCAM_TYPE_TA_NAMES.get("unknown", "மோசடி எச்சரிக்கை")
                scam_type_en = SCAM_TYPE_EN_NAMES.get(st_key.lower()) or st_key.replace("_", " ").title()
                if scam_type_en.lower() in ("unknown", "none", ""):
                    scam_type_en = "Suspicious Scam Alert"

                scam_type_label = scam_type_ta if user_lang == "ta" else scam_type_en
                caption_entry = get_reply("SHARE_CARD_CAPTION")
                caption_txt = caption_entry[user_lang] if caption_entry else ("இது உங்கள் பாதுகாப்புக்காக. தயவுசெய்து பாருங்கள் 🙏" if user_lang == "ta" else "This is for your safety. Please take a look 🙏")

                headline = "மோசடி எச்சரிக்கை!" if user_lang == "ta" else "Scam Alert!"
                advice = (
                    "இப்படி ஒரு செய்தி வந்தது. இது மோசடி. லிங்கைத் தொடாதீர்கள். OTP, PIN யாரிடமும் சொல்லாதீர்கள்."
                    if user_lang == "ta"
                    else "A suspicious message was received. This looks like a scam. Do not click links. Never share OTP or PIN with anyone."
                )

                card_img = await card_renderer.render_share_card(
                    scam_type=scam_type_label,
                    headline=headline,
                    advice=advice,
                    lang=user_lang
                )
                if card_img and os.path.exists(card_img):
                    await telegram_io.send_photo(effective_chat_id, card_img, caption=caption_txt)
                else:
                    card_entry = get_reply("SHARE_CARD")
                    card_tmpl = card_entry[user_lang] if card_entry else card_entry["ta"]
                    card_text = format_template(card_tmpl, scam_type_ta=scam_type_label)
                    full_card = f"{card_text}\n\n{caption_txt}"
                    await telegram_io.send_text(effective_chat_id, full_card)
                logger.info(f"[{timestamp}] msg_type='button' user_id={masked_user} action=SHARE_CARD_GET: SUCCESS")
                return

            elif callback_id == "SHARE_CARD_NO":
                await telegram_io.send_text(effective_chat_id, "சரி." if user_lang == "ta" else "Okay.")
                return

            elif callback_id in FOLLOWUP_KEYWORDS or callback_id in ("F_WHY", "F_TODO", "F_LEARN", "F_SHARE"):
                reply_id, reply_text, _ = resolve_intent_response(
                    intent_id=callback_id,
                    chat_id=effective_chat_id,
                    session_store=session_manager,
                    lang=user_lang
                )
                # If sharing card, attach confirmation buttons
                buttons = None
                if reply_id == "SHARE_CARD_OFFER":
                    if user_lang == "en":
                        buttons = [
                            {"id": "SHARE_CARD_GET", "title": "Get card"},
                            {"id": "SHARE_CARD_NO", "title": "No"},
                        ]
                    else:
                        buttons = [
                            {"id": "SHARE_CARD_GET", "title": "அட்டையைப் பெறு"},
                            {"id": "SHARE_CARD_NO", "title": "வேண்டாம்"},
                        ]
                await telegram_io.send_text(effective_chat_id, reply_text, buttons=buttons)
                logger.info(f"[{timestamp}] msg_type='button' user_id={masked_user} action={callback_id}: SUCCESS")
                return

            elif callback_id in ("wrong_result", "feedback_wrong", "F_WRONG"):
                db.log_feedback(sender_hash, "user_reported_incorrect")
                fb_entry = get_reply("S_FEEDBACK")
                fb_txt = fb_entry[user_lang] if fb_entry and user_lang in fb_entry else fb_entry["ta"]
                await telegram_io.send_text(effective_chat_id, fb_txt)
                logger.info(f"[{timestamp}] msg_type='button' user_id={masked_user} action=feedback_wrong: SUCCESS")
                return

            elif callback_id == "V_RETRY":
                _pending_voice_transcripts.pop(effective_chat_id, None)
                retry_entry = get_reply("S_VOICE_RETRY")
                retry_txt = retry_entry.get(user_lang) or retry_entry.get("en")
                if retry_txt == "MISSING - ask the team":
                    retry_txt = retry_entry.get("en")
                await telegram_io.send_text(effective_chat_id, retry_txt)
                logger.info(f"[{timestamp}] msg_type='button' user_id={masked_user} action=V_RETRY: SUCCESS")
                return

            elif callback_id == "V_CONFIRM":
                pending = _pending_voice_transcripts.pop(effective_chat_id, None)
                if not pending:
                    need_entry = get_reply("F_NEED_VERDICT")
                    need_txt = need_entry.get(user_lang) or need_entry.get("ta")
                    await telegram_io.send_text(effective_chat_id, need_txt)
                    return

                transcription, _ = pending

                # Step 4: Apply Voice-Only Normaliser before rule evaluation
                from engine.voice_norm import normalise_voice_transcript
                norm_transcription = normalise_voice_transcript(transcription)

                # Check if voice transcription was an intent
                intent_id = classify_intent(norm_transcription)
                if intent_id != "F_UNKNOWN":
                    reply_id, reply_text, _ = resolve_intent_response(intent_id, effective_chat_id, session_manager, lang=user_lang)
                    buttons = build_inc_menu_buttons(lang=user_lang) if intent_id in INC_KEYWORDS else None
                    await telegram_io.send_text(effective_chat_id, reply_text, buttons=buttons)
                    return

                # Deterministic verdict scoring
                analysis = analyse(norm_transcription)

                # Step 3: NO REASSURANCE FOR VOICE
                # If input came from voice note, never show NO_RED_FLAGS.
                if analysis.verdict == "NO_RED_FLAGS":
                    no_v_entry = get_reply("S_VOICE_NO_VERDICT")
                    no_v_txt = no_v_entry.get(user_lang) or no_v_entry.get("en")
                    if no_v_txt == "MISSING - ask the team":
                        no_v_txt = no_v_entry.get("en")
                    await telegram_io.send_text(effective_chat_id, no_v_txt)
                    logger.info(f"[{timestamp}] msg_type='button' user_id={masked_user} voice_verdict=NO_RED_FLAGS->S_VOICE_NO_VERDICT: SUCCESS")
                    return

                scam_type = None
                if analysis.signals:
                    pos_signals = [s for s in analysis.signals if s.points > 0]
                    if pos_signals:
                        top_sig = max(pos_signals, key=lambda s: s.points)
                        scam_type = top_sig.code.lower()

                session_manager.update(
                    chat_id=effective_chat_id,
                    verdict=analysis.verdict,
                    scam_type=scam_type,
                    signals=[s.code for s in analysis.signals]
                )

                db.log_check(
                    sender_hash=sender_hash,
                    msg_type="audio",
                    score=analysis.score,
                    verdict=analysis.verdict,
                    fired_rules=[s.code for s in analysis.signals]
                )

                reply_text = build_verdict_reply(analysis, lang=user_lang)
                session_manager.update(
                    chat_id=effective_chat_id,
                    last_reply_id=f"V_{analysis.verdict}",
                    last_reply_text=reply_text,
                    language=user_lang
                )

                await telegram_io.send_text(effective_chat_id, reply_text)

                try:
                    voice_res = await tts.synthesize_verdict_voice(
                        verdict=analysis.verdict,
                        signals=[s.code for s in analysis.signals],
                        lang=user_lang
                    )
                    if voice_res:
                        v_path, v_dur = voice_res
                        if v_path and os.path.exists(v_path):
                            await telegram_io.send_voice(effective_chat_id, v_path)
                except Exception as voice_err:
                    logger.warning(f"Voice reply skipped: {type(voice_err).__name__}")

                followup_text, buttons = build_followup_message(analysis.verdict, lang=user_lang)
                await telegram_io.send_text(
                    effective_chat_id,
                    followup_text,
                    buttons=buttons
                )
                logger.info(f"[{timestamp}] msg_type='button' user_id={masked_user} voice_verdict={analysis.verdict}: SUCCESS")
                return

            elif callback_id == "check_another":
                another_msg = "சரி! நீங்கள் சரிபார்க்க விரும்பும் அடுத்த செய்தியை எனக்கு அனுப்புங்கள்." if user_lang == "ta" else "Okay! Send me the next message you would like to check."
                await telegram_io.send_text(effective_chat_id, another_msg)
                return

            elif callback_id == "lost_money":
                reply_id, reply_text, _ = resolve_intent_response("INC_PAID", effective_chat_id, session_manager, lang=user_lang)
                await telegram_io.send_text(effective_chat_id, reply_text)
                return

            else:
                await telegram_io.send_text(effective_chat_id, get_reply("S_COMING_SOON")["ta"])
                return

        # Check if message is a language selection command (/language or /lang)
        is_lang_cmd = (
            msg_type == "text" and
            str(content or "").strip().lower().startswith(("/language", "/lang"))
        )

        # Prompt for language on first message if none is saved (unless explicitly setting language)
        if user_lang is None and not is_lang_cmd:
            bilingual_prompt = (
                "வணக்கம்! உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்.\n"
                "Welcome! Please select your language."
            )
            buttons = [
                {"id": "SET_LANG_TA", "title": "தமிழ்"},
                {"id": "SET_LANG_EN", "title": "English"},
            ]
            await telegram_io.send_text(effective_chat_id, bilingual_prompt, buttons=buttons)
            logger.info(f"[{timestamp}] msg_type='prompt_language' user_id={masked_user}: SUCCESS")
            return

        # 2. Rate Limiting Check (20 msgs / min per chat)
        if not check_rate_limit(effective_chat_id):
            await telegram_io.send_text(
                effective_chat_id,
                "⚠️ மிக விரைவாக செய்திகள் அனுப்பப்பட்டன. தயவுசெய்து ஒரு நிமிடம் கழித்து முயற்சிக்கவும்."
            )
            logger.warning(f"[{timestamp}] msg_type='{msg_type}' user_id={masked_user}: RATE_LIMITED")
            return

        # 3. Text Message Handling (includes forwarded SMS/messages)
        if msg_type == "text":
            text_str = str(content or "").strip()

            # Commands Handling
            if text_str.startswith("/"):
                cmd = text_str.split()[0].lower()
                if cmd == "/start":
                    bilingual_prompt = (
                        "வணக்கம்! உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்.\n"
                        "Welcome! Please select your language."
                    )
                    buttons = [
                        {"id": "SET_LANG_TA", "title": "தமிழ்"},
                        {"id": "SET_LANG_EN", "title": "English"},
                    ]
                    await telegram_io.send_text(effective_chat_id, bilingual_prompt, buttons=buttons)
                    logger.info(f"[{timestamp}] msg_type='command' cmd='/start' user_id={masked_user}: PROMPT_LANG")
                    return
                elif cmd == "/help":
                    demo_line_ta = "\n/demo — மாதிரி சோதனைகள் (Demo test cases)" if config.DEMO_MODE else ""
                    demo_line_en = "\n/demo — Demo test cases" if config.DEMO_MODE else ""
                    if user_lang == "en":
                        help_text = (
                            f"<b>{BOT_NAME_EN} — Commands:</b>\n\n"
                            f"/start — Start {BOT_NAME_EN} & select language\n"
                            f"/help — List commands\n"
                            f"/language — Select language\n"
                            f"/privacy — Privacy policy\n"
                            f"/stats — Live detection statistics\n"
                            f"/delete — Clear session & preferences"
                            f"{demo_line_en}"
                        )
                    else:
                        help_text = (
                            f"<b>{BOT_NAME_TA} — கட்டளைகள் (Commands):</b>\n\n"
                            f"/start — {BOT_NAME_TA} தொடங்கு (Start bot)\n"
                            f"/help — கட்டளைகளின் பட்டியல் (List commands)\n"
                            f"/language — மொழி தேர்வு (Select language)\n"
                            f"/privacy — தனியுரிமை கொள்கை (Privacy policy)\n"
                            f"/stats — நேரலை புள்ளிவிவரங்கள் (Live stats)\n"
                            f"/delete — தற்காலிக நினைவகத்தை அழி (Clear session memory)"
                            f"{demo_line_ta}"
                        )
                    await telegram_io.send_text(effective_chat_id, help_text)
                    logger.info(f"[{timestamp}] msg_type='command' cmd='/help' user_id={masked_user}: SUCCESS")
                    return
                elif cmd == "/privacy":
                    privacy_entry = get_reply("F_PRIVACY")
                    p_txt = privacy_entry[user_lang] if privacy_entry else ""
                    await telegram_io.send_text(effective_chat_id, format_template(p_txt))
                    logger.info(f"[{timestamp}] msg_type='command' cmd='/privacy' user_id={masked_user}: SUCCESS")
                    return
                elif cmd == "/delete":
                    session_manager.clear(effective_chat_id)
                    db.delete_user_language(sender_hash)
                    del_msg = "நினைவகம் மற்றும் மொழி அமைப்பு அழிக்கப்பட்டது (Session memory and preferences cleared)." if user_lang == "ta" else "Session memory and preferences cleared."
                    await telegram_io.send_text(effective_chat_id, del_msg)
                    logger.info(f"[{timestamp}] msg_type='command' cmd='/delete' user_id={masked_user}: SUCCESS")
                    return
                elif cmd in ("/language", "/lang"):
                    parts = text_str.split()
                    if len(parts) > 1:
                        target_lang = parts[1].lower()
                        if target_lang in ("en", "english"):
                            user_lang = "en"
                            db.set_user_language(sender_hash, "en")
                            session_manager.update(effective_chat_id, language="en")
                            await telegram_io.send_text(effective_chat_id, "Language set to English.")
                        else:
                            user_lang = "ta"
                            db.set_user_language(sender_hash, "ta")
                            session_manager.update(effective_chat_id, language="ta")
                            await telegram_io.send_text(effective_chat_id, "மொழி தமிழுக்கு மாற்றப்பட்டது.")
                    else:
                        prompt_txt = "மொழியைத் தேர்ந்தெடுக்கவும் / Select your language:"
                        btns = [
                            {"id": "SET_LANG_TA", "title": "தமிழ்"},
                            {"id": "SET_LANG_EN", "title": "English"},
                        ]
                        await telegram_io.send_text(effective_chat_id, prompt_txt, buttons=btns)
                    logger.info(f"[{timestamp}] msg_type='command' cmd='{cmd}' user_id={masked_user}: SUCCESS")
                    return
                elif cmd == "/demo":
                    if not config.DEMO_MODE:
                        msg = "டெமோ முறை முடக்கப்பட்டுள்ளது (Demo mode is disabled)." if user_lang == "ta" else "Demo mode is disabled. Set DEMO_MODE=true in .env to enable."
                        await telegram_io.send_text(effective_chat_id, msg)
                        return

                    demo_title = (
                        "🎯 <b>மாதிரி சோதனைகள் (Demo Cases):</b>\n"
                        "கீழே உள்ள மாதிரி செய்திகளில் ஒன்றைத் தேர்ந்தெடுக்கவும்:"
                        if user_lang == "ta"
                        else "🎯 <b>Demo Test Cases:</b>\nSelect one of the canned test cases below:"
                    )
                    demo_btns = [
                        {"id": "DEMO_1_KYC", "title": "1. SBI KYC Phishing"},
                        {"id": "DEMO_2_OTP", "title": "2. OTP Mistake Threat"},
                        {"id": "DEMO_3_ARREST", "title": "3. Digital Arrest"},
                        {"id": "DEMO_4_UPI", "title": "4. UPI Collect Scam"},
                        {"id": "DEMO_5_JOB", "title": "5. Job Task Scam"},
                    ]
                    await telegram_io.send_text(effective_chat_id, demo_title, buttons=demo_btns)
                    logger.info(f"[{timestamp}] msg_type='command' cmd='/demo' user_id={masked_user}: SUCCESS")
                    return
                elif cmd == "/stats":
                    stats = db.get_stats()
                    v_counts = stats.get("verdict_counts", {})
                    scam_c = v_counts.get("SCAM", 0)
                    susp_c = v_counts.get("SUSPICIOUS", 0)
                    safe_c = v_counts.get("NO_RED_FLAGS", 0) or v_counts.get("LIKELY_SAFE", 0)
                    total_c = scam_c + susp_c + safe_c
                    if user_lang == "en":
                        msg = (
                            f"📊 <b>{BOT_NAME_EN} Live Statistics</b>\n\n"
                            f"• Total checks: {total_c}\n"
                            f"• Scams detected: {scam_c}\n"
                            f"• Suspicious: {susp_c}\n"
                            f"• No red flags: {safe_c}"
                        )
                    else:
                        msg = (
                            f"📊 <b>{BOT_NAME_TA} நேரலை புள்ளிவிவரங்கள் ({BOT_NAME_EN} Live Stats)</b>\n\n"
                            f"• மொத்த சோதனைகள்: {total_c}\n"
                            f"• கண்டறியப்பட்ட மோசடிகள்: {scam_c}\n"
                            f"• சந்தேகத்திற்குரியவை: {susp_c}\n"
                            f"• எச்சரிக்கை அறிகுறி இல்லாதவை: {safe_c}"
                        )
                    await telegram_io.send_text(effective_chat_id, msg)
                    return

            # Greetings Handling
            greetings = {"/start", "hi", "hello", "vanakkam", "வணக்கம்", "start"}
            if text_str.lower() in greetings:
                if text_str.lower() in ("/start", "start"):
                    bilingual_prompt = (
                        "வணக்கம்! உங்கள் மொழியைத் தேர்ந்தெடுக்கவும்.\n"
                        "Welcome! Please select your language."
                    )
                    buttons = [
                        {"id": "SET_LANG_TA", "title": "தமிழ்"},
                        {"id": "SET_LANG_EN", "title": "English"},
                    ]
                    await telegram_io.send_text(effective_chat_id, bilingual_prompt, buttons=buttons)
                    return
                welcome_entry = get_reply("S_WELCOME")
                w_txt = welcome_entry[user_lang] if welcome_entry and user_lang in welcome_entry else welcome_entry.get("ta")
                await telegram_io.send_text(effective_chat_id, format_template(w_txt))
                logger.info(f"[{timestamp}] msg_type='command' cmd='greeting' user_id={masked_user}: SUCCESS")
                return

            if text_str.lower() == "help":
                demo_line_ta = "\n/demo — மாதிரி சோதனைகள் (Demo test cases)" if config.DEMO_MODE else ""
                demo_line_en = "\n/demo — Demo test cases" if config.DEMO_MODE else ""
                if user_lang == "en":
                    help_text = (
                        f"<b>{BOT_NAME_EN} — Commands:</b>\n\n"
                        f"/start — Start {BOT_NAME_EN} & select language\n"
                        f"/help — List commands\n"
                        f"/language — Select language\n"
                        f"/privacy — Privacy policy\n"
                        f"/stats — Live detection statistics\n"
                        f"/delete — Clear session & preferences"
                        f"{demo_line_en}"
                    )
                else:
                    help_text = (
                        f"<b>{BOT_NAME_TA} — கட்டளைகள் (Commands):</b>\n\n"
                        f"/start — {BOT_NAME_TA} தொடங்கு (Start bot)\n"
                        f"/help — கட்டளைகளின் பட்டியல் (List commands)\n"
                        f"/language — மொழி தேர்வு (Select language)\n"
                        f"/privacy — தனியுரிமை கொள்கை (Privacy policy)\n"
                        f"/stats — நேரலை புள்ளிவிவரங்கள் (Live stats)\n"
                        f"/delete — தற்காலிக நினைவகத்தை அழி (Clear session memory)"
                        f"{demo_line_ta}"
                    )
                await telegram_io.send_text(effective_chat_id, help_text)
                logger.info(f"[{timestamp}] msg_type='command' cmd='help' user_id={masked_user}: SUCCESS")
                return

            # Clear any pending voice transcript when user sends typed text
            _pending_voice_transcripts.pop(effective_chat_id, None)

            # Routing rule: short text (< 8 words, no link, no number/phone) goes to intent matcher.
            # Anything longer or containing a link/number goes to verdict engine.
            if should_route_to_intent(text_str):
                intent_id = classify_intent(text_str)
                if intent_id != "F_UNKNOWN":
                    reply_id, reply_text, _ = resolve_intent_response(
                        intent_id=intent_id,
                        chat_id=effective_chat_id,
                        session_store=session_manager,
                        lang=user_lang
                    )
                    buttons = build_inc_menu_buttons(lang=user_lang) if intent_id in INC_KEYWORDS else None
                    await telegram_io.send_text(effective_chat_id, reply_text, buttons=buttons)
                    logger.info(f"[{timestamp}] msg_type='intent' intent='{intent_id}' user_id={masked_user}: SUCCESS")
                    return

            # Unrecognized input: Analyze as a scam candidate message
            # Show S_WORKING status while processing
            working_entry = get_reply("S_WORKING")
            working_txt = working_entry[user_lang] if working_entry else "சரிபார்க்கிறேன்..."
            await telegram_io.send_text(effective_chat_id, working_txt)

            # Deterministic analysis (< 1ms)
            analysis = analyse(text_str)

            scam_type = None
            if analysis.signals:
                pos_signals = [s for s in analysis.signals if s.points > 0]
                if pos_signals:
                    top_sig = max(pos_signals, key=lambda s: s.points)
                    scam_type = top_sig.code.lower()

            # Update session memory (Zero message text stored!)
            session_manager.update(
                chat_id=effective_chat_id,
                verdict=analysis.verdict,
                scam_type=scam_type,
                signals=[s.code for s in analysis.signals]
            )

            # Log check in SQLite (Zero message text stored!)
            db.log_check(
                sender_hash=sender_hash,
                msg_type="text",
                score=analysis.score,
                verdict=analysis.verdict,
                fired_rules=[s.code for s in analysis.signals]
            )

            reply_text = build_verdict_reply(analysis, lang=user_lang)

            # Update session with last reply for F_REPEAT
            session_manager.update(
                chat_id=effective_chat_id,
                last_reply_id=f"V_{analysis.verdict}",
                last_reply_text=reply_text,
                language=user_lang
            )

            # 1. Send HTML verdict text (no buttons)
            await telegram_io.send_text(
                effective_chat_id,
                reply_text
            )

            # 2. Synthesize and send verdict voice (10-15s target, <=20s hard cap)
            try:
                voice_res = await tts.synthesize_verdict_voice(
                    verdict=analysis.verdict,
                    signals=[s.code for s in analysis.signals],
                    lang=user_lang
                )
                if voice_res:
                    v_path, v_dur = voice_res
                    if v_path and os.path.exists(v_path):
                        await telegram_io.send_voice(effective_chat_id, v_path)
            except Exception as voice_err:
                logger.warning(f"Voice reply skipped: {type(voice_err).__name__}")

            # 3. Send ONE short follow-up message with interactive buttons in the selected language
            followup_text, buttons = build_followup_message(analysis.verdict, lang=user_lang)
            await telegram_io.send_text(
                effective_chat_id,
                followup_text,
                buttons=buttons
            )

            logger.info(f"[{timestamp}] msg_type='text' user_id={masked_user} verdict={analysis.verdict}: SUCCESS")

        # 4. Voice Note Audio Handling
        elif msg_type == "audio":
            if not getattr(config, "VOICE_IN_ENABLED", False):
                nov_entry = get_reply("S_NOVOICE")
                reply_txt = nov_entry.get(user_lang) or nov_entry.get("ta")
                await telegram_io.send_text(effective_chat_id, reply_txt)
                return

            voice_path = None
            try:
                working_entry = get_reply("S_WORKING")
                working_txt = working_entry.get(user_lang) or working_entry.get("ta")
                await telegram_io.send_text(effective_chat_id, working_txt)

                voice_path = await telegram_io.download_voice(content)

                # Non-blocking: run off event loop with 25s timeout
                res = await asyncio.wait_for(
                    asyncio.to_thread(
                        speech.transcribe_with_metadata,
                        voice_path,
                        language_hint=user_lang,
                        delete_source=True
                    ),
                    timeout=25.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"[{timestamp}] msg_type='audio' user_id={masked_user}: TIMEOUT_25S")
                retry_entry = get_reply("S_VOICE_RETRY")
                reply_txt = retry_entry.get(user_lang) or retry_entry.get("en")
                if reply_txt == "MISSING - ask the team":
                    reply_txt = retry_entry.get("en")
                await telegram_io.send_text(effective_chat_id, reply_txt)
                return
            except ValueError:
                logger.warning(f"[{timestamp}] msg_type='audio' user_id={masked_user}: DURATION_LIMIT")
                duration_msg = "குரல் பதிவு 1 முதல் 60 வினாடிகளுக்குள் இருக்க வேண்டும்." if user_lang == "ta" else "Voice note must be between 1 and 60 seconds."
                await telegram_io.send_text(effective_chat_id, duration_msg)
                return
            except Exception as stt_err:
                logger.error(f"STT Error: {type(stt_err).__name__}")
                retry_entry = get_reply("S_VOICE_RETRY")
                reply_txt = retry_entry.get(user_lang) or retry_entry.get("en")
                if reply_txt == "MISSING - ask the team":
                    reply_txt = retry_entry.get("en")
                await telegram_io.send_text(effective_chat_id, reply_txt)
                return
            finally:
                if voice_path and os.path.exists(voice_path):
                    try:
                        os.remove(voice_path)
                    except Exception:
                        pass

            # Confidence Gate:
            if not res.get("confidence_passed"):
                retry_entry = get_reply("S_VOICE_RETRY")
                reply_txt = retry_entry.get(user_lang) or retry_entry.get("en")
                if reply_txt == "MISSING - ask the team":
                    reply_txt = retry_entry.get("en")
                await telegram_io.send_text(effective_chat_id, reply_txt)
                return

            transcription = res["text"]

            # Store in-memory pending transcript for confirmation (zero DB logging)
            _pending_voice_transcripts[effective_chat_id] = (transcription, time.time())

            # Echo transcript for user confirmation with buttons
            escaped_transcription = html.escape(transcription)
            heard_entry = get_reply("S_HEARD")
            heard_template = heard_entry.get(user_lang) or heard_entry.get("ta")
            heard_text = format_template(heard_template, transcript=escaped_transcription)

            confirm_title = "சரி" if user_lang == "ta" else "Correct"
            retry_title = "மீண்டும் சொல்கிறேன்" if user_lang == "ta" else "Say again"
            confirm_buttons = [
                {"id": "V_CONFIRM", "title": confirm_title},
                {"id": "V_RETRY", "title": retry_title}
            ]
            await telegram_io.send_text(effective_chat_id, heard_text, buttons=confirm_buttons)
            logger.info(f"[{timestamp}] msg_type='audio' user_id={masked_user} confidence_passed=True: PENDING_CONFIRMATION")
            return

            # 3. Send ONE short follow-up message with interactive buttons
            followup_text, buttons = build_followup_message(analysis.verdict, lang=user_lang)
            await telegram_io.send_text(
                effective_chat_id,
                followup_text,
                buttons=buttons
            )

            logger.info(f"[{timestamp}] msg_type='audio' user_id={masked_user} verdict={analysis.verdict}: SUCCESS")

    except Exception as e:
        # Never log stack trace or user message text; log only exception type
        logger.error(f"Error: {type(e).__name__}")
        error_entry = get_reply("S_ERROR")
        error_msg = error_entry["ta"] if error_entry else "மன்னிக்கவும், இப்போது சரிபார்க்க முடியவில்லை. சிறிது நேரம் கழித்து முயற்சிக்கவும்."
        await telegram_io.send_text(effective_chat_id, error_msg)


# =====================================================================
# TELEGRAM EVENT HANDLERS
# =====================================================================
async def on_start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user = update.effective_user
        chat = update.effective_chat
        if not user or not chat:
            return
        await handle_message(user_id=user.id, msg_type="text", content="/start", chat_id=chat.id)
    except Exception as e:
        logger.error(f"Error: {type(e).__name__}")


async def on_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user = update.effective_user
        chat = update.effective_chat
        if not user or not chat:
            return
        await handle_message(user_id=user.id, msg_type="text", content="/help", chat_id=chat.id)
    except Exception as e:
        logger.error(f"Error: {type(e).__name__}")


async def on_privacy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user = update.effective_user
        chat = update.effective_chat
        if not user or not chat:
            return
        await handle_message(user_id=user.id, msg_type="text", content="/privacy", chat_id=chat.id)
    except Exception as e:
        logger.error(f"Error: {type(e).__name__}")


async def on_delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user = update.effective_user
        chat = update.effective_chat
        if not user or not chat:
            return
        await handle_message(user_id=user.id, msg_type="text", content="/delete", chat_id=chat.id)
    except Exception as e:
        logger.error(f"Error: {type(e).__name__}")


async def on_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user = update.effective_user
        chat = update.effective_chat
        if not user or not chat:
            return
        await handle_message(user_id=user.id, msg_type="text", content="/stats", chat_id=chat.id)
    except Exception as e:
        logger.error(f"Error: {type(e).__name__}")


async def on_language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user = update.effective_user
        chat = update.effective_chat
        if not user or not chat or not update.message:
            return
        text = update.message.text or "/language"
        await handle_message(user_id=user.id, msg_type="text", content=text, chat_id=chat.id)
    except Exception as e:
        logger.error(f"Error: {type(e).__name__}")


async def on_demo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user = update.effective_user
        chat = update.effective_chat
        if not user or not chat or not update.message:
            return
        await handle_message(user_id=user.id, msg_type="text", content="/demo", chat_id=chat.id)
    except Exception as e:
        logger.error(f"Error: {type(e).__name__}")


async def on_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user = update.effective_user
        chat = update.effective_chat
        if not user or not chat or not update.message:
            return
        text = update.message.text or ""
        await handle_message(user_id=user.id, msg_type="text", content=text, chat_id=chat.id)
    except Exception as e:
        logger.error(f"Error: {type(e).__name__}")


async def on_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        user = update.effective_user
        chat = update.effective_chat
        if not user or not chat or not update.message or not update.message.voice:
            return
        await handle_message(user_id=user.id, msg_type="audio", content=update.message, chat_id=chat.id)
    except Exception as e:
        logger.error(f"Error: {type(e).__name__}")


async def on_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"Callback answer warning: {type(e).__name__}")

    try:
        user = update.effective_user
        chat = update.effective_chat
        if not user or not chat:
            return
        callback_id = query.data or ""
        await handle_message(user_id=user.id, msg_type="button", content=callback_id, chat_id=chat.id)
    except Exception as e:
        logger.error(f"Error: {type(e).__name__}")


async def on_unsupported_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        chat = update.effective_chat
        if chat:
            await telegram_io.send_text(
                chat.id,
                "மன்னிக்கவும், உரை செய்திகள் மற்றும் குரல் குறிப்புகள் மட்டுமே ஏற்கப்படும்.\n"
                "(Sorry, only text messages and voice notes are supported.)"
            )
    except Exception as e:
        logger.error(f"Error: {type(e).__name__}")


async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    err_type = type(context.error).__name__ if context.error else "UnknownError"
    logger.error(f"Global Application Error: {err_type}")
    if isinstance(update, Update) and update.effective_chat:
        try:
            error_entry = get_reply("S_ERROR")
            error_msg = error_entry["ta"] if error_entry else "மன்னிக்கவும், இப்போது சரிபார்க்க முடியவில்லை. சிறிது நேரம் கழித்து முயற்சிக்கவும்."
            await telegram_io.send_text(update.effective_chat.id, error_msg)
        except Exception:
            pass


# =====================================================================
# APPLICATION LAUNCHER (LONG POLLING)
# =====================================================================
def main():
    logger.info(f"Initializing {BOT_NAME_EN} Telegram Bot...")
    app = Application.builder().token(BOT_TOKEN).build()

    telegram_io.set_bot(app.bot)
    db.init_db()
    logger.info("Database initialized successfully.")

    app.add_handler(CommandHandler("start", on_start_command))
    app.add_handler(CommandHandler("help", on_help_command))
    app.add_handler(CommandHandler("privacy", on_privacy_command))
    app.add_handler(CommandHandler("delete", on_delete_command))
    app.add_handler(CommandHandler("language", on_language_command))
    app.add_handler(CommandHandler("lang", on_language_command))
    app.add_handler(CommandHandler("stats", on_stats_command))
    app.add_handler(CommandHandler("demo", on_demo_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_message))
    app.add_handler(MessageHandler(filters.VOICE, on_voice_message))
    app.add_handler(CallbackQueryHandler(on_button_callback))

    unsupported_filters = (
        ~filters.COMMAND &
        ~filters.TEXT &
        ~filters.VOICE
    )
    app.add_handler(MessageHandler(unsupported_filters, on_unsupported_media))
    app.add_error_handler(global_error_handler)

    logger.info(f"{BOT_NAME_EN} Telegram Bot is now polling for updates (No public URL/ngrok required)...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
