"""HTTP for the two-class run (judge deployment only, like Demo Studio). `as` names who is acting:
T1 and T2 (the two teachers), T3 (a teacher outside the cohort), C1 (the coach), M1 (the cohort's
mentor), M2 (another mentor) or officer. Every answer is labelled simulated unless the run is the
local pilot run."""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ai.client import CallContext
from engine.model import ErrorCode
from services.api.cohorts.thread import NotMember, PostRejected, ThreadClosed
from services.api.practice import AI_CONTEXT, SPEECH
from services.api.profiles import SESSION
from services.api.roles import judge_session
from services.cohort_run import scenario as sc
from services.cohort_run import service as svc
from services.cohort_run.models import CohortRun

RUN_RE = re.compile(r"^run-[0-9a-f]{16}$")
CODES = {c.value for c in ErrorCode}


def _judge() -> None:
    if not judge_session():
        raise HTTPException(404, "The two-class run is part of the judge deployment.")


router = APIRouter(prefix="/api/cohort-run", tags=["cohort-run"], dependencies=[Depends(_judge)])


def _run(db: Session, rid: str) -> CohortRun:
    if not RUN_RE.match(rid):
        raise HTTPException(422, "Bad run id.")
    row = db.get(CohortRun, rid)
    if row is None:
        raise HTTPException(404, "Start the run first.")
    return row


def _call(fn: Any, *args: Any, **kwargs: Any) -> Any:
    from services.api.cohorts import lifecycle
    from services.chat import service as chat
    from services.content import review, versions

    try:
        return fn(*args, **kwargs)
    except (svc.NotAllowed, NotMember, versions.NotAllowed) as exc:
        raise HTTPException(403, str(exc) or "Not allowed.") from exc
    except LookupError as exc:
        raise HTTPException(409, str(exc)) from exc
    except (chat.BadState, versions.BadState, lifecycle.BadTransition, ThreadClosed) as exc:
        raise HTTPException(409, str(exc)) from exc
    except (PostRejected, review.EditBlocked) as exc:
        raise HTTPException(422, "That text was held by a check. Change it and try again.") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


class StartIn(BaseModel):
    run: str = Field(pattern=RUN_RE.pattern)
    scenario: str = Field(default=sc.DEFAULT, pattern=r"^[a-z0-9_]{3,40}$")


@router.post("/runs")
def start(body: StartIn, db: Session = SESSION) -> dict[str, Any]:
    row = _call(svc.new_run, db, body.run, body.scenario)
    return svc.view(db, row, "C1")


@router.delete("/runs/{rid}")
def reset(rid: str, db: Session = SESSION) -> dict[str, Any]:
    svc.reset(db, _run(db, rid))
    return {"reset": True}


@router.get("/runs/{rid}")
def view(rid: str, as_: str = Query("C1", alias="as"), db: Session = SESSION) -> dict[str, Any]:
    return dict(_call(svc.view, db, _run(db, rid), as_))


class CheckIn(BaseModel):
    """Counts only: anything else (a per-child row, a roll number, a name) is refused."""

    model_config = ConfigDict(extra="forbid")
    as_: str = Field(alias="as", pattern=r"^T[12]$")
    synthetic: bool = True
    children_checked: int | None = Field(default=None, ge=1, le=200)
    counts: dict[str, int] = Field(default_factory=dict)
    possible: dict[str, int] = Field(default_factory=dict)


