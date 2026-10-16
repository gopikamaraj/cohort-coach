"""Personal data in text: phone numbers, emails, 12-digit ID-like numbers, roster names.

Violations never repeat what they matched.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from ai.validators import Violation
from ai.validators._data import ascii_digits, tokens

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_DIGIT_RUN = re.compile(r"(?<![\d])\+?\d(?:[\d\s-]{6,}\d)(?![\d])")


def check_pii(text: str, roster_names: Iterable[str] = ()) -> list[Violation]:
    out: list[Violation] = []
    plain = ascii_digits(text)
    if _EMAIL.search(plain):
        out.append(Violation("pii_email"))
    kinds: set[str] = set()
    for run in _DIGIT_RUN.findall(plain):
        digits = re.sub(r"\D", "", run)
        if len(digits) == 10 and digits[0] in "6789":
            kinds.add("pii_phone")
        elif len(digits) == 12 and digits.startswith("91") and digits[2] in "6789":
            kinds.add("pii_phone")
        elif len(digits) == 12:
            kinds.add("pii_id_number")
    out.extend(Violation(k) for k in sorted(kinds))
    words = set(tokens(text))
    for name in roster_names:
        parts = tokens(name)
        if parts and all(p in words for p in parts):
            out.append(Violation("pii_roster_name"))
            break
    return out
