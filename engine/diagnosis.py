"""Diagnosis: the 2-item rule per child, and the class profile (prevalence, eligibility, track).

No rounding happens here; callers format. Teacher-facing text uses counts, never percentages.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import replace

from engine.bugs import classify, probes
from engine.model import (
    ChildDiagnosis,
    ClassProfile,
    ErrorCode,
    Form,
    Item,
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


def _carries(a: int, b: int) -> int:
    n, carry, total = 0, 0, 0
    while a or b:
        carry = 1 if a % 10 + b % 10 + carry >= 10 else 0
        total += carry
        a, b, n = a // 10, b // 10, n + 1
    return total


def _borrows(a: int, b: int) -> int:
    borrow, total = 0, 0
    while a or b:
        borrow = 1 if a % 10 - borrow < b % 10 else 0
        total += borrow
        a, b = a // 10, b // 10
    return total


def skill_family(item: Item) -> str:
    """The skill an item tests, worked out from its numbers: two items of one family test the same
    thing (38 + 47 and 46 + 28), while 246 + 178 (three digits, two carries) is a different one."""
    a, b = item.a, item.b
    width = len(str(max(a, b)))
    match item.type:
        case ItemType.DICTATION:
            return "dictate-zero" if "0" in str(a) else f"dictate-{width}d"
        case ItemType.ADD_CARRY:
            return f"add-{width}d-{_carries(a, b)}c"
        case ItemType.SUB_ANCHOR:
            return f"sub-{width}d-0b"
        case ItemType.SUB_BORROW:
            if width == 3 and (a // 10) % 10 == 0 and a % 10 < b % 10:
                return "sub-across-zero"
            return f"sub-{width}d-{_borrows(a, b)}b"


def single_probe_items(form: Form) -> dict[ErrorCode, frozenset[int]]:
    """Per error: the items that are the only item of their skill on this paper. The 2-item rule
    cannot be met on one of these skills, so a mistake there is "possible", never "shows"."""
    out: dict[ErrorCode, frozenset[int]] = {}
    for code in ErrorCode:
        fams: dict[str, list[int]] = {}
        for item in form.items:
            if code in probes(item):
                fams.setdefault(skill_family(item), []).append(item.n)
        out[code] = frozenset(ns[0] for ns in fams.values() if len(ns) == 1)
    return out


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
    single = single_probe_items(form)
    possible = frozenset(
        code
        for item, mark in zip(form.items, marks, strict=True)
        if mark.kind is Mark.ERROR
        for code in mark.codes
        if code not in shows and item.n in single.get(code, frozenset())
    )
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
        possible=possible,
    )


def class_profile(children: Sequence[ChildDiagnosis]) -> ClassProfile:
    """Class-level counts, prevalence, eligible errors and the chosen track.

    Children checked = every diagnosed child, including ones with blank or unreadable boxes.
    """
    counts = {code: sum(code in c.shows for c in children) for code in ErrorCode}
    untracked: Counter[str] = Counter()
    for c in children:
        untracked.update(c.untracked)
    profile = profile_from_counts(
        len(children),
        counts,
        anchor_wrong_count=sum(c.anchor_wrong for c in children),
        untracked=dict(untracked),
    )
    possible = {code: sum(code in c.possible for c in children) for code in ErrorCode}
    return replace(profile, possible_counts=possible)


def profile_from_counts(
    children_checked: int,
    counts: Mapping[ErrorCode, int],
    anchor_wrong_count: int = 0,
    untracked: Mapping[str, int] | None = None,
) -> ClassProfile:
    """The same profile from class-level counts alone: all the server ever stores."""
    full = {code: counts.get(code, 0) for code in ErrorCode}
    if any(n < 0 or n > children_checked for n in full.values()):
        raise ValueError("a count must be between 0 and the number of children checked")
    prevalence = {
        code: (n / children_checked if children_checked else 0.0) for code, n in full.items()
    }
    eligible = tuple(
        code
        for code in ErrorCode
        if children_checked >= MIN_CHILDREN_CHECKED
        and full[code] * MIN_PREVALENCE_DENOMINATOR >= children_checked * MIN_PREVALENCE_NUMERATOR
    )
    return ClassProfile(
        children_checked=children_checked,
        counts=full,
        prevalence=prevalence,
        eligible=eligible,
        track=_choose_track(eligible, full),
        anchor_wrong_count=anchor_wrong_count,
        untracked=dict(untracked or {}),
    )


def _choose_track(
    eligible: tuple[ErrorCode, ...], counts: Mapping[ErrorCode, int]
) -> ErrorCode | None:
    """PV-HEARD first, else the highest-p tracked error (ties: first in code order)."""
    candidates = [code for code in eligible if code in TRACKED]
    if ErrorCode.PV_HEARD in candidates:
        return ErrorCode.PV_HEARD
    if not candidates:
        return None
    return max(candidates, key=lambda code: (counts[code], -list(ErrorCode).index(code)))
