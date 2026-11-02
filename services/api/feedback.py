"""Feedback, the admin review page, consent records and erasure.

Feedback is anonymous: no user id, class id or name is stored, and the text (at most 500 characters)
is refused if it holds a phone number, an email or an ID-like number. The admin endpoints list
feedback and the simulation observations for review. They need the header X-Admin-Key when the
ADMIN_KEY environment variable is set. With no key they are CLOSED (503) unless ADMIN_OPEN=1 is set
on purpose for local dev or the judge demo, and the admin page then says it is open. A real
deployment must set ADMIN_KEY (docs/privacy.md).
"""

from __future__ import annotations

import hmac
import os
import re
from collections import Counter
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import delete, select

from ai.validators.pii import check_pii
from services.api.db import Consent, Feedback, ProfileSync, SimObservation
from services.api.profiles import CLASS_ID, SESSION

router = APIRouter(prefix="/api", tags=["feedback"])

Kind = Literal["app", "simulation", "content", "card_flag"]
Role = Literal["teacher", "coach", "mentor", "admin", "judge"]
SCOPES = ("core", "counts", "practice_ai", "share_rehearsal", "feedback", "keep_sheets")
DEVICE_ID = re.compile(r"^[0-9a-f]{16}$")


class FeedbackIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Kind
    rating: int | None = Field(None, ge=1, le=5)
    text: str | None = Field(None, max_length=500)
    language: Literal["en", "hi", "ta"]
    role: Role
    context: str | None = Field(
        None, pattern=r"^(practice|PV-HEARD|PV-REVERSE|ADD-NOCARRY|SUB-SFL|SUB-NODEC)$"
    )

    @field_validator("text")
    @classmethod
    def _no_personal_data(cls, v: str | None) -> str | None:
        if v and check_pii(v):
            raise ValueError("The text looks like it holds a phone number, email or ID number.")
        return v.strip() or None if v else None

    @field_validator("text")
    @classmethod
    def _flags_have_no_text(cls, v: str | None, info: Any) -> str | None:
        if v and info.data.get("kind") == "card_flag":
            raise ValueError("A card flag carries no text.")
        return v


@router.post("/feedback")
def add_feedback(body: FeedbackIn, db=SESSION) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    db.add(Feedback(**body.model_dump()))
    db.commit()
    return {"stored": True}


class ConsentIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    device_id: str
    scope: Literal["core", "counts", "practice_ai", "share_rehearsal", "feedback", "keep_sheets"]
    granted: bool
    version: int = Field(ge=1, le=99)

    @field_validator("device_id")
    @classmethod
    def _random_id_only(cls, v: str) -> str:
        if not DEVICE_ID.match(v):
            raise ValueError("device_id must be the random id the app made")
        return v


@router.post("/consents")
def add_consent(body: ConsentIn, db=SESSION) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    """A consent or its withdrawal is a new row; the history is kept (DPDP: proof of consent)."""
    db.add(
        Consent(
            subject_id=body.device_id, scope=f"{body.scope}.v{body.version}", granted=body.granted
        )
    )
    db.commit()
    return {"stored": True}


@router.delete("/classes/{class_id}")
def erase_class(class_id: str, db=SESSION) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    """Erase a class's counts from the server (the right to erasure). Feedback is anonymous."""
    if not CLASS_ID.match(class_id):
        raise HTTPException(422, "Unknown class id.")
    res = db.execute(delete(ProfileSync).where(ProfileSync.class_id == class_id))
    db.commit()
    return {"deleted": res.rowcount or 0}


# ---- admin --------------------------------------------------------------------------------


def admin_open() -> bool:
    """Open only when ADMIN_OPEN=1 is set on purpose (local dev and the judge demo)."""
    return os.environ.get("ADMIN_OPEN") == "1" and not os.environ.get("ADMIN_KEY")


def admin_guard(x_admin_key: str | None = Header(None)) -> None:
    """Fail closed: with no ADMIN_KEY and no explicit ADMIN_OPEN=1 nobody gets in."""
    key = os.environ.get("ADMIN_KEY")
    if key:
        if not x_admin_key or not hmac.compare_digest(x_admin_key.encode(), key.encode()):
            raise HTTPException(401, "The admin key is missing or wrong.")
    elif os.environ.get("ADMIN_OPEN") != "1":
        raise HTTPException(503, "The admin page is closed: set ADMIN_KEY on the server.")


ADMIN = Depends(admin_guard)


def _item(r: Feedback) -> dict[str, Any]:
    return {
        "id": r.id, "kind": r.kind, "rating": r.rating, "text": r.text, "language": r.language,
        "role": r.role, "context": r.context, "status": r.status, "note": r.admin_note,
        "created_at": r.created_at.isoformat(),
    }  # fmt: skip


@router.get("/admin/feedback")
def admin_feedback(
    kind: Kind | None = None,
    status: Literal["new", "reviewed"] | None = None,
    db=SESSION,  # type: ignore[no-untyped-def]
    _: None = ADMIN,
) -> dict[str, Any]:
    q = select(Feedback).order_by(Feedback.id.desc()).limit(500)
    if kind:
        q = q.where(Feedback.kind == kind)
    if status:
        q = q.where(Feedback.status == status)
    return {
        "items": [_item(r) for r in db.execute(q).scalars()],
        "open_admin": admin_open(),
    }


class ReviewIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["new", "reviewed"]
    note: str | None = Field(None, max_length=300)


@router.patch("/admin/feedback/{item_id}")
def admin_review(item_id: int, body: ReviewIn, db=SESSION, _: None = ADMIN) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    row = db.get(Feedback, item_id)
    if row is None:
        raise HTTPException(404, "No such feedback item.")
    row.status, row.admin_note = body.status, body.note
    db.commit()
    return _item(row)


@router.get("/admin/observations")
def admin_observations(db=SESSION, _: None = ADMIN) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    rows = db.execute(
        select(SimObservation).order_by(SimObservation.id.desc()).limit(500)
    ).scalars()
    return {
        "items": [
            {"id": r.id, "scenario": r.scenario, "language": r.language, "likeness": r.likeness,
             "differences": r.differences, "created_at": r.created_at.isoformat()}
            for r in rows
        ]
    }  # fmt: skip


@router.get("/admin/summary")
def admin_summary(db=SESSION, _: None = ADMIN) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    rows = list(db.execute(select(Feedback)).scalars())
    status = Counter(r.status for r in rows)
    return {
        "feedback": {"new": status.get("new", 0), "reviewed": status.get("reviewed", 0)},
        "by_kind": dict(Counter(r.kind for r in rows)),
        "observations": len(list(db.execute(select(SimObservation.id)).scalars())),
        "open_admin": admin_open(),
    }
