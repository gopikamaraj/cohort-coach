"""Practice Class API: create a session, take turns, end it for feedback.

Session state lives in memory with a time limit and is never persisted. The full transcript
comes back to the client, which keeps it on the teacher's phone. The server stores only the
metadata-only audit rows written by the AI calls.
"""

from __future__ import annotations

import time
from dataclasses import asdict, replace
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ai import config
from ai.client import BudgetExceeded, CallContext
from engine.model import ErrorCode
from services.practice.content import LANGS, load_scenario
from services.practice.session import (
    PracticeSession,
    SessionFinished,
    end_session,
    start_session,
    take_turn,
)
from services.practice.stub_client import StubClient

router = APIRouter(prefix="/api/practice", tags=["practice"])

SESSION_TTL_S = 2 * 60 * 60
MAX_SESSIONS = 500
_SESSIONS: dict[str, tuple[PracticeSession, float]] = {}


def get_ai_context() -> CallContext:
    """The AI mode from the environment (recorded, live, record, or stub for offline demos)."""
    mode = config.ai_mode()
    if mode == "stub":
        return CallContext(mode="stub", client=StubClient())
    return CallContext(mode=mode)


AI_CONTEXT = Depends(get_ai_context)


class CreateSession(BaseModel):
    scenario: str = "SUB-SFL"
    language: str = "en"
    judge: bool = False
    counts: dict[str, int] | None = (
        None  # class-level error counts, to seat children like her class
    )
    checked: int = Field(0, ge=0, le=200)
    seed: int | None = None


class TurnRequest(BaseModel):
    text: str | None = Field(None, max_length=1000)
    material: str | None = None
    stt_confidence: float | None = Field(None, ge=0, le=1)


def _sweep() -> None:
    now = time.time()
    for sid in [k for k, (_, at) in _SESSIONS.items() if now - at > SESSION_TTL_S]:
        del _SESSIONS[sid]
    while len(_SESSIONS) >= MAX_SESSIONS:
        del _SESSIONS[min(_SESSIONS, key=lambda k: _SESSIONS[k][1])]


def _get(session_id: str) -> PracticeSession:
    entry = _SESSIONS.get(session_id)
    if entry is None or time.time() - entry[1] > SESSION_TTL_S:
        raise HTTPException(404, "This practice session has expired. Start a new one.")
    _SESSIONS[session_id] = (entry[0], time.time())
    return entry[0]


def _to_dict(obj: Any) -> dict[str, Any]:
    out = asdict(obj)
    for k, v in list(out.items()):
        if hasattr(v, "value"):
            out[k] = v.value
    return out


@router.post("/sessions")
def create_session(body: CreateSession) -> dict[str, Any]:
    if body.language not in LANGS:
        raise HTTPException(422, f"language must be one of {', '.join(LANGS)}")
    try:
        load_scenario(body.scenario)
        counts = {ErrorCode(k): v for k, v in (body.counts or {}).items()}
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(422, "Unknown scenario or error code.") from exc
    _sweep()
    session = start_session(
        body.scenario, body.language, counts=counts, checked=body.checked, seed=body.seed,
        judge=body.judge,
    )  # fmt: skip
    _SESSIONS[session.id] = (session, time.time())
    loaded = session.loaded
    return {
        "session_id": session.id,
        "seed": session.seed,  # lets her retry with the same children
        "language": session.language,
        "judge": session.judge,
        "children": [{"name": c.name, "shy": c.shy} for c in session.state.children],
        "materials": loaded.scenario.materials,
        "turn_cap": loaded.config.max_turns,
        "moves": [{"id": m.id, "label": m.label[session.language]} for m in loaded.movelist.moves],
    }


@router.post("/sessions/{session_id}/turns")
def post_turn(session_id: str, body: TurnRequest, ctx: CallContext = AI_CONTEXT) -> dict[str, Any]:
    session = _get(session_id)
    try:
        result = take_turn(
            session,
            text=body.text,
            material=body.material,
            stt_confidence=body.stt_confidence,
            context=ctx,
        )
    except SessionFinished as exc:
        raise HTTPException(409, "This rehearsal has finished. Ask for feedback.") from exc
    except BudgetExceeded as exc:
        raise HTTPException(503, "Practice is paused for today. Try again later.") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {**_to_dict(result), "turns_left": session.loaded.config.max_turns - session.state.turn}


@router.post("/sessions/{session_id}/end")
def post_end(session_id: str, ctx: CallContext = AI_CONTEXT) -> dict[str, Any]:
    session = _get(session_id)
    try:
        card, layers = end_session(session, context=ctx)
    except BudgetExceeded as exc:
        raise HTTPException(503, "Feedback is paused for today. Try again later.") from exc
    out = _to_dict(replace(card, gate=None))
    out.pop("gate", None)
    return {
        "card": out,
        "layers": layers,
        "transcript": [
            {"turn": r.turn, "teacher": r.teacher_text, "child": r.child_text, "speaker": r.speaker}
            for r in session.records
        ],
        "explanation": card.gate.explanation if card.gate else "",
    }
