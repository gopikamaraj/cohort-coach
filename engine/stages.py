"""Stage of breakdown: where a child's errors most likely arose (addendum v3.1 section F).

Final answers cannot prove a cause, so every stage here is "most likely". Signature answers are
generated from each item, never typed in. Nothing per child leaves this module: `class_counts`
reduces a class to counts per (signature, stage). Pure: no I/O, no randomness.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from engine.bugs import (
    both_heard_and_reversed,
    correct_answer,
    error_answers,
    untracked_signatures,
)
from engine.model import Form, Item, ItemType, Reading


class Stage(StrEnum):
    INPUT_TEACHING = "Input (teaching)"
    INPUT_TEST = "Input (test)"
    CORE = "Core"
    OUTPUT = "Output"


# Every signature needs at least this many items (for dictation, both of the two items).
MIN_HITS = 2
NO_METHOD_ITEMS_7_10 = 3
ANCHOR = 6
_ADD_ITEMS = (3, 4, 5)
_SUB_ITEMS = (7, 8, 9, 10)

_STAGE_OF: dict[str, Stage] = {
    "PV-HEARD": Stage.CORE,
    "ADD-NOCARRY": Stage.CORE,
    "ADD-WHOLE-ONES": Stage.CORE,
    "SUB-SFL": Stage.CORE,
    "SUB-NODEC": Stage.CORE,
    "CORE-OFF1": Stage.CORE,
    "IN-OP": Stage.INPUT_TEST,
    "IN-OPND": Stage.INPUT_TEST,
    "IN-NEAR": Stage.INPUT_TEST,
    "OUT-REV": Stage.OUTPUT,
    "OUT-REC": Stage.OUTPUT,
    "NO-METHOD": Stage.INPUT_TEACHING,
}


def stage_rules() -> dict[str, object]:
    """The constants the phone needs to apply the stage rules (exported with the answer keys)."""
    return {
        "min_hits": MIN_HITS,
        "no_method_items_7_10": NO_METHOD_ITEMS_7_10,
        "anchor": ANCHOR,
        "add_items": list(_ADD_ITEMS),
        "sub_items": list(_SUB_ITEMS),
        "stage_of": {code: stage.value for code, stage in _STAGE_OF.items()},
        "pv_reverse": {"with_out_rev": Stage.OUTPUT.value, "otherwise": Stage.INPUT_TEST.value},
    }


def _rev(n: int) -> int:
    return int(str(n)[::-1])


def _near(n: int) -> frozenset[int]:
    """Off by one in exactly one digit, same length."""
    s = str(n)
    out: set[int] = set()
    for i, ch in enumerate(s):
        for d in (-1, 1):
            t = int(ch) + d
            if 0 <= t <= 9:
                v = s[:i] + str(t) + s[i + 1 :]
                if v[0] != "0":
                    out.add(int(v))
    return frozenset(out)


def _raw(item: Item) -> list[tuple[str, frozenset[int]]]:
    """Signature answer sets in priority order, before removing collisions."""
    c = correct_answer(item)
    out: list[tuple[str, frozenset[int]]] = []
    if item.type is ItemType.DICTATION:
        both = both_heard_and_reversed(item)
        for code, answers in error_answers(item).items():
            out.append((code.value, answers | both))
        out.append(("IN-NEAR", _near(item.a)))
        return out
    if item.type not in (ItemType.ADD_CARRY, ItemType.SUB_BORROW):
        return out
    add = item.type is ItemType.ADD_CARRY
    for code, answers in error_answers(item).items():
        out.append((code.value, answers))
    for name, answers in untracked_signatures(item).items():
        out.append((name, answers))
    out.append(("CORE-OFF1", frozenset({c - 1, c + 1})))
    out.append(("IN-OP", frozenset({abs(item.a - item.b)} if add else {item.a + item.b})))
    ops = {
        (x + y if add else x - y)
        for x, y in ((_rev(item.a), item.b), (item.a, _rev(item.b)), (_rev(item.a), _rev(item.b)))
    }
    out.append(("IN-OPND", frozenset(v for v in ops if v >= 0)))
    out.append(("OUT-REV", frozenset({_rev(c)})))
    return out


_EXISTING = {"PV-HEARD", "PV-REVERSE", "ADD-NOCARRY", "ADD-WHOLE-ONES", "SUB-SFL", "SUB-NODEC"}


def _resolved(item: Item) -> tuple[dict[str, frozenset[int]], dict[str, frozenset[int]]]:
    """(signature answers, answers dropped because they collided), by code."""
    c = correct_answer(item)
    kept: dict[str, frozenset[int]] = {}
    dropped: dict[str, frozenset[int]] = {}
    taken: set[int] = set()
    for code, answers in _raw(item):
        if code in _EXISTING:
            kept[code] = answers
            taken |= answers
            continue
        keep = answers - {c} - taken
        if answers - keep:
            dropped[code] = answers - keep
        kept[code] = keep
        taken |= keep
    return kept, dropped


def signature_answers(item: Item) -> dict[str, frozenset[int]]:
    """Each signature's answers on this item. Disjoint from each other and from the correct
    answer, except the designed PV-HEARD / PV-REVERSE overlap on dictation items."""
    return {k: v for k, v in _resolved(item)[0].items() if v}


def signature_overlaps(form: Form) -> dict[tuple[int, str], frozenset[int]]:
    """Answers a new signature lost to an earlier one on this form (empty on the real forms)."""
    return {
        (item.n, code): gone
        for item in form.items
        if item.n != ANCHOR
        for code, gone in _resolved(item)[1].items()
    }


@dataclass(frozen=True)
class StageResult:
    signatures: frozenset[str]
    signature_stages: frozenset[tuple[str, Stage]]
    stages: frozenset[Stage]
    not_attempted: bool
    anchor_wrong: bool
    no_method_possible: bool
    no_method_confirmed: bool
    missed_teaching: bool


def classify_child(
    form: Form,
    readings: Sequence[Reading],
    *,
    missed_teaching: bool = False,
    unreadable: int = 0,
    two_answers: int = 0,
) -> StageResult:
    """One child's stages from ten readings and the teacher's tags. Held in memory only."""
    if len(readings) != len(form.items):
        raise ValueError(f"expected {len(form.items)} answers, got {len(readings)}")
    hits: Counter[str] = Counter()
    unmatched: dict[int, bool] = {}
    blanks_7_10 = 0
    anchor_wrong = False
    for item, reading in zip(form.items, readings, strict=True):
        if reading in ("blank", "unreadable") or not isinstance(reading, int):
            if item.n in _SUB_ITEMS and reading == "blank":
                blanks_7_10 += 1
            continue
        if item.n == ANCHOR:
            anchor_wrong = reading != correct_answer(item)
            continue
        if reading == correct_answer(item):
            continue
        sigs = signature_answers(item)
        matched = [code for code, answers in sigs.items() if reading in answers]
        hits.update(matched)
        unmatched[item.n] = not matched
    sigs_found = {code for code, n in hits.items() if n >= MIN_HITS}
    wrong_7_10 = sum(1 for n in _SUB_ITEMS if unmatched.get(n))
    all_3_5 = all(unmatched.get(n) for n in _ADD_ITEMS)
    if wrong_7_10 >= NO_METHOD_ITEMS_7_10 or all_3_5:
        sigs_found.add("NO-METHOD")
    if unreadable + two_answers >= MIN_HITS:
        sigs_found.add("OUT-REC")
    pairs: set[tuple[str, Stage]] = set()
    for code in sigs_found:
        if code == "PV-REVERSE":
            stage = Stage.OUTPUT if "OUT-REV" in sigs_found else Stage.INPUT_TEST
        else:
            stage = _STAGE_OF[code]
        pairs.add((code, stage))
    return StageResult(
        signatures=frozenset(sigs_found),
        signature_stages=frozenset(pairs),
        stages=frozenset(s for _, s in pairs),
        not_attempted=blanks_7_10 >= NO_METHOD_ITEMS_7_10,
        anchor_wrong=anchor_wrong,
        no_method_possible="NO-METHOD" in sigs_found,
        no_method_confirmed="NO-METHOD" in sigs_found and missed_teaching,
        missed_teaching=missed_teaching,
    )


@dataclass(frozen=True)
class ClassStageCounts:
    """The only thing stored about stages: counts for the class, never a child."""

    checked: int
    missed_teaching: int
    not_attempted: int
    by_signature: dict[tuple[str, Stage], int]
    by_stage: dict[Stage, int]


def class_counts(results: Sequence[StageResult]) -> ClassStageCounts:
    """Counts per (signature, stage). Children tagged "missed the teaching" are counted on their
    own line and left out of the stage counts, so they do not inflate Core."""
    by_sig: Counter[tuple[str, Stage]] = Counter()
    by_stage: Counter[Stage] = Counter()
    for r in results:
        if r.missed_teaching:
            continue
        by_sig.update(r.signature_stages)
        by_stage.update(r.stages)
    return ClassStageCounts(
        checked=len(results),
        missed_teaching=sum(1 for r in results if r.missed_teaching),
        not_attempted=sum(1 for r in results if r.not_attempted),
        by_signature=dict(by_sig),
        by_stage=dict(by_stage),
    )
