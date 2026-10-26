"""Intervention audio: approval, lesson links, voicing on demand, the published bucket, sharing.

The order is fixed: a script passes the gates (lessons.py), the coach approves the TEXT, and the
text can then be shared as a lesson link. The voice is paid for later and once: the first time a
teacher taps Download audio on the link (or the coordinator presses Make audio) the approved
script is voiced and written to the published-audio bucket; every later tap serves that file.
Staff download and the signed audio link still refuse any card that is not `audio_ready`, and a
card past a lowered audio count is inactive.
"""

from __future__ import annotations

import os
import re
import threading
from datetime import UTC, datetime, timedelta
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.guard.rejections import RejectionReason, add_approved_example
from services.api.db import PilotAudio, PilotAudit, PilotShare, ReviewDecision, ReviewItem
from services.pilot import auth
from services.pilot.common import LANGUAGES, audio_count, audit
from services.pilot.storage import BlobStore
from services.speech.audio import join_to_file
from services.speech.sarvam import SpeechError
from services.speech.service import SpeechService
from services.speech.voices import Voice

VOICES = Path(__file__).resolve().parents[2] / "content" / "voices" / "pilot.v1.yaml"
CHUNK_CHARS = 1200  # well under the speech API's per-request limit
TARGET_BYTES = 1_000_000  # a 2 to 3 minute note should stay under 1 MB
LINK_HOURS = 24
TEACHER_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{1,23}$")
MIME = {"m4a": "audio/mp4", "mp3": "audio/mpeg"}
LESSON_LINK_DAYS = 14
LINK_ACTOR = "lesson-link"  # audit actor for a voicing a teacher's tap caused
DAILY_VOICE_MAX = 20  # new voicings a day that teachers' taps may cause (PILOT_VOICE_DAILY_MAX)
LINK_ENDED = "This link has ended or is not right. Ask the person who sent it for a new one."


