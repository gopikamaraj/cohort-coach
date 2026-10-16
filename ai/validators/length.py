"""Length limits in words and characters."""

from __future__ import annotations

from ai.validators import Violation


def word_count(text: str) -> int:
    return len(text.split())


def check_length(
    text: str, *, max_words: int | None = None, max_chars: int | None = None, min_chars: int = 0
) -> list[Violation]:
    out: list[Violation] = []
    if len(text.strip()) < min_chars:
        out.append(Violation("too_short", f"fewer than {min_chars} characters"))
    if max_words is not None and word_count(text) > max_words:
        out.append(Violation("too_many_words", f"{word_count(text)} words, limit {max_words}"))
    if max_chars is not None and len(text) > max_chars:
        out.append(Violation("too_many_chars", f"{len(text)} characters, limit {max_chars}"))
    return out
