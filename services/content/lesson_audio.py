"""The voiced lessons a coach can listen to, regenerate and approve (after publishing; optional).

Publishing voices each lesson through services/speech/lessons.py and keeps a record here: provider,
voice, the sentences, the timing map, the round-trip check per sentence, size and length. A coach
can regenerate one sentence (only that chunk is made again, then the lesson is re-stitched) or the
whole lesson; each makes a new revision and the published audio stays until she approves the new
one. On approval, the manifests that list the lesson point to the approved revision and older
revisions are deleted. Every action leaves a ContentAudit row (ids and counts, never text).

A filled lesson carries the pooled counts of its cohort's classes, and so does its audio. A coach
may see cohort-level figures, but not a figure that covers fewer than 5 classes (CLAUDE.md rules 3
and 15; the manifests view hides scripts for the same reason). So a lesson whose cohort has fewer
than `MIN_CLASSES` classes is listed as hidden: no script, no audio, no regenerate."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column
from sqlalchemy.orm.attributes import flag_modified

from services.api.db import Base, ContentAudit, TrackManifest
from services.speech import lessons

MIME = "audio/mpeg"
MIN_CLASSES = 5  # rule 3: no figure covering fewer than 5 classes


def _now() -> datetime:
    return datetime.now(UTC)


class LessonAudioRecord(Base):
    """One revision of one lesson's audio. The script is the lesson text already published in the
    manifest (no child, no teacher)."""

    __tablename__ = "lesson_audio"

    id: Mapped[str] = mapped_column(String(24), primary_key=True)
    part_id: Mapped[str] = mapped_column(String(60), index=True)
    track_id: Mapped[str] = mapped_column(String(40))
    cohort_id: Mapped[str] = mapped_column(String(60), default="", index=True)
    cohort_classes: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer)
    language: Mapped[str] = mapped_column(String(4))
    day: Mapped[int] = mapped_column(Integer, default=0)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    digest: Mapped[str] = mapped_column(String(64), index=True)
    script: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(16))
    voice: Mapped[str] = mapped_column(String(32))
    style: Mapped[str | None] = mapped_column(String(40))
    audio_key: Mapped[str] = mapped_column(String(160))
    bytes: Mapped[int] = mapped_column(Integer)
    seconds: Mapped[float] = mapped_column(Float)
    sentences: Mapped[list[str]] = mapped_column(JSON)
    timing: Mapped[list[dict[str, float]]] = mapped_column(JSON)
    checks: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    chunks: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    cost_inr: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(
        String(12), default="unreviewed"
    )  # unreviewed | approved | superseded
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


def digest(text: str, language: str) -> str:
    raw = json.dumps([text, language, lessons.PIPELINE_VERSION, lessons.settings()["kbps"]])
    return hashlib.sha256(raw.encode()).hexdigest()


def _key(track_id: str, version: int, language: str, part: str, revision: int, d: str) -> str:
    return f"tracks/{track_id}/v{version}/{language}/{part}-r{revision}-{d[:16]}.mp3"


def summary(rec: LessonAudioRecord) -> dict[str, int]:
    checked = [c for c in rec.checks if c.get("cer") is not None]
    flagged = sum(1 for c in checked if c.get("flagged"))
    return {
        "sentences": len(rec.checks),
        "checked": len(checked),
        "passed": len(checked) - flagged,
        "flagged": flagged,
    }


def _save(
    db: Session,
    store: Any,
    got: lessons.LessonAudio,
    *,
    part_id: str,
    track_id: str,
    cohort_id: str,
    cohort_classes: int,
    version: int,
    language: str,
    day: int,
    script: str,
    revision: int,
) -> LessonAudioRecord:
    d = digest(script, language)
    key = _key(track_id, version, language, part_id, revision, d)
    store.put(key, got.mp3, MIME)
    rec = LessonAudioRecord(
        id=uuid.uuid4().hex[:24],
        part_id=part_id,
        track_id=track_id,
        cohort_id=cohort_id,
        cohort_classes=cohort_classes,
        version=version,
        language=language,
        day=day,
        revision=revision,
        digest=d,
        script=script,
        provider=got.provider,
        voice=got.voice,
        style=got.style,
        audio_key=key,
        bytes=len(got.mp3),
        seconds=got.seconds,
        sentences=got.sentences,
        timing=got.timing,
        checks=got.checks,
        chunks=got.chunks,
        cost_inr=got.cost_inr,
        status="unreviewed",
    )
    db.add(rec)
    return rec


def voice_for_publish(
    db: Session,
    store: Any,
    speech: Any,
    *,
    part_id: str,
    track_id: str,
    cohort_id: str,
    cohort_classes: int,
    version: int,
    language: str,
    day: int,
    text: str,
) -> LessonAudioRecord:
    """The lesson's audio for a manifest: the newest approved or unreviewed revision of exactly
    this text if one exists (no provider call), else a new one. Raises LessonAudioUnavailable."""
    d = digest(text, language)
    old = (
        db.execute(
            select(LessonAudioRecord)
            .where(
                LessonAudioRecord.part_id == part_id,
                LessonAudioRecord.digest == d,
                LessonAudioRecord.cohort_id == cohort_id,
                LessonAudioRecord.status != "superseded",
            )
            .order_by(LessonAudioRecord.revision.desc())
        )
        .scalars()
        .first()
    )
    if old is not None and store.size(old.audio_key) is not None:
        return old
    got = lessons.generate(text, language, speech, store)
    rec = _save(
        db,
        store,
        got,
        part_id=part_id,
        track_id=track_id,
        cohort_id=cohort_id,
        cohort_classes=cohort_classes,
        version=version,
        language=language,
        day=day,
        script=text,
        revision=_next_revision(db, part_id, cohort_id),
    )
    db.add(
        _audit(
            "system",
            "publisher",
            "voice_lesson",
            rec,
            {"provider": got.provider, "fallbacks": got.fallbacks, **got.summary},
        )
    )
    return rec


def _next_revision(db: Session, part_id: str, cohort_id: str) -> int:
    revs = db.execute(
        select(LessonAudioRecord.revision).where(
            LessonAudioRecord.part_id == part_id, LessonAudioRecord.cohort_id == cohort_id
        )
    ).scalars()
    return max(revs, default=0) + 1


def _audit(
    role: str, actor: str, action: str, rec: LessonAudioRecord, detail: dict[str, Any]
) -> ContentAudit:
    return ContentAudit(
        role=role,
        actor=actor,
        action=action,
        content_type="lesson_audio",
        content_id=rec.part_id,
        version=rec.version,
        detail={"revision": rec.revision, "id": rec.id, **detail},
    )


def get(db: Session, rec_id: str) -> LessonAudioRecord:
    rec = db.get(LessonAudioRecord, rec_id)
    if rec is None:
        raise LookupError("That lesson audio does not exist.")
    return rec


def regenerate(
    db: Session,
    store: Any,
    speech: Any,
    rec_id: str,
    *,
    sentence: int | None,
    actor: str,
    role: str = "coach",
) -> LessonAudioRecord:
    """A new revision: with `sentence`, only the chunk holding it is made again (same provider, the
    rest from the cache); without, the whole lesson is made again from scratch."""
    rec = get(db, rec_id)
    if hidden(rec):
        raise PermissionError("This lesson's cohort has fewer than 5 classes.")
    if sentence is not None:
        if not 0 <= sentence < len(rec.sentences):
            raise ValueError("No such sentence in this lesson.")
        chunk = lessons.chunk_of_sentence(rec.script, sentence)
        got = lessons.generate(
            rec.script, rec.language, speech, store, fresh={chunk}, only_provider=rec.provider
        )
    else:
        n = len(lessons.make_chunks(lessons.split_sentences(rec.script)))
        got = lessons.generate(rec.script, rec.language, speech, store, fresh=set(range(n)))
    new = _save(
        db,
        store,
        got,
        part_id=rec.part_id,
        track_id=rec.track_id,
        cohort_id=rec.cohort_id,
        cohort_classes=rec.cohort_classes,
        version=rec.version,
        language=rec.language,
        day=rec.day,
        script=rec.script,
        revision=_next_revision(db, rec.part_id, rec.cohort_id),
    )
    db.add(
        _audit(
            role,
            actor,
            "regen_sentence" if sentence is not None else "regen_lesson",
            new,
            {
                "from_revision": rec.revision,
                "sentence": sentence,
                "provider": got.provider,
                "cost_inr": got.cost_inr,
                **got.summary,
            },
        )
    )
    db.commit()
    return new


def approve(
    db: Session, store: Any, rec_id: str, *, actor: str, role: str = "coach"
) -> LessonAudioRecord:
    """Approve this revision: manifests listing the lesson now point to it; older revisions of the
    same lesson are superseded and their files deleted."""
    rec = get(db, rec_id)
    if hidden(rec):
        raise PermissionError("This lesson's cohort has fewer than 5 classes.")
    rec.status = "approved"
    rec.approved_at = _now()
    for other in db.execute(
        select(LessonAudioRecord).where(
            LessonAudioRecord.part_id == rec.part_id,
            LessonAudioRecord.cohort_id == rec.cohort_id,
            LessonAudioRecord.id != rec.id,
        )
    ).scalars():
        if other.status != "superseded":
            other.status = "superseded"
            if other.audio_key != rec.audio_key:
                store.delete(other.audio_key)
    for m in db.execute(
        select(TrackManifest).where(TrackManifest.cohort_id == rec.cohort_id)
    ).scalars():
        changed = False
        for part in m.body.get("parts", []):
            if part.get("id") == rec.part_id and part.get("language") == rec.language:
                part.update(manifest_fields(rec))
                changed = True
        if changed:
            flag_modified(m, "body")
    db.add(_audit(role, actor, "approve_audio", rec, summary(rec)))
    db.commit()
    return rec


def manifest_fields(rec: LessonAudioRecord) -> dict[str, Any]:
    """What a manifest part carries about its audio (the teacher's player and the review screen)."""
    return {
        "audio_key": rec.audio_key,
        "mime": MIME,
        "bytes": rec.bytes,
        "seconds": round(rec.seconds, 1),
        "sentences": rec.sentences,
        "timing": rec.timing,
        "audio_id": rec.id,
        "audio_review": rec.status,
        "voice_provider": rec.provider,
        "ai_voice": True,
    }


def hidden(rec: LessonAudioRecord) -> bool:
    return rec.cohort_classes < MIN_CLASSES


def view(rec: LessonAudioRecord, audio_url: str | None) -> dict[str, Any]:
    base = {
        "id": rec.id,
        "part_id": rec.part_id,
        "track_id": rec.track_id,
        "version": rec.version,
        "language": rec.language,
        "day": rec.day,
        "revision": rec.revision,
        "provider": rec.provider,
        "voice": rec.voice,
        "status": rec.status,
        "summary": summary(rec),
        "hidden": hidden(rec),
    }
    if hidden(rec):
        return base  # no script, no audio, no numbers (rule 3)
    return {
        **base,
        "style": rec.style,
        "bytes": rec.bytes,
        "seconds": rec.seconds,
        "sentences": rec.sentences,
        "timing": rec.timing,
        "checks": rec.checks,
        "audio_url": audio_url,
        "sentence_costs_inr": [
            lessons.estimate(s, rec.language, rec.provider)["cost_inr"] for s in rec.sentences
        ],
    }


def latest_for_review(db: Session) -> list[LessonAudioRecord]:
    """The newest revision of each voiced lesson."""
    rows = db.execute(
        select(LessonAudioRecord)
        .where(LessonAudioRecord.status != "superseded")
        .order_by(LessonAudioRecord.part_id, LessonAudioRecord.revision.desc())
    ).scalars()
    seen: set[tuple[str, str, str]] = set()
    out = []
    for r in rows:
        if (r.part_id, r.language, r.cohort_id) not in seen:
            seen.add((r.part_id, r.language, r.cohort_id))
            out.append(r)
    return sorted(out, key=lambda r: (r.track_id, r.language, r.day))
