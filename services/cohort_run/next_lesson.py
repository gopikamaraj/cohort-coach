"""Which lesson comes next for one teacher, chosen by code from her answer after the last lesson.

- tried: the next lesson in the track's order.
- partly: the same lesson's approach again, as a smaller step with more practice.
- not yet: the next lesson in the track whose approaches she has not had yet; if every lesson
  repeats one, the one that repeats the fewest.
- no answer by the set date: the planned next lesson. Silence is never counted as a result.

The decision and its reason are code; call 5 only words the lesson it names.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ANSWERS = ("tried", "partly", "not_yet")


@dataclass(frozen=True)
class Decision:
    day: int  # the track lesson the next one is built on
    mode: str  # next | smaller_step | other_approach | planned | end
    reason: str  # a code the screen words: tried_next, partly_same, not_yet_other, ...
    skipped: tuple[str, ...] = ()  # approaches left out because she already had them
    practice_level: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "day": self.day,
            "mode": self.mode,
            "reason": self.reason,
            "skipped": list(self.skipped),
            "practice_level": self.practice_level,
        }


def decide(track: Any, had_days: list[int], last_day: int, answer: str | None) -> Decision:
    """`had_days`: the track lessons she has had, in order (the last is `last_day`)."""
    lessons = sorted(track.lessons, key=lambda x: x.day)
    by_day = {x.day: x for x in lessons}
    later = [x for x in lessons if x.day > last_day]
    if answer is None:
        if not later:
            return Decision(last_day, "end", "silence_end")
        return Decision(later[0].day, "planned", "silence_planned")
    if answer not in ANSWERS:
        raise ValueError(f"answer must be one of {ANSWERS}")
    if answer == "tried":
        if not later:
            return Decision(last_day, "end", "tried_end")
        return Decision(later[0].day, "next", "tried_next")
    if answer == "partly":
        return Decision(last_day, "smaller_step", "partly_same", practice_level=1)
    had = {s for d in had_days for s in by_day[d].strategies}
    pool = [x for x in lessons if x.day not in had_days] or later
    if not pool:
        return Decision(last_day, "end", "not_yet_end")
    fresh = [x for x in pool if not set(x.strategies) & had]
    if fresh:
        pick = min(fresh, key=lambda x: x.day)
        skipped = tuple(
            sorted({s for x in pool if x.day < pick.day for s in x.strategies if s in had})
        )
        return Decision(pick.day, "other_approach", "not_yet_other", skipped)
    pick = min(pool, key=lambda x: (len(set(x.strategies) & had), x.day))
    skipped = tuple(sorted(set(pick.strategies) & had))
    return Decision(pick.day, "other_approach", "not_yet_fewest_repeats", skipped)
