# ruff: noqa: E501
"""Cohort space API. Every route names the permission it needs; the role comes from the same
config as everywhere (services/api/roles/permissions.yaml).

A coach acts only on cohorts assigned to her and a mentor sees only cohorts she mentors; both are
identified by a pseudonymous id (`X-Person`, in the judge deployment; otherwise "<role>-demo" until
P12 brings real role assignment). A teacher is identified by her device id. Responses carry display
names, never a teacher id, a handle or a phone number.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.cohorts import lifecycle, mentor_items, thread
from services.api.db import CohortSpace, ThreadPost
from services.api.flows.engine import FlowEngine
from services.api.identity import optional_user, user_of
from services.api.profiles import SESSION
from services.api.roles import require

router = APIRouter(prefix="/api/cohorts", tags=["cohorts"])
PERSON = re.compile(r"^[a-z0-9][a-z0-9-]{2,29}$")


def person_id(role: str, x_person: str | None) -> str:
    """Who is acting in a staff role: the signed-in user's id (each role account is a user). `role_of` already
    refuses a non-teacher role outside a judge session, so this never grants one."""
    if not x_person:
        raise HTTPException(401, {"code": "sign_in", "message": "Sign in with your nickname first."})
    return x_person


def _wrap(fn: Callable[[], Any]) -> Any:
    try:
        return fn()
    except lifecycle.NotAllowed as exc:
        raise HTTPException(403, str(exc)) from exc
    except (lifecycle.BadTransition, mentor_items.BadState, thread.ThreadClosed) as exc:
        raise HTTPException(409, str(exc)) from exc
    except thread.NotMember as exc:
        raise HTTPException(403, str(exc)) from exc
    except thread.PostRejected as exc:
        raise HTTPException(
            422, {"codes": exc.codes, "message": "Please rewrite it without names or details."}
        ) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def _teacher(db: Session, uid: str) -> Any:
    return FlowEngine(db).teacher_for("pwa", uid)


# ---- officer: create, status, retention -------------------------------------------------------


class CreateIn(BaseModel):
    error: str = Field(pattern=r"^[A-Z0-9-]{3,16}$")
    coach_id: str
    mentor_ids: list[str] = Field(default_factory=list, max_length=5)
    school_count: int = Field(default=0, ge=0, le=500)


@router.post("/officer/cohorts")
def officer_create(
    body: CreateIn,
    role: str = Depends(require("officer.approve_cohorts")),
    x_person: str | None = Depends(optional_user),
    db: Session = SESSION,
) -> dict[str, Any]:
    cohort = lifecycle.create(
        db,
        error=body.error,
        coach_id=body.coach_id,
        mentor_ids=body.mentor_ids,
        officer_id=person_id(role, x_person),
        school_count=body.school_count,
    )
    return lifecycle.summary(db, cohort)


class StatusIn(BaseModel):
    to: str
    reason: str | None = Field(default=None, max_length=60)
    post_test_received: bool | None = None


@router.post("/officer/cohorts/{cohort_id}/status")
def officer_status(
    cohort_id: str,
    body: StatusIn,
    role: str = Depends(require("officer.approve_cohorts")),
    x_person: str | None = Depends(optional_user),
    db: Session = SESSION,
) -> dict[str, Any]:
    cohort = _wrap(
        lambda: lifecycle.transition(
            db,
            cohort_id,
            body.to,
            role="officer",
            actor=person_id(role, x_person),
            reason=body.reason,
            post_test_received=body.post_test_received,
        )  # fmt: skip
    )
    return lifecycle.summary(db, cohort)


@router.post("/officer/retention/run")
def officer_retention(
    _: str = Depends(require("officer.approve_cohorts")), db: Session = SESSION
) -> dict[str, int]:
    return thread.purge(db)


@router.get("/officer/cohorts")
def officer_list(
    _: str = Depends(require("officer.approve_cohorts")), db: Session = SESSION
) -> list[dict[str, Any]]:
    return [lifecycle.summary(db, c) for c in db.execute(select(CohortSpace)).scalars()]


# ---- coach ------------------------------------------------------------------------------------


@router.get("/coach/cohorts")
def coach_list(
    role: str = Depends(require("coach.moderate")),
    x_person: str | None = Depends(optional_user),
    db: Session = SESSION,
) -> list[dict[str, Any]]:
    me = person_id(role, x_person)
    rows = db.execute(select(CohortSpace).where(CohortSpace.coach_id == me)).scalars()
    return [lifecycle.summary(db, c) for c in rows]


@router.get("/coach/cohorts/{cohort_id}/thread")
def coach_thread(
    cohort_id: str,
    role: str = Depends(require("coach.moderate")),
    x_person: str | None = Depends(optional_user),
    db: Session = SESSION,
) -> list[dict[str, Any]]:
    cohort = _wrap(lambda: lifecycle.get(db, cohort_id))
    _wrap(lambda: lifecycle.require_assigned(cohort, "coach", person_id(role, x_person)))
    return thread.posts_for(db, cohort_id, moderator=True)


class DecideIn(BaseModel):
    action: str
    identifier: bool = False


@router.post("/coach/posts/{post_id}/decide")
def coach_decide_post(
    post_id: str,
    body: DecideIn,
    role: str = Depends(require("coach.moderate")),
    x_person: str | None = Depends(optional_user),
    db: Session = SESSION,
) -> dict[str, Any]:
    me = person_id(role, x_person)
    post = db.get(ThreadPost, post_id)
    if post is None:
        raise HTTPException(404, "That post does not exist.")
    _wrap(lambda: lifecycle.require_assigned(lifecycle.get(db, post.cohort_id), "coach", me))
    done = _wrap(
        lambda: thread.decide(db, post_id, body.action, actor=me, identifier=body.identifier)
    )
    return thread.view(done)


class PostIn(BaseModel):
    body: str = Field(min_length=1, max_length=500)
    language: str = Field(default="en", pattern="^(en|hi|ta)$")


@router.post("/coach/cohorts/{cohort_id}/prompt")
def coach_prompt(
    cohort_id: str,
    body: PostIn,
    role: str = Depends(require("coach.moderate")),
    x_person: str | None = Depends(optional_user),
    db: Session = SESSION,
) -> dict[str, Any]:
    me = person_id(role, x_person)
    _wrap(lambda: lifecycle.require_assigned(lifecycle.get(db, cohort_id), "coach", me))
    return thread.view(
        _wrap(lambda: thread.post_as_staff(db, cohort_id, "coach", me, body.body, body.language))
    )


@router.post("/coach/cohorts/{cohort_id}/closing")
def coach_closing(
    cohort_id: str,
    role: str = Depends(require("coach.moderate")),
    x_person: str | None = Depends(optional_user),
    db: Session = SESSION,
) -> dict[str, Any]:
    me = person_id(role, x_person)
    cohort = _wrap(lambda: lifecycle.transition(db, cohort_id, "closing", role="coach", actor=me))
    return lifecycle.summary(db, cohort)


@router.get("/coach/items")
def coach_items(
    role: str = Depends(require("coach.approve_items")),
    x_person: str | None = Depends(optional_user),
    db: Session = SESSION,
) -> list[dict[str, Any]]:
    rows = mentor_items.awaiting_for_coach(db, person_id(role, x_person))
    return [_item(i) for i in rows]


class ItemDecisionIn(BaseModel):
    decision: str
    reason: str | None = None
    note: str = Field(default="", max_length=300)


@router.post("/coach/items/{item_id}/decide")
def coach_item_decide(
    item_id: str,
    body: ItemDecisionIn,
    role: str = Depends(require("coach.approve_items")),
    x_person: str | None = Depends(optional_user),
    db: Session = SESSION,
) -> dict[str, Any]:
    item = _wrap(
        lambda: mentor_items.decide(
            db,
            item_id,
            body.decision,
            coach_id=person_id(role, x_person),
            reason=body.reason,
            note=body.note,
        )  # fmt: skip
    )
    return _item(item)


# ---- mentor -----------------------------------------------------------------------------------


@router.get("/mentor/cohorts")
def mentor_list(
    role: str = Depends(require("mentor.items_view")),
    x_person: str | None = Depends(optional_user),
    db: Session = SESSION,
) -> list[dict[str, Any]]:
    me = person_id(role, x_person)
    rows = [
        c for c in db.execute(select(CohortSpace)).scalars() if lifecycle.assigned(c, "mentor", me)
    ]
    return [lifecycle.summary(db, c) for c in rows]  # cohort-level figures only, no member list


class ItemIn(BaseModel):
    cohort_id: str
    kind: str


@router.post("/mentor/items")
def mentor_create_item(
    body: ItemIn,
    role: str = Depends(require("mentor.items_view")),
    x_person: str | None = Depends(optional_user),
    db: Session = SESSION,
) -> dict[str, Any]:
    me = person_id(role, x_person)
    return _item(_wrap(lambda: mentor_items.create(db, body.cohort_id, me, body.kind)))


@router.post("/mentor/items/{item_id}/submit")
def mentor_submit_item(
    item_id: str,
    role: str = Depends(require("mentor.items_view")),
    x_person: str | None = Depends(optional_user),
    db: Session = SESSION,
) -> dict[str, Any]:
    return _item(_wrap(lambda: mentor_items.submit(db, item_id, person_id(role, x_person))))


@router.get("/mentor/items")
def mentor_items_list(
    role: str = Depends(require("mentor.items_view")),
    x_person: str | None = Depends(optional_user),
    db: Session = SESSION,
) -> list[dict[str, Any]]:
    return [_item(i) for i in mentor_items.list_for_mentor(db, person_id(role, x_person))]


def _item(i: Any) -> dict[str, Any]:
    return {
        "id": i.id,
        "cohort_id": i.cohort_id,
        "kind": i.kind,
        "version": i.version,
        "status": i.status,
        "reason_code": i.reason_code,
        "note": i.note,
    }


# ---- the thread: teachers (device) and mentors (person) ---------------------------------------


@router.get("/open")
def open_cohorts(
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> list[dict[str, Any]]:
    """Cohorts a teacher can join or has joined: status and the error in words only; the figures
    follow the same under-5 rule as everywhere. Whether she is already in is hers to know."""
    teacher = _teacher(db, uid)
    out = []
    for c in db.execute(
        select(CohortSpace).where(CohortSpace.status.in_(("proposed", "active")))
    ).scalars():
        row = lifecycle.summary(db, c)
        row["joined"] = thread_member(db, c.id, teacher.teacher_id) is not None
        out.append(row)
    return out


class JoinIn(BaseModel):
    consent: bool = False  # the separate, explicit tap: joining is its own consent


@router.post("/{cohort_id}/join")
def join(
    cohort_id: str,
    body: JoinIn,
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, Any]:
    if not body.consent:
        raise HTTPException(403, "Joining the cohort chat needs your own tap to agree.")
    teacher = _teacher(db, uid)
    cohort = _wrap(lambda: lifecycle.get(db, cohort_id))
    if cohort.status not in ("active", "proposed"):
        raise HTTPException(409, "This cohort is not open to join.")
    teacher.consent = {**(teacher.consent or {}), "cohort": True}
    db.merge(teacher)
    member = thread.join(db, cohort_id, teacher.teacher_id)
    return {"display_name": member.display_name, "thread": lifecycle.thread_state(db, cohort)}


@router.get("/{cohort_id}/thread")
def get_thread(
    cohort_id: str,
    role: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    x_person: str | None = Depends(optional_user),
    db: Session = SESSION,
) -> dict[str, Any]:
    cohort = _wrap(lambda: lifecycle.get(db, cohort_id))
    if role == "mentor":
        _wrap(lambda: lifecycle.require_assigned(cohort, "mentor", person_id(role, x_person)))
    else:
        teacher = _teacher(db, uid)
        if thread_member(db, cohort_id, teacher.teacher_id) is None:
            raise HTTPException(403, "Join the cohort first.")
    return {
        "state": lifecycle.thread_state(db, cohort),
        "posts": thread.posts_for(db, cohort_id),
    }


def thread_member(db: Session, cohort_id: str, teacher_id: str) -> Any:
    from services.api.db import CohortMember

    return db.get(CohortMember, (cohort_id, teacher_id))


@router.post("/{cohort_id}/posts")
def post(
    cohort_id: str,
    body: PostIn,
    role: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    x_person: str | None = Depends(optional_user),
    db: Session = SESSION,
) -> dict[str, Any]:
    if role == "mentor":
        me = person_id(role, x_person)
        cohort = _wrap(lambda: lifecycle.get(db, cohort_id))
        _wrap(lambda: lifecycle.require_assigned(cohort, "mentor", me))
        made = _wrap(
            lambda: thread.post_as_staff(db, cohort_id, "mentor", me, body.body, body.language)
        )
    else:
        teacher = _teacher(db, uid)
        made = _wrap(
            lambda: thread.post_as_teacher(
                db, cohort_id, teacher.teacher_id, body.body, body.language
            )
        )
    return thread.view(made)


@router.post("/posts/{post_id}/report")
def report_post(
    post_id: str,
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, str]:
    teacher = _teacher(db, uid)
    _wrap(lambda: thread.report(db, post_id, teacher.teacher_id))
    return {"status": "held for the coach"}


@router.delete("/posts/{post_id}")
def delete_post(
    post_id: str,
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, str]:
    teacher = _teacher(db, uid)
    _wrap(lambda: thread.delete_own(db, post_id, teacher.teacher_id))
    return {"status": "deleted"}
