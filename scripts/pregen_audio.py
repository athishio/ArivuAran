"""
Audio Pre-generation Script for ArivuAran.
Generates spoken audio for EVERY entry in data/replies.json in BOTH languages.
Includes:
- Standard fixed replies (reasons, follow-ups, INC_*, teach lessons T_*, system, share).
- Slot replies generated per scam type (V_SCAM, V_SUSPICIOUS, SHARE_CARD).
- Dynamic placeholder resolution for branding (BOT_NAME_TA, BOT_NAME_EN).
Enforces:
- Hard duration limit: fail any clip under 2s or over 20s (teach lessons allowed up to 25s).
- Fallback chain: cache -> edge-tts (8s timeout) -> gTTS -> text only with note.
- OGG/Opus conversion for Telegram voice notes.
"""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, List, Tuple, Any

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import config
import tts

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pregen_audio")

# Canonical scam types with representative signals
SCAM_TYPES = {
    "electricity_bill": ["SHORTENER", "URGENT_DEMAND"],
    "kyc_block": ["KYC_UPDATE", "SHORTENER"],
    "digital_arrest": ["POLICE_IMPERSONATION", "URGENT_DEMAND"],
    "job_task": ["JOB_TASK", "SHORTENER"],
    "upi_collect": ["UPI_REQUEST"],
    "lottery_prize": ["PRIZE_WIN"],
    "loan_approved": ["PRIZE_WIN", "FEE_ADVANCE"],
    "apk_remote": ["APK_DOWNLOAD", "REMOTE_ACCESS"],
}

SCAM_TYPE_TA_NAMES = {
    "electricity_bill": "மின் கட்டண மோசடி",
    "kyc_block": "வங்கி KYC மோசடி",
    "digital_arrest": "டிஜிட்டல் அரெஸ்ட் மிரட்டல்",
    "job_task": "பகுதி நேர வேலை மோசடி",
    "upi_collect": "UPI பணம் பறிப்பு",
    "lottery_prize": "பரிசு விழுந்ததாக ஏமாற்றுதல்",
    "loan_approved": "கடன் தருவதாக மோசடி",
    "apk_remote": "ஆப் நிறுவ வைக்கும் மோசடி",
}


def fill_placeholders(text: str, lang: str = "ta") -> str:
    """Fills branding and standard template variables."""
    out = text
    out = out.replace("{BOT_NAME_TA}", config.BOT_NAME_TA)
    out = out.replace("{BOT_NAME_EN}", config.BOT_NAME_EN)
    out = out.replace("{BOT_NAME_TA_GEN}", config.BOT_NAME_TA_GEN)
    # Generic teach/repeat topics if slot exists
    if lang == "ta":
        out = out.replace("{topics_list}", "KYC, OTP, பகுதி நேர வேலை, டிஜிட்டல் அரெஸ்ட்")
        out = out.replace("{last_reply}", "முந்தைய பதிலை மீண்டும் கேட்கிறீர்கள்.")
        out = out.replace("{reasons}", "காரணங்கள் மீண்டும் கேட்கப்படுகின்றன.")
    else:
        out = out.replace("{topics_list}", "KYC, OTP, Part-time job, Digital arrest")
        out = out.replace("{last_reply}", "Repeating the previous response.")
        out = out.replace("{reasons}", "Repeating the detection reasons.")
    return out


