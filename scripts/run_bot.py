"""Run the Telegram bot locally by long polling: `python scripts/run_bot.py`.

Needs TELEGRAM_BOT_TOKEN in .env. In production the same `process` is called from the webhook
route (`POST /api/telegram/webhook`), so this file only moves updates and sends messages.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update  # noqa: E402

from ai.config import load_env  # noqa: E402
from services.api.channels.base import Message  # noqa: E402
from services.api.channels.telegram import keyboard, process  # noqa: E402
from services.api.profiles import _factory  # noqa: E402


class BotSender:
    """Collects what `process` wants sent; the loop below sends it (process is synchronous)."""

    def __init__(self) -> None:
        self.out: list[tuple[str, Message]] = []

    def send(self, chat_id: str, message: Message) -> None:
        self.out.append((chat_id, message))


def markup(m: Message) -> InlineKeyboardMarkup | None:
    rows = [
        [InlineKeyboardButton(b["text"], callback_data=b["callback_data"]) for b in row]
        for row in keyboard(m)
    ]
    if m.url:
        rows.append([InlineKeyboardButton(m.url_label or m.url, url=m.url)])
    return InlineKeyboardMarkup(rows) if rows else None


async def main() -> None:
    load_env()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        sys.exit("TELEGRAM_BOT_TOKEN is not set in .env")
    bot = Bot(token)
    offset = 0
    print("Bot running. Press Ctrl+C to stop.")
    async with bot:
        while True:
            for upd in await bot.get_updates(offset=offset, timeout=30):
                offset = upd.update_id + 1
                sender = BotSender()
                with _factory()() as db:
                    process(db, upd.to_dict(), sender)
                cb = upd.callback_query
                if cb:
                    await bot.answer_callback_query(cb.id)
                for chat_id, m in sender.out:
                    await bot.send_message(chat_id, m.text, reply_markup=markup(m))


if __name__ == "__main__":
    _ = Update
    asyncio.run(main())
