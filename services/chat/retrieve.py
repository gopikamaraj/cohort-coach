"""The only material the chat may answer from: what a coach has approved.

1. **Lessons**: the approved parts (six lessons and the model-lesson script) of the track version
   both keys switched on, for the cohort's error, in the teacher's language (English if that
   language has none). The text is the approved wording with its class-number slots and child-
   mistake tags, so no cohort's figures can leak: a sentence that still holds a slot is not used.
2. **Strategies**: entries of the strategy library whose status is approved or active, for the
   error.

Mentor method cards are not retrieved: no method-card text exists yet (call 4 is not built), and
the chat never reads a mentor's recording. Nothing else is ever offered to the model.

Ranking is by shared words with the question (no vector store). When nothing overlaps, the first
sentences still go to the model, which must then answer "no answer" unless a source supports it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.validators._data import tokens
from ai.validators.arithmetic import normalise_child_tags, strip_child_tags
from services.api.db import ContentVersion, ReviewItem
from services.content.track import load_strategies

MAX_SOURCES = 8
MIN_WORDS, MAX_WORDS = 3, 40
_SENTENCE = re.compile(r"(?<=[.!?।])\s+|\n+")


@dataclass(frozen=True)
class Source:
    id: str  # L2.3 (lesson 2, sentence 3), L0.1 (model lesson), S.show_bundles.1 (strategy)
    kind: str  # lesson | model_lesson | strategy
    title: str
    text: str
    language: str


def _sentences(text: str) -> list[str]:
    plain = strip_child_tags(normalise_child_tags(text))
    out = []
    for s in _SENTENCE.split(plain):
        s = s.strip()
        words = len(s.split())
        if "{{" in s or not MIN_WORDS <= words <= MAX_WORDS:
            continue  # a sentence with a class-number slot, or too short or long to quote
        out.append(s)
    return out


def _lesson_sources(db: Session, error: str, language: str) -> list[Source]:
    out: list[Source] = []
    versions = db.execute(
        select(ContentVersion).where(
            ContentVersion.content_type == "track", ContentVersion.status == "active"
        )
    ).scalars()
    for v in versions:
        if v.body.get("error") != error:
            continue
        languages: dict[str, dict[str, dict[str, str]]] = v.body.get("languages", {})
        lang = language if language in languages else ("en" if "en" in languages else None)
        if lang is None:
            continue
        for ref in languages[lang].values():
            item = db.get(ReviewItem, ref["item_id"])
            if item is None or item.status != "approved":
                continue  # approval can be withdrawn: a part that is no longer approved is skipped
            kind = str(item.content.get("kind", "lesson"))
            day = int(item.content.get("day", 0))
            title = "Model lesson" if kind == "model_lesson" else f"Lesson {day}"
            for n, sentence in enumerate(_sentences(str(item.content["script"])), start=1):
                out.append(Source(f"L{day}.{n}", kind, title, sentence, lang))
    return out


def _strategy_sources(error: str, language: str) -> list[Source]:
    out: list[Source] = []
    for sid, s in load_strategies().items():
        if s.status not in ("approved", "active") or error not in s.fits:
            continue
        lang = language if language in s.description else "en"
        texts = [s.description[lang], *s.worked_examples]
        for n, sentence in enumerate((x for t in texts for x in _sentences(t)), start=1):
            out.append(
                Source(f"S.{sid}.{n}", "strategy", s.label.get(lang, s.label["en"]), sentence, lang)
            )
    return out


def approved_sources(db: Session, error: str, language: str) -> list[Source]:
    return _lesson_sources(db, error, language) + _strategy_sources(error, language)


def rank(sources: list[Source], question: str, k: int = MAX_SOURCES) -> list[Source]:
    """The k sources that share most words with the question, then the rest in order."""
    wanted = {t for t in tokens(question) if len(t) > 2}
    scored = [(len(wanted & set(tokens(s.text))), -i, s) for i, s in enumerate(sources)]
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [s for _, _, s in scored[:k]]
