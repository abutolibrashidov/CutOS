"""
CutOS Telegram bot.

Runs as its own process (separate from the FastAPI backend) using long
polling. Its only job right now is to greet the user on /start and give
them a button that opens the Mini App webview.

Run with:
    python -m bot.main

(from the backend/ directory, so `app.core.config` resolves correctly)
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from app.core.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

# The URL your Mini App is served from. During local dev this is your
# Cloudflare tunnel URL — the SAME one you registered with @BotFather.
# Update MINI_APP_URL in backend/.env every time the tunnel URL changes.
MINI_APP_URL = settings.MINI_APP_URL

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


@dp.message(CommandStart())
async def handle_start(message: Message) -> None:
    if not MINI_APP_URL:
        await message.answer(
            "Bot ishlayapti, lekin Mini App URL sozlanmagan. "
            "MINI_APP_URL environment variable qo'shing."
        )
        logger.warning("MINI_APP_URL is not set — cannot show 'Open App' button.")
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✂️ Ochish / Open App",
                    web_app=WebAppInfo(url=MINI_APP_URL),
                )
            ]
        ]
    )
    await message.answer(
        "CutOS ga xush kelibsiz! Ilovani ochish uchun tugmani bosing 👇",
        reply_markup=keyboard,
    )


async def main() -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set in backend/.env — bot cannot start."
        )
    logger.info("Starting CutOS bot (polling mode)...")
    # Drop any pending updates from before this process started, so
    # restarting the bot doesn't replay a backlog of old /start commands.
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())