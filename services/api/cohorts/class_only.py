# ruff: noqa: E501
"""A cohort just for one teacher's class (scope "class_only").

She picks which of her class's errors to work on and names it; the server keeps the choice and the
counts, nothing else. It is labelled "Just my class: no other teachers yet" wherever it appears.
The production minimum of classes (COHORT_MIN_CLASSES) is not changed: this is its own, separate
path, and the cohort formation never reads it. A coach sees it in counts, never a teacher id.
"""

from __future__ import annotations

import json
import re
import secrets
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.validators.thread import check_thread_post
from engine.model import ErrorCode
from services.api.cohorts.routes import _teacher
from services.api.db import ClassCohort
from services.api.identity import user_of
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
        "counts": {k: v for k, v in row.counts.items() if not k.startswith("_")},
        "children_checked": row.children_checked,
        "classes": int(row.counts.get("_classes", 1)),
        "simulated": row.simulated,
    }


@router.post("")
def make(
    body: MakeIn,
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, Any]:
    teacher = _teacher(db, uid)
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


class CoachMakeIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    error: str
    language: str = "en"


COACH_OWNER = "coach-cohorts"


@router.post("/coach")
def make_for_coach(
    body: CoachMakeIn, _: str = Depends(require("coach.moderate")), uid: str = Depends(user_of), db: Session = SESSION
) -> dict[str, Any]:
    return _make_group(body, db, coach=uid)


@router.post("/officer")
def make_for_officer(
    body: CoachMakeIn, _: str = Depends(require("officer.approve_cohorts")), uid: str = Depends(user_of), db: Session = SESSION
) -> dict[str, Any]:
    return _make_group(body, db, coach=None)


@router.get("/officer")
def for_officer(
    _: str = Depends(require("officer.approve_cohorts")), db: Session = SESSION
) -> list[dict[str, Any]]:
    return [view(r) for r in db.execute(select(ClassCohort)).scalars()]


def _group_for(db: Session, code: str, coach: str | None = None) -> ClassCohort | None:
    """The cohort already formed for a mistake by this coach (or by the officer when `coach` is None). Ones
    formed before terms were removed are named `coach:CODE:1`."""
    for g in db.execute(select(ClassCohort).where(ClassCohort.teacher_id == COACH_OWNER, ClassCohort.check_id.like(f"coach:{code}%"))).scalars():
        if g.counts.get("_coach") == coach:
            return g
    return None


def _make_group(body: CoachMakeIn, db: Session, coach: str | None = None) -> dict[str, Any]:
    """A coach or the officer forms a cohort from the entered classes that show one mistake (each class by its most recent check), counts added up.
    One per mistake; a second tap returns the same cohort."""
    from services.api.devicestore import entered_summary

    if body.error not in CODES:
        raise HTTPException(422, "Choose from the errors the check can find.")
    classes = entered_summary(db)["classes"]
    if not classes:
        raise HTTPException(422, "No class has entered a check yet.")
    picked = [c for c in classes if c["_counts"].get(body.error, 0) > 0]
    if len(picked) < 2:
        raise HTTPException(422, "A cohort needs at least two classes that show this mistake.")
    check_id = f"coach:{body.error}"
    have = _group_for(db, body.error, coach)
    if have is not None:
        return view(have)
    problems = check_thread_post(body.name, body.language)
    if problems:
        raise HTTPException(422, {"codes": [p.code for p in problems], "message": "Please rewrite the name."})
    row = ClassCohort(
        id="cc-" + secrets.token_hex(6),
        teacher_id=COACH_OWNER,
        check_id=check_id,
        name=body.name.strip(),
        scope="coach",
        errors=[body.error],
        counts={body.error: sum(c["_counts"][body.error] for c in picked), "_classes": len(picked), "_members": {c["_owner"]: c["_check"] for c in picked if c.get("_check")}, **({"_coach": coach} if coach else {})},
        children_checked=sum(c["children_checked"] for c in picked),
        simulated=False,
    )
    db.add(row)
    db.commit()
    return view(row)


def _error_label(code: str) -> str:
    try:
        table = json.loads((Path(__file__).resolve().parents[3] / "strings" / "en.json").read_text(encoding="utf-8"))
        return str(table.get(f"err.{code}") or code)
    except (OSError, ValueError):
        return code


@router.post("/form")
def form_cohorts(
    _: str = Depends(require("officer.approve_cohorts")), db: Session = SESSION
) -> dict[str, Any]:
    """The officer's one button: for every mistake that two or more entered classes show (each class by its most recent check), form
    a cohort from them, once. Each teacher whose class is in it finds it on her next visit."""
    from services.api.devicestore import entered_summary

    classes = entered_summary(db)["classes"]
    if not classes:
        return {"created": [], "already": 0, "waiting": []}
    created: list[dict[str, Any]] = []
    already, waiting = 0, []
    for code in sorted(CODES):
        n = sum(1 for c in classes if c["_counts"].get(code, 0) > 0)
        if n == 0:
            continue
        if n < 2:
            waiting.append(code)
            continue
        if _group_for(db, code, None) is not None:
            already += 1
            continue
        created.append(_make_group(CoachMakeIn(name=f"{_error_label(code)} cohort", error=code), db))
    return {"created": created, "already": already, "waiting": waiting}


def _adopt_group_cohorts(db: Session, teacher_id: str) -> None:
    """A cohort a coach or the officer formed lists the user ids of the classes in it. When one of those users
    opens the app she gets her own copy of it (owned by her, on her own check), so everything that works for her
    own cohort works for it: its track, its chat space, the class page. Pooled counts only."""
    store_key = teacher_id
    mine_checks = {r.check_id for r in db.execute(select(ClassCohort).where(ClassCohort.teacher_id == teacher_id)).scalars()}
    groups = db.execute(select(ClassCohort).where(ClassCohort.teacher_id == COACH_OWNER, ClassCohort.scope == "coach")).scalars().all()
    changed = False
    for g in groups:
        check = (g.counts.get("_members") or {}).get(store_key)
        if not check or check in mine_checks:
            continue
        db.add(
            ClassCohort(
                id="cc-" + secrets.token_hex(6),
                teacher_id=teacher_id,
                check_id=check,
                group_id=g.id,
                name=g.name,
                scope="member",
                errors=g.errors,
                counts={k: v for k, v in g.counts.items() if k not in ("_members", "_coach")},
                children_checked=g.children_checked,
                simulated=g.simulated,
            )
        )
        mine_checks.add(check)
        changed = True
    if changed:
        db.commit()


@router.get("")
def mine(
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> list[dict[str, Any]]:
    teacher = _teacher(db, uid)
    _adopt_group_cohorts(db, teacher.teacher_id)
    rows = db.execute(
        select(ClassCohort).where(ClassCohort.teacher_id == teacher.teacher_id)
    ).scalars()
    # her own list: it also says which check each came from
    return [{**view(r), "check_id": r.check_id} for r in rows]


@router.get("/coach")
def for_coach(
    _: str = Depends(require("coach.moderate")), uid: str = Depends(user_of), db: Session = SESSION
) -> list[dict[str, Any]]:
    """The coach's Cohorts view: the cohorts this coach made, in counts (the teachers are never named)."""
    return [view(r) for r in db.execute(select(ClassCohort).where(ClassCohort.scope == "coach")).scalars() if r.counts.get("_coach") == uid]
