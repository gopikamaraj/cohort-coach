"""Did the track work? Two methods, one verdict vocabulary. Code computes; no AI states a number.

Block scale: Δp(track classes) − Δp(comparison classes), 95% percentile bootstrap over classes.
Pilot scale: extra fall over untrained errors, plus an exact McNemar test on Fixed vs New.
Verdicts are per track version, never per teacher. Percentages are for officer views only; the
points here are percentage points of class prevalence.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from fractions import Fraction
from math import comb

import numpy as np

from engine.grouping import ClassRecord
from engine.model import ErrorCode

# Block scale
MIN_CLASSES_PER_ARM = 15
WORKING_MIN_FALL_POINTS = 10.0
NOT_WORKING_FALL_BELOW_POINTS = 5.0
CI_LEVEL = 0.95
# Pilot scale
PILOT_UNTRAINED_MIN_PRE_P = 0.10
PILOT_WORKING_MIN_EXTRA_FALL = 10.0
PILOT_NOT_WORKING_EXTRA_FALL_BELOW = 5.0
PILOT_ALPHA = 0.05
# Any figure covering fewer than this many classes is hidden from officer views.
MIN_CLASSES_SHOWN = 5


class Verdict(StrEnum):
    WORKING = "working"
    NOT_WORKING = "not_working"
    INCONCLUSIVE = "inconclusive"


class Group(StrEnum):
    TRACK = "track"
    COMPARISON = "comparison"


def confidence_note(n_classes: int) -> str | None:
    """A small-sample note, worded the same everywhere: 'from 3 classes, read as directional'."""
    if n_classes >= MIN_CLASSES_PER_ARM:
        return None
    return f"from {n_classes} classes, read as directional"


# --- block scale -------------------------------------------------------------------------


@dataclass(frozen=True)
class ClassChange:
    """One class's change in prevalence of the track's error, in percentage points."""

    class_id: str
    group: Group
    delta_points: float


@dataclass(frozen=True)
class BlockEffect:
    version: str
    verdict: Verdict
    reason: str
    estimate_points: float | None  # negative = the track classes fell more
    ci_low: float | None
    ci_high: float | None
    n_track: int
    n_comparison: int
    mean_delta_track: float | None
    mean_delta_comparison: float | None
    confidence_note: str | None

    @property
    def hidden(self) -> bool:
        """True when either arm covers fewer than 5 classes: officer views must not show it."""
        return min(self.n_track, self.n_comparison) < MIN_CLASSES_SHOWN

    def facts(self) -> dict[str, object]:
        return {
            "version": self.version,
            "verdict": self.verdict.value,
            "reason": self.reason,
            "estimate_points": self.estimate_points,
            "ci_low": self.ci_low,
            "ci_high": self.ci_high,
            "n_track": self.n_track,
            "n_comparison": self.n_comparison,
            "mean_delta_track": self.mean_delta_track,
            "mean_delta_comparison": self.mean_delta_comparison,
        }


def block_effect(
    version: str, changes: Sequence[ClassChange], *, B: int = 2000, seed: int = 0
) -> BlockEffect:
    """Effect of one track version at block scale, with a 95% percentile bootstrap over classes."""
    track = np.array([c.delta_points for c in changes if c.group is Group.TRACK], dtype=float)
    comp = np.array([c.delta_points for c in changes if c.group is Group.COMPARISON], dtype=float)
    n_t, n_c = len(track), len(comp)
    note = confidence_note(min(n_t, n_c))
    if n_t == 0 or n_c == 0:
        return BlockEffect(
            version,
            Verdict.INCONCLUSIVE,
            "too_few_classes",
            None,
            None,
            None,
            n_t,
            n_c,
            None,
            None,
            note,
        )
    mean_t, mean_c = float(track.mean()), float(comp.mean())
    estimate = round(mean_t - mean_c, 9)
    rng = np.random.default_rng(seed)
    boot_t = track[rng.integers(0, n_t, size=(B, n_t))].mean(axis=1)
    boot_c = comp[rng.integers(0, n_c, size=(B, n_c))].mean(axis=1)
    lo, hi = np.percentile(boot_t - boot_c, [100 * (1 - CI_LEVEL) / 2, 100 * (1 + CI_LEVEL) / 2])
    ci_low, ci_high = round(float(lo), 9), round(float(hi), 9)
    if min(n_t, n_c) < MIN_CLASSES_PER_ARM:
        verdict, reason = Verdict.INCONCLUSIVE, "too_few_classes"
    elif ci_high < 0 and estimate <= -WORKING_MIN_FALL_POINTS:
        verdict, reason = Verdict.WORKING, "ci_below_zero_and_fall_at_least_10"
    elif estimate > -NOT_WORKING_FALL_BELOW_POINTS:
        verdict, reason = Verdict.NOT_WORKING, "fall_below_5_or_rise"
    else:
        verdict, reason = Verdict.INCONCLUSIVE, "between_the_bars"
    return BlockEffect(
        version, verdict, reason, estimate, ci_low, ci_high, n_t, n_c, mean_t, mean_c, note
    )


def class_changes(
    error: ErrorCode,
    before: Mapping[str, ClassRecord],
    after: Mapping[str, ClassRecord],
    groups: Mapping[str, Group],
) -> list[ClassChange]:
    """Per-class change in prevalence of `error` (points) for the classes listed in `groups`.

    Classes missing a term, or with no children checked in either term, are skipped.
    """
    out: list[ClassChange] = []
    for class_id, group in sorted(groups.items()):
        b, a = before.get(class_id), after.get(class_id)
        if b is None or a is None or not b.children_checked or not a.children_checked:
            continue
        p0 = Fraction(b.counts.get(error, 0), b.children_checked)
        p1 = Fraction(a.counts.get(error, 0), a.children_checked)
        out.append(ClassChange(class_id, group, float((p1 - p0) * 100)))
    return out


# --- pilot scale -------------------------------------------------------------------------


@dataclass(frozen=True)
class PairedTable:
    still: int  # showed the error before and after
    fixed: int  # before yes, after no
    new: int  # before no, after yes
    never: int  # neither time
    pre_only: int  # tested before only (dropped)
    post_only: int  # tested after only (dropped)

    @property
    def paired(self) -> int:
        return self.still + self.fixed + self.new + self.never


def paired_table(pre: Mapping[str, bool], post: Mapping[str, bool]) -> PairedTable:
    """Pair children by key (roll number) who were present at both tests.

    Pure and local: in production it runs on the phone or in a local script, never on the server.
    """
    both = pre.keys() & post.keys()
    still = sum(pre[k] and post[k] for k in both)
    fixed = sum(pre[k] and not post[k] for k in both)
    new = sum(not pre[k] and post[k] for k in both)
    never = len(both) - still - fixed - new
    return PairedTable(still, fixed, new, never, len(pre.keys() - both), len(post.keys() - both))


def mcnemar_exact(fixed: int, new: int) -> float:
    """Two-sided exact binomial test on the discordant pairs. (12, 2) -> 0.012939453125."""
    if fixed < 0 or new < 0:
        raise ValueError("counts cannot be negative")
    n = fixed + new
    if n == 0:
        return 1.0
    tail = sum(comb(n, i) for i in range(min(fixed, new) + 1))
    return float(min(Fraction(1), Fraction(2 * tail, 2**n)))


@dataclass(frozen=True)
class PilotExtraFall:
    trained_fall: float
    baseline_fall: float | None  # None when no untrained error had p >= 10% at pre-test
    extra_fall: float | None
    untrained_used: tuple[ErrorCode, ...]


def pilot_extra_fall(
    pre: Mapping[ErrorCode, float],
    post: Mapping[ErrorCode, float],
    trained: ErrorCode,
    extra_baseline_falls: Sequence[float] = (),
) -> PilotExtraFall:
    """Trained error's fall minus the mean fall of untrained errors that had p >= 10% at pre-test.

    Falls are in percentage points. `extra_baseline_falls` adds the natural change of an error a
    class qualified for but was not trained on. With no baseline at all, extra fall is None.
    """
    trained_fall = (pre.get(trained, 0.0) - post.get(trained, 0.0)) * 100
    used = tuple(
        e for e in ErrorCode if e is not trained and pre.get(e, 0.0) >= PILOT_UNTRAINED_MIN_PRE_P
    )
    falls = [(pre[e] - post.get(e, 0.0)) * 100 for e in used] + list(extra_baseline_falls)
    if not falls:
        return PilotExtraFall(trained_fall, None, None, used)
    baseline = sum(falls) / len(falls)
    return PilotExtraFall(trained_fall, baseline, trained_fall - baseline, used)


def pilot_verdict(extra_fall: float | None, mcnemar_p: float | None) -> Verdict:
    """Working: extra fall >= 10 and p < 0.05. Not working: extra fall < 5 or a rise."""
    if extra_fall is None:
        return Verdict.INCONCLUSIVE
    if extra_fall < PILOT_NOT_WORKING_EXTRA_FALL_BELOW:
        return Verdict.NOT_WORKING
    if (
        extra_fall >= PILOT_WORKING_MIN_EXTRA_FALL
        and mcnemar_p is not None
        and mcnemar_p < PILOT_ALPHA
    ):
        return Verdict.WORKING
    return Verdict.INCONCLUSIVE
