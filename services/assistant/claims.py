"""Does the deck or the video script claim more than RUBRIC_MAP.md? (scripts/check_claims.py)

For each rubric row, the slides and video segments it names are read for status words. If they use a
word stronger than the row's status (say "live" for a row that is Partly built), that is a mismatch:
the assistant then reports the row's stricter status and says the deck or video differs. Some words
are never allowed in the deck or video at all ("proven"; and "listened" or "watched", which the
system cannot know: CLAUDE.md rule 11).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from services.assistant.rubric import RANK, Row

# Words that claim a status. Ambiguous words are left out on purpose: "live" (a live connection),
# "working" (a verdict label) and "running" say nothing about whether a feature is built.
STATUS_WORDS: dict[str, tuple[str, ...]] = {
    "Built": ("built", "deployed", "shipped"),
    "Partly built": ("partly", "partial", "reduced"),
    "Simulated": ("simulated", "synthetic", "made up", "fictional"),
    "Mock": ("mock", "stub", "stand-in"),
    "Roadmap": ("roadmap", "planned", "not yet", "not built"),
}
NEVER = ("proven", "listened", "watched")
KEY_CLAIM_LIMIT_S = 180  # reviewers need not watch beyond three minutes


@dataclass(frozen=True)
class Mismatch:
    row: str
    where: str  # "slide 10" or "video 02:00"
    word: str
    says: str  # the status the word implies
    row_status: str


def _has(text: str, word: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", text, re.I) is not None


_NEGATED = re.compile(
    r"\b(?:not|never|nothing|isn't|aren't)\s+(?:yet\s+|been\s+)?(?:built|deployed|shipped)\b", re.I
)
_PARTLY = re.compile(r"\bpartly\s+built\b", re.I)


def implied(text: str) -> tuple[str, str] | None:
    """The strongest status a text claims, with the word that claims it. "Partly built" and "not
    built" are read as what they say, not as the word "built"."""
    text = _PARTLY.sub("partly", _NEGATED.sub("roadmap", text))
    best: tuple[str, str] | None = None
    for status, words in STATUS_WORDS.items():
        for w in words:
            if _has(text, w) and (best is None or RANK[status] > RANK[best[0]]):
                best = (status, w)
    return best


def mismatches(rows: list[Row], slides: dict[int, str], segments: dict[str, str]) -> list[Mismatch]:
    out: list[Mismatch] = []
    for r in rows:
        places = [(f"slide {n}", slides.get(n, "")) for n in r.slides] + [
            (f"video {t}", segments.get(t, "")) for t in r.video
        ]
        for where, text in places:
            hit = implied(text)
            if hit and RANK[hit[0]] > RANK[r.status]:
                out.append(Mismatch(r.id, where, hit[1], hit[0], r.status))
    return out


def forbidden(slides: dict[int, str], segments: dict[str, str]) -> list[str]:
    found = []
    for n, text in slides.items():
        found += [f"slide {n}: {w}" for w in NEVER if _has(text, w)]
    for t, text in segments.items():
        found += [f"video {t}: {w}" for w in NEVER if _has(text, w)]
    return found


def late_claims(rows: list[Row]) -> list[str]:
    """Rows shown only after 03:00 in the video, which a reviewer may never see."""
    out = []
    for r in rows:
        secs = [int(t[:2]) * 60 + int(t[3:]) for t in r.video]
        if secs and min(secs) >= KEY_CLAIM_LIMIT_S:
            out.append(f"{r.id} first appears at {r.video[0]}")
    return out
