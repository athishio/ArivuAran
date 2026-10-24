import os
import sys
import hashlib
import pytesseract
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')
WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
os.makedirs('eval', exist_ok=True)

images = sorted([f for f in os.listdir('data/images') if f.lower().endswith(('.jpeg', '.jpg', '.png'))])

from engine.decide import analyse

print("======================================================================")
print("OCR VERIFICATION: SHA-256, RAW OCR (REPR), AND PIPELINE EVALUATION")
print("======================================================================")

results = []

for img_name in images:
    img_path = os.path.join('data/images', img_name)
    with open(img_path, 'rb') as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()
    
    img = Image.open(img_path)
    raw_ocr = pytesseract.image_to_string(img, lang='tam+eng')
    
    out_file = os.path.join('eval', f'ocr_raw_{img_name}.txt')
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(raw_ocr)
        
    # Read EXACTLY the text saved in that file
    with open(out_file, 'r', encoding='utf-8') as f:
        saved_text = f.read()
        
    analysis = analyse(saved_text)
    signal_codes = [s.code for s in analysis.signals]
    scam_type = None
    if analysis.signals:
        top_sig = max(analysis.signals, key=lambda s: s.points)
        scam_type = top_sig.code.lower()
    
    print(f"\n--- {img_name} ---")
    print(f"SHA-256: {sha256}")
    print(f"Saved to: {out_file} ({len(saved_text)} chars)")
    print(f"Full OCR repr:\n{repr(saved_text)}")
    print(f"Pipeline Verdict: {analysis.verdict}")
    print(f"Pipeline Scam Type: {scam_type}")
    print(f"Pipeline Signal Codes: {signal_codes}")
    print(f"Pipeline Score: {analysis.score}")
    
    results.append({
        "image": img_name,
        "sha256": sha256,
        "verdict": analysis.verdict,
        "scam_type": scam_type,
        "signals": signal_codes,
        "score": analysis.score
    })

print("\n======================================================================")
print("SUMMARY TABLE OF VERDICTS")
print("======================================================================")
for r in results:
    print(f"{r['image']:<12} | Verdict: {r['verdict']:<14} | Scam Type: {str(r['scam_type']):<12} | Signals: {r['signals']}")
