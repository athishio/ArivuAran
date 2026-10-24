"""
Arivaran Project Global Configuration.
Contains display names, constants, and localized placeholders.
"""

import os
from dotenv import load_dotenv

load_dotenv()

BOT_NAME_EN = "ARIVUARAN"
# BOT_NAME_TA and its genitive form BOT_NAME_TA_GEN must be updated together
BOT_NAME_TA = "அறிவுஅரண்"
BOT_NAME_TA_GEN = "அறிவுஅரணின்"

# System binary paths for OCR and Audio processing
TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")
DEMO_MODE = os.getenv("DEMO_MODE", "false").lower() in ("true", "1", "yes")
VOICE_IN_ENABLED = os.getenv("VOICE_IN_ENABLED", "false").lower() in ("true", "1", "yes")

# Configure pytesseract binary if library is available
try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
except ImportError:
    pass

