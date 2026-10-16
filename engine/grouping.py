"""Grouping: one track per class, the waitlist split, cohorts, and the matched-group fallback.

Pure functions over class-level counts (all the server stores). Randomness is seeded, so the same
inputs and seed always give the same split. Every result carries the facts its one-line
explanation needs; the sentence itself is built later, from those facts.
"""

from __future__ import annotations

import random
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction

from engine.diagnosis import profile_from_counts
from engine.model import ErrorCode

COHORT_MIN = 15
COHORT_MAX = 20
PER_SCHOOL_CAP = 2
STRATA = 3
MATCH_WITHIN_POINTS = 5


class Arm(StrEnum):
    THIS_TERM = "this_term"
    NEXT_TERM = "next_term"  # the waitlist: becomes the comparison group


@dataclass(frozen=True)
class ClassRecord:
    """One class's check result for one term: counts only, never per-child data."""

    class_id: str
    school_id: str
    block_id: str
    school_type: str
    grade: int
    medium: str
    children_checked: int
    counts: Mapping[ErrorCode, int]


@dataclass(frozen=True)
class TrackAssignment:
    class_id: str
    school_id: str
    block_id: str
    school_type: str
    grade: int
    medium: str
    error: ErrorCode
    children_checked: int
    children_showing: int
    reason: str  # "pv_heard_first" or "highest_p"

    @property
    def baseline_p(self) -> float:
        return self.children_showing / self.children_checked

    def facts(self) -> dict[str, object]:
        return {
            "class_id": self.class_id,
            "error": self.error.value,
            "children_checked": self.children_checked,
            "children_showing": self.children_showing,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class WaitlistEntry:
    assignment: TrackAssignment
    arm: Arm
    stratum: int  # 0 = lowest third of baseline p

    def facts(self) -> dict[str, object]:
        return {**self.assignment.facts(), "arm": self.arm.value, "stratum": self.stratum}


@dataclass(frozen=True)
class Cohort:
    cohort_id: str
    error: ErrorCode
    grade: int
    medium: str
    block_id: str | None  # None when formed across blocks
    class_ids: tuple[str, ...]
    cross_block: bool
    undersized: bool
    mentor_slot: bool = True

    def facts(self) -> dict[str, object]:
        return {
            "cohort_id": self.cohort_id,
            "error": self.error.value,
            "size": len(self.class_ids),
            "cross_block": self.cross_block,
            "undersized": self.undersized,
        }


@dataclass(frozen=True)
class CohortPlan:
    cohorts: tuple[Cohort, ...]
    unplaced: tuple[tuple[str, str], ...]  # (class_id, reason: "school_cap" or "cohort_full")


def assign_tracks(records: Sequence[ClassRecord]) -> list[TrackAssignment]:
    """Each eligible class gets one track: PV-HEARD first, else its highest-p error."""
    out: list[TrackAssignment] = []
    for r in records:
        profile = profile_from_counts(r.children_checked, r.counts)
        if profile.track is None:
            continue
        reason = "pv_heard_first" if profile.track is ErrorCode.PV_HEARD else "highest_p"
        out.append(
            TrackAssignment(
                class_id=r.class_id,
                school_id=r.school_id,
                block_id=r.block_id,
                school_type=r.school_type,
                grade=r.grade,
                medium=r.medium,
                error=profile.track,
                children_checked=r.children_checked,
                children_showing=profile.counts[profile.track],
                reason=reason,
            )
        )
    return out


def _tercile_chunks(n: int) -> list[tuple[int, int]]:
    """Contiguous (start, end) chunks for min(3, n) strata, sizes as equal as possible."""
    k = min(STRATA, n)
    base, extra = divmod(n, k)
    chunks, start = [], 0
    for i in range(k):
        size = base + (1 if i < extra else 0)
        chunks.append((start, start + size))
        start += size
    return chunks


def split_waitlist(assignments: Sequence[TrackAssignment], seed: int) -> list[WaitlistEntry]:
    """Randomly assign eligible teachers to this term or next, stratified by baseline p.

    Teachers with the same track, grade and medium form one group; the group is cut into terciles
    of baseline p, and each tercile is split as evenly as possible (the odd one out is random).
    """
    groups: dict[tuple[str, int, str], list[TrackAssignment]] = defaultdict(list)
    for a in assignments:
        groups[(a.error.value, a.grade, a.medium)].append(a)
    out: list[WaitlistEntry] = []
    for key in sorted(groups):
        members = sorted(
            groups[key],
            key=lambda a: (Fraction(a.children_showing, a.children_checked), a.class_id),
        )
        for stratum, (start, end) in enumerate(_tercile_chunks(len(members))):
            chunk = members[start:end]
            rng = random.Random(f"{seed}|{key[0]}|{key[1]}|{key[2]}|{stratum}")
            rng.shuffle(chunk)
            this_term = len(chunk) // 2 + (rng.random() < 0.5 if len(chunk) % 2 else 0)
            for i, a in enumerate(chunk):
                arm = Arm.THIS_TERM if i < this_term else Arm.NEXT_TERM
                out.append(WaitlistEntry(a, arm, stratum))
    return sorted(out, key=lambda e: e.assignment.class_id)


def _place(
    pool: list[WaitlistEntry],
    seed_text: str,
    error: ErrorCode,
    grade: int,
    medium: str,
    block_id: str | None,
    cross_block: bool,
    schools: Mapping[str, str],
) -> tuple[list[Cohort], list[tuple[str, str]]]:
    n = len(pool)
    if n == 0:
        return [], []
    k = max(1, n // COHORT_MIN)  # as many cohorts as keep every cohort at 15 or more
    rng = random.Random(seed_text)
    order = sorted(pool, key=lambda e: e.assignment.class_id)
    rng.shuffle(order)
    members: list[list[str]] = [[] for _ in range(k)]
    school_counts: list[dict[str, int]] = [defaultdict(int) for _ in range(k)]
    unplaced: list[tuple[str, str]] = []
    for e in order:
        cid, school = e.assignment.class_id, schools[e.assignment.class_id]
        open_slots = [i for i in range(k) if len(members[i]) < COHORT_MAX]
        if not open_slots:
            unplaced.append((cid, "cohort_full"))
            continue
        allowed = [i for i in open_slots if school_counts[i][school] < PER_SCHOOL_CAP]
        if not allowed:
            unplaced.append((cid, "school_cap"))
            continue
        i = min(allowed, key=lambda j: (len(members[j]), j))
        members[i].append(cid)
        school_counts[i][school] += 1
    cohorts = [
        Cohort(
            cohort_id=f"{error.value}-g{grade}-{medium}-{block_id or 'X'}-{i + 1}",
            error=error,
            grade=grade,
            medium=medium,
            block_id=block_id,
            class_ids=tuple(sorted(ids)),
            cross_block=cross_block,
            undersized=len(ids) < COHORT_MIN,
        )
        for i, ids in enumerate(members)
        if ids
    ]
    return cohorts, unplaced


def form_cohorts(entries: Sequence[WaitlistEntry], arm: Arm, seed: int) -> CohortPlan:
    """Cohorts of 15 to 20 from one arm, at most 2 per school, one mentor slot each.

    A block with fewer than 15 eligible teachers for a track is pooled with the other short blocks
    (cross-block); a pool still under 15 becomes one undersized cohort, which pilots expect.
    Teachers that do not fit (school cap, cohort full) are returned as unplaced for the next cohort.
    """
    chosen = [e for e in entries if e.arm is arm]
    schools = {e.assignment.class_id: e.assignment.school_id for e in chosen}
    by_group: dict[tuple[str, int, str], list[WaitlistEntry]] = defaultdict(list)
    for e in chosen:
        a = e.assignment
        by_group[(a.error.value, a.grade, a.medium)].append(e)
    cohorts: list[Cohort] = []
    unplaced: list[tuple[str, str]] = []
    for code, grade, medium in sorted(by_group):
        error = ErrorCode(code)
        by_block: dict[str, list[WaitlistEntry]] = defaultdict(list)
        for e in by_group[(code, grade, medium)]:
            by_block[e.assignment.block_id].append(e)
        short: list[WaitlistEntry] = []
        for block in sorted(by_block):
            if len(by_block[block]) >= COHORT_MIN:
                c, u = _place(
                    by_block[block],
                    f"{seed}|{code}|{grade}|{medium}|{block}",
                    error,
                    grade,
                    medium,
                    block,
                    False,
                    schools,
                )
                cohorts += c
                unplaced += u
            else:
                short += by_block[block]
        c, u = _place(
            short,
            f"{seed}|{code}|{grade}|{medium}|cross",
            error,
            grade,
            medium,
            None,
            True,
            schools,
        )
        cohorts += c
        unplaced += u
    return CohortPlan(tuple(cohorts), tuple(sorted(unplaced)))


def matched_comparison(
    target: TrackAssignment, candidates: Sequence[TrackAssignment]
) -> list[TrackAssignment]:
    """Fallback comparison group when there is no waitlist.

    Same error, grade, medium and school type, with baseline p within 5 points (exact arithmetic),
    closest first.
    """
    p0 = Fraction(target.children_showing, target.children_checked)
    scored: list[tuple[Fraction, str, TrackAssignment]] = []
    for c in candidates:
        if c.class_id == target.class_id:
            continue
        same = (c.error, c.grade, c.medium, c.school_type) == (
            target.error,
            target.grade,
            target.medium,
            target.school_type,
        )
        gap = abs(Fraction(c.children_showing, c.children_checked) - p0)
        if same and gap * 100 <= MATCH_WITHIN_POINTS:
            scored.append((gap, c.class_id, c))
    return [c for _, _, c in sorted(scored, key=lambda t: (t[0], t[1]))]
