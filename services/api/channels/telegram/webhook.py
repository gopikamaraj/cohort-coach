"""The production entry for Telegram: `POST /api/telegram/webhook`.

Telegram sends the secret you set with `setWebhook` in a header; any other caller gets 403, and with
no secret configured the route is closed. Replies go out over the Bot API with httpx.
"""

from __future__ import annotations

import hmac
import json
import logging
import os
from typing import Any

import httpx
from fastapi import APIRouter, Header, HTTPException
from sqlalchemy.orm import Session

from services.api.channels.base import Message
from services.api.channels.telegram import keyboard, process
from services.api.flows.steps import SceneRef
from services.api.profiles import SESSION
from services.api.sprite_media import scene_png

# httpx logs request URLs at INFO, and the bot token is in the URL.
logging.getLogger("httpx").setLevel(logging.WARNING)

router = APIRouter(prefix="/api/telegram", tags=["telegram"])
CAPTION_MAX = 1024  # the Bot API limit on a photo caption


def requests_for(
    message: Message, chat_id: str
) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    """The Bot API calls for one message: (method, form fields, files). A message with a scene is a
    photo with the text as its caption; the picture is drawn from the same data as in the web app.
    A scene that cannot be drawn is dropped and the text goes alone."""
    rows: list[list[dict[str, str]]] = keyboard(message)
    if message.url:
        rows.append([{"text": message.url_label or message.url, "url": message.url}])
    markup = json.dumps({"inline_keyboard": rows}) if rows else None
    png: bytes | None = None
    if message.scene:
        try:
            png = scene_png(SceneRef(**message.scene))
        except (ValueError, KeyError, TypeError):
            png = None
    if png is None:
        fields: dict[str, Any] = {"chat_id": chat_id, "text": message.text}
        if markup:
            fields["reply_markup"] = markup
        return [("sendMessage", fields, {})]
    photo = {"photo": ("scene.png", png, "image/png")}
    if len(message.text) <= CAPTION_MAX:
        fields = {"chat_id": chat_id, "caption": message.text}
        if markup:
            fields["reply_markup"] = markup
        return [("sendPhoto", fields, photo)]
    text = {"chat_id": chat_id, "text": message.text}
    if markup:
        text["reply_markup"] = markup
    return [
        ("sendPhoto", {"chat_id": chat_id, "caption": message.alt or ""}, photo),
        ("sendMessage", text, {}),
    ]


class HttpSender:
    def __init__(self, token: str) -> None:
        self.token = token

    def send(self, chat_id: str, message: Message) -> None:
        for method, fields, files in requests_for(message, chat_id):
            try:
                httpx.post(
                    f"https://api.telegram.org/bot{self.token}/{method}",
                    data=fields,
                    files=files or None,
                    timeout=20 if files else 10,
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
