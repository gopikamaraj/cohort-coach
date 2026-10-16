"""Script detection: the text must be in the script of the language asked for.

Code-mixing is configured per language: Hindi and Tamil lines may carry some Latin letters
(English maths words, romanised terms); English may carry almost nothing else.
"""

from __future__ import annotations

from ai.validators import Violation

# Words of another script allowed, as a share of all words.
MAX_OTHER_SHARE = {"en": 0.05, "hi": 0.30, "ta": 0.30}
# A short Hindi or Tamil line may still carry one English word (a maths term) whatever the share.
FREE_OTHER_WORDS = {"en": 0, "hi": 1, "ta": 1}
EXPECTED_SCRIPT = {"en": "latin", "hi": "devanagari", "ta": "tamil"}


def script_of(ch: str) -> str | None:
    if not ch.isalpha():
        return None
    code = ord(ch)
    if 0x0900 <= code <= 0x097F:
        return "devanagari"
    if 0x0B80 <= code <= 0x0BFF:
        return "tamil"
    if ch.isascii() or 0x00C0 <= code <= 0x024F:
        return "latin"
    return "other"


def word_script(word: str) -> str | None:
    """The script most of a word's letters are in."""
    counts: dict[str, int] = {}
    for ch in word:
        s = script_of(ch)
        if s:
            counts[s] = counts.get(s, 0) + 1
    return max(counts, key=lambda s: counts[s]) if counts else None


def script_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for word in text.split():
        s = word_script(word)
        if s:
            counts[s] = counts.get(s, 0) + 1
    return counts


def script_shares(text: str) -> dict[str, float]:
    """Share of words in each script (words, not letters: Indic vowel signs are not letters)."""
    counts = script_counts(text)
    total = sum(counts.values())
    return {s: n / total for s, n in counts.items()} if total else {}


def check_language(text: str, lang: str) -> list[Violation]:
    """Text with no letters at all (a bare number) passes: there is nothing to mismatch."""
    counts = script_counts(text)
    total = sum(counts.values())
    if not total:
        return []
    expected = EXPECTED_SCRIPT[lang]
    other_words = total - counts.get(expected, 0)
    if other_words > FREE_OTHER_WORDS[lang] and other_words / total > MAX_OTHER_SHARE[lang]:
        return [Violation("script_mismatch", f"expected {expected} script for {lang}")]
    return []
