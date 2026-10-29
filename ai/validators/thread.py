"""The posting check for the cohort thread: best effort, rule based, never sent to a model.

A teacher must not name a child or give a detail that identifies one (CLAUDE.md rule 15). This
check blocks the common cases: a first name from the list, a roll-number phrase ("roll no 14",
"no. 14"), a relationship phrase ("Rahul's sister"), a phone number, an email or an ID-like number,
and what the pre-filter blocks (harsh words, markup). It is a filter, not a guarantee: a teacher can
still describe a child without a name, which is why the compose screen carries a notice, posts are
capped at 500 characters, and every post has a Report button and a fast hide.

If the check cannot run, the post is held, never passed (the caller treats any exception that way).
"""

from __future__ import annotations

import re

from ai.validators import Violation
from ai.validators._data import load_yaml, tokens
from ai.validators.pii import check_pii
from ai.validators.prefilter import check_prefilter

MAX_CHARS = 500
_ROLL = re.compile(
    r"(?:\b(?:roll|रोल|ரோல்)\s*(?:no\.?|number|नंबर|எண்)?\s*\d{1,3}\b)"
    r"|(?:\b(?:no|number|नं|नंबर|எண்)\.?\s*\d{1,3}\b\s*(?:child|student|boy|girl|बच्चा|बच्ची|குழந்தை)?)"
    r"|(?:\b(?:child|student|boy|girl)\s*(?:no\.?|number)\s*\d{1,3}\b)",
    re.IGNORECASE,
)
_RELATIVE = re.compile(
    r"\w+['’]s\s+(?:sister|brother|mother|father|son|daughter|cousin|uncle|aunt)\b"
    r"|\b(?:sister|brother|mother|father|son|daughter)\s+of\s+[A-Z]\w+",
)


# Tamil attaches case endings to a name (மீனா + வுக்கு); only these endings count, so that a name
# that starts an ordinary word (அனு in அனுபவம்) does not block a post.
_TAMIL_ENDINGS = {
    "", "ை", "ின்", "ுக்கு", "வுக்கு", "க்கு", "ிடம்", "ுடன்", "ால்", "வின்", "யின்", "வை", "யை",
    "வும்", "ும்", "ே", "ா", "வோடு", "ோடு", "வால்", "யால்",
}  # fmt: skip


def _names() -> list[tuple[str, str]]:
    data = load_yaml("safety/child_names.yaml")
    return [(str(n).casefold(), script) for script, names in data.items() for n in names]


def _hit(token: str, name: str, script: str) -> bool:
    if script == "tamil":
        return token.startswith(name) and token[len(name) :] in _TAMIL_ENDINGS
    return token == name


def check_personal(text: str) -> list[Violation]:
    """Personal data in text: phone, email, ID number, roll number, a relative of a child, or a
    first name from the list. Used by the posting check and on what the chat drafts."""
    out: list[Violation] = []
    out.extend(check_pii(text))
    if _ROLL.search(text):
        out.append(Violation("roll_number", "a roll-number phrase"))
    if _RELATIVE.search(text):
        out.append(Violation("relationship", "a name with a relationship word"))
    toks = tokens(text)
    if any(_hit(t, n, script) for t in toks for n, script in _names()):
        out.append(Violation("child_name", "a first name from the list"))
    return out


def check_thread_post(text: str, language: str) -> list[Violation]:
    """Violations that stop a post; an empty list means it may be posted."""
    out: list[Violation] = []
    if len(text) > MAX_CHARS:
        out.append(Violation("too_long", f"{len(text)} characters, limit {MAX_CHARS}"))
    out.extend(check_personal(text))
    out.extend(check_prefilter(text, language, max_chars=MAX_CHARS))
    seen: set[str] = set()
    unique: list[Violation] = []
    for v in out:
        if v.code not in seen:
            seen.add(v.code)
            unique.append(v)
    return unique
