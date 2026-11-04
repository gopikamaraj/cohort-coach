# ruff: noqa: E501
"""HTTP for improvement tracks. A teacher sees only her own tracks; a coach sees counts per module,
never a teacher id. The daily job can also be run through `POST /api/modules/jobs/due` (secured by
MODULES_JOB_TOKEN, for Cloud Scheduler); in development, `MODULES_INPROCESS_JOB=1` runs it from the app."""

from __future__ import annotations

import os
from datetime import UTC, date, datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from services.api.cohorts.routes import _teacher
from services.api.db import ClassCohort
from services.api.identity import user_of
from services.api.profiles import SESSION
from services.api.roles import require
from services.modules import checkin, jobs, review, service
from services.modules.models import ModuleFeedback
from services.modules.service import ModulesError

router = APIRouter(prefix="/api/modules", tags=["modules"])
LANG = r"^(en|hi|ta)$"
STATUS = {
    "no_track": 404,
    "not_hers": 403,
    "needs_feedback": 409,
    "not_ready": 409,
    "not_made": 409,
    "fixed_date": 409,
    "not_held": 409,
    "share_closed": 409,
    "no_peers": 409,
    "thread_closed": 409,
    "not_shared": 409,
    "not_needed": 409,
    "no_answer": 409,
}


def clock() -> datetime:
    """The one place the app reads the time; tests replace it."""
    return datetime.now(UTC)


def _raise(exc: ModulesError) -> HTTPException:
    if exc.code.startswith("blocked:"):  # Share is blocked: say what to remove
        return HTTPException(
            422,
            {
                "code": "blocked",
                "problems": exc.code.split(":", 1)[1].split(","),
                "message": str(exc),
            },
        )
    return HTTPException(STATUS.get(exc.code, 422), {"code": exc.code, "message": str(exc)})


class StartIn(BaseModel):
    cohort_id: str = Field(max_length=40)
    error: str = Field(pattern=r"^[A-Z0-9-]{3,16}$")
    language: str = Field(default="en", pattern=LANG)
    end_date: date | None = None


class FeedbackIn(BaseModel):
    answer: str
    note: str = Field(default="", max_length=400)


class WhyIn(BaseModel):
    chip: str = Field(max_length=12)


class FollowUpAnswer(BaseModel):
    id: str = Field(max_length=40)
    chip: str | None = Field(default=None, max_length=20)
    text: str | None = Field(default=None, max_length=200)


class ReviewAnswersIn(BaseModel):
    answers: list[FollowUpAnswer] = Field(default_factory=list, max_length=2)
    skip: bool = False


class DraftIn(BaseModel):
    fields: dict[str, bool] | None = None
    text: str | None = Field(default=None, max_length=1500)


class ShareIn(BaseModel):
    text: str = Field(min_length=1, max_length=1500)
    fields: dict[str, bool] | None = None
    named: bool = False
    ai_help: bool = False


def _assigned(db: Session, uid: str, role: str, cohort_id: str) -> None:
    """A coach or mentor reaches a cohort's plan only if the cohort is assigned to her."""
    from services.api.cohorts.assign import is_assigned

    if not is_assigned(db, uid, role, cohort_id):
        raise HTTPException(403, {"code": "not_assigned", "message": "This cohort is not assigned to you."})


class DownloadedIn(BaseModel):
    audio_ref: str = Field(min_length=1, max_length=120)


@router.post("/tracks")
def start(
    body: StartIn,
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, Any]:
    teacher = _teacher(db, uid)
    cohort = db.get(ClassCohort, body.cohort_id)
    if cohort is None or cohort.teacher_id != teacher.teacher_id:
        raise HTTPException(404, {"code": "no_cohort", "message": "There is no such cohort."})
    try:
        track = service.start_track(db, cohort, body.error, body.language, clock(), body.end_date)
    except ModulesError as exc:
        raise _raise(exc) from exc
    return service.track_view(db, track, body.language, clock())


