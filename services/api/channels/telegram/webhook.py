"""The production entry for Telegram: `POST /api/telegram/webhook`.

Telegram sends the secret you set with `setWebhook` in a header; any other caller gets 403, and with
no secret configured the route is closed. Replies go out over the Bot API with httpx.
"""

from __future__ import annotations

import hmac
import logging
import os
from typing import Any

import httpx
from fastapi import APIRouter, Header, HTTPException
from sqlalchemy.orm import Session

from services.api.channels.base import Message
from services.api.channels.telegram import keyboard, process
from services.api.profiles import SESSION

# httpx logs request URLs at INFO, and the bot token is in the URL.
logging.getLogger("httpx").setLevel(logging.WARNING)

router = APIRouter(prefix="/api/telegram", tags=["telegram"])


class HttpSender:
    def __init__(self, token: str) -> None:
        self.token = token

    def send(self, chat_id: str, message: Message) -> None:
        rows: list[list[dict[str, str]]] = keyboard(message)
        if message.url:
            rows.append([{"text": message.url_label or message.url, "url": message.url}])
        payload: dict[str, Any] = {"chat_id": chat_id, "text": message.text}
        if rows:
            payload["reply_markup"] = {"inline_keyboard": rows}
        try:
            httpx.post(
                f"https://api.telegram.org/bot{self.token}/sendMessage", json=payload, timeout=10
            )
        except httpx.HTTPError:  # not re-raised: the error text would carry the token URL
            pass


@router.post("/webhook")
def webhook(
    update: dict[str, Any],
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
    db: Session = SESSION,
) -> dict[str, bool]:
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not secret or not token:
        raise HTTPException(403, "The Telegram webhook is not configured.")
    if not hmac.compare_digest(x_telegram_bot_api_secret_token or "", secret):
        raise HTTPException(403, "Not Telegram.")
    process(db, update, HttpSender(token))
    return {"ok": True}
