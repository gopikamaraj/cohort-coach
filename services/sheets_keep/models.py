"""One kept answer-sheet picture: an object in the private sheets bucket and a row saying whose.

A sheet carries a roll number only (no child, teacher or school), and a teacher agrees before any of
her sheets is kept. The picture is kept from her approval of that roll number for the retention
period (60 days), then deleted.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from services.api.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class KeptSheet(Base):
    __tablename__ = "kept_sheet"
    __table_args__ = (UniqueConstraint("class_id", "owner", "check_id", "roll"),)

    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    class_id: Mapped[str] = mapped_column(String(40), index=True)
    owner: Mapped[str] = mapped_column(String(32))  # the user id (the normalised nickname)
    check_id: Mapped[str] = mapped_column(String(60))  # "<class id>:<term>"
    roll: Mapped[int] = mapped_column(Integer)
    object_key: Mapped[str] = mapped_column(String(100))
    sha256: Mapped[str] = mapped_column(String(64))
    approved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    delete_after: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
