"""Gate 4: a teacher taps 'this is wrong' on an AI card. One tap, no free text is stored."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.api.db import TeacherFlag

FLAG_KINDS = frozenset({"wrong_maths", "not_my_class", "unclear", "other"})


def add_flag(
    session: Session, *, kind: str, ai_call_id: int | None = None, item_id: str | None = None
) -> int:
    if kind not in FLAG_KINDS:
        raise ValueError(f"unknown flag kind {kind!r}")
    if ai_call_id is None and item_id is None:
        raise ValueError("a flag needs an AI call id or a review item id")
    row = TeacherFlag(kind=kind, ai_call_id=ai_call_id, item_id=item_id)
    session.add(row)
    session.commit()
    return row.id


def flag_count(session: Session, *, item_id: str) -> int:
    q = select(func.count()).select_from(TeacherFlag).where(TeacherFlag.item_id == item_id)
    return int(session.execute(q).scalar_one())
