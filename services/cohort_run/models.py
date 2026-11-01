"""One two-class run: class counts, the cohort it formed, its lessons, feedback and events.

Counts only. No child's answer, roll number or name is stored here; feedback notes are masked
before they are saved. The chat and the review items live in their own tables (one cohort space,
real review items), and the run keeps their ids.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from services.api.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class CohortRun(Base):
    __tablename__ = "cohort_runs"

    id: Mapped[str] = mapped_column(String(24), primary_key=True)  # "run-" + 16 hex
    scenario: Mapped[str] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(String(10), default="synthetic")  # synthetic | pilot
    state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
