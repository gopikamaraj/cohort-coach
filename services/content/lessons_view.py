"""What a teacher is shown of a published track: the manifest's lessons, in her language, and when
each is due.

A lesson reaches a teacher only through a manifest, and a manifest exists only for a version both
keys switched on (publish.py). This module reads; it decides nothing about approval.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.db import TrackManifest

# Two lessons a week for three weeks: the lesson on day N of the track is due this many days after
# the track starts (a week starts on the start day; the second lesson is three days later).
LESSON_OFFSETS_DAYS = (0, 3, 7, 10, 14, 17)
MAX_LESSON_SECONDS = 5 * 60  # the content gate: a lesson over 5 minutes is not published


def latest_manifest(db: Session, error: str) -> TrackManifest | None:
    """The newest published manifest for the track of this error, or None."""
    rows = db.execute(select(TrackManifest).order_by(TrackManifest.id.desc())).scalars()
    for row in rows:
        if row.body.get("error") == error:
            return row
    return None


def lessons(manifest: TrackManifest, language: str) -> list[dict[str, Any]]:
    """The lesson parts for one language, by day. Falls back to English, then to any language the
    manifest has, so a teacher is never shown nothing when the track exists in another language."""
    parts = [p for p in manifest.body.get("parts", []) if p.get("kind") == "lesson"]
    for wanted in (language, "en", None):
        chosen = [p for p in parts if wanted is None or p.get("language") == wanted]
        if chosen:
            first = chosen[0]["language"]
            return sorted((p for p in chosen if p["language"] == first), key=lambda p: p["day"])
    return []


def model_lesson(manifest: TrackManifest, language: str) -> dict[str, Any] | None:
    parts = [p for p in manifest.body.get("parts", []) if p.get("kind") == "model_lesson"]
    for wanted in (language, "en", None):
        for p in parts:
            if wanted is None or p.get("language") == wanted:
                return p
    return None


def due_day(day: int, started: datetime, now: datetime) -> bool:
    """Is lesson `day` (1-based) due? The first lesson is due at once."""
    offset = LESSON_OFFSETS_DAYS[min(day, len(LESSON_OFFSETS_DAYS)) - 1]
    return now >= started + timedelta(days=offset)


def days_until(day: int, started: datetime, now: datetime) -> int:
    offset = LESSON_OFFSETS_DAYS[min(day, len(LESSON_OFFSETS_DAYS)) - 1]
    left = (started + timedelta(days=offset)) - now
    return max(0, -(-int(left.total_seconds()) // 86400))
