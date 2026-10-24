"""
Card Renderer for Arivaran using Playwright.
Renders HTML visual cards with Noto Sans Tamil and Latin fallback.
Generates pixel-perfect screenshots for Telegram image sharing.
"""

import os
import glob
import logging
from typing import Optional
from playwright.async_api import async_playwright

logger = logging.getLogger("arivuaran_card")

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "cards")


def find_chromium_executable() -> Optional[str]:
    """Finds installed chromium executable in local ms-playwright directory."""
    local_app_data = os.getenv("LOCALAPPDATA", "")
    playwright_dir = os.path.join(local_app_data, "ms-playwright")
    if not os.path.isdir(playwright_dir):
        return None

    # Search for chrome.exe or chrome-headless-shell.exe
    candidates = glob.glob(os.path.join(playwright_dir, "chromium*", "**", "chrome.exe"), recursive=True)
    if candidates and os.path.exists(candidates[0]):
        return candidates[0]

    shell_candidates = glob.glob(os.path.join(playwright_dir, "chromium*", "**", "chrome-headless-shell.exe"), recursive=True)
    if shell_candidates and os.path.exists(shell_candidates[0]):
        return shell_candidates[0]

    return None


def build_card_html(scam_type: str, headline: str, advice: str, lang: str = "ta") -> str:
    """Builds clean HTML for warning card with Noto Sans Tamil and Latin fallback."""
    badge_text = "⚠️ எச்சரிக்கை" if lang == "ta" else "⚠️ SCAM ALERT"
    type_label = "வகை:" if lang == "ta" else "Type:"
    footer_brand = "அறிவுஅரண் (Arivaran)"
    footer_warn = "OTP, PIN யாரிடமும் சொல்லாதீர்கள்" if lang == "ta" else "Never share OTP or PIN with anyone"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil:wght@400;600;700&display=swap');
  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }}
  body {{
    font-family: 'Noto Sans Tamil', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: transparent;
    padding: 16px;
    display: inline-block;
  }}
  .card {{
    width: 480px;
    background: #0f172a;
    border: 2px solid #ef4444;
    border-radius: 16px;
    padding: 24px;
    color: #f8fafc;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
  }}
  .badge {{
    display: inline-block;
    background: #7f1d1d;
    color: #fca5a5;
    border: 1px solid #ef4444;
    font-size: 13px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 6px;
    margin-bottom: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .headline {{
    font-size: 20px;
    font-weight: 700;
    color: #ffffff;
    margin-bottom: 16px;
    line-height: 1.4;
  }}
  .alert-box {{
    background: #1e293b;
    border-left: 4px solid #ef4444;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 16px;
  }}
  .alert-title {{
    font-size: 14px;
    font-weight: 600;
    color: #94a3b8;
    margin-bottom: 4px;
  }}
  .alert-text {{
    font-size: 16px;
    font-weight: 700;
    color: #f87171;
  }}
  .advice {{
    font-size: 15px;
    line-height: 1.6;
    color: #cbd5e1;
    margin-bottom: 16px;
  }}
  .footer {{
    border-top: 1px solid #334155;
    padding-top: 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 12px;
    color: #64748b;
  }}
  .brand {{
    font-weight: 700;
    color: #38bdf8;
  }}
</style>
</head>
<body>
  <div class="card">
    <div class="badge">{badge_text}</div>
    <div class="headline">{headline}</div>
    <div class="alert-box">
      <div class="alert-title">{type_label}</div>
      <div class="alert-text">{scam_type}</div>
    </div>
    <div class="advice">{advice}</div>
    <div class="footer">
      <div class="brand">{footer_brand}</div>
      <div>{footer_warn}</div>
    </div>
  </div>
</body>
</html>
"""


async def render_share_card(
    scam_type: str,
    headline: str,
    advice: str,
    lang: str = "ta",
    out_path: Optional[str] = None
) -> Optional[str]:
    """
    Renders a shareable warning card as a PNG image using Playwright.
    Uses Noto Sans Tamil font with Latin fallback.
    """
    if out_path is None:
        os.makedirs(CACHE_DIR, exist_ok=True)
        filename = f"share_card_{lang}_{abs(hash(scam_type + headline)) % 1000000}.png"
        out_path = os.path.join(CACHE_DIR, filename)

    parent_dir = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(parent_dir, exist_ok=True)

    html_content = build_card_html(scam_type=scam_type, headline=headline, advice=advice, lang=lang)

    try:
        exec_path = find_chromium_executable()
        launch_kwargs = {"executable_path": exec_path} if exec_path else {}
        async with async_playwright() as p:
            browser = await p.chromium.launch(**launch_kwargs)
            page = await browser.new_page(viewport={"width": 560, "height": 400})
            await page.set_content(html_content, wait_until="networkidle")
            card_el = await page.query_selector(".card")
            if card_el:
                await card_el.screenshot(path=out_path)
            else:
                await page.screenshot(path=out_path)
            await browser.close()
        logger.info(f"Rendered share card: {out_path}")
        return out_path
    except Exception as e:
        logger.error(f"Card rendering failed: {type(e).__name__} ({str(e)})")
        return None
