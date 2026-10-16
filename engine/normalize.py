"""Raw answer-box text -> a number, "blank" or "unreadable"."""

from __future__ import annotations

from engine.model import Reading

_MAX_DIGITS = 9
_DEVANAGARI = "०१२३४५६७८९"
_TAMIL = "௦௧௨௩௪௫௬௭௮௯"
_TO_ASCII = {ord(d): str(i) for digits in (_DEVANAGARI, _TAMIL) for i, d in enumerate(digits)}


def normalize_answer(raw: str | None) -> Reading:
    """Map Devanagari and Tamil digits to ASCII and strip spaces.

    Empty -> "blank". Anything that is not only digits afterwards (letters, "?", signs,
    decimals, other scripts, absurdly long runs) -> "unreadable", for a human to check.
    """
    if raw is None:
        return "blank"
    text = "".join(raw.split()).translate(_TO_ASCII)
    if text == "":
        return "blank"
    if not (text.isascii() and text.isdigit()) or len(text) > _MAX_DIGITS:
        return "unreadable"
    return int(text)