async def pregen_all() -> Dict[str, Any]:
    replies_path = os.path.join(WORKSPACE_ROOT, "data", "replies.json")
    with open(replies_path, "r", encoding="utf-8") as f:
        replies = json.load(f)

    generated = []
    skipped = []
    failed = []

    print("\n" + "=" * 70)
    print("ARIVUARAN AUDIO PRE-GENERATION PIPELINE")
    print("=" * 70)

    # 1. Pre-generate verdict spoken clips per scam type
    for scam_key, signals in SCAM_TYPES.items():
        for verdict in ["SCAM", "SUSPICIOUS"]:
            for lang in ["ta", "en"]:
                clip_id = f"V_{verdict}_{scam_key}_{lang}"
                res = await tts.synthesize_verdict_voice(
                    verdict=verdict,
                    signals=signals,
                    lang=lang
                )
                if res:
                    path, dur = res
                    # Duration check (verdict voice target 10-20s, cap 20s)
                    if 2.0 <= dur <= 20.0:
                        generated.append({"id": clip_id, "path": path, "duration": dur, "lang": lang})
                        print(f"  [OK] {clip_id:<32} {dur:>5.2f}s  -> {os.path.basename(path)}")
                    else:
                        failed.append({"id": clip_id, "reason": f"Duration out of range: {dur:.2f}s", "duration": dur})
                        print(f"  [FAIL] {clip_id:<32} {dur:>5.2f}s  (Out of bounds: 2s-20s)")
                else:
                    failed.append({"id": clip_id, "reason": "Synthesis returned None"})
                    print(f"  [FAIL] {clip_id:<32} Synthesis failed")

    # 2. NO_RED_FLAGS verdict
    for lang in ["ta", "en"]:
        clip_id = f"V_NOFLAG_{lang}"
        res = await tts.synthesize_verdict_voice(
            verdict="NO_RED_FLAGS",
            signals=[],
            lang=lang
        )
        if res:
            path, dur = res
            if 2.0 <= dur <= 20.0:
                generated.append({"id": clip_id, "path": path, "duration": dur, "lang": lang})
                print(f"  [OK] {clip_id:<32} {dur:>5.2f}s  -> {os.path.basename(path)}")
            else:
                failed.append({"id": clip_id, "reason": f"Duration out of range: {dur:.2f}s", "duration": dur})
                print(f"  [FAIL] {clip_id:<32} {dur:>5.2f}s  (Out of bounds)")
        else:
            failed.append({"id": clip_id, "reason": "Synthesis returned None"})
            print(f"  [FAIL] {clip_id:<32} Synthesis failed")

    # 3. All individual replies from data/replies.json
    for r in replies:
        rid = r["id"]
        # Skip V_SCAM and V_SUSPICIOUS and V_NOFLAG since handled per scam type above
        if rid in ("V_SCAM", "V_SUSPICIOUS", "V_NOFLAG"):
            continue

        # Skip runtime-only prompt entries
        if rid in ("S_HEARD", "S_OCR"):
            skipped.append({"id": rid, "reason": "Runtime dynamic text (heard audio/OCR result)"})
            continue

        for lang in ["ta", "en"]:
            clip_id = f"{rid}_{lang}"
            raw_script = r.get(f"tts_{lang}", "")
            if not raw_script:
                skipped.append({"id": clip_id, "reason": f"Empty tts_{lang}"})
                continue

            script = fill_placeholders(raw_script, lang=lang)

            # Teach mode lessons allow up to 25s
            max_limit = 25.0 if rid.startswith("T_") else 20.0

            res = await tts.synthesize_speech(
                text=script,
                lang=lang,
                reply_id=clip_id
            )
            if res:
                path, dur = res
                if 2.0 <= dur <= max_limit:
                    generated.append({"id": clip_id, "path": path, "duration": dur, "lang": lang})
                    print(f"  [OK] {clip_id:<32} {dur:>5.2f}s  -> {os.path.basename(path)}")
                else:
                    failed.append({"id": clip_id, "reason": f"Duration out of range: {dur:.2f}s (max {max_limit}s)", "duration": dur})
                    print(f"  [FAIL] {clip_id:<32} {dur:>5.2f}s  (Duration exceeded max {max_limit}s)")
            else:
                failed.append({"id": clip_id, "reason": "Synthesis returned None"})
                print(f"  [FAIL] {clip_id:<32} Synthesis failed")

    print("\n" + "=" * 70)
    print("PRE-GENERATION SUMMARY")
    print("=" * 70)
    print(f"✅ Generated / Cached clips : {len(generated)}")
    print(f"⏭️ Skipped (dynamic) clips : {len(skipped)}")
    print(f"❌ Failed clips             : {len(failed)}")

    return {
        "generated": generated,
        "skipped": skipped,
        "failed": failed,
    }


if __name__ == "__main__":
    result = asyncio.run(pregen_all())
    if result["failed"]:
        sys.exit(1)
    sys.exit(0)
