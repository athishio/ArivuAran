"""
Voice-only transcript normaliser for Arivaran.
Normalises spoken/phonetic Tamil transliterations of common financial, technical,
and institutional terms into standard keywords expected by the engine.

Applied strictly to transcribed voice notes BEFORE rule evaluation.
Does NOT modify or affect typed text messages.
"""

import re

# Deterministic substitution mappings for spoken Tamil transcripts.
# Keeps ONLY unambiguous transliterations of technical / financial / institutional terms.
# All ordinary native Tamil words (e.g. "பின்" = after/behind) are strictly excluded.
VOICE_NORMALISATION_RULES = [
    # 1. OTP variations: ஓடிபி, ஓ டி பி, ஓட்டிபி, ஓட்டிப் பே, ஓட்டிப் பீ, ஓடிபீ
    (r"ஓட்டிப்\s*(?:பே|பீ)(?:\s*ணிங்க)?|ஓட்டிப்பி|ஓடிபி|ஓ\s*டி\s*பி|ஓடிபீ", "OTP"),

    # 2. KYC variations: கேஒய்சி, கே ஒய்சி, கே ஒய் சி
    (r"கேஒய்சி|கே\s*ஒய்சி|கே\s*ஒய்\s*சி", "KYC"),

    # 3. UPI variations: யூபிஐ, யுபிஐ, யூ பி ஐ, யு பி ஐ
    (r"யூபிஐ|யுபிஐ|யூ\s*பி\s*ஐ|யு\s*பி\s*ஐ", "UPI"),

    # 4. ATM variations: ஏடிஎம், ஏ டி எம், ஏ.டி.எம்
    (r"ஏடிஎம்|ஏ\s*டி\s*எம்|ஏ\.டி\.எம்", "ATM"),

    # 5. AnyDesk variations: அனிடெஸ்க், எனிடெஸ்க், அனி டெஸ்க்
    (r"அனிடெஸ்க்|எனிடெஸ்க்|அனி\s*டெஸ்க்|எனி\s*டெஸ்க்", "AnyDesk"),

    # 6. SBI variations: எஸ்பிஐ, எஸ் பி ஐ, எஸ்.பி.ஐ
    (r"எஸ்பிஐ|எஸ்\s*பி\s*ஐ|எஸ்\.பி\.ஐ", "SBI"),

    # 7. Police / Law enforcement transliterations: போலிஸ், போலீஸ்
    (r"போலிஸ்|போலீஸ்", "police"),
]


def normalise_voice_transcript(text: str) -> str:
    """
    Normalises voice-transcribed text to match engine security keywords.
    Only applied to voice audio transcripts, never to typed text.
    """
    if not text:
        return text

    normalised = text
    for pattern, replacement in VOICE_NORMALISATION_RULES:
        normalised = re.sub(pattern, replacement, normalised, flags=re.IGNORECASE)

    return normalised.strip()
