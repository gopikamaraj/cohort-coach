"""No lesson, practice set, script, model run, hint or worked example may hold a check item.

A check item is any item of Form A or Form B of the pilot test: the same two numbers in either
order with either operation, or a dictation number (as digits or as the spoken words). The list is
read from `docs/design/pilot_forms.golden.json` at run time, so it cannot drift from the forms.
"""

from __future__ import annotations

import json
import re
from functools import cache
from pathlib import Path
from typing import Any

from ai.validators import Violation
from ai.validators._data import ascii_digits

GOLDEN = Path(__file__).resolve().parents[2] / "docs" / "design" / "pilot_forms.golden.json"
SCAN_SUFFIXES = {".yaml", ".yml", ".md", ".json", ".txt"}
# Rows of made-up answer sheets are test data (what a child wrote), never teaching content: they
# necessarily hold the printed items' answers. Nothing else is exempt.
EXEMPT = frozenset({"demo/sample_sheets.v1.yaml"})

_UNITS = {
    w: i
    for i, w in enumerate(
        "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
        "fifteen sixteen seventeen eighteen nineteen".split()
    )
}
_TENS = {
    w: 10 * i
    for i, w in enumerate("_ _ twenty thirty forty fifty sixty seventy eighty ninety".split())
    if w != "_"
}
_WORD = "|".join([*_UNITS, *_TENS, "hundred"])
_WORDS = re.compile(rf"\b(?:{_WORD})(?:(?:[-\s]+and)?[-\s]+(?:{_WORD}))*\b", re.I)
_DIGITS = re.compile(r"(?<!\d)\d+(?!\d)")
_SEGMENT = re.compile(r"[.?!।\n;]+")
_GAP = re.compile(
    r"\s*(?:[+\-−–]|plus|minus|add|added\s+to|from|take\s+away|less|subtract)\s*", re.I
)


@cache
def _golden() -> dict[str, Any]:
    return json.loads(GOLDEN.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


@cache
def _by_pair() -> dict[frozenset[int], tuple[str, ...]]:
    out: dict[frozenset[int], list[str]] = {}
    for form, data in _golden()["forms"].items():
        for item in data["items"]:
            if "a" in item and "b" in item:
                out.setdefault(frozenset((item["a"], item["b"])), []).append(
                    f"Form {form} item {item['n']}"
                )
    return {k: tuple(v) for k, v in out.items()}


def forbidden_pairs() -> set[frozenset[int]]:
    return set(_by_pair())


def dictation_numbers() -> set[int]:
    return {
        int(item["value"])
        for data in _golden()["forms"].values()
        for item in data["items"]
        if item["type"] == "dictation"
    }


@cache
def _dictation_phrases() -> dict[str, str]:
    """Spoken forms of the dictation numbers, from the forms' prompts (English and Hindi)."""
    out: dict[str, str] = {}
    for form, data in _golden()["forms"].items():
        for item in data["items"]:
            if item["type"] == "dictation":
                for phrase in item["prompt"].values():
                    out[str(phrase).casefold()] = f"Form {form} item {item['n']}"
    return out


def _words_to_int(text: str) -> int | None:
    total = current = 0
    seen = False
    for w in re.split(r"[-\s]+", text.casefold()):
        if w == "and":
            continue
        if w in _UNITS:
            current += _UNITS[w]
        elif w in _TENS:
            current += _TENS[w]
        elif w == "hundred":
            current = max(current, 1) * 100
            total += current
            current = 0
        else:
            return None
        seen = True
    return total + current if seen else None


def _numbers(segment: str) -> list[tuple[int, int, int]]:
    """(start, end, value) for each number in the segment, as digits or English words."""
    found = [(m.start(), m.end(), int(m.group())) for m in _DIGITS.finditer(segment)]
    for m in _WORDS.finditer(segment):
        v = _words_to_int(m.group())
        if v is not None:
            found.append((m.start(), m.end(), v))
    return sorted(found)


def check_pair(a: int, op: str, b: int) -> list[Violation]:
    """A structured item {a, op, b}: the order and the operation do not matter."""
    where = _by_pair().get(frozenset((a, b)))
    if where:
        return [Violation("check_item", f"{a} and {b} ({op}) is {' and '.join(where)}")]
    return []


def check_items(text: str) -> list[Violation]:
    out: list[Violation] = []
    plain = ascii_digits(text)
    for segment in _SEGMENT.split(plain):
        nums = _numbers(segment)
        for (_, e1, a), (s2, _, b) in zip(nums, nums[1:], strict=False):
            if _GAP.fullmatch(segment[e1:s2]):
                out += check_pair(a, "op", b)
        for _, _, value in nums:
            if value in dictation_numbers():
                out.append(Violation("check_item", f"{value} is a dictation item of Form A or B"))
    folded = plain.casefold()
    for phrase, where in _dictation_phrases().items():
        if phrase in folded:
            out.append(Violation("check_item", f"the spoken form of {where}"))
    seen: set[tuple[str, str]] = set()
    unique: list[Violation] = []
    for v in out:
        if (v.code, v.detail) not in seen:
            seen.add((v.code, v.detail))
            unique.append(v)
    return unique


def scan_content(root: Path) -> list[tuple[Path, list[Violation]]]:
    """Every content file under `root` that contains a check item (CI and the content gate)."""
    hits: list[tuple[Path, list[Violation]]] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix in SCAN_SUFFIXES:
            if path.relative_to(root).as_posix() in EXEMPT:
                continue
            v = check_items(path.read_text(encoding="utf-8"))
            if v:
                hits.append((path, v))
    return hits
