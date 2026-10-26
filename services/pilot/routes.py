"""The pilot API. In pilot mode these routes (and /api/health) are the only ones mounted.

Every route but sign-in and the signed-blob endpoints needs a token and a permission from
services/api/roles/permissions.yaml. Nothing here computes a number about a class: counts come
from the engine, drafts from the chain in lessons.py, and the gates are the existing ones.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ai import config
from ai.client import CallContext
from ai.guard.rejections import RejectionReason
from services.api.practice import AI_CONTEXT, SPEECH
from services.api.profiles import SESSION, _factory
from services.api.roles import require
from services.pilot import audio as audio_mod
from services.pilot import lessons, sheets
from services.pilot.auth import Principal, current_principal, sign_in
from services.pilot.common import (
    DEFAULT_AUDIO_COUNT,
    LANGUAGES,
    MAX_RETENTION_DAYS,
    MIN_RETENTION_DAYS,
    audio_count,
    audit,
    retention_days,
    set_setting,
)
from services.pilot.storage import (
    BlobStore,
    LocalBlobStore,
    get_audio_store,
    get_sheets_store,
)
from services.speech.service import SpeechService

router = APIRouter(prefix="/api/pilot", tags=["pilot"])

MIN_CLASSES_SHOWN = (
    5  # CLAUDE.md rule 3: a figure over fewer than 5 classes is hidden from officers
)

SHEETS = Depends(get_sheets_store)
AUDIO = Depends(get_audio_store)
ACTOR = Depends(current_principal)


def get_factory() -> Callable[[], Session]:
    """A session factory for work that outlives the request (reading a sheet in the background)."""
    return _factory()


FACTORY = Depends(get_factory)


# ---- sign-in ----------------------------------------------------------------------------------


class SignInIn(BaseModel):
    name: str = Field(max_length=24)
    key: str = Field(max_length=128)


@router.post("/auth/signin")
def signin(body: SignInIn) -> dict[str, Any]:
    token, principal = sign_in(body.name, body.key)
    return {"token": token, "name": principal.name, "roles": list(principal.roles)}


@router.get("/auth/me")
def me(principal: Principal = ACTOR) -> dict[str, Any]:
    from services.api.roles import config as role_config

    cfg = role_config()
    can = sorted(
        {p for r in principal.roles for p in cfg["roles"][r]["can"] if p.startswith("pilot.")}
    )
    return {"name": principal.name, "roles": list(principal.roles), "can": can}


# ---- settings ---------------------------------------------------------------------------------


@router.get("/config", dependencies=[Depends(require("pilot.audio_view"))])
def get_config(db: Session = SESSION) -> dict[str, Any]:
    return {
        "audio_count": audio_count(db),
        "audio_default": DEFAULT_AUDIO_COUNT,
        "audio_max": config.pilot_audio_max(),
        "retention_days": retention_days(db),
        "retention_range": [MIN_RETENTION_DAYS, MAX_RETENTION_DAYS],
        "languages": list(LANGUAGES),
        "voices": audio_mod.voice_options()["voices"],
        "voice_default": audio_mod.voice_options()["default"],
        "share_link_hours": audio_mod.LINK_HOURS,
    }


class CountIn(BaseModel):
    audio_count: int


@router.put("/config/audio-count", dependencies=[Depends(require("pilot.generate_audio"))])
def set_audio_count(
    body: CountIn, principal: Principal = ACTOR, db: Session = SESSION
) -> dict[str, Any]:
    top = config.pilot_audio_max()
    if not 1 <= body.audio_count <= top:
        raise HTTPException(422, f"Choose a number from 1 to {top}.")
    before = audio_count(db)
    set_setting(db, "audio_count", body.audio_count, principal.name)
    db.commit()
    audit(db, principal.name, "config.audio_count", "", before=before, after=body.audio_count)
    return {"audio_count": body.audio_count}


class RetentionIn(BaseModel):
    retention_days: int


@router.put("/config/retention", dependencies=[Depends(require("pilot.sheets_admin"))])
def set_retention(
    body: RetentionIn, principal: Principal = ACTOR, db: Session = SESSION
) -> dict[str, Any]:
    if not MIN_RETENTION_DAYS <= body.retention_days <= MAX_RETENTION_DAYS:
        raise HTTPException(422, f"Choose from {MIN_RETENTION_DAYS} to {MAX_RETENTION_DAYS} days.")
    before = retention_days(db)
    set_setting(db, "retention_days", body.retention_days, principal.name)
    db.commit()
    audit(db, principal.name, "config.retention", "", before=before, after=body.retention_days)
    return {"retention_days": body.retention_days}


# ---- sheets -----------------------------------------------------------------------------------


@router.get("/sheets/summary", dependencies=[Depends(require("pilot.upload_sheets"))])
def sheets_summary(
    tasks: BackgroundTasks,
    db: Session = SESSION,
    store: BlobStore = SHEETS,
    factory: Callable[[], Session] = FACTORY,
    ctx: CallContext = AI_CONTEXT,
) -> dict[str, Any]:
    out = sheets.summary(db)
    if out["waiting"]:  # a read that never ran is tried again, once the sheet is old enough
        tasks.add_task(sheets.retry_stuck, factory, store, ctx)
    return out


@router.get("/sheets", dependencies=[Depends(require("pilot.upload_sheets"))])
def sheets_list(db: Session = SESSION) -> dict[str, Any]:
    return {"sheets": sheets.list_sheets(db)}


@router.post("/sheets/init", dependencies=[Depends(require("pilot.upload_sheets"))])
def sheets_init(
    body: sheets.InitIn,
    principal: Principal = ACTOR,
    db: Session = SESSION,
    store: BlobStore = SHEETS,
) -> dict[str, Any]:
    return sheets.init_upload(db, store, principal.name, body)


@router.post("/sheets/{sheet_id}/complete", dependencies=[Depends(require("pilot.upload_sheets"))])
def sheets_complete(
    sheet_id: str,
    tasks: BackgroundTasks,
    principal: Principal = ACTOR,
    db: Session = SESSION,
    store: BlobStore = SHEETS,
    factory: Callable[[], Session] = FACTORY,
    ctx: CallContext = AI_CONTEXT,
) -> dict[str, Any]:
    sheet = sheets.complete_upload(db, store, principal.name, sheet_id)
    if sheet.status == "stored":
        tasks.add_task(sheets.read_stored_sheet, factory, store, sheet.id, ctx)
    return {"id": sheet.id, "status": sheet.status}


@router.get("/sheets/{sheet_id}/url", dependencies=[Depends(require("pilot.sheets_admin"))])
def sheet_url(
    sheet_id: str,
    principal: Principal = ACTOR,
    db: Session = SESSION,
    store: BlobStore = SHEETS,
) -> dict[str, Any]:
    from services.api.db import PilotSheet

    sheet = db.get(PilotSheet, sheet_id)
    if sheet is None or sheet.status == "pending":
        raise HTTPException(404, "That sheet is not stored.")
    audit(db, principal.name, "sheet.link", sheet.id)
    return {
        "url": store.presign_get(sheet.object_key, sheets.GET_EXPIRES_S),
        "expires_in": sheets.GET_EXPIRES_S,
    }


@router.delete(
    "/sheets/school/{school_code}", dependencies=[Depends(require("pilot.sheets_admin"))]
)
def sheets_delete_school(
    school_code: str,
    confirm: str = "",
    principal: Principal = ACTOR,
    db: Session = SESSION,
    store: BlobStore = SHEETS,
) -> dict[str, int]:
    if confirm != school_code:
        raise HTTPException(422, "Type the school code to confirm.")
    return sheets.delete_school(db, store, principal.name, school_code)


@router.post("/sheets/retention/run", dependencies=[Depends(require("pilot.sheets_admin"))])
def sheets_retention(
    principal: Principal = ACTOR, db: Session = SESSION, store: BlobStore = SHEETS
) -> dict[str, int]:
    n = sheets.purge_expired(db, store)
    audit(db, principal.name, "sheets.retention_run", "", deleted=n)
    return {"deleted": n}


# ---- local signed blobs (dev and tests only: S3 serves its own signed URLs) ----------------------


def _local(store: BlobStore) -> LocalBlobStore:
    if not isinstance(store, LocalBlobStore):
        raise HTTPException(404)
    return store


@router.put("/blob/{token}", include_in_schema=False)
async def blob_put(request: Request, token: str, store: BlobStore = SHEETS) -> Response:
    local = _local(store)
    claims = local.verify(token, "PUT")
    if claims is None:
        raise HTTPException(403, "This upload link has expired. Try the sheet again.")
    body = await request.body()
    if len(body) > sheets.MAX_UPLOAD_BYTES:
        raise HTTPException(413, "That file is too large.")
    local.put(claims["k"], body, claims.get("t", "application/octet-stream"))
    return Response(status_code=200)


@router.get("/blob/{token}", include_in_schema=False)
def blob_get(
    token: str, sheets_store: BlobStore = SHEETS, audio_store: BlobStore = AUDIO
) -> Response:
    for store in (sheets_store, audio_store):
        if isinstance(store, LocalBlobStore):
            claims = store.verify(token, "GET")
            if claims and store.size(claims["k"]) is not None:
                return Response(
                    store.get(claims["k"]),
                    media_type=store.types.get(claims["k"], "application/octet-stream"),
                )
    raise HTTPException(403, "This link has expired.")


# ---- audio ------------------------------------------------------------------------------------


@router.get("/audio", dependencies=[Depends(require("pilot.audio_view"))])
def audio_list(
    language: str | None = None, principal: Principal = ACTOR, db: Session = SESSION
) -> dict[str, Any]:
    pooled = lessons.pooled_counts(db)
    cards = [audio_mod.card_json(db, c, pooled.hash) for c in audio_mod.latest_cards(db, language)]
    if "coordinator" not in principal.roles:
        for c in cards:
            c["shared_with"] = []  # which teacher got which file is the coordinator's record
    if set(principal.roles) == {"officer"} and pooled.classes < MIN_CLASSES_SHOWN:
        # officers see aggregates only: nothing that covers fewer than 5 classes
        for c in cards:
            c["script"] = ""
        return {
            "cards": cards,
            "audio_count": audio_count(db),
            "sheets_read": 0,
            "classes_read": 0,
        }
    return {
        "cards": cards,
        "audio_count": audio_count(db),
        "sheets_read": pooled.children_checked,
        "classes_read": pooled.classes,
    }


class GenerateIn(BaseModel):
    language: str
    voice: str
    force: bool = False


@router.post("/audio/generate", dependencies=[Depends(require("pilot.generate_audio"))])
def audio_generate(
    body: GenerateIn,
    principal: Principal = ACTOR,
    db: Session = SESSION,
    ctx: CallContext = AI_CONTEXT,
) -> dict[str, Any]:
    if body.language not in LANGUAGES:
        raise HTTPException(422, "Choose English, Hindi or Tamil.")
    if body.voice not in audio_mod.voice_ids():
        raise HTTPException(422, "Choose one of the listed voices.")
    pooled = lessons.pooled_counts(db)
    try:
        error, showing = lessons.choose_error(pooled)
    except lessons.NoTrack as exc:
        raise HTTPException(409, {"reason": exc.reason}) from exc
    total = audio_count(db)
    existing = {c.slot: c for c in audio_mod.latest_cards(db, body.language)}
    made = 0
    for plan in lessons.plan_slots(error, showing, pooled.children_checked, total):
        card = existing.get(plan.slot)
        if (
            card
            and card.status not in ("failed", "draft")  # a draft never finished: make it again
            and card.counts_hash == pooled.hash
            and not body.force
        ):
            continue  # already made from these counts: do not pay for the checker again
        lessons.make_card(db, plan, body.language, body.voice, pooled, principal.name, ctx)
        made += 1
    audit(db, principal.name, "audio.generate", "", lang=body.language, slots=total, made=made)
    return {"made": made}


@router.post(
    "/audio/{audio_id}/regenerate", dependencies=[Depends(require("pilot.generate_audio"))]
)
def audio_regenerate(
    audio_id: str,
    voice: str | None = None,
    principal: Principal = ACTOR,
    db: Session = SESSION,
    ctx: CallContext = AI_CONTEXT,
) -> dict[str, Any]:
    card = audio_mod.get_card(db, audio_id)
    if voice is not None and voice not in audio_mod.voice_ids():
        raise HTTPException(422, "Choose one of the listed voices.")
    pooled = lessons.pooled_counts(db)
    try:
        error, showing = lessons.choose_error(pooled)
    except lessons.NoTrack as exc:
        raise HTTPException(409, {"reason": exc.reason}) from exc
    plan = lessons.plan_slots(error, showing, pooled.children_checked, audio_count(db))
    if card.slot > len(plan):
        raise HTTPException(409, "This lesson is switched off.")
    new = lessons.make_card(
        db, plan[card.slot - 1], card.language, voice or card.voice, pooled, principal.name, ctx
    )
    return {"id": new.id, "status": new.status}


@router.post("/audio/{audio_id}/approve", dependencies=[Depends(require("pilot.approve_audio"))])
def audio_approve(
    audio_id: str, principal: Principal = ACTOR, db: Session = SESSION
) -> dict[str, Any]:
    """Approves the TEXT. The voice is made later, on the first teacher tap or Make audio."""
    card = audio_mod.approve(db, principal.name, audio_mod.get_card(db, audio_id))
    return {"id": card.id, "status": card.status}


@router.post("/audio/{audio_id}/render", dependencies=[Depends(require("pilot.generate_audio"))])
def audio_render(
    audio_id: str,
    principal: Principal = ACTOR,
    db: Session = SESSION,
    store: BlobStore = AUDIO,
    speech: SpeechService = SPEECH,
) -> dict[str, Any]:
    """Try the voice again for an approved lesson whose audio failed."""
    card = audio_mod.render(db, principal.name, store, speech, audio_mod.get_card(db, audio_id))
    return {"id": card.id, "status": card.status}


class RejectIn(BaseModel):
    reason: RejectionReason


@router.post("/audio/{audio_id}/reject", dependencies=[Depends(require("pilot.approve_audio"))])
def audio_reject(
    audio_id: str, body: RejectIn, principal: Principal = ACTOR, db: Session = SESSION
) -> dict[str, Any]:
    card = audio_mod.reject(db, principal.name, audio_mod.get_card(db, audio_id), body.reason)
    return {"id": card.id, "status": card.status}


@router.get("/audio/{audio_id}/file", dependencies=[Depends(require("pilot.audio_view"))])
def audio_file(audio_id: str, db: Session = SESSION, store: BlobStore = AUDIO) -> Response:
    card = audio_mod.get_card(db, audio_id)
    audio_mod.require_ready(db, card)
    assert card.object_key is not None
    fmt = card.object_key.rsplit(".", 1)[-1]
    return Response(
        store.get(card.object_key),
        media_type=audio_mod.MIME.get(fmt, "audio/mp4"),
        headers={
            "Content-Disposition": f'attachment; filename="{audio_mod.file_name(card, fmt)}"',
            "Cache-Control": "private, max-age=86400",
        },
    )


@router.get("/audio/{audio_id}/link", dependencies=[Depends(require("pilot.share_audio"))])
def audio_link(
    audio_id: str,
    principal: Principal = ACTOR,
    db: Session = SESSION,
    store: BlobStore = AUDIO,
) -> dict[str, Any]:
    card = audio_mod.get_card(db, audio_id)
    audio_mod.require_ready(db, card)
    assert card.object_key is not None
    seconds = audio_mod.LINK_HOURS * 3600
    fmt = card.object_key.rsplit(".", 1)[-1]
    url = store.presign_get(card.object_key, seconds, audio_mod.file_name(card, fmt))
    audit(db, principal.name, "audio.link", card.id, hours=audio_mod.LINK_HOURS)
    return {"url": url, "expires_in": seconds}


class ShareIn(BaseModel):
    teacher_refs: list[str] = Field(min_length=1, max_length=200)


@router.post("/audio/{audio_id}/shares", dependencies=[Depends(require("pilot.share_audio"))])
def audio_shares(
    audio_id: str, body: ShareIn, principal: Principal = ACTOR, db: Session = SESSION
) -> dict[str, int]:
    card = audio_mod.get_card(db, audio_id)
    return {"recorded": audio_mod.record_shares(db, principal.name, card, body.teacher_refs)}


@router.get("/audio/{audio_id}/lesson-link", dependencies=[Depends(require("pilot.share_audio"))])
def audio_lesson_link(
    audio_id: str, principal: Principal = ACTOR, db: Session = SESSION
) -> dict[str, Any]:
    """The link a teacher opens: the approved text; audio is made on the first tap."""
    origin = os.environ.get("PWA_ORIGIN", "").rstrip("/")
    if not origin:
        raise HTTPException(503, "The web address of this app is not set up on the server.")
    card = audio_mod.get_card(db, audio_id)
    audio_mod.require_shareable(db, card)
    token = audio_mod.lesson_token(card)
    audit(db, principal.name, "audio.lesson_link", card.id, days=audio_mod.LESSON_LINK_DAYS)
    return {"url": f"{origin}/#/lesson/{token}", "expires_in_days": audio_mod.LESSON_LINK_DAYS}


# ---- the lesson link a teacher opens (no sign-in; one approved lesson only) --------------------


@router.get("/lesson/{token}")
def lesson_page(token: str, db: Session = SESSION) -> dict[str, Any]:
    return audio_mod.lesson_view(audio_mod.card_for_token(db, token))


@router.post("/lesson/{token}/audio")
def lesson_audio(
    token: str,
    db: Session = SESSION,
    store: BlobStore = AUDIO,
    speech: SpeechService = SPEECH,
) -> dict[str, Any]:
    """The first tap voices the approved script and keeps the file; later taps reuse it."""
    card = audio_mod.voice_for_link(db, store, speech, audio_mod.card_for_token(db, token))
    assert card.object_key is not None
    fmt = card.object_key.rsplit(".", 1)[-1]
    url = store.presign_get(card.object_key, 600, audio_mod.file_name(card, fmt))
    return {
        "url": url,
        "file_name": audio_mod.file_name(card, fmt),
        "mime": audio_mod.MIME.get(fmt, "audio/mp4"),
        "seconds": round(card.duration_s, 1),
        "bytes": card.bytes,
    }
