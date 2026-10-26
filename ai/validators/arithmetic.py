"""Check "a - b = c" and "a + b = c" statements in text.

An intentional wrong child answer carries a tag right after it: "52 - 29 = 37 [child-wrong]".
Authors may write it as "52 - 29 = [child: 37]"; normalise_child_tags turns that into the form
above before checking, and strip_child_tags removes the tag from what is shown or voiced.
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


_CHILD_TAG = re.compile(r"\[child:\s*(\d+)\s*\]")


def normalise_child_tags(text: str) -> str:
    """ "[child: 37]" -> "37 [child-wrong]", the form check_arithmetic understands."""
    return _CHILD_TAG.sub(lambda m: f"{m.group(1)} [child-wrong]", ascii_digits(text))


def strip_child_tags(text: str) -> str:
    """The text as shown or voiced: the tag removed, the child's answer kept."""
    return strip_tags(text)


def check_child_tags(text: str) -> list[Violation]:
    """A tag on an answer that is actually right would hide nothing but would mislead a reviewer."""
    out: list[Violation] = []
    for a, op, b, c, tag in _STATEMENT.findall(ascii_digits(text)):
        if tag and _apply(int(a), op, int(b)) == int(c):
            out.append(Violation("child_tag_is_correct", f"{a} {op} {b} is {c}: not a mistake"))
    return out
