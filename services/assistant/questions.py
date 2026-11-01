"""Suggested questions: one bank per role, and a pure function that picks the top five.

The same context (role, screen, step of the test path) always gives the same five questions, in the
same order: no clock, no randomness, no history (tests/assistant/test_questions.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

VALID_SCREENS = (
    "any",
    "landing",
    "home",
    "check",
    "papers",
    "cards",
    "practice",
    "programme",
    "profile",
    "tour",
    "watch",
    "aimap",
    "audit",
    "review",
    "cohort",
    "mentor",
    "officer",
    "assistant",
    "judge",
    "demo",
    "two-classes",
    "admin",
    "testing",
    "flow",
    "history",
    "privacy",
    "coach",
)
VALID_CRITERIA = ("efficacy", "innovation", "ai", "roadmap")
CRITERION_LABEL = {
    "efficacy": "Efficacy and user centricity (35%)",
    "innovation": "Innovation (25%)",
    "ai": "Effective AI use and technical strength (30%)",
    "roadmap": "Future roadmap (10%)",
}
SCREEN_POINTS, ANY_POINTS, STEP_POINTS = 10, 3, 8


@dataclass(frozen=True)
class Question:
    id: str
    text: dict[str, str]
    screens: tuple[str, ...]
    criteria: tuple[str, ...]
    rubric_rows: tuple[str, ...]
    steps: tuple[int, ...]
    query: str

    def label(self, lang: str) -> str:
        return self.text.get(lang) or self.text["en"]


def parse_bank(raw: list[dict[str, Any]]) -> list[Question]:
    return [
        Question(
            id=d["id"],
            text=dict(d["text"]),
            screens=tuple(d.get("screens", ["any"])),
            criteria=tuple(d.get("criteria", [])),
            rubric_rows=tuple(d.get("rubric_rows", [])),
            steps=tuple(d.get("steps", [])),
            query=d.get("query") or d["text"]["en"],
        )
        for d in raw
    ]


def top_five(bank: list[Question], screen: str = "any", step: int | None = None) -> list[Question]:
    """The five best questions for this screen and, for a judge, this step of the test path. A question
    for the current screen scores most, one marked for any screen a little, one for this step a lot;
    ties keep the bank's own order."""

    def score(q: Question) -> int:
        s = (
            SCREEN_POINTS
            if screen in q.screens and screen != "any"
            else (ANY_POINTS if "any" in q.screens else 0)
        )
        if step is not None and step in q.steps:
            s += STEP_POINTS
        return s

    ranked = sorted(enumerate(bank), key=lambda p: (-score(p[1]), p[0]))
    return [q for _, q in ranked[:5]]
