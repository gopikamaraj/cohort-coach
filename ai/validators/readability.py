"""Reading-level proxies: sentence length, word length and a jargon list.

`audience="child"` lines must sound like a Grade 3 child; `audience="teacher"` lines must be
plain spoken language. Call 7 adds a rubric item on top of these proxies.
"""

from __future__ import annotations

import re

from ai.validators import Violation
from ai.validators._data import token_matches, tokens, word_list

# audience -> (max words in one sentence, longest word allowed in English letters)
LIMITS = {"child": (20, 12), "teacher": (28, 18)}
_SENTENCE = re.compile(r"[.!?।॥]+")


def sentences(text: str) -> list[str]:
    return [s for s in _SENTENCE.split(text) if s.strip()]


def check_readability(text: str, lang: str, audience: str) -> list[Violation]:
    max_sentence, max_word = LIMITS[audience]
    out: list[Violation] = []
    longest = max((len(s.split()) for s in sentences(text)), default=0)
    if longest > max_sentence:
        out.append(Violation("sentence_too_long", f"{longest} words, limit {max_sentence}"))
    toks = tokens(text)
    if lang == "en" and any(len(t) > max_word and t.isascii() and t.isalpha() for t in toks):
        out.append(Violation("word_too_long", f"a word is over {max_word} letters"))
    suffix = 3 if lang == "ta" else 0
    jargon = word_list("lang/jargon.yaml", lang)
    if any(token_matches(t, j, suffix=suffix) for t in toks for j in jargon):
        out.append(Violation("jargon", "a word from the jargon list"))
    return out
