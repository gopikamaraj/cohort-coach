"""The spoken script: the one shape both surfaces hand to the speech layer.

Spoken text is its own output, separate from the screen text; the screen and its labels do not
change. Pause tokens live in the text: [pause] (short) and [pause:long] (a section break, or after
an instruction the teacher must act on). A place-value number is written {pv:496} by the content
or the generation prompt, never guessed from a verb.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Literal

Speaker = Literal["narrator", "coach", "simulated_child"]
Surface = Literal["intervention", "practice"]

PAUSE_SHORT = "[pause]"
PAUSE_LONG = "[pause:long]"
PAUSE_RE = re.compile(r"\[pause(?::long)?\]")
PV_RE = re.compile(r"\{pv:(\d+)\}")


@dataclass(frozen=True)
class Utterance:
    id: str
    speaker: str
    text: str  # spoken-ready: no digits, symbols or screen-only words; pause tokens allowed

    @property
    def words(self) -> int:
        return len(PAUSE_RE.sub(" ", self.text).split())


@dataclass(frozen=True)
class SpokenScript:
    surface: str
    language: str
    speaker: str
    content_version_hash: str
    utterances: tuple[Utterance, ...]
    total_words: int = 0
    est_seconds: float = 0.0
    fallback: bool = (
        False  # the language asked for had no text for part of it: English was used there
    )
    issues: tuple[str, ...] = field(default_factory=tuple)  # validator findings (empty when clean)

    @property
    def text(self) -> str:
        """One string for the speech layer: a blank line between utterances (a section break)."""
        return "\n\n".join(u.text for u in self.utterances if u.text.strip())


def version_hash(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()[:16]
