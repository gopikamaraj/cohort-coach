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
from services.api.profiles import SESSION
from services.api.roles import require
from services.modules import jobs, review, service
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
}


def clock() -> datetime:
    """The one place the app reads the time; tests replace it."""
    return datetime.now(UTC)


def _raise(exc: ModulesError) -> HTTPException:
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


class DownloadedIn(BaseModel):
    audio_ref: str = Field(min_length=1, max_length=120)


@router.post("/tracks")
def start(
    body: StartIn,
    _: str = Depends(require("cohort.chat")),
    x_device_id: str | None = Header(default=None),
    db: Session = SESSION,
) -> dict[str, Any]:
    teacher = _teacher(db, x_device_id)
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
    x_device_id: str | None = Header(default=None),
    db: Session = SESSION,
) -> list[dict[str, Any]]:
    teacher = _teacher(db, x_device_id)
    return [
        service.track_view(db, t, lang, clock())
        for t in service.tracks_of(db, teacher.teacher_id, cohort_id)
    ]


def _own(db: Session, track_id: str, x_device_id: str | None) -> Any:
    teacher = _teacher(db, x_device_id)
    try:
        return service._owned(db, track_id, teacher.teacher_id), teacher
    except ModulesError as exc:
        raise _raise(exc) from exc


@router.get("/tracks/{track_id}")
def one(
    track_id: str,
    lang: str = "en",
    _: str = Depends(require("cohort.chat")),
    x_device_id: str | None = Header(default=None),
    db: Session = SESSION,
) -> dict[str, Any]:
    track, _t = _own(db, track_id, x_device_id)
    return service.track_view(db, track, lang, clock())


@router.post("/tracks/{track_id}/next")
def get_next(
    track_id: str,
    lang: str = "en",
    _: str = Depends(require("cohort.chat")),
    x_device_id: str | None = Header(default=None),
    db: Session = SESSION,
) -> dict[str, Any]:
    track, teacher = _own(db, track_id, x_device_id)
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
    x_device_id: str | None = Header(default=None),
    db: Session = SESSION,
) -> dict[str, Any]:
    track, teacher = _own(db, track_id, x_device_id)
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
    x_device_id: str | None = Header(default=None),
    db: Session = SESSION,
) -> dict[str, Any]:
    """Why not yet?: one approved reason chip for a module she has not tried (private to her)."""
    track, teacher = _own(db, track_id, x_device_id)
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
    x_device_id: str | None = Header(default=None),
    db: Session = SESSION,
) -> dict[str, Any]:
    track, _t = _own(db, track_id, x_device_id)
    return review.view(db, _module(db, track, number), lang)


@router.post("/tracks/{track_id}/modules/{number}/review")
def review_run(
    track_id: str,
    number: int,
    lang: str = "en",
    _: str = Depends(require("cohort.chat")),
    x_device_id: str | None = Header(default=None),
    db: Session = SESSION,
) -> dict[str, Any]:
    """After her answer: the AI review of her note (call 17). Never blocks and never fails the page: AI
    off or any failure gives state "none" or "failed", and only the branch table applies."""
    track, _t = _own(db, track_id, x_device_id)
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
    x_device_id: str | None = Header(default=None),
    db: Session = SESSION,
) -> dict[str, Any]:
    track, _t = _own(db, track_id, x_device_id)
    module = _module(db, track, number)
    try:
        review.answer_follow_ups(
            db, module, [a.model_dump() for a in body.answers], body.skip, lang
        )
    except ModulesError as exc:
        raise _raise(exc) from exc
    return review.view(db, module, lang)


@router.post("/tracks/{track_id}/modules/{number}/downloaded")
def downloaded(
    track_id: str,
    number: int,
    body: DownloadedIn,
    lang: str = "en",
    _: str = Depends(require("cohort.chat")),
    x_device_id: str | None = Header(default=None),
    db: Session = SESSION,
) -> dict[str, Any]:
    track, teacher = _own(db, track_id, x_device_id)
    try:
        service.mark_downloaded(db, track_id, number, teacher.teacher_id, body.audio_ref, clock())
    except ModulesError as exc:
        raise _raise(exc) from exc
    db.refresh(track)
    return service.track_view(db, track, lang, clock())


# ---- coach ---------------------------------------------------------------------------------------


class ShiftIn(BaseModel):
    days: int = Field(ge=-60, le=60)
    reason: str = Field(min_length=1, max_length=120)


class DueIn(BaseModel):
    due_date: date
    reason: str = Field(min_length=1, max_length=120)


@router.get("/coach/cohorts/{cohort_id}")
def coach_counts(
    cohort_id: str, _: str = Depends(require("coach.moderate")), db: Session = SESSION
) -> dict[str, Any]:
    return service.coach_counts(db, cohort_id, clock())


@router.post("/coach/cohorts/{cohort_id}/shift")
def coach_shift(
    cohort_id: str,
    body: ShiftIn,
    _: str = Depends(require("coach.moderate")),
    db: Session = SESSION,
) -> dict[str, Any]:
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
    db: Session = SESSION,
) -> dict[str, Any]:
    from sqlalchemy import select

    from services.modules.models import Track

    tracks = list(db.execute(select(Track).where(Track.class_cohort_id == cohort_id)).scalars())
    if not tracks:
        raise HTTPException(
            404, {"code": "no_track", "message": "There is no track for this cohort."}
        )
    try:
        for t in tracks:
            service.set_due_date(db, t.id, number, body.due_date, body.reason, clock())
    except ModulesError as exc:
        raise _raise(exc) from exc
    return service.coach_counts(db, cohort_id, clock())


@router.post("/coach/cohorts/{cohort_id}/generate")
def coach_generate(
    cohort_id: str, _: str = Depends(require("coach.moderate")), db: Session = SESSION
) -> dict[str, Any]:
    """Make the next module for every active track of the cohort (audited as trigger "coach")."""
    from sqlalchemy import select

    from services.modules.models import Track

    made = 0
    for t in db.execute(
        select(Track).where(Track.class_cohort_id == cohort_id, Track.status == "active")
    ).scalars():
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
