import pytest
from engine.voice_norm import normalise_voice_transcript
from engine.decide import analyse


def test_voice_normaliser_transliterations():
    assert "OTP" in normalise_voice_transcript("உங்கள் ஓடிபி எண்ணை சொல்லுங்கள்")
    assert "OTP" in normalise_voice_transcript("வந்திருக்கும் ஓ டி பி சொல்லுங்கள்")
    assert "OTP" in normalise_voice_transcript("ஓட்டிப் பே சொல்லுங்கள்")
    assert "KYC" in normalise_voice_transcript("உங்கள் கணக்கிற்கு கேஒய்சி தேவை")
    assert "UPI" in normalise_voice_transcript("யூபிஐ மூலம் பணம் அனுப்பவும்")
    assert "ATM" in normalise_voice_transcript("ஏடிஎம் கார்டு விவரங்கள்")
    assert "AnyDesk" in normalise_voice_transcript("அனிடெஸ்க் ஆப் டவுன்லோட் செய்யுங்கள்")
    assert "SBI" in normalise_voice_transcript("எஸ்பிஐ வங்கி கணக்கு")
    assert "police" in normalise_voice_transcript("நாங்கள் போலிஸ் ஸ்டேஷனில் இருந்து பேசுகிறோம்")


def test_ordinary_sentence_unchanged():
    sentence = "அதன் பின் நான் வந்தேன்"
    assert normalise_voice_transcript(sentence) == sentence


def test_typed_text_verdicts_unaffected():
    # Regular typed text directly passed to analyse without normalisation
    text_genuine = "123456 is your secret OTP for login. Never share OTP with anyone."
    assert analyse(text_genuine).verdict == "NO_RED_FLAGS"

    text_scam = "Dear customer, your SBI account is blocked. Update KYC immediately: http://bit.ly/sbi-kyc"
    assert analyse(text_scam).verdict == "SCAM"
