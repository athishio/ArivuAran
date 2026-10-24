"""
Preflight Verification Script for ArivuAran.
Checks all environment prerequisites, system binaries, models, database, and audio cache.
Outputs clear green [PASS] / red [FAIL] status.
"""

import os
import sys
import json
import sqlite3
import urllib.request
from typing import Dict, List, Tuple

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import config
import db


def check_internet() -> Tuple[bool, str]:
    """Checks internet connectivity."""
    urls = ["https://1.1.1.1", "https://www.google.com"]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                if resp.status in (200, 301, 302):
                    return True, f"Connected ({url})"
        except Exception:
            continue
    return False, "No internet access or high latency timeout"


def check_telegram_token() -> Tuple[bool, str]:
    """Checks if Telegram bot token is configured and validates via getMe (never logs URL or token)."""
    token = os.getenv("BOT_TOKEN", "")
    if not token or "mock" in token or token.startswith("your_"):
        return False, "BOT_TOKEN missing or set to placeholder"
    # Basic Telegram token format check: <digits>:<alphanumeric>
    parts = token.split(":")
    if not (len(parts) == 2 and parts[0].isdigit() and len(parts[1]) >= 20):
        return False, "Invalid token format"

    # Make getMe call to Telegram Bot API - NEVER log or print the URL or token!
    endpoint = f"https://api.telegram.org/bot{token}/getMe"
    try:
        req = urllib.request.Request(endpoint, headers={"User-Agent": "ArivuAranPreflight/1.0"})
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok"):
                username = data.get("result", {}).get("username", "unknown")
                return True, f"Token valid and verified via getMe (@{username})"
            return False, f"Telegram API returned ok=false: {data.get('description', '')}"
    except urllib.error.HTTPError as e:
        return False, f"Telegram API error HTTP {e.code}"
    except Exception as e:
        return False, f"Network error during getMe call: {type(e).__name__}"


def check_whisper_cache() -> Tuple[bool, str]:
    """Checks if faster-whisper models are cached locally."""
    hf_home = os.getenv("HF_HOME", os.path.expanduser("~/.cache/huggingface/hub"))
    if not os.path.isdir(hf_home):
        return False, f"HuggingFace hub directory not found at {hf_home}"

    whisper_dirs = [d for d in os.listdir(hf_home) if "whisper" in d.lower()]
    if whisper_dirs:
        return True, f"Cached model(s) found: {', '.join(whisper_dirs)}"
    return False, "No faster-whisper model found in cache"


def check_tesseract() -> Tuple[bool, str]:
    """Checks if Tesseract executable is installed with tam and eng language packs."""
    cmd = config.TESSERACT_CMD
    if not os.path.exists(cmd):
        return False, f"Binary not found at {cmd}"

    import subprocess
    try:
        res = subprocess.run([cmd, "--list-langs"], capture_output=True, text=True, check=True)
        langs = set(res.stdout.splitlines())
        has_tam = "tam" in langs
        has_eng = "eng" in langs
        if has_tam and has_eng:
            return True, f"Installed at {cmd} (includes tam + eng)"
        missing = []
        if not has_tam:
            missing.append("tam")
        if not has_eng:
            missing.append("eng")
        return False, f"Missing language pack(s): {', '.join(missing)}"
    except Exception as e:
        return False, f"Execution failed: {type(e).__name__}"


def check_audio_tools() -> Tuple[bool, str]:
    """Checks for ffmpeg binary or PyAV with libopus/ogg support."""
    ffmpeg_bin = config.FFMPEG_PATH
    has_ffmpeg = False
    import subprocess
    try:
        res = subprocess.run([ffmpeg_bin, "-version"], capture_output=True, text=True)
        if res.returncode == 0:
            has_ffmpeg = True
    except Exception:
        pass

    try:
        import av
        has_av = "libopus" in av.codecs_available and "ogg" in av.formats_available
    except ImportError:
        has_av = False

    if has_ffmpeg:
        return True, f"ffmpeg available ({ffmpeg_bin})"
    if has_av:
        return True, "PyAV available with libopus + ogg (built-in fallback)"
    return False, "Neither ffmpeg nor PyAV libopus available for Opus/OGG conversion"


def check_audio_cache_completeness() -> Tuple[bool, str]:
    """Checks audio cache directory and report status."""
    cache_dir = os.path.join(WORKSPACE_ROOT, "cache", "audio")
    if not os.path.isdir(cache_dir):
        return False, "cache/audio directory does not exist"

    files = [f for f in os.listdir(cache_dir) if f.endswith((".mp3", ".ogg"))]
    if len(files) >= 50:
        return True, f"{len(files)} cached clips present in cache/audio"
    elif len(files) > 0:
        return True, f"Partial cache: {len(files)} clips present (run scripts/pregen_audio.py for full cache)"
    return False, "Cache empty (0 clips found)"


def check_database() -> Tuple[bool, str]:
    """Verifies that SQLite database is writable and tables exist."""
    db_path = os.path.join(WORKSPACE_ROOT, "arivaran.db")
    try:
        db.init_db(db_path)
        with db.get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM checks")
            c1 = cursor.fetchone()[0]
            cursor.execute("SELECT count(*) FROM user_prefs")
            c2 = cursor.fetchone()[0]
        return True, f"Database writable ({db_path}, checks: {c1}, prefs: {c2})"
    except Exception as e:
        return False, f"Database error: {type(e).__name__} ({e})"


def check_ml_classifier() -> Tuple[bool, str]:
    """Checks if optional scikit-learn classifier model is present."""
    model_path = os.path.join(WORKSPACE_ROOT, "models", "clf_v1.joblib")
    if os.path.exists(model_path):
        return True, f"Model present ({model_path})"
    return False, "Optional classifier not built yet (USE_CLASSIFIER=false)"


def run_preflight() -> bool:
    print("\n" + "=" * 70)
    print("ARIVUARAN (அறிவுஅரண்) SYSTEM PREFLIGHT CHECKLIST")
    print("=" * 70)

    checks = [
        ("Internet Connectivity", check_internet, True),
        ("Telegram Bot Token", check_telegram_token, False),
        ("Faster-Whisper Model Cache", check_whisper_cache, True),
        ("Tesseract OCR (tam + eng)", check_tesseract, True),
        ("Audio Encoding (ffmpeg / PyAV)", check_audio_tools, True),
        ("Audio Cache Completeness", check_audio_cache_completeness, False),
        ("SQLite Database Writable", check_database, True),
        ("ML Text Classifier", check_ml_classifier, False),
    ]

    all_critical_passed = True

    for name, func, critical in checks:
        passed, details = func()
        badge = "✅ [PASS]" if passed else ("❌ [FAIL]" if critical else "⚠️ [OPTIONAL]")
        if critical and not passed:
            all_critical_passed = False
        print(f"  {badge:<16} {name:<30} : {details}")

    print("=" * 70)
    if all_critical_passed:
        print("🎉 ALL CRITICAL PREREQUISITES VERIFIED! Bot is ready for launch.")
    else:
        print("⚠️ Some critical prerequisites failed. Please inspect the items above.")
    print("=" * 70 + "\n")
    return all_critical_passed


if __name__ == "__main__":
    success = run_preflight()
    sys.exit(0 if success else 1)
