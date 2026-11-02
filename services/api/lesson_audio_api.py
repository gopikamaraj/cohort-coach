"""Lesson audio review over HTTP: the coach listens to a voiced lesson, sees the script with each
sentence's round-trip check, and regenerates one sentence, regenerates the lesson, or approves it.

Reading is for the coach and the officer (`content.review_view`); regenerating and approving are the
coach's (`content.coach_approve`). A lesson whose cohort has fewer than 5 classes is listed without
its script or audio (rule 3). Every action is in the audit trail (services/content/lesson_audio.py).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from services.api.practice import SPEECH
from services.api.profiles import SESSION
from services.api.roles import require
from services.content import lesson_audio
from services.media.storage import BlobStore, get_audio_store
from services.speech import lessons
from services.speech.sarvam import SpeechError

router = APIRouter(prefix="/api/review/lesson-audio", tags=["review"])

VIEW = Depends(require("content.review_view"))
COACH = Depends(require("content.coach_approve"))
AUDIO = Depends(get_audio_store)


def _url(store: BlobStore, rec: lesson_audio.LessonAudioRecord) -> str | None:
    if lesson_audio.hidden(rec) or store.size(rec.audio_key) is None:
        return None
    return store.presign_get(rec.audio_key, expires=900)


def _get(db: Session, rec_id: str) -> lesson_audio.LessonAudioRecord:
    try:
        return lesson_audio.get(db, rec_id)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("")
def list_audio(_: str = VIEW, db: Session = SESSION) -> list[dict[str, Any]]:
    return [
        {
            "id": r.id, "track_id": r.track_id, "language": r.language, "day": r.day,
            "revision": r.revision, "status": r.status, "provider": r.provider,
            "summary": lesson_audio.summary(r), "hidden": lesson_audio.hidden(r),
            "bytes": r.bytes, "seconds": r.seconds,
        }
        for r in lesson_audio.latest_for_review(db)
    ]  # fmt: skip


@router.get("/{rec_id}")
def one(
    rec_id: str, _: str = VIEW, db: Session = SESSION, store: BlobStore = AUDIO
) -> dict[str, Any]:
    rec = _get(db, rec_id)
    return lesson_audio.view(rec, _url(store, rec))


class RegenIn(BaseModel):
    sentence: int | None = Field(default=None, ge=0, le=500)


@router.post("/{rec_id}/regenerate")
def regenerate(
    rec_id: str,
    body: RegenIn,
    role: str = COACH,
    db: Session = SESSION,
    store: BlobStore = AUDIO,
    speech: Any = SPEECH,
) -> dict[str, Any]:
    """A new revision; the published audio stays until the coach approves it."""
    _get(db, rec_id)
    try:
        new = lesson_audio.regenerate(
            db, store, speech, rec_id, sentence=body.sentence, actor=f"{role}-demo", role=role
        )
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except (lessons.LessonAudioUnavailable, SpeechError) as exc:
        raise HTTPException(503, "The voice service is not available. Try again later.") from exc
    return lesson_audio.view(new, _url(store, new))


@router.post("/{rec_id}/approve")
def approve(
    rec_id: str, role: str = COACH, db: Session = SESSION, store: BlobStore = AUDIO
) -> dict[str, Any]:
    _get(db, rec_id)
    try:
        rec = lesson_audio.approve(db, store, rec_id, actor=f"{role}-demo", role=role)
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    return lesson_audio.view(rec, _url(store, rec))
