"""Database models. Class-level counts only: no child, roll number, answer or photo columns.

Alembic migrations arrive with the first real API schema (see DECISIONS.md); until then the dev
and test databases are built with `Base.metadata.create_all`.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Engine,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class School(Base):
    __tablename__ = "school"

    school_id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    school_type: Mapped[str]
    medium: Mapped[str]
    simulated: Mapped[bool] = mapped_column(default=False)


class ClassRoom(Base):
    __tablename__ = "classroom"

    class_id: Mapped[str] = mapped_column(primary_key=True)
    school_id: Mapped[str] = mapped_column(ForeignKey("school.school_id"))
    block_id: Mapped[str]
    grade: Mapped[int]
    section: Mapped[str]
    medium: Mapped[str]
    teacher_id: Mapped[str]
    teacher_name: Mapped[str]  # fictional in the simulated block
    simulated: Mapped[bool] = mapped_column(default=False)


class ClassTermCount(Base):
    """What one class's check produced in one term: how many children showed each error."""

    __tablename__ = "class_term_count"
    __table_args__ = (UniqueConstraint("class_id", "term"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    class_id: Mapped[str] = mapped_column(ForeignKey("classroom.class_id"))
    term: Mapped[str]
    form_label: Mapped[str]
    children_checked: Mapped[int]
    counts: Mapped[dict[str, Any]] = mapped_column(JSON)
    anchor_wrong_count: Mapped[int]
    untracked: Mapped[dict[str, Any]] = mapped_column(JSON)
    simulated: Mapped[bool] = mapped_column(default=False)


class Assignment(Base):
    """A class's track for the coming term and its waitlist arm (computed by the engine)."""

    __tablename__ = "assignment"

    class_id: Mapped[str] = mapped_column(ForeignKey("classroom.class_id"), primary_key=True)
    track: Mapped[str]
    version: Mapped[str]
    arm: Mapped[str]
    stratum: Mapped[int]
    reason: Mapped[str]
    children_checked: Mapped[int]
    children_showing: Mapped[int]
    simulated: Mapped[bool] = mapped_column(default=False)


class Cohort(Base):
    __tablename__ = "cohort"

    cohort_id: Mapped[str] = mapped_column(primary_key=True)
    error: Mapped[str]
    medium: Mapped[str]
    size: Mapped[int]
    class_ids: Mapped[list[str]] = mapped_column(JSON)
    block_id: Mapped[str | None]
    cross_block: Mapped[bool]
    undersized: Mapped[bool]
    mentor_slot: Mapped[bool]
    simulated: Mapped[bool] = mapped_column(default=False)


def _now() -> datetime:
    return datetime.now(UTC)


class AiCall(Base):
    """The audit trail: one row per AI call. Metadata only, never prompt or output text."""

    __tablename__ = "ai_calls"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    call_id: Mapped[int] = mapped_column(Integer)
    call_key: Mapped[str] = mapped_column(String(40), index=True)
    prompt_version: Mapped[int] = mapped_column(Integer)
    model: Mapped[str] = mapped_column(String(60))
    mode: Mapped[str] = mapped_column(String(10))  # recorded | live | record
    judge: Mapped[bool] = mapped_column(Boolean, default=False)
    metadata_only: Mapped[bool] = mapped_column(Boolean, default=False)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    tokens_cache_read: Mapped[int] = mapped_column(Integer, default=0)
    tokens_cache_write: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    validator_results: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    checker_verdict: Mapped[str | None] = mapped_column(String(10))  # pass | fail | none
    checker_reason: Mapped[str | None] = mapped_column(String(300))
    retries: Mapped[int] = mapped_column(Integer, default=0)
    fallback_used: Mapped[str | None] = mapped_column(String(40))
    input_hash: Mapped[str] = mapped_column(String(64))
    reviewer_decision: Mapped[str | None] = mapped_column(String(20))
    reviewer_reason: Mapped[str | None] = mapped_column(String(40))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SpeechCall(Base):
    """One speech request (stt or tts). Metadata only: never the audio or the text."""

    __tablename__ = "speech_calls"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    stage: Mapped[str] = mapped_column(String(8))  # stt | tts
    mode: Mapped[str] = mapped_column(String(8))  # live | stub
    language: Mapped[str] = mapped_column(String(4))
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    audio_bytes: Mapped[int] = mapped_column(Integer, default=0)
    characters: Mapped[int] = mapped_column(Integer, default=0)
    seconds: Mapped[float] = mapped_column(Float, default=0.0)
    cost_inr: Mapped[float] = mapped_column(Float, default=0.0)
    from_cache: Mapped[bool] = mapped_column(Boolean, default=False)
    error_kind: Mapped[str | None] = mapped_column(String(16))


class SimObservation(Base):
    """A teacher's view, after trying it in class, of how like her real class the simulated children
    were. Choices only (no free text, no class or teacher id): a signal for tuning the simulator."""

    __tablename__ = "sim_observations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    scenario: Mapped[str] = mapped_column(String(12))
    language: Mapped[str] = mapped_column(String(4))
    likeness: Mapped[str] = mapped_column(String(10))  # like | some | not_like
    differences: Mapped[list[str]] = mapped_column(JSON, default=list)


class Feedback(Base):
    """App, simulation, content and card feedback. Anonymous: no user, class or device id."""

    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)
    kind: Mapped[str] = mapped_column(
        String(12), index=True
    )  # app | simulation | content | card_flag
    rating: Mapped[int | None] = mapped_column(Integer)
    text: Mapped[str | None] = mapped_column(String(500))
    language: Mapped[str] = mapped_column(String(4))
    role: Mapped[str] = mapped_column(String(10))
    context: Mapped[str | None] = mapped_column(String(40))  # e.g. the error code of a flagged card
    status: Mapped[str] = mapped_column(String(10), default="new", index=True)  # new | reviewed
    admin_note: Mapped[str | None] = mapped_column(String(300))


class ReviewItem(Base):
    """AI content waiting for, or past, human review (track drafts, method cards)."""

    __tablename__ = "review_items"

    item_id: Mapped[str] = mapped_column(primary_key=True)
    content_type: Mapped[str]  # track_draft | method_card | feedback_card
    ai_call_id: Mapped[int | None] = mapped_column(ForeignKey("ai_calls.id"))
    language: Mapped[str]
    target_error: Mapped[str | None]
    content: Mapped[dict[str, Any]] = mapped_column(JSON)
    badge: Mapped[str] = mapped_column(default="none")  # none | checked | checked_reviewed
    status: Mapped[str] = mapped_column(default="pending")  # pending | approved | rejected
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("review_items.item_id"), index=True)
    decision: Mapped[str]  # approve | reject | edit
    reason: Mapped[str | None]  # structured enum, set on reject (ai/guard/rejections.py)
    edit_diff: Mapped[str | None]
    reviewer_role: Mapped[str]  # reviewer | mentor
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class TeacherFlag(Base):
    """A teacher tapped 'this is wrong' on an AI card. No free text is stored."""

    __tablename__ = "teacher_flags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ai_call_id: Mapped[int | None] = mapped_column(ForeignKey("ai_calls.id"))
    item_id: Mapped[str | None] = mapped_column(ForeignKey("review_items.item_id"))
    kind: Mapped[str]  # wrong_maths | not_my_class | unclear | other
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Consent(Base):
    """What a teacher or mentor agreed to share. Withdrawing adds a row; history is kept."""

    __tablename__ = "consents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    subject_id: Mapped[str] = mapped_column(index=True)
    scope: Mapped[str]  # e.g. counts.v1, practice_ai.v1, share_rehearsal.v1, feedback.v1, core.v1
    granted: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


def make_engine(url: str | None = None) -> Engine:
    """Engine from DATABASE_URL (SQLite for local dev and tests, Postgres in production)."""
    return create_engine(url or os.environ.get("DATABASE_URL") or "sqlite:///./dev.sqlite")


class ProfileSync(Base):
    """A class's check result as the phone sends it: counts only, never a per-child answer.

    The class id is a random id made on the phone; no school, teacher or child is named here.
    """

    __tablename__ = "profile_sync"
    __table_args__ = (UniqueConstraint("class_id", "term"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    class_id: Mapped[str] = mapped_column(String(40), index=True)
    term: Mapped[str] = mapped_column(String(8))
    form: Mapped[str] = mapped_column(String(4))
    children_checked: Mapped[int] = mapped_column(Integer)
    counts: Mapped[dict[str, Any]] = mapped_column(JSON)
    anchor_wrong_count: Mapped[int] = mapped_column(Integer)
    untracked: Mapped[dict[str, Any]] = mapped_column(JSON)
    simulated: Mapped[bool] = mapped_column(Boolean, default=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
