"""What a teacher is told about each message, as string keys the screens translate.

Every label is an icon plus words, never colour alone. A person's own answer has no AI label. The
text of each key is in strings/{en,hi,ta}.json and is tested word for word in
tests/chat/test_labels.py.

- A person wrote it: no label.
- The AI drafted it and a person sent or edited it: `chat.label.ai_checked`
  ("Drafted with AI, checked by your mentor.")
- The AI sent it after the timeout: `chat.label.auto`
  ("AI-generated from approved material. Your mentor will check it.")
- A person corrected an AI answer: `chat.label.correction` ("Correction from your mentor")
- Waiting, and the AI may answer by a time: `chat.waiting_by`
  ("Waiting for your mentor. You will get an answer by {time}.")
- Waiting, with no promise of a time: `chat.waiting`
  ("Waiting for your mentor. They will answer as soon as they can.")
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from services.api.db import ChatMessage

AI_CHECKED = "chat.label.ai_checked"
AUTO = "chat.label.auto"
CORRECTION = "chat.label.correction"
WAITING_BY = "chat.waiting_by"
WAITING = "chat.waiting"
ALL_KEYS = (AI_CHECKED, AUTO, CORRECTION, WAITING_BY, WAITING)


def aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def answer_label(m: ChatMessage) -> str | None:
    """The label on an answer or correction, or None for a person's own words."""
    if m.kind == "correction":
        return CORRECTION
    if m.author_role == "ai":
        return AUTO
    if m.ai_assisted:
        return AI_CHECKED
    return None


def waiting(question: ChatMessage, *, ai_may_answer: bool) -> dict[str, Any] | None:
    """The line under a question nobody has answered yet. It promises a time only when the AI
    really may answer by then (the draft passed its checks and auto-send is on)."""
    if question.status not in ("pending", "ai_draft_ready"):
        return None
    if ai_may_answer and question.ai_due_at is not None:
        return {"key": WAITING_BY, "params": {"time": aware(question.ai_due_at).isoformat()}}
    return {"key": WAITING, "params": {}}
