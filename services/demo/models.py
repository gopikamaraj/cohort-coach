"""Demo Studio tables. Judge demo only, SIMULATED data only, keyed by the demo session.

A demo session is one judge's device (a random id the browser makes); Reset deletes its rows.
The AI read cache is keyed by the image's hash, so the same synthetic sheet is read by the model
once, whichever session uploads it. Nothing here touches pilot data.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from services.api.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class DemoSession(Base):
    __tablename__ = "demo_session"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    scenario: Mapped[str] = mapped_column(String(40))
    seed: Mapped[int] = mapped_column(Integer)
    class_code: Mapped[str] = mapped_column(String(12))
    paper_id: Mapped[str | None] = mapped_column(String(24))
    ai_reads: Mapped[int] = mapped_column(Integer, default=0)
    ai_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    # class-level only: the cohort plan, the first audio, the chat cohort id, the post-test flag
    state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class DemoReadCache(Base):
    __tablename__ = "demo_read_cache"

    image_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    cells: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    retried: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class DemoAiRead(Base):
    """One AI read of a synthetic sheet in a session, scored against the known truth (boxes read
    correctly), for the demo reading summary. Synthetic sheets only."""

    __tablename__ = "demo_ai_read"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(40))
    image_hash: Mapped[str] = mapped_column(String(64))
    sheet: Mapped[str] = mapped_column(String(40))
    boxes: Mapped[int] = mapped_column(Integer)
    boxes_right: Mapped[int] = mapped_column(Integer)
    cached: Mapped[bool] = mapped_column(default=False)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
