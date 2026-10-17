"""Call 2, the teacher-move labeller: what did the teacher just do, and to whom?

Guards: the label set is fixed by the JSON schema (an enum built from the scenario's move list);
low confidence becomes `other`, which changes nothing; a line that looks like an instruction to
the system is forced to `off_task` by code whatever the model says; a posed problem must use
numbers that are in her line and be a valid two-digit problem, or it is dropped (the scenario's
next problem is used instead); the line is cut at 600 characters.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Literal

from pydantic import BaseModel, create_model

from ai.client import CallContext, CallInput, CallResult, run_call
from ai.schemas import MoveLabel
from ai.validators.numbers import extract_numbers
from ai.validators.prefilter import check_prefilter
from engine.simulator import Problem, valid_problem

CONFIDENCE_BAR = 0.6
MAX_TEACHER_CHARS = 600
KIND = {"-": "sub", "+": "add", "dictate": "dictation"}


@dataclass(frozen=True)
class LabelResult:
    move_id: str
    addressed: str | None  # a child's name, or None for the whole class or nobody
    posed: Problem | None
    confidence: float
    forced: str | None  # injection | low_confidence | fallback | None
    run: CallResult | None


def label_model(move_ids: Sequence[str], children: Sequence[str]) -> type[MoveLabel]:
    """MoveLabel with move_id and addressed_child narrowed to enums for this lesson."""
    moves = Literal[tuple([*move_ids, "other", "off_task"])]  # type: ignore[valid-type]
    names = Literal[tuple([*children, "class", "none"])]  # type: ignore[valid-type]
    model = create_model(
        "MoveLabelChoice",
        __base__=MoveLabel,
        move_id=(moves, ...),
        addressed_child=(names, ...),
    )
    return model


def _posed(label: BaseModel, teacher_text: str) -> Problem | None:
    raw = getattr(label, "posed_problem", None)
    if raw is None:
        return None
    kind = KIND[raw.op]
    b = raw.b if raw.b is not None else 0
    spoken = set(extract_numbers(teacher_text))
    if raw.a not in spoken or (kind != "dictation" and b not in spoken):
        return None  # a number she did not say
    problem = Problem(kind, raw.a, b)  # type: ignore[arg-type]
    return problem if valid_problem(problem) else None


def label_move(
    teacher_text: str,
    *,
    moves: Sequence[tuple[str, str]],  # (move id, description in English)
    children: Sequence[str],
    language: str,
    context: CallContext | None = None,
) -> LabelResult:
    base = context or CallContext()
    text = teacher_text.strip()[:MAX_TEACHER_CHARS]
    model = label_model([m for m, _ in moves], children)
    fallback_label = model(move_id="other", addressed_child="none", confidence=0.0)
    ctx = replace(base, output_model=model, fallback=lambda: fallback_label)
    payload = CallInput(
        trusted={
            "language": language,
            "moves": [{"id": mid, "description": desc} for mid, desc in moves],
            "children": list(children),
        },
        untrusted={"teacher_line": text},
    )
    run = run_call(2, payload, context=ctx)
    label = run.output
    assert label is not None
    move_id = str(getattr(label, "move_id"))  # noqa: B009
    confidence = float(getattr(label, "confidence"))  # noqa: B009
    named = str(getattr(label, "addressed_child"))  # noqa: B009
    forced: str | None = "fallback" if run.fallback_used else None
    if any(v.code == "injection_marker" for v in check_prefilter(text, language)):
        move_id, forced = "off_task", "injection"
    elif move_id not in ("off_task",) and confidence < CONFIDENCE_BAR:
        move_id, forced = "other", forced or "low_confidence"
    posed = _posed(label, text) if move_id not in ("other", "off_task") else None
    return LabelResult(
        move_id=move_id,
        addressed=named if named in children else None,
        posed=posed,
        confidence=confidence,
        forced=forced,
        run=run,
    )
