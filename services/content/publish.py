"""Publishing a track version for one cohort: fill the slots, check again, voice, manifest.

Only a version both keys switched on (`active`) is published. Class numbers come from code: the
pooled counts of the cohort's classes for the track's error (rule 1). The filled text is checked
again (arithmetic, check items, child tags) before a single word is voiced, because a wrong sum
can hide behind slots until the numbers are in. Each lesson is voiced once: the file is named by a
hash of its words, voice and format, so the same words are never paid for twice. The model-lesson
script is published as text (the teacher reads it to her class); its audio is the model run.

Lessons are voiced through services/speech/lessons.py (1 Nov, branch speech-bodhan): Bodhan first,
Sarvam as the fallback, one voice per lesson, MP3 mono 48 kbps with a timing map, each chunk checked
by transcribing it back. A coach can listen, regenerate and approve afterwards
(services/content/lesson_audio.py); a lesson whose providers all fail is published as text only.

The manifest lists, for the lesson screen (T4) and the bot, every part's id, audio, size, script,
badge, and who reviewed and switched it on (role and time, never a name).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.guard.explain import error_name
from ai.validators.arithmetic import (
    check_arithmetic,
    check_child_tags,
    normalise_child_tags,
    strip_child_tags,
)
from ai.validators.check_items import check_items
from services.api.db import ContentAudit, ContentVersion, ReviewItem, TrackManifest
from services.content import lesson_audio, slots, versions
from services.content.lessons_view import MAX_LESSON_SECONDS
from services.content.track import load_track
from services.media.storage import BlobStore
from services.speech import lessons

BLOCK = Path(__file__).resolve().parents[2] / "data" / "synthetic" / "block_T1T2.json"
FORMAT = "mp3"  # MP3 mono 48 kbps (decided 1 Nov 2026, DECISIONS.md; was OGG/Opus 16 kbps)
KBPS = lessons.settings()["kbps"]  # the lesson bit rate (LESSON_MP3_KBPS, default 48)
BUDGET_BYTES_PER_5_MIN = 1_850_000  # CLAUDE.md section 9: ~1.8 MB per 5 minutes at 48 kbps
MIME = lesson_audio.MIME


class PublishBlocked(ValueError):
    """A filled lesson failed a check, so nothing was voiced or published."""

    def __init__(self, part: str, codes: list[str]) -> None:
        super().__init__(f"{part}: {', '.join(codes)}")
        self.part = part
        self.codes = codes


@cache
def block() -> dict[str, Any]:
    data = json.loads(BLOCK.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def cohorts_for_error(error: str) -> list[str]:
    return [c["cohort_id"] for c in block()["cohorts"] if c["error"] == error]


def cohort_values(cohort_id: str, error: str, *, example: tuple[int, int]) -> dict[str, str]:
    """The slot values for one cohort, computed by code: the pooled counts of its classes for
    this error, and the worked example's answers from the engine."""
    cohort = next((c for c in block()["cohorts"] if c["cohort_id"] == cohort_id), None)
    if cohort is None:
        raise versions.BadState("That cohort does not exist.")
    if cohort["error"] != error:
        raise versions.BadState("That cohort is grouped for another error.")
    rows = [
        a
        for a in block()["assignments"]
        if a["class_id"] in cohort["class_ids"] and a["track"] == error
    ]
    showing = sum(int(r["children_showing"]) for r in rows)
    checked = sum(int(r["children_checked"]) for r in rows)
    if checked <= 0 or not 0 <= showing <= checked:
        raise versions.BadState("The cohort has no checked children for this error.")
    return {
        **slots.example_values(error, *example),
        "class.count_showing": str(showing),
        "class.children_checked": str(checked),
    }


def encode(clips: list[bytes]) -> tuple[bytes, float]:
    """Clips joined with the sentence pause, loudness-normalised, as MP3 mono (LESSON_MP3_KBPS)."""
    cfg = lessons.settings()
    pcms = [lessons._pcm(c) for c in clips]
    fake = [lessons.Chunk(i, "x", 0, (i,)) for i in range(len(clips))]
    sentences = [lessons.Sentence(i, "x", 0) for i in range(len(clips))]
    wav, seconds, _ = lessons.stitch(pcms, fake, sentences, cfg["sentence_gap_ms"])
    return lessons.encode_mp3(wav, cfg["kbps"]), seconds


def checked_text(script: str, values: Mapping[str, str], part: str) -> str:
    """Fill the slots, check the filled text, and return what is said (tags removed)."""
    try:
        filled = normalise_child_tags(slots.fill(script, values, keep_tags=True))
    except slots.SlotError as exc:
        raise PublishBlocked(part, [f"slot:{exc}"]) from exc
    problems = check_arithmetic(filled) + check_child_tags(filled) + check_items(filled)
    if problems:
        raise PublishBlocked(part, [v.code for v in problems])
    return strip_child_tags(filled)