@cache
def voice_options() -> dict[str, Any]:
    data = yaml.safe_load(VOICES.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def voice_ids() -> list[str]:
    return [v["id"] for v in voice_options()["voices"]]


def audio_format() -> str:
    fmt = os.environ.get("PILOT_AUDIO_FORMAT", "m4a")
    return fmt if fmt in MIME else "m4a"


def file_name(card: PilotAudio, fmt: str | None = None) -> str:
    """Slot and language only: never a school, a teacher or a child."""
    return f"cc-pilot-slot{card.slot}-{card.language}.{fmt or audio_format()}"


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


# ---- cards ------------------------------------------------------------------------------------


def latest_cards(db: Session, language: str | None = None) -> list[PilotAudio]:
    rows = list(
        db.execute(select(PilotAudio).order_by(PilotAudio.slot, PilotAudio.version)).scalars()
    )
    latest: dict[tuple[int, str], PilotAudio] = {}
    for r in rows:
        latest[(r.slot, r.language)] = r  # ascending versions: the last one wins
    cards = sorted(latest.values(), key=lambda r: (r.language, r.slot))
    return [c for c in cards if language in (None, c.language)]


def card_json(db: Session, card: PilotAudio, current_counts_hash: str | None) -> dict[str, Any]:
    versions = list(
        db.execute(
            select(PilotAudio)
            .where(PilotAudio.slot == card.slot, PilotAudio.language == card.language)
            .order_by(PilotAudio.version.desc())
        ).scalars()
    )
    shares = list(db.execute(select(PilotShare).where(PilotShare.audio_id == card.id)).scalars())
    return {
        "id": card.id,
        "slot": card.slot,
        "language": card.language,
        "version": card.version,
        "title": card.title,
        "script": card.script,
        "voice": card.voice,
        "status": card.status,
        "note": card.note,
        "duration_s": round(card.duration_s, 1),
        "bytes": card.bytes,
        "active": card.slot <= audio_count(db),
        "stale": bool(current_counts_hash) and card.counts_hash != current_counts_hash,
        "ready": card.status == "audio_ready",
        "shareable": lesson_shareable(db, card),
        "file_name": file_name(card),
        "mime": MIME[audio_format()],
        "created_at": _aware(card.created_at).isoformat(),
        "shared_with": sorted({s.teacher_ref for s in shares}),
        "versions": [
            {
                "id": v.id,
                "version": v.version,
                "status": v.status,
                "ready": v.status == "audio_ready",
            }
            for v in versions
        ],
    }


def get_card(db: Session, audio_id: str) -> PilotAudio:
    card = db.get(PilotAudio, audio_id)
    if card is None:
        raise HTTPException(404, "That audio is not known.")
    return card


def require_ready(db: Session, card: PilotAudio) -> None:
    """The one gate for download, share and signed links: approved and voiced, and still wanted."""
    if card.status != "audio_ready" or not card.object_key:
        raise HTTPException(409, "Only approved audio can be downloaded or shared.")
    if card.slot > audio_count(db):
        raise HTTPException(409, "This lesson is switched off. Raise the number of audio files.")


def lesson_shareable(db: Session, card: PilotAudio) -> bool:
    """The text is approved (voiced or not) and the lesson is still wanted. A lesson whose voice
    failed stays shareable: the words were approved, only the sound is missing."""
    approved = card.status in ("approved", "audio_ready") or (
        card.status == "failed" and (card.note or "").startswith("audio:")
    )
    return approved and card.slot <= audio_count(db)


def require_shareable(db: Session, card: PilotAudio) -> None:
    if not lesson_shareable(db, card):
        raise HTTPException(409, "Only an approved lesson can be shared.")


def voice_daily_max() -> int:
    raw = os.environ.get("PILOT_VOICE_DAILY_MAX", "")
    return int(raw) if raw.isdigit() else DAILY_VOICE_MAX


# ---- lesson links -----------------------------------------------------------------------------


def lesson_token(card: PilotAudio, days: int = LESSON_LINK_DAYS) -> str:
    """An unguessable, expiring token for one approved lesson. It carries no teacher, school or
    child, and opens nothing but that lesson's text and its audio."""
    return auth.sign_claims({"k": "lesson", "a": card.id, "e": int(auth.now()) + days * 86400})


def card_for_token(db: Session, token: str) -> PilotAudio:
    claims = auth.read_claims(token)
    card = None
    if claims and claims.get("k") == "lesson":
        card = db.get(PilotAudio, str(claims.get("a")))
    if card is None or not lesson_shareable(db, card):
        raise HTTPException(404, LINK_ENDED)
    return card


def lesson_view(card: PilotAudio) -> dict[str, Any]:
    """What a teacher sees: the approved words and whether the audio exists yet."""
    return {
        "title": card.title,
        "script": card.script,
        "language": card.language,
        "slot": card.slot,
        "audio_ready": card.status == "audio_ready" and bool(card.object_key),
        "seconds": round(card.duration_s, 1),
        "bytes": card.bytes,
        "mime": MIME[audio_format()],
    }


def voicings_today(db: Session) -> int:
    """Voicings a teacher's tap caused since midnight UTC, failures included (each cost a call)."""
    since = datetime.now(UTC) - timedelta(days=2)
    midnight = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    rows = db.execute(
        select(PilotAudit.at).where(
            PilotAudit.actor == LINK_ACTOR,
            PilotAudit.action.in_(("audio.published", "audio.render_failed")),
            PilotAudit.at >= since.replace(tzinfo=None),
        )
    ).scalars()
    return sum(1 for at in rows if _aware(at) >= midnight)


_guard = threading.Lock()
_locks: dict[str, threading.Lock] = {}


def voice_for_link(
    db: Session, store: BlobStore, speech: SpeechService, card: PilotAudio
) -> PilotAudio:
    """The audio for a lesson a teacher asked for. Made once (the first tap), then served from the
    bucket. A daily cap stops a leaked link from running up speech credit."""
    require_shareable(db, card)
    with _guard:
        lock = _locks.setdefault(card.id, threading.Lock())
    with lock:  # two taps at once make it once
        db.refresh(card)
        if card.status == "audio_ready" and card.object_key:
            return card
        if voicings_today(db) >= voice_daily_max():
            audit(db, LINK_ACTOR, "audio.cap_reached", card.id)
            raise HTTPException(
                429, "Audio is busy today. You can read the lesson here, and try again tomorrow."
            )
        render(db, LINK_ACTOR, store, speech, card)
    if card.status != "audio_ready":
        raise HTTPException(503, "The voice is not available just now. Read the lesson here.")
    return card


# ---- approval and voicing ---------------------------------------------------------------------


def approve(db: Session, actor: str, card: PilotAudio) -> PilotAudio:
    if card.status != "needs_review" or card.review_item_id is None:
        raise HTTPException(409, "Only a lesson waiting for review can be approved.")
    newer = db.execute(
        select(PilotAudio.id).where(
            PilotAudio.slot == card.slot,
            PilotAudio.language == card.language,
            PilotAudio.version > card.version,
        )
    ).first()
    if newer:
        raise HTTPException(409, "A newer version exists. Review that one.")
    item = db.get(ReviewItem, card.review_item_id)
    assert item is not None
    item.status = "approved"
    item.badge = "checked_reviewed"
    db.add(ReviewDecision(item_id=item.item_id, decision="approve", reviewer_role="reviewer"))
    card.status = "approved"
    card.approved_by = actor
    card.approved_at = datetime.now(UTC)
    db.commit()
    audit(db, actor, "audio.approved", card.id, slot=card.slot, lang=card.language)
    return card


def reject(
    db: Session,
    actor: str,
    card: PilotAudio,
    reason: RejectionReason,
    examples_dir: Path | None = None,
) -> PilotAudio:
    if card.status != "needs_review" or card.review_item_id is None:
        raise HTTPException(409, "Only a lesson waiting for review can be returned.")
    item = db.get(ReviewItem, card.review_item_id)
    assert item is not None
    item.status = "rejected"
    db.add(
        ReviewDecision(
            item_id=item.item_id, decision="reject", reason=reason.value, reviewer_role="reviewer"
        )
    )
    card.status = "failed"
    card.note = f"rejected:{reason.value}"[:60]
    db.commit()
    # "Rejections feed the checker": the reason and the text become an example for call 7.
    add_approved_example(
        card.script,
        reason,
        card.language,
        date=datetime.now(UTC).date().isoformat(),
        directory=examples_dir,
    )
    audit(
        db,
        actor,
        "audio.rejected",
        card.id,
        slot=card.slot,
        lang=card.language,
        reason=reason.value,
    )
    return card


def chunks(text: str, limit: int = CHUNK_CHARS) -> list[str]:
    """Whole sentences, joined up to the limit, so a pause never falls mid-sentence."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?।])\s+|\n+", text) if s.strip()]
    out: list[str] = []
    for s in sentences:
        if out and len(out[-1]) + 1 + len(s) <= limit:
            out[-1] += " " + s
        else:
            out.append(s[:limit] if len(s) > limit else s)
    return out


def render(
    db: Session, actor: str, store: BlobStore, speech: SpeechService, card: PilotAudio
) -> PilotAudio:
    """Voice an approved script and publish the file. Refuses anything not approved."""
    item = db.get(ReviewItem, card.review_item_id) if card.review_item_id else None
    approved = (
        item is not None
        and item.status == "approved"
        and card.status in ("approved", "failed")
        and (card.status == "approved" or (card.note or "").startswith("audio:"))
    )
    if not approved:
        raise HTTPException(409, "Only an approved lesson can be voiced.")
    fmt = audio_format()
    pace = float(voice_options().get("pace", 1.0))
    voice = Voice(speaker=card.voice, pitch=1.0, pace=pace)
    try:
        clips = [speech.synthesize(c, card.language, voice) for c in chunks(card.script)]
        data, seconds = join_to_file(clips, fmt=fmt)
        if (
            len(data) > TARGET_BYTES
        ):  # a long script: re-encode smaller rather than ship a heavy file
            data, seconds = join_to_file(clips, fmt=fmt, kbps=24)
    except SpeechError as exc:
        card.status = "failed"
        card.note = f"audio:{exc.kind}"[:60]
        db.commit()
        audit(db, actor, "audio.render_failed", card.id, kind=exc.kind)
        return card
    key = f"pilot-audio/{card.id}.{fmt}"
    store.put(key, data, MIME[fmt])
    card.object_key, card.bytes, card.duration_s = key, len(data), seconds
    card.status, card.note = "audio_ready", None
    db.commit()
    audit(
        db, actor, "audio.published", card.id, slot=card.slot, lang=card.language, bytes=len(data)
    )
    return card


# ---- sharing ----------------------------------------------------------------------------------


def record_shares(db: Session, actor: str, card: PilotAudio, teacher_refs: list[str]) -> int:
    """A manual record that the coordinator sent this lesson to these teachers. Not delivery."""
    require_shareable(db, card)
    refs = sorted({r.strip() for r in teacher_refs})
    if not refs or any(not TEACHER_REF.match(r) for r in refs):
        raise HTTPException(422, "Choose teacher codes, not names.")
    now = datetime.now(UTC)
    for ref in refs:
        db.add(PilotShare(audio_id=card.id, teacher_ref=ref, shared_at=now, shared_by=actor))
    db.commit()
    audit(
        db, actor, "audio.shared", card.id, slot=card.slot, lang=card.language, teachers=len(refs)
    )
    return len(refs)


def languages() -> tuple[str, ...]:
    return LANGUAGES
