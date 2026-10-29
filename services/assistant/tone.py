"""Words an answer to a teacher, mentor or coach must never use: pressure, blame or ranking.

The assistant never scores or ranks a teacher, and never makes her feel behind. This list is the
code check behind that (CLAUDE.md rule 3). It is deliberately short and plain; the model is also
told not to, and a test plants each word.
"""

from __future__ import annotations

import re

from ai.validators import Violation

PRESSURE = (
    "you must",
    "you have to",
    "you should have",
    "you failed",
    "you are late",
    "you're late",
    "behind schedule",
    "falling behind",
    "fallen behind",
    "hurry",
    "last chance",
    "don't miss",
    "do not miss",
    "overdue",
    "lazy",
    "poor teacher",
    "weak teacher",
    "bad teacher",
    "best teacher",
    "top teacher",
    "worst",
    "ranked",
    "ranking",
    "leaderboard",
)
ACTION_CLAIM = re.compile(
    r"\bI(?:'ve| have)?\s+(?:just\s+)?(?:approved|sent|deleted|submitted|published|posted|rejected|saved|removed|switched)\b",
    re.I,
)
ROLES_WITH_TONE_RULES = ("teacher", "mentor", "coach")


def check_pressure(text: str) -> list[Violation]:
    low = text.lower()
    return [
        Violation("pressure_word", f"avoid '{w}'")
        for w in PRESSURE
        if re.search(rf"(?<![\w']){re.escape(w)}(?![\w'])", low)
    ]


def check_read_only(text: str) -> list[Violation]:
    """An answer may not claim an action: the assistant approves, sends and deletes nothing."""
    return (
        [Violation("claims_action", "the assistant is read-only")]
        if ACTION_CLAIM.search(text)
        else []
    )
