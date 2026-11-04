"""Audio on request: the teacher presses "Download audio" on a part of the intervention pack and the
text she is reading is voiced and sent back as an MP3 file. Nothing is made until she presses it.

The voice comes from the speech layer (Bodhan AI first, Sarvam as the fallback, one narrator for the
whole file: if a provider fails part-way the whole file is made again on the next one). Finished
files and their chunks are cached, so a repeat press costs nothing. Each phone has a character cap
(AUDIO_DOWNLOAD_CHARS_PER_DEVICE, else AUTOPILOT_MAX_TTS_CHARS, else 20000): a repeat that is served
from the cache does not count. The text is our own pack text, never a child's; it is not kept.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from services.api.cohorts.routes import _teacher
from services.api.db import AudioDownloadUse
from services.api.identity import user_of
from services.api.practice import get_speech
from services.api.profiles import SESSION
from services.api.roles import require
from services.media.storage import BlobStore, get_audio_store
from services.speech import lessons
from services.speech.sarvam import SpeechError
from services.speech.service import SpeechService
from services.spoken import normalize
from services.spoken.adapters.intervention import build_script

router = APIRouter(prefix="/api/audio", tags=["audio"])
log = logging.getLogger(__name__)
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,79}$")
MAX_REQUEST_CHARS = 8000
EXPOSE = "Content-Disposition, X-Audio-Seconds, X-Audio-Provider, X-Audio-Chars, X-Audio-Cached"
SPEECH = Depends(get_speech)
STORE = Depends(get_audio_store)


def chars_cap() -> int:
    for var in ("AUDIO_DOWNLOAD_CHARS_PER_DEVICE", "AUTOPILOT_MAX_TTS_CHARS"):
        raw = os.environ.get(var, "").strip()
        if raw.isdigit() and int(raw) > 0:
            return int(raw)
    return 20000


class PackIn(BaseModel):
    """Either `code` (the server builds the spoken script from content and her class's counts) or
    `text` (her own edited spoken text; it still goes through the normaliser)."""

    text: str | None = Field(default=None, min_length=1, max_length=MAX_REQUEST_CHARS)
    language: Literal["en", "hi", "ta"]
    name: str = Field(default="audio", max_length=80)
    code: str | None = Field(default=None, max_length=20)
    children: int = Field(default=0, ge=0, le=200)
    total: int = Field(default=0, ge=0, le=200)
    rolls: dict[str, list[int]] | None = None
    example: dict[str, str] | None = None


def spoken_text(body: PackIn) -> tuple[str, str]:
    """(spoken-ready text, its language). English when the content has no text in the language."""
    if body.text:
        return normalize(body.text, body.language), body.language
    if not body.code or body.children > body.total:
        raise HTTPException(422, "There is no text to voice.")
    try:
        script = build_script(
            body.code, body.language, body.children, body.total, body.rolls, body.example
        )
    except ValueError as exc:
        raise HTTPException(422, "There is no text to voice.") from exc
    return script.text, script.language


def cache_key(text: str, language: str) -> str:
    """The same text, language and narrator give the same key; a change to any of them does not."""
    voices = json.dumps(lessons.lesson_voices().get(language, {}), sort_keys=True)
    plain = re.sub(r"\s+", " ", text).strip()
    return (
        "pack-audio/" + hashlib.sha256(f"{language}|{voices}|{plain}".encode()).hexdigest() + ".mp3"
    )


def _use(db: Session, teacher_id: str) -> AudioDownloadUse:
    row = db.get(AudioDownloadUse, teacher_id)
    if row is None:
        row = AudioDownloadUse(teacher_id=teacher_id, chars=0)
        db.add(row)
    return row


def _reply(
    mp3: bytes, name: str, seconds: float, provider: str, chars: int, cached: bool
) -> Response:
    return Response(
        content=mp3,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f'attachment; filename="{name}.mp3"',
            "X-Audio-Seconds": f"{seconds:.1f}",
            "X-Audio-Provider": provider,
            "X-Audio-Chars": str(chars),
            "X-Audio-Cached": "1" if cached else "0",
            "Access-Control-Expose-Headers": EXPOSE,
            "Cache-Control": "no-store",
        },
    )


@router.post("/pack")
def pack_audio(
    body: PackIn,
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
    speech: SpeechService = SPEECH,
    store: BlobStore = STORE,
) -> Response:
    teacher = _teacher(db, uid)
    name = body.name if NAME.match(body.name) else "audio"
    text, language = spoken_text(body)
    key = cache_key(text, language)
    if store.size(key) is not None:  # a repeat press: no call, no characters used
        return _reply(store.get(key), name, 0.0, "cache", 0, True)
    chars = int(lessons.estimate(text, language)["chars"])
    use = _use(db, teacher.teacher_id)
    if use.chars + chars > chars_cap():
        raise HTTPException(429, {"code": "cap", "message": "The audio limit is reached."})
    try:
        made = lessons.generate(text, language, speech, store, check=False, max_sentences=8)
    except ValueError as exc:
        raise HTTPException(422, "There is no text to voice.") from exc
    except (lessons.LessonAudioUnavailable, SpeechError) as exc:
        log.warning("pack audio: every provider failed (%s)", type(exc).__name__)
        raise HTTPException(
            503, {"code": "unavailable", "message": "Audio is not available."}
        ) from exc
    use.chars += made.chars_billed or chars
    db.commit()
    store.put(key, made.mp3, "audio/mpeg")
    return _reply(made.mp3, name, made.seconds, made.provider, made.chars_billed or chars, False)


@router.post("/pack/script")
def pack_script(body: PackIn, _: str = Depends(require("cohort.chat"))) -> dict[str, Any]:
    """The spoken text she can read and change before it is voiced. Nothing is voiced or billed."""
    text, language = spoken_text(body)
    plain = re.sub(r"\[pause(?::long)?\]", " ", text)
    return {
        "text": text,
        "language": language,
        "fallback": language != body.language,
        "words": len(plain.split()),
    }


@router.get("/pack/cap")
def pack_cap(
    _: str = Depends(require("cohort.chat")),
    uid: str = Depends(user_of),
    db: Session = SESSION,
) -> dict[str, Any]:
    teacher = _teacher(db, uid)
    row = db.get(AudioDownloadUse, teacher.teacher_id)
    return {"cap": chars_cap(), "used": row.chars if row else 0}
