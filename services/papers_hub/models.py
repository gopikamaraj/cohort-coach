"""Tables for the Papers page. Class-level data only: no child, no name, no answer.

`paper_import` is a draft of a paper read from an upload. It holds the printed questions the reader
found (never handwriting) and, for at most 24 hours, the page images on disk. `paper_assignment` is
who was asked to use which paper, as what kind, by when, with one row per class.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from services.api.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class PaperImport(Base):
    __tablename__ = "paper_import"

    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    owner: Mapped[str] = mapped_column(String(40))  # a pseudonymous person id
    role: Mapped[str] = mapped_column(String(10))
    file_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(10), default="draft")  # draft | confirmed | gone
    draft: Mapped[dict[str, Any]] = mapped_column(JSON)
    history: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)  # for Undo
    pages: Mapped[int] = mapped_column(Integer, default=0)
    paper_id: Mapped[str | None] = mapped_column(String(24))
    cost_usd: Mapped[float] = mapped_column(default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PaperAssignment(Base):
    __tablename__ = "paper_assignment"

    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    paper_id: Mapped[str] = mapped_column(String(24), index=True)
    target_type: Mapped[str] = mapped_column(String(8))  # teacher | class | cohort
    target_id: Mapped[str] = mapped_column(String(40))
    class_id: Mapped[str] = mapped_column(String(40), index=True)  # one row per class
    cohort_id: Mapped[str | None] = mapped_column(String(40))
    kind: Mapped[str] = mapped_column(String(8))  # pre | post | termly
    form: Mapped[str] = mapped_column(String(2))
    assigned_by: Mapped[str] = mapped_column(String(40))
    assigned_role: Mapped[str] = mapped_column(String(10))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    start_date: Mapped[str | None] = mapped_column(String(10))
    due_date: Mapped[str | None] = mapped_column(String(10))
    # assigned | opened | in_progress | completed | withdrawn
    status: Mapped[str] = mapped_column(String(12), default="assigned")
    note: Mapped[str] = mapped_column(Text, default="")
    sheets_entered: Mapped[int] = mapped_column(Integer, default=0)
    sheets_expected: Mapped[int] = mapped_column(Integer, default=0)
    via_assistant: Mapped[bool] = mapped_column(Boolean, default=False)
