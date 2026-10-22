"""The one table that maps a simulated child's state to an expression. AI never picks one.

Inputs are facts the engine already computed for the turn: whether this child is the speaker,
the turn's intent, whether her answer was right, her engagement and strength, and whether she is
quiet or shy. The table is total: every combination maps to a registered expression.
"""

from __future__ import annotations

from dataclasses import dataclass

from services.api.sprites.avatar import expression_ids

FLAT_ENGAGEMENT = 0.35  # below this the child has switched off (the simulator's own "flat" mood)
HOLDING = 0.66  # a strength at or above this: she still holds the mistake


@dataclass(frozen=True)
class ChildState:
    speaking: bool
    # the turn's intent: answer, explain, work_aloud, doubt, agree, thanks, quiet, confused, silent
    intent: str
    correct: bool | None  # was what she just said and wrote right; None when she said no number
    engagement: float
    strength: float
    quiet: bool
    shy: bool


# (intent, correct) -> expression, for a child who spoke this turn. Order matters only for the
# defaults below it.
SPOKE: dict[tuple[str, bool | None], str] = {
    ("answer", True): "got_it",
    ("answer", False): "wrong_answer",
    ("explain", True): "got_it",
    ("explain", False): "wrong_answer",
    ("work_aloud", True): "got_it",
    ("work_aloud", False): "wrong_answer",
    ("doubt", True): "got_it",
    ("doubt", False): "confused",
    ("agree", True): "thinking",
    ("agree", False): "thinking",
    ("thanks", True): "got_it",
    ("thanks", False): "got_it",
    ("thanks", None): "got_it",
    ("quiet", None): "shy",
    ("quiet", True): "shy",
    ("quiet", False): "shy",
    ("confused", None): "confused",
    ("confused", True): "confused",
    ("confused", False): "confused",
}


def expression_for(s: ChildState) -> str:
    """The expression for one child this turn."""
    if s.quiet:
        return "shy"
    if s.speaking:
        hit = SPOKE.get((s.intent, s.correct))
        if hit is not None:
            return hit
        return "thinking" if s.strength >= HOLDING else "neutral"
    if s.shy:
        return "shy"
    if s.engagement < FLAT_ENGAGEMENT:
        return "distracted"
    return "thinking" if s.strength >= HOLDING else "neutral"


def all_targets() -> set[str]:
    """Every expression the table can return (a test checks they are all registered)."""
    return {*SPOKE.values(), "shy", "thinking", "neutral", "distracted"}


def registered() -> set[str]:
    return set(expression_ids())
