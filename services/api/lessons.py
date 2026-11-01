"""Lesson audio for the teacher flows: a signed, short-lived link per lesson.

The bot sends the link to Telegram as a voice note and the web app plays it. The link names a
manifest and a part and nothing else; it carries no person. Only audio that a published manifest
lists (so only content both keys switched on) can be served.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.db import TrackManifest
from services.api.flows.links import verify
from services.api.profiles import SESSION
from services.media.storage import BlobStore, get_audio_store

router = APIRouter(prefix="/api/lessons", tags=["lessons"])
AUDIO = Depends(get_audio_store)


@router.get("/audio")
def lesson_audio(t: str, db: Session = SESSION, store: BlobStore = AUDIO) -> Response:
    facts = verify(t)
    if not facts or "m" not in facts or "p" not in facts:
        raise HTTPException(404, "This lesson link has ended. Ask the bot for a new one.")
    manifest = db.execute(
        select(TrackManifest).where(TrackManifest.id == int(facts["m"]))
    ).scalar_one_or_none()
    part = next(
        (
            p
            for p in (manifest.body.get("parts", []) if manifest else [])
            if p.get("id") == facts["p"]
        ),
        None,
    )
    if part is None or not part.get("audio_key"):
        raise HTTPException(404, "This lesson has no audio.")
    return Response(
        store.get(str(part["audio_key"])),
        media_type=str(part.get("mime") or "audio/ogg"),
        headers={"Cache-Control": "private, max-age=86400"},
    )
