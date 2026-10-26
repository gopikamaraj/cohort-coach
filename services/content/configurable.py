"""The few thresholds that may be changed, each with a safe range (addendum v3.1 D3).

A change is a new version of a `setting` through the same two keys as any other content: the
coach approves it, the officer switches it on. A value outside its range is refused, and a rule
that is not listed here has no write route at all (eligibility and the verdict rules are fixed in
code: changing them would change what the evaluation means).

TODO-HUMAN(Seema): confirm these ranges. They are the build's first proposal.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from services.content import versions


class NotConfigurable(ValueError):
    """The rule is fixed in code, or does not exist."""


class OutOfRange(ValueError):
    """The value is outside the safe range, or is not a whole number."""


@dataclass(frozen=True)
class Setting:
    key: str
    low: int
    high: int
    default: int
    unit: str


CONFIGURABLE: dict[str, Setting] = {
    s.key: s
    for s in (
        Setting("stage_routine_threshold_pct", 20, 40, 25, "% of children checked"),
        Setting("stage_routine_min_checked", 8, 20, 10, "children checked"),
        Setting("stage_routine_seconds", 30, 60, 60, "seconds added to a lesson"),
        Setting("practice_turn_cap", 20, 40, 40, "turns in a Practice Class session"),
    )
}

# Fixed in code. They appear here only so a test can prove they have no write route.
FIXED: dict[str, str] = {
    "eligibility_prevalence_pct": "25% of children checked (engine/grouping.py)",
    "eligibility_min_children": "10 children checked (engine/grouping.py)",
    "verdict_rules": "Working / Not working / Inconclusive (engine/evaluation.py)",
}

SETTING_TYPE = "setting"


def _check(key: str, value: object) -> Setting:
    spec = CONFIGURABLE.get(key)
    if spec is None:
        raise NotConfigurable(f"{key} cannot be changed.")
    if isinstance(value, bool) or not isinstance(value, int):
        raise OutOfRange(f"{key} must be a whole number between {spec.low} and {spec.high}.")
    if not spec.low <= value <= spec.high:
        raise OutOfRange(f"{key} must be between {spec.low} and {spec.high}.")
    return spec


def propose(db: Session, key: str, value: int, actor: str, role: str) -> versions.ContentVersion:
    """A proposed change, already sent for review. Nothing changes until both keys turn."""
    _check(key, value)
    v = versions.create_draft(db, SETTING_TYPE, key, {"value": value}, actor, role)
    return versions.submit_for_review(db, v.id, actor, role)


def effective_value(db: Session, key: str) -> int:
    spec = CONFIGURABLE[key]
    active = versions.active_version(db, SETTING_TYPE, key)
    if active is None:
        return spec.default
    return int(active.body["value"])
