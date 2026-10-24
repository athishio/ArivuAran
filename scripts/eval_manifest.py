import csv
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from engine.decide import analyse
from engine.voice_norm import normalise_voice_transcript

def levenshtein(s1, s2):
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (1 if c1 != c2 else 0)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def cer(ref, hyp):
    d = levenshtein(ref, hyp)
    return d / max(1, len(ref))

def wer(ref, hyp):
    ref_words = ref.split()
    hyp_words = hyp.split()
    d = levenshtein(ref_words, hyp_words)
    return d / max(1, len(ref_words))

# Transcripts from previous benchmark
transcripts_a = {
    "Audio-1.ogg": "எனக்கு விரங்கிலிலிருந்த ஒரு மேசிஜ் வந்திருக்கிறது. அந்த மேசிஜ் வந்திருந்து அந்த நிங்கத் தோட்டில்லினா என் அக்கோட் பிள்ளைக் காயிரோ அப்படிச் செல்லிருந்து போட்டிருக்கிறது. இது ச்காம் மேசிஜ் அல்லையா?",
    "Audio-2.ogg": "எனக்கு ஒரு கால வந்தது, அந்த காலில் ஒரு பரசன் போலிஸ் இந்த மெரி உங்களுக்கு ஒரு ஓட்டிப் பே வந்திருக்கும் அந்த ஓட்டிப் பீண்டுங்கள் சொல்லுங்கள் நீங்கள் அன்னால் உங்கள் மேல் ஒரு ராங் கேசு, நீங்கள் போலியில் கட்டும் மாதிரியாக இருக்கும் என்று சொல்லுங்கள் இப்போது நான் என்ன செய்துவிட்டேன்",
    "Audio-3.ogg": "ஏன் கூறுகிறும் பெயர் கூறுகிறோம் என்று தெரியும் மேசைக்கு வந்து செய்துவிட்டேன் ஒரு திரு தொட்டாய் என்று பார்த்தாயர் வாட்டே வீட்டிற்கு வந்து பணையான் பெட்டு வந்துவிடும்",
    "Audio-4.ogg": "இந்த மாறி ஒரு லிங்கத்தான் அனுப்பிவுட்டு இந்த மாறி இந்த மாறி சேர சொல்கிறார்கள். இது வந்து ச்கமா இல்லையா?"
}

transcripts_b = {
    "Audio-1.ogg": "எனக்கு பிராங்க் மெசேஜ் வந்திருக்கு அந்த மெசேஜ் வந்து அந்த லிங்கத் பிளாக் ஆயிடும் அப்படி சொல்லிருக்கு மெசேஜ் இல்லையா",
    "Audio-2.ogg": "எனக்கு ஒரு கால் வந்துச்சு அந்த கால்ல வந்து ஒரு பர்சன் வந்து நான் போலீஸ் இந்த மாதிரி உங்களுக்கு ஓடிப் வந்திருக்கும் அந்த ஓட்டப் நீங்க சொல்லுங்க இல்லனா உங்க மேல ஒரு ராங்க் பையன் ஆயிடும் பைன்ட் மாதிரியா இருக்கும் அப்டின்னு சொல்ட்டு சொல்றாங்க இப்ப நான் என்ன பண்றது",
    "Audio-3.ogg": "ஏதோ மெசேஜ் வந்துச்சு தொட்டத்தில் பத்தாயிரம் ரூபா டெபிட் வந்து என்ன பட்டது",
    "Audio-4.ogg": "இந்த மாதிரி ஒரு லிங்க் தான் அனுப்பிவிட்டு இன்னிக்கு இந்த மாதிரி சேர சொல்றாங்க இது வந்து ஸ்கேம் இல்லையா"
}

manifest_path = os.path.join(WORKSPACE_ROOT, "data", "audio", "manifest.csv")

print("======================================================================")
print("EVALUATION AGAINST data/audio/manifest.csv")
print("======================================================================")

with open(manifest_path, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    rows = list(reader)

print(f"Total Rows in manifest.csv: {len(rows)}")
for r in rows:
    f_name = r["file"]
    ref = r["what_was_said_or_shown"]
    notes = r["notes"]
    verified = r["verified"]
    
    hyp_a = transcripts_a.get(f_name, "")
    hyp_b = transcripts_b.get(f_name, "")
    
    cer_a = cer(ref, hyp_a)
    wer_a = wer(ref, hyp_a)
    
    cer_b = cer(ref, hyp_b)
    wer_b = wer(ref, hyp_b)
    
    # Engine analysis on reference
    norm_ref = normalise_voice_transcript(ref)
    analysis_ref = analyse(norm_ref)
    sigs_ref = [f"{s.code}(+{s.points})" for s in analysis_ref.signals]
    
    # Engine analysis on model A and B
    analysis_a = analyse(normalise_voice_transcript(hyp_a))
    sigs_a = [f"{s.code}(+{s.points})" for s in analysis_a.signals]
    
    analysis_b = analyse(normalise_voice_transcript(hyp_b))
    sigs_b = [f"{s.code}(+{s.points})" for s in analysis_b.signals]
    
    print(f"\n--- {f_name} ---")
    print(f"  Notes:    {notes} (verified: {verified})")
    print(f"  REF:      {ref}")
    print(f"  REF Verdict: {analysis_ref.verdict} (Score: {analysis_ref.score}, Signals: {sigs_ref})")
    print(f"  Model A:  WER={wer_a*100:.1f}%, CER={cer_a*100:.1f}% | Verdict: {analysis_a.verdict} ({sigs_a})")
    print(f"  Model B:  WER={wer_b*100:.1f}%, CER={cer_b*100:.1f}% | Verdict: {analysis_b.verdict} ({sigs_b})")
