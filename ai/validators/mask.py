"""Masking personal data before text goes anywhere: a model, a mentor's screen, the database.

A teacher must not name a child (CLAUDE.md rule 15). `mask_personal` replaces what the posting check
(`ai/validators/thread.py`) would block: a first name from the list in three scripts, a roll-number
phrase, a name with a relationship word ("Rahul's sister"), a phone number, an email and an
ID-like number. It returns the masked text and the kinds it found, never the matched text. The
first-name list is best effort (data in `content/safety/child_names.yaml`): it catches the common
cases, so the compose step carries a notice and a mentor can still report a question.

`check_masked` is the second layer, run on anything a model wrote: it fails if personal data is
still (or newly) in the text.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from ai.validators import Violation
from ai.validators.pii import _DIGIT_RUN, _EMAIL
from ai.validators.thread import _RELATIVE, _ROLL, _TAMIL_ENDINGS, _hit, _names, check_personal

CHILD = "[child]"
RELATIVE = "[a child's relative]"
ROLL = "[roll number removed]"
NUMBER = "[number removed]"
EMAIL = "[email removed]"
_TOKEN = re.compile(r"[^\s,.;:!?()\[\]{}\"'“”‘’।॥/\\|<>=+*&^%$#@~`_-]+")


@dataclass(frozen=True)
class Masked:
    text: str
    kinds: tuple[str, ...]  # child_name, roll_number, relative, phone_or_id, email

    @property
    def child_mentioned(self) -> bool:
        return bool({"child_name", "roll_number", "relative"} & set(self.kinds))


def _is_phone_or_id(run: str) -> bool:
    digits = re.sub(r"\D", "", run)
    return len(digits) in (10, 12)


def _kept(token: str, keep: tuple[str, ...]) -> bool:
    return any(
        token == k or (token.startswith(k) and token[len(k) :] in _TAMIL_ENDINGS) for k in keep
    )


def mask_personal(text: str, keep: Sequence[str] = ()) -> Masked:
    """`keep`: names that are not real children's and stay (the Practice Class children)."""
    kinds: list[str] = []
    kept = tuple(k.casefold() for k in keep if k)
    out = text

    def note(kind: str) -> None:
        if kind not in kinds:
            kinds.append(kind)

    if _EMAIL.search(out):
        note("email")
        out = _EMAIL.sub(EMAIL, out)

    def digit_run(m: re.Match[str]) -> str:
        if _is_phone_or_id(m.group()):
            note("phone_or_id")
            return NUMBER
        return m.group()

    out = _DIGIT_RUN.sub(digit_run, out)
    if _ROLL.search(out):
        note("roll_number")
        out = _ROLL.sub(ROLL, out)
    if _RELATIVE.search(out):
        note("relative")
        out = _RELATIVE.sub(RELATIVE, out)
    names = _names()
    pieces: list[str] = []
    last = 0
    for m in _TOKEN.finditer(out):
        token = m.group().casefold()
        if _kept(token, kept):
            continue
        if any(_hit(token, n, script) for n, script in names):
            note("child_name")
            pieces.append(out[last : m.start()])
            pieces.append(CHILD)
            last = m.end()
    pieces.append(out[last:])
    return Masked("".join(pieces), tuple(kinds))


def check_masked(text: str) -> list[Violation]:
    """Second layer: the text must carry no personal data. Used on every model-written draft."""
    return check_personal(text)
