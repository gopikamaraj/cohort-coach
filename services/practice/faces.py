"""What each simulated child's face shows this turn. Code decides, from facts the engine computed.

The picture is drawn on her phone from the persona id and the expression id (the same renderer
the bot uses for PNGs). The expression comes from `services/api/sprites/expression.py`, one table;
no AI call picks it. Recorded demo runs predate expressions, so they get theirs from the recorded
facts (speaker, intent, whether the answer was right) the same way.
"""

from __future__ import annotations

from typing import Any

from services.api.sprites.expression import ChildState, expression_for
from services.practice.content import load_personas

NEUTRAL_ENGAGEMENT = 0.5  # recorded runs did not keep engagement: assume she is with us


def persona_id(name: str, language: str) -> str | None:
    """The sprite persona for a child's display name in this language."""
    for kid in load_personas().children:
        if kid.names.get(language) == name:
            return kid.id
    return None


def face(
    *,
    speaking: bool,
    intent: str,
    correct: bool | None,
    engagement: float,
    strength: float,
    quiet: bool,
    shy: bool,
) -> str:
    return expression_for(
        ChildState(
            speaking=speaking,
            intent=intent,
            correct=correct if speaking else None,
            engagement=engagement,
            strength=strength,
            quiet=quiet,
            shy=shy,
        )
    )


def with_faces_recorded(run: dict[str, Any]) -> dict[str, Any]:
    """Add persona, expression and speaking to each child of a recorded run, from recorded facts."""
    language = run["provenance"]["language"]
    for turn in run["turns"]:
        speaker = turn["child"]["speaker"]
        intent = turn["child"]["intent"]
        correct = turn["machinery"]["code"]["engine"].get("correct")
        for c in turn["children"]:
            speaking = c["name"] == speaker
            c["persona"] = persona_id(c["name"], language)
            c["speaking"] = speaking
            c["expression"] = face(
                speaking=speaking,
                intent=intent,
                correct=correct,
                engagement=NEUTRAL_ENGAGEMENT,
                strength=c["level"],
                quiet=False,
                shy=False,
            )
    return run
