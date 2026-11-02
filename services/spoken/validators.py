"""Checks on spoken text. They report; they never repair (the normaliser repairs). A script that
fails is not voiced from a builder: it is a bug to fix in the builder or the content."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from services.spoken.lang import pack_for
from services.spoken.schema import PAUSE_RE, PV_RE

SPEAKERS = Path(__file__).resolve().parents[2] / "content" / "spoken.yaml"
_SCREEN_ONLY = re.compile(r"\b(source|draft)\b\s*[:·(]|\bdraft\b\s*[.)]?\s*$", re.I | re.M)
_LABEL_PREFIX = re.compile(r"^\s*(materials|steps|worked example|note)\s*:", re.I | re.M)
_SYMBOLS = re.compile(r"[+=<>×÷−*#_`~^|\\{}\[\]%@&/]|\d")
_ALLOWED_TOKENS = re.compile(r"\[pause(?::long)?\]")
_MARKDOWN = re.compile(r"(\*\*|__|^\s*#|^\s*[-*•]\s)", re.M)


@dataclass(frozen=True)
class Issue:
    code: str
    detail: str

    def __str__(self) -> str:
        return f"{self.code}: {self.detail}"


@cache
def config() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(SPEAKERS.read_text(encoding="utf-8"))
    return data


def speaker_config(speaker: str) -> dict[str, Any]:
    speakers: dict[str, Any] = config()["speakers"]
    chosen: dict[str, Any] = speakers.get(speaker) or speakers["narrator"]
    return chosen


def words_in(text: str) -> int:
    return len(PAUSE_RE.sub(" ", text).split())


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.?!।])\s+|\n+", PAUSE_RE.sub(" ", text))
    return [p.strip() for p in parts if p.strip()]


def validate(text: str, language: str, speaker: str = "narrator") -> list[Issue]:
    """Everything that makes text hard to listen to, as a list (empty when it is clean)."""
    out: list[Issue] = []
    bare = _ALLOWED_TOKENS.sub(" ", text)
    if PV_RE.search(bare) or "{pv" in bare:
        out.append(Issue("pv_token", "a {pv:N} token was left in the spoken text"))
    if m := _SYMBOLS.search(bare):
        out.append(Issue("symbol_or_digit", f"'{m.group(0)}' cannot be read aloud as written"))
    if _SCREEN_ONLY.search(bare):
        out.append(Issue("screen_only", "a Source or Draft tag is still in the text"))
    if _LABEL_PREFIX.search(bare):
        out.append(Issue("label_prefix", "a screen label with a colon is still in the text"))
    if _MARKDOWN.search(bare):
        out.append(Issue("markdown", "markdown or a bullet is still in the text"))
    if re.search(r"\[pause[^\]]*\]", text) and re.sub(_ALLOWED_TOKENS, "", text).count("[") > 0:
        out.append(Issue("pause_token", "an unknown pause token"))
    if re.search(r"(\[pause(?::long)?\]\s*){2,}", text):
        out.append(Issue("pause_twice", "two pauses in a row"))
    limit = int(speaker_config(speaker)["max_sentence_words"])
    for s in sentences(text):
        if words_in(s) > limit:
            out.append(Issue("long_sentence", f"{words_in(s)} words (limit {limit}): {s[:40]}..."))
    pack = pack_for(language)
    if pack.script != "latin":
        letters = [c for c in bare if c.isalpha()]
        own = [c for c in letters if ("ऀ" <= c <= "ॿ") or ("஀" <= c <= "௿")]
        if letters and len(own) / len(letters) < 0.5:
            out.append(Issue("script_mismatch", f"most of the text is not in {language} script"))
    return out