@router.get("/tracks")
def mine(
    cohort_id: str | None = None,
    lang: str = "en",
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> list[dict[str, Any]]:
    teacher = _teacher(db, uid)
    return [
        service.track_view(db, t, lang, clock())
        for t in service.tracks_of(db, teacher.teacher_id, cohort_id)
    ]


def _own(db: Session, track_id: str, uid: str) -> Any:
    teacher = _teacher(db, uid)
    try:
        return service._owned(db, track_id, teacher.teacher_id), teacher
    except ModulesError as exc:
        raise _raise(exc) from exc


@router.get("/tracks/{track_id}")
def one(
    track_id: str,
    lang: str = "en",
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, Any]:
    track, _t = _own(db, track_id, uid)
    return service.track_view(db, track, lang, clock())


@router.post("/tracks/{track_id}/next")
def get_next(
    track_id: str,
    lang: str = "en",
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, Any]:
    track, teacher = _own(db, track_id, uid)
    try:
        service.next_for_teacher(db, track_id, teacher.teacher_id, clock())
    except ModulesError as exc:
        raise _raise(exc) from exc
    db.refresh(track)
    return service.track_view(db, track, lang, clock())


@router.post("/tracks/{track_id}/modules/{number}/feedback")
def feedback(
    track_id: str,
    number: int,
    body: FeedbackIn,
    lang: str = "en",
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, Any]:
    track, teacher = _own(db, track_id, uid)
    try:
        service.give_feedback(
            db, track_id, number, teacher.teacher_id, body.answer, body.note, clock()
        )
    except ModulesError as exc:
        raise _raise(exc) from exc
    db.refresh(track)
    return service.track_view(db, track, lang, clock())


@router.post("/tracks/{track_id}/modules/{number}/why")
def why_not_yet(
    track_id: str,
    number: int,
    body: WhyIn,
    lang: str = "en",
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, Any]:
    """Why not yet?: one approved reason chip for a module she has not tried (private to her)."""
    track, teacher = _own(db, track_id, uid)
    try:
        service.record_reason(db, track_id, number, teacher.teacher_id, body.chip, clock())
    except ModulesError as exc:
        raise _raise(exc) from exc
    db.refresh(track)
    return service.track_view(db, track, lang, clock())


def _module(db: Session, track: Any, number: int) -> Any:
    m = service._by_number(db, track.id, number)
    if m.status in ("planned", "skipped"):
        raise HTTPException(409, {"code": "not_made", "message": "That module is not made yet."})
    return m


@router.get("/tracks/{track_id}/modules/{number}/review")
def review_view(
    track_id: str,
    number: int,
    lang: str = "en",
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, Any]:
    track, _t = _own(db, track_id, uid)
    return review.view(db, _module(db, track, number), lang)


@router.post("/tracks/{track_id}/modules/{number}/review")
def review_run(
    track_id: str,
    number: int,
    lang: str = "en",
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, Any]:
    """After her answer: the AI review of her note (call 17). Never blocks and never fails the page: AI
    off or any failure gives state "none" or "failed", and only the branch table applies."""
    track, _t = _own(db, track_id, uid)
    module = _module(db, track, number)
    fb = db.get(ModuleFeedback, module.id)
    if fb is None:
        raise HTTPException(409, {"code": "no_answer", "message": "Give your answer first."})
    review.run(db, track, module, fb.answer, fb.note, lang)
    return review.view(db, module, lang)


@router.post("/tracks/{track_id}/modules/{number}/review/answers")
def review_answers(
    track_id: str,
    number: int,
    body: ReviewAnswersIn,
    lang: str = "en",
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, Any]:
    track, _t = _own(db, track_id, uid)
    module = _module(db, track, number)
    try:
        review.answer_follow_ups(
            db, module, [a.model_dump() for a in body.answers], body.skip, lang
        )
    except ModulesError as exc:
        raise _raise(exc) from exc
    return review.view(db, module, lang)


# ---- the private check-in, and sharing a summary --------------------------------------------------


def _since(since: str | None) -> datetime | None:
    if not since:
        return None
    try:
        t = datetime.fromisoformat(since.replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=UTC)


@router.get("/tracks/{track_id}/chat")
def chat_button(
    track_id: str,
    since: str | None = None,
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, Any]:
    """For the Open cohort chat button: whether there is a chat, and how many new posts since `since`."""
    track, teacher = _own(db, track_id, uid)
    return checkin.chat_state(db, teacher.teacher_id, track, _since(since))


@router.get("/tracks/{track_id}/modules/{number}/checkin")
def checkin_state(
    track_id: str,
    number: int,
    lang: str = "en",
    since: str | None = None,
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, Any]:
    track, teacher = _own(db, track_id, uid)
    return checkin.state(
        db, track, _module(db, track, number), teacher.teacher_id, lang, _since(since)
    )


@router.post("/tracks/{track_id}/modules/{number}/checkin/draft")
def checkin_draft(
    track_id: str,
    number: int,
    body: DraftIn,
    lang: str = "en",
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, Any]:
    """The exact text that would be posted (built by code from the ticked parts), and what would block it.
    With `text` it only checks her edited text."""
    track, _t = _own(db, track_id, uid)
    module = _module(db, track, number)
    text = (
        body.text
        if body.text is not None
        else checkin.build_draft(db, track, module, body.fields, lang)
    )
    return {"text": text, "problems": checkin.problems(text, lang) if text else []}


@router.post("/tracks/{track_id}/modules/{number}/checkin/share")
def checkin_share(
    track_id: str,
    number: int,
    body: ShareIn,
    lang: str = "en",
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, Any]:
    track, teacher = _own(db, track_id, uid)
    module = _module(db, track, number)
    try:
        checkin.share(
            db,
            track,
            module,
            teacher.teacher_id,
            text=body.text,
            fields=body.fields,
            named=body.named,
            ai_help=body.ai_help,
            lang=lang,
            now=clock(),
        )
    except ModulesError as exc:
        raise _raise(exc) from exc
    return checkin.state(db, track, module, teacher.teacher_id, lang)


@router.post("/tracks/{track_id}/modules/{number}/checkin/retract")
def checkin_retract(
    track_id: str,
    number: int,
    lang: str = "en",
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, Any]:
    track, teacher = _own(db, track_id, uid)
    module = _module(db, track, number)
    try:
        checkin.retract(db, track, module, teacher.teacher_id, clock())
    except ModulesError as exc:
        raise _raise(exc) from exc
    return checkin.state(db, track, module, teacher.teacher_id, lang)


@router.post("/tracks/{track_id}/modules/{number}/checkin/call-me")
def checkin_call_me(
    track_id: str,
    number: int,
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, str]:
    """The only way the coach hears of a safety flag: she presses this. No content is sent."""
    track, _t = _own(db, track_id, uid)
    try:
        checkin.call_me(db, track, _module(db, track, number), clock())
    except ModulesError as exc:
        raise _raise(exc) from exc
    return {"status": "your coach has been asked to call you"}


@router.get("/mentor/cohorts/{cohort_id}")
def mentor_counts(
    cohort_id: str, _: str = Depends(require("mentor.items_view")), uid: str = Depends(user_of), db: Session = SESSION
) -> dict[str, Any]:
    """Counts of answers per module, never a note (a note is only ever seen if she shared it in the chat)."""
    _assigned(db, uid, "mentor", cohort_id)
    return service.coach_counts(db, cohort_id, clock())


@router.post("/tracks/{track_id}/modules/{number}/downloaded")
def downloaded(
    track_id: str,
    number: int,
    body: DownloadedIn,
    lang: str = "en",
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, Any]:
    track, teacher = _own(db, track_id, uid)
    try:
        service.mark_downloaded(db, track_id, number, teacher.teacher_id, body.audio_ref, clock())
    except ModulesError as exc:
        raise _raise(exc) from exc
    db.refresh(track)
    return service.track_view(db, track, lang, clock())


@router.post("/tracks/{track_id}/modules/{number}/played")
def played(
    track_id: str,
    number: int,
    lang: str = "en",
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, Any]:
    """The module's audio was started in the browser player. Recorded once; the module's view then says `played`."""
    track, teacher = _own(db, track_id, uid)
    try:
        service.mark_played(db, track_id, number, teacher.teacher_id, clock())
    except ModulesError as exc:
        raise _raise(exc) from exc
    db.refresh(track)
    return service.track_view(db, track, lang, clock())


@router.post("/tracks/{track_id}/generate-all")
def generate_all(
    track_id: str,
    lang: str = "en",
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, Any]:
    """Testing only: DEV_TESTING=1 on the server, a 404 anywhere else."""
    from ai.config import dev_testing

    if not dev_testing():
        raise HTTPException(status_code=404, detail="not found")
    track, teacher = _own(db, track_id, uid)
    try:
        service.generate_all_for_testing(db, track_id, teacher.teacher_id, clock())
    except ModulesError as exc:
        raise _raise(exc) from exc
    db.refresh(track)
    return service.track_view(db, track, lang, clock())


@router.post("/tracks/{track_id}/modules/{number}/narration/refresh")
def narration_refresh(
    track_id: str,
    number: int,
    lang: str = "en",
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, Any]:
    """Testing only: DEV_TESTING=1 on the server, a 404 anywhere else."""
    from ai.config import dev_testing

    if not dev_testing():
        raise HTTPException(status_code=404, detail="not found")
    track, teacher = _own(db, track_id, uid)
    try:
        total = len([m for m in service.modules_of(db, track.id) if m.status != "skipped"])
        reworded = service.refresh_narration(db, track_id, number, teacher.teacher_id, lang, total)
    except ModulesError as exc:
        raise _raise(exc) from exc
    db.refresh(track)
    return {"reworded": reworded, "track": service.track_view(db, track, lang, clock())}


# ---- coach ---------------------------------------------------------------------------------------


class ShiftIn(BaseModel):
    days: int = Field(ge=-60, le=60)
    reason: str = Field(min_length=1, max_length=120)


class DueIn(BaseModel):
    due_date: date
    reason: str = Field(min_length=1, max_length=120)


@router.get("/coach/cohorts/{cohort_id}")
def coach_counts(
    cohort_id: str, _: str = Depends(require("coach.moderate")), uid: str = Depends(user_of), db: Session = SESSION
) -> dict[str, Any]:
    _assigned(db, uid, "coach", cohort_id)
    return service.coach_counts(db, cohort_id, clock())


@router.post("/coach/cohorts/{cohort_id}/shift")
def coach_shift(
    cohort_id: str,
    body: ShiftIn,
    _: str = Depends(require("coach.moderate")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, Any]:
    _assigned(db, uid, "coach", cohort_id)
    try:
        moved = service.shift_dates(db, cohort_id, body.days, body.reason, clock())
    except ModulesError as exc:
        raise _raise(exc) from exc
    return {"moved": moved, **service.coach_counts(db, cohort_id, clock())}


@router.post("/coach/cohorts/{cohort_id}/modules/{number}/due")
def coach_due(
    cohort_id: str,
    number: int,
    body: DueIn,
    _: str = Depends(require("coach.moderate")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, Any]:
    from services.modules import plans

    _assigned(db, uid, "coach", cohort_id)
    tracks = plans.tracks_in_group(db, cohort_id)
    if not tracks:
        raise HTTPException(
            404, {"code": "no_track", "message": "There is no track for this cohort."}
        )
    try:
        plans.set_plan_due(db, cohort_id, number, body.due_date)
        for t in tracks:
            service.set_due_date(db, t.id, number, body.due_date, body.reason, clock())
    except ModulesError as exc:
        raise _raise(exc) from exc
    return service.coach_counts(db, cohort_id, clock())


@router.post("/coach/cohorts/{cohort_id}/generate")
def coach_generate(
    cohort_id: str, _: str = Depends(require("coach.moderate")), uid: str = Depends(user_of), db: Session = SESSION
) -> dict[str, Any]:
    """Make the next module for every active track of the cohort (audited as trigger "coach")."""
    from services.modules import plans

    _assigned(db, uid, "coach", cohort_id)

    made = 0
    for t in plans.tracks_in_group(db, cohort_id):
        if t.status != "active":
            continue
        try:
            if service.coach_generate(db, t.id, clock()).created:
                made += 1
        except ModulesError:
            continue
    return {"generated": made, **service.coach_counts(db, cohort_id, clock())}


# ---- the daily job over HTTP ---------------------------------------------------------------------


@router.post("/jobs/due")
def job_due(
    x_job_token: str | None = Header(default=None), db: Session = SESSION
) -> dict[str, Any]:
    """For Cloud Scheduler, 06:00 Asia/Kolkata. Off unless MODULES_JOB_TOKEN is set."""
    token = os.environ.get("MODULES_JOB_TOKEN", "")
    if not token or x_job_token != token:
        raise HTTPException(403, "Not allowed.")
    from sqlalchemy.orm import sessionmaker

    return jobs.run_due(sessionmaker(db.get_bind(), expire_on_commit=False), clock())
