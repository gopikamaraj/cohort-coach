"""Publishing a track version for one cohort: fill the slots, check again, voice, manifest.

Only a version both keys switched on (`active`) is published. Class numbers come from code: the
pooled counts of the cohort's classes for the track's error (rule 1). The filled text is checked
again (arithmetic, check items, child tags) before a single word is voiced, because a wrong sum
can hide behind slots until the numbers are in. Each lesson is voiced once: the file is named by a
hash of its words, voice and format, so the same words are never paid for twice. The model-lesson
script is published as text (the teacher reads it to her class); its audio is the model run.

The manifest lists, for the lesson screen (T4) and the bot, every part's id, audio, size, script,
badge, and who reviewed and switched it on (role and time, never a name).
"""

from __future__ import annotations

import hashlib
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
from services.content import slots, versions
from services.content.lessons_view import MAX_LESSON_SECONDS
from services.content.track import load_track
from services.media.storage import BlobStore
from services.media.voice import chunks
from services.speech.audio import join_to_file
from services.speech.voices import Voice

BLOCK = Path(__file__).resolve().parents[2] / "data" / "synthetic" / "block_T1T2.json"
FORMAT = "ogg"  # OGG/Opus: what Telegram plays as a voice note
KBPS = 16
FALLBACK_KBPS = 12
BUDGET_BYTES_PER_5_MIN = 600_000  # CLAUDE.md section 9: ~0.6 MB per 5 minutes
LESSON_VOICE = "ritu"  # the default teacher voice (content/voices/lessons.v1.yaml)
MIME = "audio/ogg"


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
    """OGG/Opus mono at 16 kbps; re-encoded at 12 kbps if the container pushes it over budget."""
    data, seconds = join_to_file(clips, fmt=FORMAT, kbps=KBPS)
    if seconds > 0 and len(data) / seconds * 300 > BUDGET_BYTES_PER_5_MIN:
        data, seconds = join_to_file(clips, fmt=FORMAT, kbps=FALLBACK_KBPS)
    return data, seconds


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


def _key(track_id: str, version: int, language: str, part: str, digest: str) -> str:
    return f"tracks/{track_id}/v{version}/{language}/{part}-{digest[:16]}.{FORMAT}"


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
    known_seconds: dict[str, float] = {}
    for old in db.execute(select(TrackManifest).where(TrackManifest.version_id == v.id)).scalars():
        for q in old.body.get("parts", []):
            if q.get("audio_key"):
                known_seconds[q["audio_key"]] = float(q.get("seconds", 0.0))
    parts: list[dict[str, Any]] = []
    voiced = 0
    for p in planned:
        digest = hashlib.sha256(
            json.dumps([p["text"], LESSON_VOICE, FORMAT, KBPS], ensure_ascii=False).encode()
        ).hexdigest()
        audio_key: str | None = None
        size, seconds = 0, 0.0
        if p["kind"] == "lesson":
            audio_key = _key(track.id, v.version, p["language"], p["part"], digest)
            existing = store.size(audio_key)
            if existing is None:
                voice = Voice(speaker=LESSON_VOICE, pitch=1.0, pace=1.0)
                clips = [speech.synthesize(c, p["language"], voice) for c in chunks(p["text"])]
                data, seconds = encode(clips)
                if seconds > MAX_LESSON_SECONDS:  # the content gate: a lesson over 5 minutes
                    raise PublishBlocked(f"{p['part']} ({p['language']})", ["lesson_too_long"])
                store.put(audio_key, data, MIME)
                size = len(data)
                voiced += 1
            else:
                size = existing
                seconds = known_seconds.get(audio_key, 0.0)
        parts.append(
            {
                "id": p["item"].item_id,
                "kind": p["kind"],
                "day": p["day"],
                "language": p["language"],
                "audio_key": audio_key,
                "mime": MIME if audio_key else None,
                "bytes": size,
                "seconds": round(seconds, 1),
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
            detail={"cohort": cohort_id, "voiced": voiced, "parts": len(parts)},
        )
    )
    db.commit()
    return manifest
