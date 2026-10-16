"""Diagnosis: the 2-item rule per child, and the class profile (prevalence, eligibility, track).

No rounding happens here; callers format. Teacher-facing text uses counts, never percentages.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from engine.bugs import classify, probes
from engine.model import (
    ChildDiagnosis,
    ClassProfile,
    ErrorCode,
    Form,
    ItemType,
    Mark,
    Reading,
)

# A child shows an error only if it appears on at least 2 of the items probing it
# (items 1-2: both; items 3-5: 2 of 3; items 7-10: 2 of 4).
MIN_HITS = 2
# A class is eligible for a track at p >= 25% (1 in 4) with at least 10 children checked.
MIN_PREVALENCE_NUMERATOR, MIN_PREVALENCE_DENOMINATOR = 1, 4
MIN_CHILDREN_CHECKED = 10
# PV-REVERSE is detected and counted, but no track exists for it yet.
TRACKED: tuple[ErrorCode, ...] = (
    ErrorCode.PV_HEARD,
    ErrorCode.ADD_NOCARRY,
    ErrorCode.SUB_SFL,
    ErrorCode.SUB_NODEC,
)


def probe_items(form: Form, code: ErrorCode) -> tuple[int, ...]:
    """Item numbers on this form that probe the error."""
    return tuple(item.n for item in form.items if code in probes(item))


def diagnose_child(form: Form, readings: Sequence[Reading]) -> ChildDiagnosis:
    """Apply the 2-item rule to one child's ten readings (in item order)."""
    if len(readings) != len(form.items):
        raise ValueError(f"expected {len(form.items)} answers, got {len(readings)}")
    marks = tuple(classify(item, r) for item, r in zip(form.items, readings, strict=True))
    hits: Counter[ErrorCode] = Counter()
    for mark in marks:
        if mark.kind is Mark.ERROR:
            hits.update(mark.codes)
    shows = frozenset(code for code, n in hits.items() if n >= MIN_HITS)
    anchor_wrong = any(
        item.type is ItemType.SUB_ANCHOR and mark.kind in (Mark.OTHER, Mark.ERROR)
        for item, mark in zip(form.items, marks, strict=True)
    )
    untracked = Counter(m.untracked for m in marks if m.untracked)
    return ChildDiagnosis(
        marks=marks,
        shows=shows,
        anchor_wrong=anchor_wrong,
        other_count=sum(m.kind is Mark.OTHER for m in marks),
        blank_count=sum(m.kind is Mark.BLANK for m in marks),
        unreadable_count=sum(m.kind is Mark.UNREADABLE for m in marks),
        untracked=dict(untracked),
    )


def class_profile(children: Sequence[ChildDiagnosis]) -> ClassProfile:
    """Class-level counts, prevalence, eligible errors and the chosen track.

    Children checked = every diagnosed child, including ones with blank or unreadable boxes.
    """
    checked = len(children)
    counts = {code: sum(code in c.shows for c in children) for code in ErrorCode}
    prevalence = {code: (n / checked if checked else 0.0) for code, n in counts.items()}
    eligible = tuple(
        code
        for code in ErrorCode
        if checked >= MIN_CHILDREN_CHECKED
        and counts[code] * MIN_PREVALENCE_DENOMINATOR >= checked * MIN_PREVALENCE_NUMERATOR
    )
    track = _choose_track(eligible, counts)
    untracked: Counter[str] = Counter()
    for c in children:
        untracked.update(c.untracked)
    return ClassProfile(
        children_checked=checked,
        counts=counts,
        prevalence=prevalence,
        eligible=eligible,
        track=track,
        anchor_wrong_count=sum(c.anchor_wrong for c in children),
        untracked=dict(untracked),
    )


def _choose_track(
    eligible: tuple[ErrorCode, ...], counts: dict[ErrorCode, int]
) -> ErrorCode | None:
    """PV-HEARD first, else the highest-p tracked error (ties: first in code order)."""
    candidates = [code for code in eligible if code in TRACKED]
    if ErrorCode.PV_HEARD in candidates:
        return ErrorCode.PV_HEARD
    if not candidates:
        return None
    return max(candidates, key=lambda code: (counts[code], -list(ErrorCode).index(code)))
