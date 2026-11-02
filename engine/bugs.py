"""The five error functions, and classification of one answer against an item.

Each error function is a pure `problem -> frozenset[int]` giving the answer a child with that
error would write. A function may return the correct answer when the error does not bite
(for example SUB-NODEC when nothing is borrowed); `error_answers` filters that out.
"""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from types import MappingProxyType

from engine.model import (
    ADD_WHOLE_ONES,
    AnswerMark,
    ErrorCode,
    Item,
    ItemType,
    Mark,
    Reading,
)

_NONE: frozenset[int] = frozenset()


def _digits(n: int) -> tuple[int, ...] | None:
    """Digits of a 2- or 3-digit number with no zero digit, else None."""
    if not (10 <= n <= 999):
        return None
    ds = tuple(int(c) for c in str(n))
    return None if 0 in ds else ds


def _tens_zero(n: int) -> tuple[int, int] | None:
    """(hundreds, ones) of a 3-digit number whose only zero is the tens digit (305), else None."""
    if not (100 <= n <= 999):
        return None
    h, t, o = (int(c) for c in str(n))
    return (h, o) if t == 0 and o != 0 else None


def pv_heard(n: int) -> frozenset[int]:
    """Writes the number the way it is said: forty-three -> 403; 346 -> 30046, 3046, 300406;
    three hundred and five -> 3005."""
    hz = _tens_zero(n)
    if hz is not None:
        return frozenset({int(f"{hz[0]}00{hz[1]}")})
    ds = _digits(n)
    if ds is None:
        return _NONE
    if len(ds) == 2:
        t, o = ds
        return frozenset({int(f"{t}0{o}")})
    h, t, o = ds
    return frozenset({int(f"{h}00{t}{o}"), int(f"{h}0{t}{o}"), int(f"{h}00{t}0{o}")})


def pv_reverse(n: int) -> frozenset[int]:
    """Swaps tens and ones: 43 -> 34; 346 -> 364; 305 -> 350."""
    hz = _tens_zero(n)
    if hz is not None:
        return frozenset({100 * hz[0] + 10 * hz[1]})
    ds = _digits(n)
    if ds is None:
        return _NONE
    if len(ds) == 2:
        t, o = ds
        return frozenset({10 * o + t})
    h, t, o = ds
    return frozenset({100 * h + 10 * o + t})


def heard_and_reversed(n: int) -> frozenset[int]:
    """Heard applied to the reversed number: 346 -> 30064, 3064, 300604. Counts for both."""
    out: set[int] = set()
    for rev in pv_reverse(n):
        out |= pv_heard(rev)
    return frozenset(out)


def _columns(a: int, b: int) -> tuple[list[int], list[int]]:
    """The digits of a and b by column, ones first, padded to the same length."""
    n = max(len(str(a)), len(str(b)))
    da = [int(c) for c in str(a).zfill(n)][::-1]
    db = [int(c) for c in str(b).zfill(n)][::-1]
    return da, db


def _from_columns(cols: list[int]) -> int:
    """Column results (ones first) written side by side; the leftmost may be two digits."""
    return int("".join(str(c) for c in reversed(cols)))


