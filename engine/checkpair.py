"""Pair a pre-test with its post-test and count what changed, by competency.

Children are matched by position in roll order (the same rule the phone uses), so no identifier is
ever needed: the only inputs are the two sets of typed boxes, and the result holds counts and a
sample-size flag, never a row, a position or a name. A child who was absent in either check, who has
nothing entered in either, or who has no partner because one check is shorter, is left out and
counted separately.

C1 place value (PV-HEARD, PV-REVERSE), C2 addition with carrying (ADD-NOCARRY), C3 subtraction with
borrowing (SUB-SFL, SUB-NODEC). A child is "flagged" for a competency when the 2-item rule says they
show any error of that competency. The TypeScript port (apps/pwa/src/lib/checks.ts) is tested
against tests/fixtures/check_pairing_cases.json, which this module's tests write.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence
from dataclasses import asdict, dataclass

from engine.diagnosis import diagnose_child
from engine.model import ErrorCode, Form
from engine.normalize import normalize_answer

COMPETENCIES: dict[str, tuple[ErrorCode, ...]] = {
    "C1": (ErrorCode.PV_HEARD, ErrorCode.PV_REVERSE),
    "C2": (ErrorCode.ADD_NOCARRY,),
    "C3": (ErrorCode.SUB_SFL, ErrorCode.SUB_NODEC),
}
SMALL_SAMPLE_BELOW = 10


@dataclass(frozen=True)
class Change:
    flagged_before: int
    fixed: int  # flagged before, not flagged after
    still_flagged: int
    newly_flagged: int  # not flagged before, flagged after


@dataclass(frozen=True)
class Pairing:
    paired: int
    excluded_absent: int
    excluded_not_entered: int
    excluded_unmatched: int
    small_sample: bool
    by_competency: dict[str, Change]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _entered(row: Sequence[str]) -> bool:
    return any(cell != "" for cell in row)


def _flags(form: Form, row: Sequence[str]) -> set[str]:
    shown = diagnose_child(form, [normalize_answer(cell) for cell in row]).shows
    return {name for name, codes in COMPETENCIES.items() if any(c in shown for c in codes)}


def pair_checks(
    pre_form: Form,
    pre_rows: Sequence[Sequence[str]],
    post_form: Form,
    post_rows: Sequence[Sequence[str]],
    pre_absent: Collection[int] = (),
    post_absent: Collection[int] = (),
) -> Pairing:
    """`*_absent` hold roll positions (0-based) she skipped because the child was away."""
    common = min(len(pre_rows), len(post_rows))
    tally = {name: [0, 0, 0, 0] for name in COMPETENCIES}  # before, fixed, still, new
    paired = absent = not_entered = 0
    for i in range(common):
        if i in pre_absent or i in post_absent:
            absent += 1
        elif not (_entered(pre_rows[i]) and _entered(post_rows[i])):
            not_entered += 1
        else:
            paired += 1
            before, after = _flags(pre_form, pre_rows[i]), _flags(post_form, post_rows[i])
            for name in COMPETENCIES:
                t = tally[name]
                if name in before:
                    t[0] += 1
                    t[1 if name not in after else 2] += 1
                elif name in after:
                    t[3] += 1
    return Pairing(
        paired=paired,
        excluded_absent=absent,
        excluded_not_entered=not_entered,
        excluded_unmatched=abs(len(pre_rows) - len(post_rows)),
        small_sample=paired < SMALL_SAMPLE_BELOW,
        by_competency={name: Change(*t) for name, t in tally.items()},
    )
