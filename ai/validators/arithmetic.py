"""Check "a - b = c" and "a + b = c" statements in text.

An intentional wrong child answer carries a tag right after it: "52 - 29 = 37 [child-wrong]".
"""

from __future__ import annotations

import re

from ai.validators import Violation
from ai.validators._data import ascii_digits

TAG = "[child-wrong]"
_STATEMENT = re.compile(
    r"(\d+)\s*([+\-−–×x*])\s*(\d+)\s*=\s*(\d+)(\s*\[child-wrong\])?",
)


def _apply(a: int, op: str, b: int) -> int:
    if op == "+":
        return a + b
    if op in "-−–":
        return a - b
    return a * b


def check_arithmetic(text: str) -> list[Violation]:
    out: list[Violation] = []
    for a, op, b, c, tag in _STATEMENT.findall(ascii_digits(text)):
        if tag:
            continue
        if _apply(int(a), op, int(b)) != int(c):
            out.append(Violation("arithmetic_wrong", f"{a} {op} {b} is not {c}"))
    return out


def strip_tags(text: str) -> str:
    """Remove the intentional-mistake tags before the text is shown."""
    return re.sub(r"\s*\[child-wrong\]", "", text)
