# ruff: noqa: E501
"""The web app's adapter: a JSON step API. The app renders `messages` and posts answers back.

A teacher is the signed-in user (header `X-User`, the normalised nickname). `X-Judge: 1` marks a judge-mode session, which sees a labelled simulated class.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from services.api.channels.base import render_turn
from services.api.flows.engine import FlowEngine, Turn
from services.api.flows.links import verify
from services.api.identity import user_of
from services.api.profiles import SESSION

router = APIRouter(prefix="/api/flow", tags=["flow"])


class AnswerIn(BaseModel):
    step_id: str = Field(max_length=40)
    value: str = Field(max_length=40)
    key: str | None = Field(default=None, max_length=64)


class CodeIn(BaseModel):
    code: str = Field(max_length=16)


def body(turn: Turn) -> dict[str, Any]:
    return {
        "lang": turn.lang,
        "consent": turn.consent,
        "messages": [asdict(m) for m in render_turn(turn)],
    }


@router.get("/current")
def current(
    uid: str = Depends(user_of),
    x_judge: str | None = Header(default=None),
    db: Session = SESSION,
) -> dict[str, Any]:
    eng = FlowEngine(db)
    teacher = eng.teacher_for("pwa", uid, judge=x_judge == "1")
    return body(eng.start(teacher))


@router.post("/answer")
def answer(
    payload: AnswerIn, uid: str = Depends(user_of), db: Session = SESSION
) -> dict[str, Any]:
    eng = FlowEngine(db)
    teacher = eng.teacher_for("pwa", uid)
    try:
        return body(eng.answer(teacher, payload.step_id, payload.value, payload.key))
    except ValueError as e:
        raise HTTPException(422, "That is not one of the choices on this step.") from e


@router.post("/code")
def code(uid: str = Depends(user_of), db: Session = SESSION) -> dict[str, str]:
    eng = FlowEngine(db)
    return {"code": eng.new_code(eng.teacher_for("pwa", uid))}


@router.post("/link")
def link(
    payload: CodeIn, uid: str = Depends(user_of), db: Session = SESSION
) -> dict[str, Any]:
    eng = FlowEngine(db)
    teacher = eng.link(payload.code, "pwa", uid)
    if teacher is None:
        raise HTTPException(404, "That code is not valid or has expired. Make a new one.")
    return body(eng.start(teacher))


@router.get("/token/{token}")
def token(token: str) -> dict[str, Any]:
    """What a signed link from the bot says (language, error to practise). No person."""
    facts = verify(token)
    if facts is None:
        raise HTTPException(404, "This link has expired. Ask the bot for a new one.")
    return facts
