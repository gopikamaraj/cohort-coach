"""The teacher's time budget: minutes a week against the 20-minute cap (CLAUDE.md rule 12).

A target that is measured and shown, never a score. Minutes come from what the system delivered and
from what she reported she tried: the length of each lesson she tapped "Tried it" on, plus the time
she spent in the Practice Class and on reflections when those are reported. The source is always
labelled: *system* (a lesson was delivered) or *self-report* (a tap). Nothing here says "listened".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.validators import Violation
from services.api.db import LessonTap
from services.content.lessons_view import MAX_LESSON_SECONDS

WEEKLY_CAP_MINUTES = 20


def check_lesson_length(seconds: float) -> list[Violation]:
    """The content gate: a lesson over 5 minutes is not published."""
    if seconds > MAX_LESSON_SECONDS:
        return [Violation("lesson_too_long", f"{seconds:.0f} s, limit {MAX_LESSON_SECONDS} s")]
    return []


@dataclass(frozen=True)
class WeekMinutes:
    teacher_id: str
    lessons_minutes: float  # self-report: lessons she tapped "Tried it in class" on this week
    practice_minutes: float  # system: Practice Class session time reported by her phone
    total: float
    over_cap: bool
    source: str = "self-report and system"


def week_start(now: datetime) -> datetime:
    day = now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    return day - timedelta(days=day.weekday())


def weekly_minutes(
    db: Session,
    teacher_id: str,
    lesson_seconds: dict[tuple[str, int], float],
    *,
    now: datetime,
    practice_seconds: float = 0.0,
) -> WeekMinutes:
    """Minutes for the week containing `now`. `lesson_seconds` maps (track_id, day) to the length of
    that lesson's audio, from the manifest."""
    start = week_start(now)
    taps = db.execute(
        select(LessonTap).where(LessonTap.teacher_id == teacher_id, LessonTap.updated_at >= start)
    ).scalars()
    lesson_total = sum(lesson_seconds.get((t.track_id, t.lesson_day), 0.0) for t in taps if t.tried)
    lessons_m = round(lesson_total / 60, 1)
    practice_m = round(practice_seconds / 60, 1)
    total = round(lessons_m + practice_m, 1)
    return WeekMinutes(teacher_id, lessons_m, practice_m, total, total > WEEKLY_CAP_MINUTES)


def median_minutes(weeks: list[WeekMinutes]) -> float | None:
    """The median across teachers, for the officer funnel; None when there are none (no number is
    made up, and a figure over fewer than 5 teachers is hidden by the caller)."""
    return round(median(w.total for w in weeks), 1) if weeks else None
