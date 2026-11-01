"""Data tools the assistant may call, filtered by scope.

Every tool is read-only. A scope lists the tools it may use (assistant_scopes.yaml); this registry
holds what each tool is and whether it is wired in this build. A tool that is declared but not wired
has status "roadmap": calling it returns an honest "not available yet", never a made-up figure.
Any count a tool returns passes through suppress() first: under the minimum, nothing is stated.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from services.assistant.scopes import Scope


class ToolDenied(Exception):
    """The tool is not in this scope."""


@dataclass(frozen=True)
class Tool:
    name: str
    status: str  # "built" or "roadmap"
    what: str
    fn: Callable[..., Any] | None = None


def _paper_status(scope: Scope, *, db: Any, who: Any, paper_id: str) -> dict[str, Any]:
    """What became of one paper, read-only, for a paper inside this person's own scope. The same
    function the Papers page uses; it changes nothing."""
    from services.papers.models import PaperRow
    from services.papers_hub import api as hub

    row = db.get(PaperRow, paper_id)
    if row is None or not hub._visible(db, who, row):
        return {"found": False, "why": "no such paper in your scope"}
    return {"found": True, **hub.paper_status(db, row)}


# Most tools below are not wired to live data yet: class numbers live on the teacher's phone, and the
# officer and coach aggregates are read from their own screens. The assistant points to the screen.
TOOLS: dict[str, Tool] = {
    t.name: t
    for t in (
        Tool(
            "paper_status",
            "built",
            "A paper's status, frozen reason, source, review state, cohort status and its reason (read-only, inside her scope).",
            _paper_status,
        ),
        Tool("own_state", "roadmap", "Where this teacher is in her track (her own state only)."),
        Tool("own_class_counts", "roadmap", "Counts of children by error in her own class."),
        Tool("own_track", "roadmap", "The track her cohort follows and the current lesson."),
        Tool("next_step", "roadmap", "The next step the next-step policy chose for her."),
        Tool("own_method_card_counts", "roadmap", "Counts for her own method cards, at least 5."),
        Tool("review_queue", "roadmap", "What waits in the review queue and how long."),
        Tool("chat_inbox", "roadmap", "What waits in the cohort chat inbox."),
        Tool("cohort_counts", "roadmap", "Cohort-level counts, at least 5 classes."),
        Tool("block_counts", "roadmap", "Block-level counts, at least 5 classes."),
        Tool(
            "track_verdicts", "roadmap", "Track verdicts with their interval, at least 5 classes."
        ),
    )
}


def tools_for(scope: Scope) -> list[Tool]:
    """Only the tools this scope lists, so a tool in another role's scope does not exist here."""
    return [TOOLS[n] for n in scope.data_tools if n in TOOLS]


def call_tool(scope: Scope, name: str, **kwargs: Any) -> dict[str, Any]:
    if name not in scope.data_tools:
        raise ToolDenied(f"{name} is not available to {scope.role}")
    tool = TOOLS[name]
    if tool.status != "built" or tool.fn is None:
        return {"available": False, "tool": name, "reason": "not wired in this build"}
    return {"available": True, "tool": name, "result": tool.fn(scope, **kwargs)}


def suppress(count: int, minimum: int) -> int | None:
    """A count is shown only if it covers at least `minimum` classes; otherwise nothing."""
    return count if count >= minimum else None
