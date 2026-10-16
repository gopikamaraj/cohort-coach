"""Gate 1b: the rule-based pre-filter. Cheap, deterministic, runs before call 7.

Checks profanity and harsh words (en, hi, ta and romanised), PII patterns, off-topic and
injection markers, malformed output, length, and script mismatch.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from ai.validators import Violation
from ai.validators._data import load_yaml, token_matches, tokens
from ai.validators.language import check_language
from ai.validators.length import check_length
from ai.validators.pii import check_pii

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f�]")
_REPEAT = re.compile(r"(.)\1{19,}")
_LEFTOVER = re.compile(r"```|</?(?:thinking|system|assistant|user)\b|^\s*[{\[]\s*\"", re.MULTILINE)


def _profanity_words() -> list[tuple[str, int]]:
    data = load_yaml("safety/profanity.yaml")
    out: list[tuple[str, int]] = []
    for lang, words in data.items():
        suffix = 3 if lang == "ta" else 0
        out.extend((str(w).casefold(), suffix) for w in words)
    return out


def check_prefilter(
    text: str,
    lang: str,
    *,
    max_words: int | None = None,
    max_chars: int | None = 4000,
    roster_names: Iterable[str] = (),
    allow_empty: bool = False,
) -> list[Violation]:
    out: list[Violation] = []
    if not text.strip():
        return [] if allow_empty else [Violation("malformed", "empty text")]
    if _CONTROL.search(text) or _REPEAT.search(text) or _LEFTOVER.search(text):
        out.append(Violation("malformed", "control characters, repeats or leftover markup"))
    toks = tokens(text)
    if any(token_matches(t, w, suffix=s) for t in toks for w, s in _profanity_words()):
        out.append(Violation("profanity", "word from the profanity or harsh list"))
    lowered = text.casefold()
    markers = load_yaml("safety/offtopic.yaml")
    if any(str(m).casefold() in lowered for m in markers.get("injection", [])):
        out.append(Violation("injection_marker", "text looks like an instruction to the system"))
    if any(str(m).casefold() in lowered for m in markers.get("offtopic", [])):
        out.append(Violation("off_topic", "off-topic marker"))
    out.extend(check_pii(text, roster_names))
    out.extend(check_length(text, max_words=max_words, max_chars=max_chars))
    out.extend(check_language(text, lang))
    return out