def add_nocarry(a: int, b: int) -> frozenset[int]:
    """Drops every carried ten: 47 + 25 -> 62; 246 + 178 -> 314. Each column's ones digit is
    written; the leftmost column is written whole (59 + 73 -> 122)."""
    if a < 100 and b < 100:
        return frozenset({10 * (a // 10 + b // 10) + (a % 10 + b % 10) % 10})
    da, db = _columns(a, b)
    cols = [(x + y) % 10 for x, y in zip(da[:-1], db[:-1], strict=True)] + [da[-1] + db[-1]]
    return frozenset({_from_columns(cols)})


def add_whole_ones(a: int, b: int) -> frozenset[int]:
    """Untracked: the whole ones total written in (38 + 47 -> 715). Only when the ones carry."""
    ones = a % 10 + b % 10
    if ones < 10:
        return _NONE
    return frozenset({100 * (a // 10 + b // 10) + ones})


def sub_sfl(a: int, b: int) -> frozenset[int]:
    """Smaller-from-larger in each column: 52 - 29 -> 37; 703 - 468 -> 365."""
    if a < 100 and b < 100:
        return frozenset({10 * abs(a // 10 - b // 10) + abs(a % 10 - b % 10)})
    da, db = _columns(a, b)
    return frozenset({_from_columns([abs(x - y) for x, y in zip(da, db, strict=True)])})


def sub_nodec(a: int, b: int) -> frozenset[int]:
    """Borrows a ten for the ones but does not reduce the tens digit: 52 - 29 -> 33.

    With three digits every other borrow is done right: 703 - 468 -> 245 (the zero becomes ten,
    taking one from the hundreds, but is not reduced for the ones) and 542 - 179 -> 373. On the
    pilot's real sheets this is the answer most children who went wrong on 703 - 468 wrote.
    """
    at, ao, bt, bo = a // 10, a % 10, b // 10, b % 10
    if ao < bo:
        return frozenset({10 * (at - bt) + (ao + 10 - bo)})
    return frozenset({a - b})


def correct_answer(item: Item) -> int:
    match item.type:
        case ItemType.DICTATION:
            return item.a
        case ItemType.ADD_CARRY:
            return item.a + item.b
        case ItemType.SUB_ANCHOR | ItemType.SUB_BORROW:
            return item.a - item.b


def probes(item: Item) -> tuple[ErrorCode, ...]:
    """The errors this item can show."""
    match item.type:
        case ItemType.DICTATION:
            return (ErrorCode.PV_HEARD, ErrorCode.PV_REVERSE)
        case ItemType.ADD_CARRY:
            return (ErrorCode.ADD_NOCARRY,)
        case ItemType.SUB_ANCHOR:
            return ()
        case ItemType.SUB_BORROW:
            return (ErrorCode.SUB_SFL, ErrorCode.SUB_NODEC)


def raw_error_answers(item: Item) -> dict[ErrorCode, frozenset[int]]:
    """Each probed error's answer set, unfiltered (may contain the correct answer)."""
    out: dict[ErrorCode, frozenset[int]] = {}
    for code in probes(item):
        match code:
            case ErrorCode.PV_HEARD:
                out[code] = pv_heard(item.a)
            case ErrorCode.PV_REVERSE:
                out[code] = pv_reverse(item.a)
            case ErrorCode.ADD_NOCARRY:
                out[code] = add_nocarry(item.a, item.b)
            case ErrorCode.SUB_SFL:
                out[code] = sub_sfl(item.a, item.b)
            case ErrorCode.SUB_NODEC:
                out[code] = sub_nodec(item.a, item.b)
    return out


def error_answers(item: Item) -> dict[ErrorCode, frozenset[int]]:
    """Wrong answers per probed error (the correct answer removed; empty sets dropped)."""
    correct = correct_answer(item)
    filtered = {c: s - {correct} for c, s in raw_error_answers(item).items()}
    return {c: s for c, s in filtered.items() if s}


def both_heard_and_reversed(item: Item) -> frozenset[int]:
    """Answers that count for PV-HEARD and PV-REVERSE at once (dictation items only)."""
    if item.type is not ItemType.DICTATION:
        return _NONE
    return heard_and_reversed(item.a) - {correct_answer(item)}


def untracked_signatures(item: Item) -> dict[str, frozenset[int]]:
    """Known untracked patterns, scored "other" but tallied (add-carry items only)."""
    if item.type is not ItemType.ADD_CARRY:
        return {}
    sigs = add_whole_ones(item.a, item.b)
    return {ADD_WHOLE_ONES: sigs} if sigs else {}


@lru_cache(maxsize=8192)
def _answer_codes(item: Item) -> Mapping[int, frozenset[ErrorCode]]:
    codes: dict[int, set[ErrorCode]] = {}
    for code, answers in error_answers(item).items():
        for ans in answers:
            codes.setdefault(ans, set()).add(code)
    for ans in both_heard_and_reversed(item):
        codes.setdefault(ans, set()).update({ErrorCode.PV_HEARD, ErrorCode.PV_REVERSE})
    return MappingProxyType({ans: frozenset(cs) for ans, cs in codes.items()})


def answer_codes(item: Item) -> Mapping[int, frozenset[ErrorCode]]:
    """Every wrong answer the item recognises -> the error codes it counts for (read-only)."""
    return _answer_codes(item)


def classify(item: Item, reading: Reading) -> AnswerMark:
    if reading == "blank":
        return AnswerMark(Mark.BLANK)
    if reading == "unreadable":
        return AnswerMark(Mark.UNREADABLE)
    if reading == correct_answer(item):
        return AnswerMark(Mark.CORRECT)
    codes = answer_codes(item).get(reading)
    if codes:
        return AnswerMark(Mark.ERROR, codes)
    for name, answers in untracked_signatures(item).items():
        if reading in answers:
            return AnswerMark(Mark.OTHER, untracked=name)
    return AnswerMark(Mark.OTHER)
