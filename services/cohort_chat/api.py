# ruff: noqa: E501
"""The gated cohort chat API. The server enforces every role; the screen only shows what is allowed.
Responses carry labels, never a name, a teacher id or a handle."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from services.api.cohorts import lifecycle
from services.api.cohorts.routes import _teacher, person_id
from services.api.profiles import SESSION
from services.api.roles import role_of
from services.cohort_chat import service
from services.cohort_chat.service import Actor, Refused

router = APIRouter(prefix="/api/cohort-chat", tags=["cohort-chat"])


def _actor(role: str, db: Session, device: str | None, person: str | None) -> Actor:
    if role == "teacher":
        return Actor("teacher", _teacher(db, device).teacher_id)
    if role in ("mentor", "coach"):
        return Actor(role, person_id(role, person))
    raise HTTPException(403, "This chat is not open to your role.")


def _run(fn: Any) -> Any:
    try:
        return fn()
    except Refused as exc:
        raise HTTPException(exc.status, {"codes": exc.codes, "message": str(exc)}) from exc
    except lifecycle.NotAllowed as exc:
        raise HTTPException(403, {"codes": ["not_assigned"], "message": str(exc)}) from exc


class MessageIn(BaseModel):
    kind: str = Field(pattern="^(question|reply|tip)$")
    text: str = Field(max_length=2000)
    language: str = Field(default="en", pattern="^(en|hi|ta)$")
    reply_to: str | None = Field(default=None, max_length=32)


class CorrectIn(BaseModel):
    text: str = Field(max_length=2000)
    language: str = Field(default="en", pattern="^(en|hi|ta)$")


class ModerateIn(BaseModel):
    action: str = Field(pattern="^(hide|restore|pin|unpin)$")


class TimeoutIn(BaseModel):
    seconds: int


@router.get("/inbox")
def inbox(role: str = Depends(role_of), x_device_id: str | None = Header(default=None), x_person: str | None = Header(default=None), db: Session = SESSION) -> dict[str, Any]:
    actor = _actor(role, db, x_device_id, x_person)
    return _run(lambda: service.inbox(db, actor))


@router.get("/{cohort_id}")
def thread_view(cohort_id: str, role: str = Depends(role_of), x_device_id: str | None = Header(default=None), x_person: str | None = Header(default=None), db: Session = SESSION) -> dict[str, Any]:
    actor = _actor(role, db, x_device_id, x_person)
    return _run(lambda: service.thread_view(db, cohort_id, actor))


@router.post("/{cohort_id}/messages")
def post_message(cohort_id: str, body: MessageIn, role: str = Depends(role_of), x_device_id: str | None = Header(default=None), x_person: str | None = Header(default=None), db: Session = SESSION) -> dict[str, Any]:
    actor = _actor(role, db, x_device_id, x_person)
    return _run(lambda: service.post_message(db, cohort_id, actor, body.kind, body.text, body.language, reply_to=body.reply_to))


@router.post("/{cohort_id}/messages/{post_id}/resolve")
def resolve(cohort_id: str, post_id: str, role: str = Depends(role_of), x_device_id: str | None = Header(default=None), x_person: str | None = Header(default=None), db: Session = SESSION) -> dict[str, bool]:
    actor = _actor(role, db, x_device_id, x_person)
    _run(lambda: service.resolve(db, cohort_id, actor, post_id))
    return {"ok": True}


@router.post("/{cohort_id}/messages/{post_id}/correct")
def correct(cohort_id: str, post_id: str, body: CorrectIn, role: str = Depends(role_of), x_device_id: str | None = Header(default=None), x_person: str | None = Header(default=None), db: Session = SESSION) -> dict[str, Any]:
    actor = _actor(role, db, x_device_id, x_person)
    return _run(lambda: service.correct_ai(db, cohort_id, actor, post_id, body.text, body.language))


@router.post("/{cohort_id}/messages/{post_id}/moderate")
def moderate(cohort_id: str, post_id: str, body: ModerateIn, role: str = Depends(role_of), x_device_id: str | None = Header(default=None), x_person: str | None = Header(default=None), db: Session = SESSION) -> dict[str, bool]:
    actor = _actor(role, db, x_device_id, x_person)
    _run(lambda: service.moderate(db, cohort_id, actor, post_id, body.action))
    return {"ok": True}


@router.post("/{cohort_id}/messages/{post_id}/report")
def report(cohort_id: str, post_id: str, role: str = Depends(role_of), x_device_id: str | None = Header(default=None), x_person: str | None = Header(default=None), db: Session = SESSION) -> dict[str, bool]:
    actor = _actor(role, db, x_device_id, x_person)
    _run(lambda: service.report(db, cohort_id, actor, post_id))
    return {"ok": True}


@router.put("/{cohort_id}/timeout")
def set_timeout(cohort_id: str, body: TimeoutIn, role: str = Depends(role_of), x_device_id: str | None = Header(default=None), x_person: str | None = Header(default=None), db: Session = SESSION) -> dict[str, Any]:
    actor = _actor(role, db, x_device_id, x_person)
    seconds = _run(lambda: service.set_timeout(db, cohort_id, actor, body.seconds))
    return {"seconds": seconds}
