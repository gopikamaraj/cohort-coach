# ruff: noqa: E501
"""The ledger tables. One row per billable event, one small row per action. Metadata only: kinds,
models, units, durations, costs and ids. Never a prompt, a reply, a transcript, audio, or anything about
a teacher or a child."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from services.api.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class UsageEntry(Base):
    __tablename__ = "usage_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    action_id: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(10))  # llm | tts | stt | cloud_run
    provider: Mapped[str] = mapped_column(String(30))
    model_or_voice: Mapped[str] = mapped_column(String(60), default="")
    units: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # numbers only, keys per kind
    cost_usd: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # None: no price (shows n/a)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(8), default="ok")  # ok | failed | retried
    request_id: Mapped[str] = mapped_column(String(40), default="")
    meta: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict
    )  # booleans only: cold, cached, estimated


class UsageAction(Base):
    """The action itself: its name and how many requests (and background steps) are still running."""

    __tablename__ = "usage_actions"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(40), default="")
    inflight: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
