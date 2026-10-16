"""Mentor rules (CLAUDE.md section 5): proven, same-term candidate, comparison-group improver.

Exact arithmetic (fractions) at every boundary, so "15 points" and "half" are never off by a
float. Each check returns its reasons: one per rule, met or not, with the numbers behind it, so a
screen can say why a teacher was or was not suggested. No AI call is involved.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction

from engine.model import ErrorCode

PROVEN_MIN_PREV = Fraction(1, 4)  # last term p at least 25%
PROVEN_MIN_FALL_POINTS = 15  # this term fell at least 15 points ...
PROVEN_MIN_CHILDREN = 15  # ... with at least 15 children checked both times
CANDIDATE_MAX_P = Fraction(1, 20)  # p at most 5% ...
CANDIDATE_BLOCK_MIN_P = Fraction(1, 4)  # ... while the block average is at least 25%
CANDIDATE_MIN_CHILDREN = 10  # the same floor the check uses for eligibility


class MentorKind(StrEnum):
    PROVEN = "proven"
    IMPROVER = "improver"
    CANDIDATE = "candidate"


@dataclass(frozen=True)
class Reason:
    key: str
    met: bool
    facts: Mapping[str, object]


@dataclass(frozen=True)
class MentorCheck:
    kind: MentorKind
    qualifies: bool
    reasons: tuple[Reason, ...]


@dataclass(frozen=True)
class TermChange:
    """One class's counts for one error in two consecutive terms, plus her consent."""

    error: ErrorCode
    grade: int
    medium: str
    prev_children_showing: int
    prev_children_checked: int
    now_children_showing: int
    now_children_checked: int
    consent: bool


def _p(showing: int, checked: int) -> Fraction:
    return Fraction(showing, checked) if checked else Fraction(0)


def _bar_reasons(c: TermChange) -> list[Reason]:
    prev = _p(c.prev_children_showing, c.prev_children_checked)
    now = _p(c.now_children_showing, c.now_children_checked)
    fall_points = (prev - now) * 100
    enough = (
        c.prev_children_checked >= PROVEN_MIN_CHILDREN
        and c.now_children_checked >= PROVEN_MIN_CHILDREN
    )
    return [
        Reason(
            "prev_p_at_least_25",
            c.prev_children_checked > 0 and prev >= PROVEN_MIN_PREV,
            {"showing": c.prev_children_showing, "checked": c.prev_children_checked},
        ),
        Reason(
            "fall_at_least_15_points",
            fall_points >= PROVEN_MIN_FALL_POINTS,
            {"fall_points": float(fall_points)},
        ),
        Reason(
            "fall_at_least_half",
            c.prev_children_checked > 0 and now <= prev / 2,
            {"prev_showing": c.prev_children_showing, "now_showing": c.now_children_showing},
        ),
        Reason(
            "enough_children_both_terms",
            enough,
            {"prev_checked": c.prev_children_checked, "now_checked": c.now_children_checked},
        ),
    ]


def check_proven(c: TermChange, comparison_avg_fall_points: float | None) -> MentorCheck:
    """Proven mentor: her class fixed the error on the track, beating the comparison group."""
    fall_points = (
        _p(c.prev_children_showing, c.prev_children_checked)
        - _p(c.now_children_showing, c.now_children_checked)
    ) * 100
    beats = comparison_avg_fall_points is not None and fall_points > Fraction(
        comparison_avg_fall_points
    )
    reasons = [
        Reason("on_track", True, {"error": c.error.value}),
        *_bar_reasons(c),
        Reason(
            "beats_comparison",
            beats,
            {
                "fall_points": float(fall_points),
                "comparison_avg_fall_points": comparison_avg_fall_points,
            },
        ),
        Reason("consent", c.consent, {}),
    ]
    return MentorCheck(MentorKind.PROVEN, all(r.met for r in reasons), tuple(reasons))


def check_improver(c: TermChange) -> MentorCheck:
    """Comparison-group improver: met the proven bar on her own, without the track.

    The "beats the comparison group" rule is dropped: she is in the comparison group.
    """
    reasons = [*_bar_reasons(c), Reason("consent", c.consent, {})]
    return MentorCheck(MentorKind.IMPROVER, all(r.met for r in reasons), tuple(reasons))


def check_candidate(
    *,
    grade: int,
    medium: str,
    children_showing: int,
    children_checked: int,
    block_children_showing: int,
    block_children_checked: int,
    cohort_grade: int,
    cohort_medium: str,
    consent: bool,
) -> MentorCheck:
    """Same-term candidate: same grade and medium, p <= 5% while the block average is >= 25%.

    The cause is unverified, so a method interview comes first and the label stays "candidate".
    """
    p = _p(children_showing, children_checked)
    block = _p(block_children_showing, block_children_checked)
    reasons = [
        Reason(
            "same_grade_and_medium",
            grade == cohort_grade and medium == cohort_medium,
            {"grade": grade, "medium": medium},
        ),
        Reason(
            "enough_children_checked",
            children_checked >= CANDIDATE_MIN_CHILDREN,
            {"checked": children_checked},
        ),
        Reason(
            "p_at_most_5_percent",
            children_checked > 0 and p <= CANDIDATE_MAX_P,
            {"showing": children_showing, "checked": children_checked},
        ),
        Reason(
            "block_average_at_least_25_percent",
            block_children_checked > 0 and block >= CANDIDATE_BLOCK_MIN_P,
            {"showing": block_children_showing, "checked": block_children_checked},
        ),
        Reason("consent", consent, {}),
    ]
    return MentorCheck(MentorKind.CANDIDATE, all(r.met for r in reasons), tuple(reasons))


@dataclass(frozen=True)
class MentorRecord:
    """What the database keeps about a mentor, for the tier-1 lookup."""

    teacher_id: str
    class_id: str
    error: ErrorCode
    grade: int
    medium: str
    kind: MentorKind
    verified: bool


_KIND_ORDER = {MentorKind.PROVEN: 0, MentorKind.IMPROVER: 1, MentorKind.CANDIDATE: 2}


def find_mentors(
    records: Sequence[MentorRecord],
    error: ErrorCode,
    grade: int,
    medium: str,
    statuses: frozenset[MentorKind] = frozenset({MentorKind.PROVEN}),
    only_verified: bool = True,
) -> list[MentorRecord]:
    """Tier-1 lookup: an exact match on error, grade, medium, status and verified.

    Mirrors the SQL query P11 will run; proven first, then improver, then candidate.
    """
    hits = [
        r
        for r in records
        if r.error is error
        and r.grade == grade
        and r.medium == medium
        and r.kind in statuses
        and (r.verified or not only_verified)
    ]
    return sorted(hits, key=lambda r: (_KIND_ORDER[r.kind], r.teacher_id))
