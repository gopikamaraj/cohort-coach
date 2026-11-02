# ruff: noqa: E501
"""Which module comes next, chosen by code. The AI only words it (and in this build, does not even do
that: the text is the library's own).

    tried        -> the next approach in the plan
    partly       -> the same approach as a smaller step, then rejoin the plan
    not yet      -> a different approach for the same error, skipping approaches already used
    none by due  -> the planned next module. Silence is never read as "tried".

An approach is never used twice, except for "partly". The cap and the end of the plan stop the track
with a reason; stopping on the cap or on "no approach left" sends the teacher to a person (a mentor or
coach); the plan simply finishing is the normal end ("time for the next check").
"""

from __future__ import annotations

from dataclasses import dataclass, field

from services.modules import states

STOP_CAP = "cap"  # the most modules was reached
STOP_EXHAUSTED = "exhausted"  # the plan and its alternatives ran out: talk to a person
STOP_DONE = "done"  # the plan finished in the normal way
STOP_END_DATE = "end_date"  # the track's end date (the next check) passed

# Reason codes. Each has a fixed sentence in strings/{en,hi,ta}.json as `module.reason.<code>`.
REASONS = (
    "first",
    "tried",
    "partly",
    "not_yet",
    "no_feedback",
    "stop_cap",
    "stop_exhausted",
    "stop_done",
    "stop_end_date",
)


@dataclass(frozen=True)
class Template:
    approach: str
    alternatives: tuple[str, ...] = ()


@dataclass(frozen=True)
class Plan:
    error: str
    templates: tuple[Template, ...]
    extra: tuple[str, ...] = ()  # other approaches the library has for this error

    def approaches(self) -> tuple[str, ...]:
        seen: list[str] = []
        for t in self.templates:
            for a in (t.approach, *t.alternatives):
                if a not in seen:
                    seen.append(a)
        for a in self.extra:
            if a not in seen:
                seen.append(a)
        return tuple(seen)


@dataclass(frozen=True)
class Done:
    """A module already made."""

    number: int
    approach: str
    branch: str = "first"


@dataclass(frozen=True)
class Reason:
    code: str
    n: int = 0  # the number of the module this reason is about
    prev: int = 0  # the module it follows

    def to_dict(self) -> dict[str, int | str]:
        return {"code": self.code, "n": self.n, "prev": self.prev}


@dataclass(frozen=True)
class NextModule:
    approach: str | None
    branch: str
    reason: Reason
    smaller: bool = False  # the smaller-step version of the same approach
    stop: str | None = None  # a STOP_* code when there is no next module
    fallback_from: tuple[str, ...] = field(
        default_factory=tuple
    )  # approaches skipped (already used)

    @property
    def stops(self) -> bool:
        return self.stop is not None


def _stop(code: str, n: int, prev: int) -> NextModule:
    return NextModule(None, "no_feedback", Reason("stop_" + code, n, prev), stop=code)


def next_module(
    plan: Plan,
    history: list[Done],
    previous_feedback: str | None,
    cap: int,
    *,
    past_end: bool = False,
) -> NextModule:
    """`history`: the modules already made, in order. `previous_feedback`: the answer on the last one
    (tried, partly, not_yet) or None. `past_end`: the track's end date has passed."""
    if previous_feedback is not None and previous_feedback not in states.ANSWERS:
        raise ValueError(f"feedback must be one of {states.ANSWERS} or None")
    n = len(history) + 1
    if not history:
        if not plan.templates:
            return _stop(STOP_EXHAUSTED, n, 0)
        return NextModule(plan.templates[0].approach, "first", Reason("first", n, 0))
    last = history[-1]
    if past_end:
        return _stop(STOP_END_DATE, n, last.number)
    if n > cap:
        return _stop(STOP_CAP, n, last.number)
    used = {d.approach for d in history}
    in_plan = [t.approach for t in plan.templates]

    if previous_feedback == "partly":
        # the same approach, smaller; the plan is rejoined by the next "tried" or silence
        return NextModule(last.approach, "partly", Reason("partly", n, last.number), smaller=True)

    if previous_feedback == "not_yet":
        template = next((t for t in plan.templates if t.approach == last.approach), None)
        candidates = [*(template.alternatives if template else ()), *plan.approaches()]
        pick = next((a for a in candidates if a not in used), None)
        if pick is None:
            return _stop(STOP_EXHAUSTED, n, last.number)
        skipped = tuple(a for a in candidates[: candidates.index(pick)] if a in used)
        return NextModule(pick, "not_yet", Reason("not_yet", n, last.number), fallback_from=skipped)

    # tried, or no answer by the due date: the planned next module. Silence is not "tried".
    branch = "tried" if previous_feedback == "tried" else "no_feedback"
    pick = next((a for a in in_plan if a not in used), None)
    if pick is None:
        # a plan that finished normally; if it only finished because of "not yet" detours the
        # remaining approaches are used up too, which is the same: nothing is left to give
        return _stop(STOP_DONE, n, last.number)
    return NextModule(pick, branch, Reason(branch, n, last.number))
