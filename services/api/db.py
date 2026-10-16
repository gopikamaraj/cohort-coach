"""Database models. Class-level counts only: no child, roll number, answer or photo columns.

Alembic migrations arrive with the first real API schema (see DECISIONS.md); until then the dev
and test databases are built with `Base.metadata.create_all`.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, ForeignKey, UniqueConstraint
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