@router.post("/runs/{rid}/classes/{code}/check")
def submit_check(
    rid: str,
    code: str,
    body: CheckIn,
    db: Session = SESSION,
    ctx: CallContext = AI_CONTEXT,
    speech: Any = SPEECH,
) -> dict[str, Any]:
    row = _run(db, rid)
    scn = svc.scenario_of(row)
    if code not in {c["code"] for c in scn["classes"]}:
        raise HTTPException(404, "No such class in this run.")
    counts = None
    if not body.synthetic:
        if body.children_checked is None:
            raise HTTPException(422, "Send the number of children checked.")
        if set(body.counts) - CODES or set(body.possible) - CODES:
            raise HTTPException(422, "Counts may only name the tracked error codes.")
        if any(
            v < 0 or v > body.children_checked
            for v in [*body.counts.values(), *body.possible.values()]
        ):
            raise HTTPException(422, "A count cannot exceed the number of children checked.")
        teacher = str(sc.class_of(scn, code)["teacher"])
        counts = sc.ClassCounts(
            code,
            teacher,
            str(scn["teachers"][teacher]["language"]),
            int(scn["grade"]),
            str(scn["medium"]),
            body.children_checked,
            body.counts,
            body.possible,
            "phone",
        )
    _call(svc.submit_check, db, row, code, body.as_, counts, ctx, speech)
    return dict(svc.view(db, row, body.as_))


@router.post("/runs/{rid}/form")
def form_now(
    rid: str, db: Session = SESSION, ctx: CallContext = AI_CONTEXT, speech: Any = SPEECH
) -> dict[str, Any]:
    row = _run(db, rid)
    _call(svc.form_now, db, row, ctx, speech, "coach")
    return dict(svc.view(db, row, "C1"))


class DecideIn(BaseModel):
    decision: str = Field(pattern=r"^(approve|reject)$")
    reason: str | None = Field(default=None, max_length=40)


@router.post("/runs/{rid}/lessons/{lid}/decide")
def decide(rid: str, lid: str, body: DecideIn, db: Session = SESSION) -> dict[str, Any]:
    row = _run(db, rid)
    _call(svc.coach_decide, db, row, lid, body.decision, body.reason)
    return dict(svc.view(db, row, "C1"))


class AsIn(BaseModel):
    as_: str = Field(alias="as", pattern=r"^T[123]$")


@router.post("/runs/{rid}/lessons/{lid}/voice")
def retry_voice(
    rid: str, lid: str, body: AsIn, db: Session = SESSION, speech: Any = SPEECH
) -> dict[str, Any]:
    row = _run(db, rid)
    _call(svc.voice, db, row, lid, body.as_, speech)
    return dict(svc.view(db, row, body.as_))


@router.get("/runs/{rid}/lessons/{lid}/audio")
def audio(
    rid: str, lid: str, as_: str = Query(alias="as"), download: bool = False, db: Session = SESSION
) -> Response:
    row = _run(db, rid)
    if not re.match(r"^T[12]$", as_):
        raise HTTPException(403, "Only the lesson's teacher can play it.")
    lesson = _call(svc._lesson, row.state or {}, lid)
    if as_ not in lesson["audience"] or svc.lesson_status(db, lesson) != "released":
        raise HTTPException(403, "This lesson is not released to you.")
    path = svc.audio_path(row, lid, as_)
    if path is None or not path.exists():
        raise HTTPException(404, "No audio for this lesson. The text is on the screen.")
    mime = {"ogg": "audio/ogg", "mp3": "audio/mpeg", "m4a": "audio/mp4"}.get(
        path.suffix[1:], "audio/mpeg"
    )
    headers = {"Cache-Control": "private, max-age=86400"}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="lesson-{lid}{path.suffix}"'
    return Response(path.read_bytes(), media_type=mime, headers=headers)


class PlayIn(AsIn):
    heard: bool = False


@router.post("/runs/{rid}/lessons/{lid}/played")
def played(rid: str, lid: str, body: PlayIn, db: Session = SESSION) -> dict[str, Any]:
    row = _run(db, rid)
    _call(svc.played, db, row, lid, body.as_, body.heard)
    return dict(svc.view(db, row, body.as_))


class FeedbackIn(AsIn):
    answer: str = Field(pattern=r"^(tried|partly|not_yet)$")
    note: str = Field(default="", max_length=300)


