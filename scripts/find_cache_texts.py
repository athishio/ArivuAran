import os
import sys
import glob

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

import tts

target_stems = {
    'ee692291d28716084468ae7597b96fc58564d7ef79b353b8eaeb009d953f777e',
    '7428ea85bc22947a7f2171e7cbcef881a6fbf3edc60062cb8329a770c19a18a2',
    '2cd156243d59b019d2c7140123ee3bad73c45c0124d2b697c053976a0345ffc2'
}

# Also check test_tts_fallbacks.py directly
test_scripts = [
    "இது ஒரு சோதனை குரல் செய்தி.",
    "This is a test voice message.",
    "இது ஒரு மாதிரி சோதனை.",
    "வங்கி கணக்கு முடக்கப்பட்டுள்ளது.",
    "மோசடி எச்சரிக்கை! இது போலி செய்தி.",
    "Suspicious patterns detected."
]

# Read all string literals from tests/test_tts_and_formatting.py and test_tts_fallbacks.py
for fpath in glob.glob(os.path.join(WORKSPACE_ROOT, "tests", "*.py")):
    with open(fpath, "r", encoding="utf-8") as f:
        content = f.read()
        import ast
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    test_scripts.append(node.value)
        except Exception:
            pass

found = {}
for text in test_scripts:
    for lang in ('ta', 'en'):
        for voice in (tts.VOICE_CONFIG['ta']['default'], tts.VOICE_CONFIG['ta']['optional'], tts.VOICE_CONFIG['en']['default']):
            for rate in (tts.DEFAULT_TTS_RATE, '+0%', '-10%'):
                clean = tts.apply_tts_replacements(text, lang)
                k = tts.get_cache_key(lang, voice, rate, clean)
                if k in target_stems and k not in found:
                    found[k] = (text, lang, voice, rate)

# Also check if any verdict builder combinations produce it
from engine.links import RISKY_TLDS
from scripts.pregen_audio import SCAM_TYPES

signals_pool = [
    ["LOOKALIKE", "BRAND_MISMATCH"],
    ["KYC_UPDATE", "THREAT"],
    ["NO_HTTPS", "LOOKALIKE"],
    ["NO_HTTPS", "FEE_FIRST"],
    ["NO_HTTPS", "LOOKALIKE", "BRAND_MISMATCH", "KYC_UPDATE", "THREAT", "URGENCY"]
]
for sigs in signals_pool:
    for verdict in ["SCAM", "SUSPICIOUS"]:
        for lang in ["ta", "en"]:
            script = tts.build_verdict_spoken_script(verdict, sigs, lang)
            clean = tts.apply_tts_replacements(script, lang)
            voice = tts.VOICE_CONFIG[lang]['default']
            k = tts.get_cache_key(lang, voice, tts.DEFAULT_TTS_RATE, clean)
            if k in target_stems and k not in found:
                found[k] = (script, lang, voice, tts.DEFAULT_TTS_RATE)

print("Found matches:", len(found))
for k, v in found.items():
    print(f"\nHash: {k}")
    print(f"Text: {v[0]}")
    print(f"Lang: {v[1]}, Voice: {v[2]}, Rate: {v[3]}")
