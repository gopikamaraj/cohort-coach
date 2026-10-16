"""A quote must be a verbatim part of the transcript, ignoring case, spacing and punctuation."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from ai.validators import Violation

_SPACES = re.compile(r"\s+")


def normalise(text: str) -> str:
    """NFKC, case-folded, punctuation turned into spaces, spaces collapsed.

    Only punctuation (Unicode category P) is dropped; Devanagari and Tamil vowel signs are kept.
    """
    text = unicodedata.normalize("NFKC", text).casefold()
    text = "".join(" " if unicodedata.category(c).startswith("P") else c for c in text)
    return _SPACES.sub(" ", text).strip()


def quote_in_transcript(quote: str, transcript: str) -> bool:
    q = normalise(quote)
    return bool(q) and q in normalise(transcript)


def check_quotes(quotes: Iterable[str], transcript: str) -> list[Violation]:
    return [
        Violation("quote_not_found", f"quote {i + 1} is not in the transcript")
        for i, q in enumerate(quotes)
        if not quote_in_transcript(q, transcript)
    ]
