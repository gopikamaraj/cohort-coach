"""Numbers in AI text: extract digit numerals in three scripts, compare with an allowed set,
and find number words so text can be forced to digits."""

from __future__ import annotations

import re
from collections.abc import Iterable

from ai.validators import Violation
from ai.validators._data import ascii_digits, token_matches, tokens, word_list

_NUMBER = re.compile(r"\d+(?:,\d{2,3})*")
_SUFFIX = {"en": 0, "hi": 0, "ta": 3}


def extract_numbers(text: str) -> list[int]:
    """Every whole number in the text, in order. 1,234 is one number; 3.5 gives 3 and 5."""
    found = _NUMBER.findall(ascii_digits(text))
    return [int(n.replace(",", "")) for n in found]


def check_numbers(text: str, allowed: Iterable[int]) -> list[Violation]:
    """Every number in the text must be one the caller allowed (for example the engine's answer)."""
    ok = set(allowed)
    return [
        Violation("number_not_allowed", f"{n} is not an allowed number")
        for n in extract_numbers(text)
        if n not in ok
    ]


def find_number_words(text: str, lang: str) -> list[str]:
    """Number words in the text for this language (curated lists in content/lang/)."""
    suffix = _SUFFIX.get(lang, 0)
    words = word_list("lang/number_words.yaml", lang)
    return [t for t in tokens(text) if any(token_matches(t, w, suffix=suffix) for w in words)]


def check_digits_only(text: str, lang: str) -> list[Violation]:
    found = find_number_words(text, lang)
    return [Violation("number_word", f"{len(found)} number word(s); write digits")] if found else []