@router.post("/runs/{rid}/lessons/{lid}/feedback")
def feedback(rid: str, lid: str, body: FeedbackIn, db: Session = SESSION) -> dict[str, Any]:
    row = _run(db, rid)
    _call(svc.give_feedback, db, row, lid, body.as_, body.answer, body.note)
    return dict(svc.view(db, row, body.as_))


class NextIn(BaseModel):
    as_: str = Field(alias="as", pattern=r"^(T[12]|C1)$")
    teacher: str | None = Field(default=None, pattern=r"^T[12]$")


@router.post("/runs/{rid}/next")
def generate_next(
    rid: str,
    body: NextIn,
    db: Session = SESSION,
    ctx: CallContext = AI_CONTEXT,
    speech: Any = SPEECH,
) -> dict[str, Any]:
    """Generate next lesson: the teacher for herself after her feedback, or the coach for one of
    the cohort's teachers."""
    row = _run(db, rid)
    teacher = body.as_ if body.as_ != "C1" else body.teacher
    if teacher is None:
        raise HTTPException(422, "Name the teacher.")
    out = _call(
        svc.generate_next, db, row, teacher, "coach" if body.as_ == "C1" else "teacher", ctx, speech
    )
    return {"next": out, **svc.view(db, row, body.as_)}


class TickIn(BaseModel):
    days: int = Field(ge=1, le=14)


@router.post("/runs/{rid}/tick")
def tick(
    rid: str,
    body: TickIn,
    db: Session = SESSION,
    ctx: CallContext = AI_CONTEXT,
    speech: Any = SPEECH,
) -> dict[str, Any]:
    row = _run(db, rid)
    made = _call(svc.tick, db, row, body.days, ctx, speech)
    return {"made": made, **svc.view(db, row, "C1")}


class AskIn(AsIn):
    text: str = Field(min_length=3, max_length=500)
    share: bool = False


@router.post("/runs/{rid}/chat/ask")
def ask(
    rid: str, body: AskIn, db: Session = SESSION, ctx: CallContext = AI_CONTEXT
) -> dict[str, Any]:
    row = _run(db, rid)
    return dict(_call(svc.ask, db, row, body.as_, body.text, body.share, ctx))


@router.get("/runs/{rid}/chat")
def chat_view(rid: str, as_: str = Query(alias="as"), db: Session = SESSION) -> dict[str, Any]:
    row = _run(db, rid)
    if not re.match(r"^T[123]$", as_):
        raise HTTPException(403, "The coach's side is the inbox.")
    return dict(_call(svc.chat_view, db, row, as_))


@router.post("/runs/{rid}/chat/skip")
def skip(rid: str, db: Session = SESSION) -> dict[str, Any]:
    row = _run(db, rid)
    tick_out = _call(svc.skip_wait, db, row)
    return {"tick": tick_out, **svc.view(db, row, "C1")}


class ReplyIn(BaseModel):
    mode: str = Field(pattern=r"^(as_is|edit|own)$")
    text: str | None = Field(default=None, max_length=1000)
    tags: list[str] = Field(default_factory=list, max_length=5)


@router.post("/runs/{rid}/chat/{message_id}/reply")
def reply(rid: str, message_id: str, body: ReplyIn, db: Session = SESSION) -> dict[str, Any]:
    row = _run(db, rid)
    _call(svc.coach_reply, db, row, message_id, body.mode, body.text, tuple(body.tags))
    return dict(svc.view(db, row, "C1"))


class CorrectIn(BaseModel):
    text: str = Field(min_length=3, max_length=1000)
    tags: list[str] = Field(min_length=1, max_length=5)


@router.post("/runs/{rid}/chat/answers/{answer_id}/correct")
def correct(rid: str, answer_id: str, body: CorrectIn, db: Session = SESSION) -> dict[str, Any]:
    row = _run(db, rid)
    _call(svc.coach_correct, db, row, answer_id, body.text, tuple(body.tags))
    return dict(svc.view(db, row, "C1"))
