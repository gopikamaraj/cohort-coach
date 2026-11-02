"""English number words written by a child, as a number: "Three hundred fourty six" -> 346.

Pure code. Children misspell ("fourty", "ninty", "hundered"), so each word is matched to the
nearest known word and a word that matches none makes the whole phrase unreadable (None): a
guess is never made. Words only; digits are read by call 8.
"""

from __future__ import annotations

import difflib
import re

_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19,
}  # fmt: skip
_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90,
}  # fmt: skip
_BIG = {"hundred": 100, "thousand": 1000}
_FILLER = {"and", "oh"}
_VOCAB = [*_UNITS, *_TENS, *_BIG, *_FILLER]
_ALIASES = {"fourty": "forty", "ninty": "ninety", "fifty": "fifty", "eight": "eight"}


def _word(w: str) -> str | None:
    w = _ALIASES.get(w, w)
    if w in _VOCAB:
        return w
    near = difflib.get_close_matches(w, _VOCAB, n=1, cutoff=0.8)
    return near[0] if near else None


def parse(text: str | None) -> int | None:
    """The number the words say, or None if any word is not a number word."""
    if not text:
        return None
    raw = re.findall(r"[a-z]+", text.lower())
    if not raw:
        return None
    words = []
    for w in raw:
        known = _word(w)
        if known is None:
            return None
        if known not in _FILLER:
            words.append(known)
    total = current = 0
    seen = False
    for w in words:
        seen = True
        if w in _UNITS:
            current += _UNITS[w]
        elif w in _TENS:
            current += _TENS[w]
        elif w == "hundred":
            current = max(current, 1) * 100
        else:  # thousand
            total += max(current, 1) * 1000
            current = 0
    return total + current if seen else None