def publish_version(
    db: Session,
    version_id: str,
    cohort_id: str,
    *,
    store: BlobStore,
    speech: Any,
    example: tuple[int, int] = (52, 29),
) -> dict[str, Any]:
    v = db.get(ContentVersion, version_id)
    if v is None or v.content_type != "track":
        raise versions.BadState("That track version does not exist.")
    if v.status != "active":
        raise versions.BadState("Only content that both keys switched on can be published.")
    track = load_track(str(v.body["track_id"]))
    values = {
        **cohort_values(cohort_id, track.error, example=example),
        "track.total_days": str(len(track.lessons)),
    }
    # 1. check every part first: nothing is voiced unless every part passes
    planned: list[dict[str, Any]] = []
    for language, chosen in v.body["languages"].items():
        for part_key, ref in chosen.items():
            item = db.get(ReviewItem, ref["item_id"])
            if item is None or item.status != "approved":
                raise versions.BadState(f"{part_key} ({language}) is no longer approved.")
            kind = str(item.content["kind"])
            day = int(item.content["day"])
            part_values = {
                **values,
                "track.error_name": error_name(track.error, language),
                "track.day": str(day),
            }
            spoken = checked_text(
                str(item.content["script"]), part_values, f"{part_key} ({language})"
            )
            planned.append(
                {
                    "item": item,
                    "kind": kind,
                    "day": day,
                    "language": language,
                    "part": part_key,
                    "text": spoken,
                }
            )

    # 2. voice what is not already published, and build the manifest
    classes = len(
        next((c["class_ids"] for c in block()["cohorts"] if c["cohort_id"] == cohort_id), [])
    )
    known_seconds: dict[str, float] = {}
    for old in db.execute(select(TrackManifest).where(TrackManifest.version_id == v.id)).scalars():
        for q in old.body.get("parts", []):
            if q.get("audio_key"):
                known_seconds[q["audio_key"]] = float(q.get("seconds", 0.0))
    parts: list[dict[str, Any]] = []
    voiced = 0
    text_only = 0
    for p in planned:
        digest = lesson_audio.digest(p["text"], p["language"])
        audio: dict[str, Any] = {"audio_key": None, "mime": None, "bytes": 0, "seconds": 0.0}
        if p["kind"] == "lesson":
            try:
                rec = lesson_audio.voice_for_publish(
                    db, store, speech, part_id=p["item"].item_id, track_id=track.id,
                    cohort_id=cohort_id, cohort_classes=classes, version=v.version,
                    language=p["language"], day=p["day"], text=p["text"],
                )  # fmt: skip
            except lessons.LessonAudioUnavailable as exc:
                # every provider failed: the lesson is published as text, and can be voiced later
                audio["audio_status"] = "text_only"
                audio["audio_error"] = sorted(exc.reasons.values())[:3]
                text_only += 1
            else:
                if rec.seconds > MAX_LESSON_SECONDS:  # the content gate: a lesson over 5 minutes
                    raise PublishBlocked(f"{p['part']} ({p['language']})", ["lesson_too_long"])
                voiced += int(rec.audio_key not in known_seconds)
                audio = lesson_audio.manifest_fields(rec)
        parts.append(
            {
                "id": p["item"].item_id,
                "kind": p["kind"],
                "day": p["day"],
                "language": p["language"],
                **audio,
                "sha256": digest,
                "script": p["text"],
                "badge": p["item"].badge,
            }
        )
    # the model run, if the coach approved one and it has been voiced: listed, never voiced here
    scripts = {
        p["id"]: p for p in parts if p["kind"] == "model_lesson"
    }  # a run is built from exactly this script version
    for run in db.execute(
        select(ReviewItem).where(
            ReviewItem.content_type == "model_run", ReviewItem.status == "approved"
        )
    ).scalars():
        script = scripts.get(run.content.get("source_item_id"))
        audio = run.content.get("audio")
        if script is None or not audio:
            continue
        parts.append(
            {
                "id": run.item_id,
                "kind": "model_run",
                "day": 0,
                "language": run.language,
                "audio_key": audio["key"],
                "mime": audio["mime"],
                "bytes": audio["bytes"],
                "seconds": audio["seconds"],
                "sha256": audio["sha256"],
                "script": "",
                "caption": run.content["caption"],
                "badge": run.badge,
            }
        )
    manifest = {
        "track_id": track.id,
        "error": track.error,
        "version": v.version,
        "version_id": v.id,
        "cohort_id": cohort_id,
        "simulated": bool(block().get("simulated", True)),
        "generated_at": datetime.now(UTC).isoformat(),
        "reviewed": {
            "role": "coach",
            "at": v.coach_approved_at.isoformat() if v.coach_approved_at else None,
        },
        "activated": {
            "role": "officer",
            "at": v.officer_activated_at.isoformat() if v.officer_activated_at else None,
        },
        "parts": parts,
    }
    db.add(TrackManifest(version_id=v.id, cohort_id=cohort_id, body=manifest))
    db.add(
        ContentAudit(
            role="system",
            actor="publisher",
            action="publish",
            content_type="track",
            content_id=track.id,
            version=v.version,
            detail={
                "cohort": cohort_id,
                "voiced": voiced,
                "text_only": text_only,
                "parts": len(parts),
            },
        )
    )
    db.commit()
    return manifest
