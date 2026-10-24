"""
Telegram I/O helper layer for Arivaran.
Handles sending text, interactive inline buttons, and voice note downloads.
Includes Telegram rate-limit (RetryAfter) retries and privacy masking.
"""

import os
import sys
import logging
import asyncio
import tempfile
from typing import List, Dict, Optional, Any
from dotenv import load_dotenv

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.error import RetryAfter, TimedOut

# Configure minimal logger
logger = logging.getLogger("telegram_io")
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

# Global bot instance holder
_bot_instance: Optional[Bot] = None


def set_bot(bot: Bot) -> None:
    """Sets the active Telegram Bot instance for I/O operations."""
    global _bot_instance
    _bot_instance = bot


def get_bot() -> Bot:
    """Returns the active Bot instance, creating one if not already set."""
    global _bot_instance
    if _bot_instance is None:
        _bot_instance = Bot(token=BOT_TOKEN)
    return _bot_instance


def mask_id(raw_id: Any) -> str:
    """
    Masks user ID or chat ID, showing only the last 2 digits for privacy.
    Example: 123456789 -> ***89
    """
    id_str = str(raw_id)
    if len(id_str) <= 2:
        return "**"
    return f"***{id_str[-2:]}"


async def _execute_with_retry(coro_fn):
    """Executes an async Telegram API call with one automatic retry on RetryAfter."""
    try:
        return await coro_fn()
    except RetryAfter as e:
        logger.warning(f"Telegram rate limit hit. Waiting {e.retry_after}s before single retry...")
        await asyncio.sleep(e.retry_after)
        return await coro_fn()


async def send_text(
    chat_id: int,
    text: str,
    parse_mode: Optional[str] = "HTML",
    buttons: Optional[List[Dict[str, str]]] = None,
    reply_markup: Optional[Any] = None
) -> Optional[Message]:
    """
    Sends a message to the specified Telegram chat.
    Supports HTML parsing by default and attached inline buttons.
    Handles rate-limiting (RetryAfter) with a single automatic retry.
    """
    bot = get_bot()
    masked = mask_id(chat_id)

    if reply_markup is None and buttons:
        keyboard = []
        for btn in buttons:
            btn_id = str(btn.get("id", ""))
            btn_title = str(btn.get("title", ""))[:35]
            keyboard.append([InlineKeyboardButton(text=btn_title, callback_data=btn_id)])
        reply_markup = InlineKeyboardMarkup(keyboard)

    async def _send():
        kwargs = {"chat_id": chat_id, "text": text}
        if parse_mode is not None:
            kwargs["parse_mode"] = parse_mode
        if reply_markup is not None:
            kwargs["reply_markup"] = reply_markup
        try:
            return await bot.send_message(**kwargs)
        except Exception as pe:
            # Fallback to plain text without markup if HTML parsing fails
            if parse_mode is not None:
                logger.warning(f"Parse mode '{parse_mode}' failed ({pe}). Retrying without parse_mode...")
                kwargs.pop("parse_mode", None)
                return await bot.send_message(**kwargs)
            raise pe

    try:
        msg = await _execute_with_retry(_send)
        logger.info(f"msg_type='text' chat_id={masked}: SUCCESS")
        return msg
    except Exception as e:
        logger.error(f"msg_type='text' chat_id={masked}: FAILED ({type(e).__name__})")
        raise


