# ruff: noqa: E501
"""Tables of the gated cohort chat. A message is a `thread_posts` row (services/api/db.py) with one
`chat_post_meta` row beside it, so the posting, moderation, labels and retention that already exist
stay the one place they live. Nothing here holds a teacher id or a name: the author is the label the
thread row carries."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from services.api.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class PostMeta(Base):
    __tablename__ = "chat_post_meta"

    post_id: Mapped[str] = mapped_column(ForeignKey("thread_posts.id"), primary_key=True)
    cohort_id: Mapped[str] = mapped_column(String(40), index=True)
    # question | reply | tip | ai_reply | correction | system
    kind: Mapped[str] = mapped_column(String(12))
    reply_to: Mapped[str | None] = mapped_column(String(32), index=True)
    language: Mapped[str] = mapped_column(String(4), default="en")
    # questions only: waiting | answering | answered_human | answered_ai | corrected | resolved
    qstatus: Mapped[str | None] = mapped_column(String(14), index=True)
    ai_due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    answered_by: Mapped[str | None] = mapped_column(String(6))  # human | ai
    after_seconds: Mapped[int | None] = mapped_column(Integer)  # an AI answer: how long it waited
    ai_label: Mapped[str | None] = mapped_column(String(8))  # ai | recorded
    sources: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    ai_call_id: Mapped[int | None] = mapped_column(Integer)
    corrects: Mapped[str | None] = mapped_column(String(32))
    corrected: Mapped[bool] = mapped_column(Boolean, default=False)
    abstained: Mapped[bool] = mapped_column(Boolean, default=False)  # the AI found no approved source
    demo: Mapped[bool] = mapped_column(Boolean, default=False)
    masked: Mapped[list[str]] = mapped_column(JSON, default=list)  # what masking hid (kinds only)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ChatTimeout(Base):
    """A coach's own timeout for one cohort, in seconds (5 to 86400)."""

    __tablename__ = "chat_timeout"

    cohort_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    seconds: Mapped[int] = mapped_column(Integer)
    set_by: Mapped[str] = mapped_column(String(40))
    set_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
