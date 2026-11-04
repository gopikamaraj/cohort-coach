# ruff: noqa: E501
"""A cohort just for one teacher's class (scope "class_only").

She picks which of her class's errors to work on and names it; the server keeps the choice and the
counts, nothing else. It is labelled "Just my class: no other teachers yet" wherever it appears.
The production minimum of classes (COHORT_MIN_CLASSES) is not changed: this is its own, separate
path, and the cohort formation never reads it. A coach sees it in counts, never a teacher id.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
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
from services.api import caps
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
        "rule": {"min_hits": int(row.counts.get("_rule", 1 if (row.scope == "coach" or row.group_id) else 2))},  # a group cohort made before the rule was stored counted any sighting; a teacher's own counts confirmed
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
    class_refs: list[str] | None = None  # the classes to include (from /officer/candidates); None = every class that shows it
    min_hits: int | None = None  # the rule it is built under: 2 confirmed, 1 possible (else the creator's saved rule)


COACH_OWNER = "coach-cohorts"


@router.post("/coach")
def make_for_coach(
    body: CoachMakeIn, _: str = Depends(require("coach.moderate")), uid: str = Depends(user_of), db: Session = SESSION
) -> dict[str, Any]:
    return _make_group(body, db, coach=uid, creator=uid)


@router.post("/officer")
def make_for_officer(
    body: CoachMakeIn, _: str = Depends(require("officer.approve_cohorts")), uid: str = Depends(user_of), db: Session = SESSION
) -> dict[str, Any]:
    return _make_group(body, db, coach=None, creator=uid)


@router.get("/officer")
def for_officer(
    _: str = Depends(require("officer.approve_cohorts")), db: Session = SESSION
) -> list[dict[str, Any]]:
    return [view(r) for r in db.execute(select(ClassCohort)).scalars()]


def _ref(owner: str, class_id: str) -> str:
    """An opaque reference to one entered class: the same every time, and it says nothing about who or where. The
    officer picks classes by it; the page shows only an anonymous label ("Class A") and a count of children."""
    salt = os.environ.get("AUDIT_HASH_SALT", "") or "cohort-coach"
    return hmac.new(salt.encode(), f"{owner}/{class_id}".encode(), hashlib.sha256).hexdigest()[:16]


def _letters(n: int) -> str:
    out = ""
    n += 1
    while n:
        n, r = divmod(n - 1, 26)
        out = chr(65 + r) + out
    return out


def _showing(db: Session, error: str, rule: int) -> list[dict[str, Any]]:
    """The entered classes (each by its most recent check) that show this mistake under the rule, as anonymous
    entries: a reference, a label and the number of children with it. No nickname, class code or child detail."""
    from services.api.devicestore import entered_summary

    picked = sorted((c for c in entered_summary(db, None, rule)["classes"] if c["_counts"].get(error, 0) > 0), key=lambda c: _ref(c["_owner"], c["_class"].split("/", 1)[1]))
    return [{"ref": _ref(c["_owner"], c["_class"].split("/", 1)[1]), "label": f"Class {_letters(n)}", "children": int(c["_counts"][error]), "children_checked": c["children_checked"], "_c": c} for n, c in enumerate(picked)]


@router.get("/officer/candidates")
def candidates(
    error: str,
    _: str = Depends(require("officer.approve_cohorts")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
    min_hits: int | None = None,
) -> dict[str, Any]:
    """For Create a cohort: the classes that show this mistake under the rule, as Class A, Class B, ... with the
    number of children who show it. Nothing that names a teacher, a class or a child."""
    from services.api.devicestore import rule_for

    if error not in CODES:
        raise HTTPException(422, "Choose from the errors the check can find.")
    rule = rule_for(db, uid, min_hits)
    return {"error": error, "rule": {"min_hits": rule}, "caps": caps.describe(), "classes": [{k: v for k, v in c.items() if k != "_c"} for c in _showing(db, error, rule)]}


def _selection_key(owners: list[str]) -> str:
    return hashlib.sha1("|".join(sorted(owners)).encode()).hexdigest()[:8]  # noqa: S324 (a label, not security)


def _group_for(db: Session, check_id: str, coach: str | None = None) -> ClassCohort | None:
    """The cohort already formed from this exact set of classes by this coach (or by the officer when `coach` is None)."""
    for g in db.execute(select(ClassCohort).where(ClassCohort.teacher_id == COACH_OWNER, ClassCohort.check_id == check_id)).scalars():
        if g.counts.get("_coach") == coach:
            return g
    return None


def _make_group(body: CoachMakeIn, db: Session, coach: str | None = None, creator: str = "") -> dict[str, Any]:
    """A coach or the officer forms a cohort from entered classes that show one mistake (each class by its most
    recent check), counts added up. With `class_refs` it is exactly those classes; without, every class that shows it.
    The same set of classes gives the same cohort on a second tap. A cohort leaves an audit row."""
    from services.api.cohorts.lifecycle import audit
    from services.api.devicestore import rule_for

    if body.error not in CODES:
        raise HTTPException(422, "Choose from the errors the check can find.")
    rule = rule_for(db, creator, body.min_hits)
    offered = _showing(db, body.error, rule)
    if not offered:
        raise HTTPException(422, "No class has entered a check yet." if not body.class_refs else "None of those classes shows this mistake.")
    chosen = [c for c in offered if body.class_refs is None or c["ref"] in set(body.class_refs)]
    if body.class_refs is not None and len(chosen) != len(set(body.class_refs)):
        raise HTTPException(422, "A class you chose does not show this mistake under this rule.")
    picked = [c["_c"] for c in chosen]
    need = caps.min_cohort_classes()
    if len(picked) < need:
        raise HTTPException(422, "A cohort needs at least two classes that show this mistake." if need > 1 else "Choose at least one class.")
    members: dict[str, str] = {}
    for c in picked:  # a user is in a cohort once, on the first of her chosen classes
        members.setdefault(c["_owner"], c["_check"])
    check_id = f"coach:{body.error}:{_selection_key(list(members))}"
    have = _group_for(db, check_id, coach)
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
        counts={body.error: sum(c["_counts"][body.error] for c in picked), "_classes": len(picked), "_rule": rule, "_members": {k: v for k, v in members.items() if v}, **({"_coach": coach} if coach else {})},
        children_checked=sum(c["children_checked"] for c in picked),
        simulated=False,
    )
    db.add(row)
    audit(db, row.id, "coach" if coach else "officer", creator or (coach or "officer"), "group_created", error=body.error, classes=len(picked), children=sum(c["_counts"][body.error] for c in picked), min_hits=rule)
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
    _: str = Depends(require("officer.approve_cohorts")), uid: str = Depends(user_of), db: Session = SESSION, min_hits: int | None = None
) -> dict[str, Any]:
    """The officer's one button: for every mistake that enough entered classes show (each by its most recent check), form
    a cohort from all of them, once. Each teacher whose class is in it finds it on her next visit."""
    from services.api.devicestore import rule_for

    rule = rule_for(db, uid, min_hits)
    created: list[dict[str, Any]] = []
    already, waiting = 0, []
    for code in sorted(CODES):
        offered = _showing(db, code, rule)
        if not offered:
            continue
        if len(offered) < caps.min_cohort_classes():
            waiting.append(code)
            continue
        owners = {c["_c"]["_owner"] for c in offered}
        if _group_for(db, f"coach:{code}:{_selection_key(list(owners))}", None) is not None:
            already += 1
            continue
        created.append(_make_group(CoachMakeIn(name=f"{_error_label(code)} cohort", error=code, min_hits=rule), db, creator=uid))
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
