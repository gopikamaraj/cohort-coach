"""Load the word lists in content/ (data owned by the team, never hardcoded in code)."""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path
from typing import Any

import yaml

CONTENT = Path(__file__).resolve().parents[2] / "content"

_DIGIT_TABLE = {ord(c): str(i) for i, c in enumerate("०१२३४५६७८९")}
_DIGIT_TABLE.update({ord(c): str(i) for i, c in enumerate("௦௧௨௩௪௫௬௭௮௯")})
_TOKEN_SPLIT = re.compile(r"[\s,.;:!?()\[\]{}\"'“”‘’।॥/\\|<>=+*&^%$#@~`_-]+")


@cache
def load_yaml(relative: str) -> dict[str, Any]:
    data = yaml.safe_load((CONTENT / relative).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{relative} must be a mapping")
    return data


def ascii_digits(text: str) -> str:
    """Devanagari and Tamil digits become 0-9; everything else is unchanged."""
    return text.translate(_DIGIT_TABLE)


def tokens(text: str) -> list[str]:
    return [t for t in _TOKEN_SPLIT.split(text.casefold()) if t]


def word_list(relative: str, lang: str) -> list[str]:
    words = load_yaml(relative).get(lang, [])
    return [str(w).casefold() for w in words]


def token_matches(token: str, word: str, *, suffix: int) -> bool:
    """Exact match, or for inflected languages the word plus up to `suffix` extra letters."""
    if token == word:
        return True
    if suffix == 0:
        return False
    # Tamil changes the final vowel sign when it adds an ending (இரண்டு -> இரண்டை): match the stem.
    stem = word.rstrip("".join(chr(c) for c in range(0x0BBE, 0x0BCE))) or word
    return token.startswith(stem) and len(token) - len(stem) <= suffix + 1
