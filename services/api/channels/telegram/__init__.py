"""Telegram adapter: parses an update, asks the flow engine, renders the steps as messages.

`process` takes the update as the Bot API sends it and a `Sender`; the real sender
(python-telegram-bot or the HTTP API) lives in `scripts/run_bot.py` and the webhook route, so
tests use a fake one.
A button carries `step_id:option_id`. Nothing is decided here.
"""

from __future__ import annotations

import re
from typing import Any, Protocol

from sqlalchemy.orm import Session

from services.api.channels.base import Message, parse_button, render_turn
from services.api.flows.engine import FlowEngine, Turn

CODE = re.compile(r"^[A-Z2-9]{8}$")


class Sender(Protocol):
    def send(self, chat_id: str, message: Message) -> None: ...


def _send_all(sender: Sender, chat_id: str, turn: Turn) -> None:
    for m in render_turn(turn):
        sender.send(chat_id, m)


def process(db: Session, update: dict[str, Any], sender: Sender) -> None:
    eng = FlowEngine(db)
    cb = update.get("callback_query")
    if cb:
        chat_id = str(cb["message"]["chat"]["id"])
        parsed = parse_button(str(cb.get("data", "")))
        if parsed is None:
            return
        teacher = eng.teacher_for("telegram", chat_id)
        try:
            turn = eng.answer(teacher, parsed[0], parsed[1], key=f"tg{cb['id']}")
        except ValueError:
            turn = eng.start(teacher)
        _send_all(sender, chat_id, turn)
        return
    msg = update.get("message")
    if not msg or "text" not in msg:
        return
    chat_id = str(msg["chat"]["id"])
    text = str(msg["text"]).strip()
    arg = text.split(maxsplit=1)[1].strip() if text.startswith("/start") and " " in text else ""
    code = arg if CODE.match(arg) else ""
    if not code and CODE.match(text):  # a code typed on its own
        code = text
    if code:
        teacher = eng.link(code, "telegram", chat_id)
        if teacher is not None:
            _send_all(sender, chat_id, eng.start(teacher))
            return
    if text.split()[0:1] == ["/stop"]:
        _send_all(sender, chat_id, eng.ask_delete(eng.teacher_for("telegram", chat_id)))
        return
    judge = arg.lower() == "judge"
    teacher = eng.teacher_for("telegram", chat_id, judge=judge)
    _send_all(sender, chat_id, eng.start(teacher))


def keyboard(message: Message) -> list[list[dict[str, str]]]:
    """The inline keyboard for a message: one button per row, callback data `step_id:option_id`."""
    return [
        [{"text": b.label, "callback_data": f"{message.step_id}:{b.id}"}] for b in message.buttons
    ]
