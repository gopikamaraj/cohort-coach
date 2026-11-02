# ruff: noqa: E501
"""Tables for improvement tracks. Counts and text only: no child, no name, no roll number. A feedback note
is masked before it is saved. The database is built by `Base.metadata.create_all` (the project has no
migration folder); the unique constraint on (track_id, number) is what makes generation safe to repeat."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from services.api.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class Track(Base):
    __tablename__ = "tracks"
    __table_args__ = (UniqueConstraint("class_cohort_id", "error"),)

    id: Mapped[str] = mapped_column(String(24), primary_key=True)  # "trk-" + 12 hex
    class_cohort_id: Mapped[str] = mapped_column(String(40), index=True)
    teacher_id: Mapped[str] = mapped_column(String(18), index=True)
    error: Mapped[str] = mapped_column(String(16))
    language: Mapped[str] = mapped_column(String(4), default="en")
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)  # the next check: nothing is planned after it
    status: Mapped[str] = mapped_column(String(10), default="active")  # active|completed|stopped
    stop_reason: Mapped[str | None] = mapped_column(String(12))  # cap|exhausted|done|end_date
    cap: Mapped[int] = mapped_column(Integer, default=6)
    note: Mapped[str | None] = mapped_column(
        String(120)
    )  # e.g. "no plan for this error: one module"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class TrackModule(Base):
    __tablename__ = "track_modules"
    __table_args__ = (UniqueConstraint("track_id", "number"),)

    id: Mapped[str] = mapped_column(String(28), primary_key=True)  # "mod-" + 12 hex
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    template_id: Mapped[str | None] = mapped_column(String(60))  # "<error>:<approach>[:small]"
    approach_id: Mapped[str | None] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(160), default="")
    due_date: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(14), default="planned")
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    generated_by: Mapped[str | None] = mapped_column(String(10))  # start|teacher|due_date|coach
    branch: Mapped[str | None] = mapped_column(
        String(12)
    )  # first|worked|partly|not_yet|no_feedback
    reason: Mapped[dict[str, Any] | None] = mapped_column(
        JSON
    )  # {code, n, prev}: the screen words it
    text: Mapped[dict[str, Any] | None] = mapped_column(
        JSON
    )  # the module text as generated (frozen)
    audio_ref: Mapped[str | None] = mapped_column(String(120))  # the audio cache key, once taken
    language: Mapped[str | None] = mapped_column(String(4))
    failures: Mapped[int] = mapped_column(Integer, default=0)


class ModuleFeedback(Base):
    __tablename__ = "module_feedback"

    module_id: Mapped[str] = mapped_column(ForeignKey("track_modules.id"), primary_key=True)
    answer: Mapped[str] = mapped_column(String(10))  # worked|partly|not_yet|not_tried
    note: Mapped[str] = mapped_column(String(320), default="")  # masked
    given_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ModuleEvent(Base):
    __tablename__ = "module_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    track_id: Mapped[str] = mapped_column(String(24), index=True)
    module_id: Mapped[str | None] = mapped_column(String(28), index=True)
    event: Mapped[str] = mapped_column(String(30))
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # codes and numbers only
    actor: Mapped[str] = mapped_column(String(10))  # teacher|coach|system
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