async def send_buttons(
    chat_id: int,
    text: str,
    buttons: List[Dict[str, str]],
    parse_mode: Optional[str] = "HTML"
) -> Optional[Message]:
    """
    Sends a message with up to 3 interactive inline buttons (one button per row).
    Buttons schema: [{'id': 'button_callback_id', 'title': 'Button Text'}]
    Title is capped at 20 characters as per project specification.
    """
    bot = get_bot()
    masked = mask_id(chat_id)

    keyboard = []
    for btn in buttons[:3]:
        btn_id = str(btn.get("id", ""))
        btn_title = str(btn.get("title", ""))[:20]
        keyboard.append([InlineKeyboardButton(text=btn_title, callback_data=btn_id)])

    reply_markup = InlineKeyboardMarkup(keyboard)

    async def _send():
        kwargs = {"chat_id": chat_id, "text": text, "reply_markup": reply_markup}
        if parse_mode is not None:
            kwargs["parse_mode"] = parse_mode
        try:
            return await bot.send_message(**kwargs)
        except Exception as pe:
            if parse_mode is not None:
                logger.warning(f"Parse mode '{parse_mode}' failed ({pe}). Retrying without parse_mode...")
                kwargs.pop("parse_mode", None)
                return await bot.send_message(**kwargs)
            raise pe

    try:
        msg = await _execute_with_retry(_send)
        logger.info(f"msg_type='buttons' chat_id={masked}: SUCCESS")
        return msg
    except Exception as e:
        logger.error(f"msg_type='buttons' chat_id={masked}: FAILED ({type(e).__name__})")
        raise


async def download_voice(message: Message) -> str:
    """
    Downloads a Telegram voice note to a temporary .ogg file on disk.
    Returns the absolute path to the downloaded audio file.
    Caller MUST clean up the file in a finally block.
    """
    if not message.voice:
        raise ValueError("Provided message does not contain a voice note.")

    masked = mask_id(message.chat_id)

    async def _download():
        voice_file = await message.voice.get_file()
        fd, temp_path = tempfile.mkstemp(suffix=".ogg", prefix="arivaran_voice_")
        os.close(fd)
        await voice_file.download_to_drive(custom_path=temp_path)
        return temp_path

    try:
        path = await _execute_with_retry(_download)
        logger.info(f"msg_type='audio_download' chat_id={masked}: SUCCESS")
        return path
    except Exception as e:
        logger.error(f"msg_type='audio_download' chat_id={masked}: FAILED ({type(e).__name__})")
        raise


async def send_voice(chat_id: int, voice_path: str, caption: Optional[str] = None) -> Optional[Message]:
    """
    Sends an audio voice note to the specified Telegram chat.
    Uses 30s read/write/connect timeouts and retries once on TimedOut or RetryAfter.
    """
    bot = get_bot()
    masked = mask_id(chat_id)
    file_size = os.path.getsize(voice_path) if os.path.exists(voice_path) else 0

    async def _send():
        with open(voice_path, "rb") as vf:
            return await bot.send_voice(
                chat_id=chat_id,
                voice=vf,
                caption=caption,
                read_timeout=30.0,
                write_timeout=30.0,
                connect_timeout=30.0
            )

    try:
        try:
            msg = await _execute_with_retry(_send)
        except TimedOut:
            logger.warning(f"Voice send timed out for chat {masked} (size: {file_size}b). Retrying once with 30s timeout...")
            msg = await _execute_with_retry(_send)
        logger.info(f"msg_type='voice_send' chat_id={masked} size={file_size}b: SUCCESS")
        return msg
    except Exception as e:
        logger.error(f"msg_type='voice_send' chat_id={masked} size={file_size}b: FAILED ({type(e).__name__})")
        raise


async def send_photo(chat_id: int, photo_path: str, caption: Optional[str] = None) -> Optional[Message]:
    """
    Sends an image / photo card to the specified Telegram chat.
    Handles rate-limiting (RetryAfter) with a single automatic retry.
    """
    bot = get_bot()
    masked = mask_id(chat_id)

    async def _send():
        with open(photo_path, "rb") as pf:
            return await bot.send_photo(chat_id=chat_id, photo=pf, caption=caption)

    try:
        msg = await _execute_with_retry(_send)
        logger.info(f"msg_type='photo_send' chat_id={masked}: SUCCESS")
        return msg
    except Exception as e:
        logger.error(f"msg_type='photo_send' chat_id={masked}: FAILED ({type(e).__name__})")
        raise
