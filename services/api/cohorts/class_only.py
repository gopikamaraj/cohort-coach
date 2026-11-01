"""A cohort just for one teacher's class (scope "class_only").

She picks which of her class's errors to work on and names it; the server keeps the choice and the
counts, nothing else. It is labelled "Just my class: no other teachers yet" wherever it appears.
The production minimum of classes (COHORT_MIN_CLASSES) is not changed: this is its own, separate
path, and the cohort formation never reads it. A coach sees it in counts, never a teacher id.
"""

from __future__ import annotations

import re
import secrets
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.validators.thread import check_thread_post
from engine.model import ErrorCode
from services.api.cohorts.routes import _teacher
from services.api.db import ClassCohort
from services.api.profiles import SESSION
from services.api.roles import require

router = APIRouter(prefix="/api/cohorts/class-only", tags=["cohorts"])
CODES = {c.value for c in ErrorCode}
CHECK_ID = re.compile(r"^[A-Za-z0-9:_-]{1,80}$")


class MakeIn(BaseModel):
    check_id: str
    name: str = Field(min_length=1, max_length=80)
    errors: list[str] = Field(min_length=1, max_length=5)
    counts: dict[str, int]
    children_checked: int = Field(ge=0, le=200)
    simulated: bool = False
    language: str = "en"


def view(row: ClassCohort) -> dict[str, Any]:
    """Counts only. No teacher id, no check id, nothing about a child."""
    return {
        "id": row.id,
        "name": row.name,
        "scope": row.scope,
        "status": row.status,
        "errors": row.errors,
        "counts": row.counts,
        "children_checked": row.children_checked,
        "classes": 1,
        "simulated": row.simulated,
    }


@router.post("")
def make(
    body: MakeIn,
    _: str = Depends(require("cohort.chat")),
    x_device_id: str | None = Header(default=None),
    db: Session = SESSION,
) -> dict[str, Any]:
    teacher = _teacher(db, x_device_id)
    if not CHECK_ID.match(body.check_id):
        raise HTTPException(422, "The check id is not valid.")
    if not set(body.errors) <= CODES or len(set(body.errors)) != len(body.errors):
        raise HTTPException(422, "Choose from the errors the check can find.")
    for code in body.errors:
        n = body.counts.get(code)
        if n is None or n < 0 or n > body.children_checked:
            raise HTTPException(422, "Each chosen error needs its count of children.")
    if set(body.counts) - CODES:
        raise HTTPException(422, "Unknown error in the counts.")
    mine = db.execute(
        select(ClassCohort).where(
            ClassCohort.teacher_id == teacher.teacher_id, ClassCohort.check_id == body.check_id
        )
    ).scalar_one_or_none()
    if mine is not None:  # one per check: a second tap, or a retry after a lost reply
        return view(mine)
    try:
        problems = check_thread_post(body.name, body.language)
    except Exception as exc:  # the check could not run: hold, never pass
        raise HTTPException(503, "The name could not be checked. Try again.") from exc
    if problems:
        raise HTTPException(
            422, {"codes": [p.code for p in problems], "message": "Please rewrite the name."}
        )
    row = ClassCohort(
        id="cc-" + secrets.token_hex(6),
        teacher_id=teacher.teacher_id,
        check_id=body.check_id,
        name=body.name.strip(),
        errors=body.errors,
        counts={c: body.counts[c] for c in body.errors},
        children_checked=body.children_checked,
        simulated=body.simulated,
    )
    db.add(row)
    db.commit()
    return view(row)


@router.get("")
def mine(
    _: str = Depends(require("cohort.chat")),
    x_device_id: str | None = Header(default=None),
    db: Session = SESSION,
) -> list[dict[str, Any]]:
    teacher = _teacher(db, x_device_id)
    rows = db.execute(
        select(ClassCohort).where(ClassCohort.teacher_id == teacher.teacher_id)
    ).scalars()
    return [view(r) for r in rows]


@router.get("/coach")
def for_coach(
    _: str = Depends(require("coach.moderate")), db: Session = SESSION
) -> list[dict[str, Any]]:
    """The coach's Cohorts view: every class-only cohort, in counts (a class of one is not a
    figure about another teacher, and the teacher is never named)."""
    return [view(r) for r in db.execute(select(ClassCohort)).scalars()]
