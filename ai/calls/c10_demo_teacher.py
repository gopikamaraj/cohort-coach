"""Call 10, the demo teacher (judge mode only): the AI plays the teacher in a Watch run.

It never reaches a real teacher, who hears the reviewed model run. The model picks one approved
move and writes a line of at most 25 words in one of two styles. Code checks it: the move is on the
style's approved list, every number comes from the scenario (what the children said, the operands,
their digits and tens, and, for the struggling style only, the answer), no check item, the
pre-filter, digits only.
digits only. On any failure the move's sample line is used, or a numberless line from the style.
Call 7 is not used: the line never reaches a real teacher, and the label says so.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from functools import cache
from typing import Literal

import yaml
from pydantic import BaseModel, create_model

from ai.client import CallContext, CallInput, CallResult, run_call
from ai.config import judge_mode
from ai.schemas import DemoTeacherTurn
from ai.validators import ValidatorResult, Violation
from ai.validators._data import CONTENT
from ai.validators.check_items import check_items
from ai.validators.length import check_length
from ai.validators.numbers import check_digits_only, check_numbers, extract_numbers
from ai.validators.prefilter import check_prefilter
from engine.simulator import Problem
from services.practice.content import MoveList

MAX_WORDS = 25
LABEL = "AI playing the teacher (demo only)"


@dataclass(frozen=True)
class StyleDef:
    id: str
    description: str
    moves: tuple[str, ...]
    script: tuple[str, ...]
    may_state_answer: bool
    fallback_move: str
    fallback_lines: dict[str, str]


@dataclass(frozen=True)
class DemoTurn:
    move_id: str
    addressed: str | None  # a child's name, or None for the whole class
    line: str
    source: str  # ai | template
    run: CallResult | None


@cache
def load_styles() -> dict[str, StyleDef]:
    raw = yaml.safe_load((CONTENT / "demo" / "styles.v1.yaml").read_text(encoding="utf-8"))
    return {
        sid: StyleDef(
            id=sid,
            description=str(s["description"]["en"]).strip(),
            moves=tuple(s["moves"]),
            script=tuple(s["script"]),
            may_state_answer=bool(s["may_state_answer"]),
            fallback_move=str(s["fallback_move"]),
            fallback_lines=dict(s["fallback_lines"]),
        )
        for sid, s in raw["styles"].items()
    }


def allowed_numbers(
    problem: Problem, *, may_state_answer: bool, child_lines: Sequence[str] = ()
) -> frozenset[int]:
    """The numbers the AI teacher may write: the operands and their digits and tens, 1 to 10 and
    the multiples of ten, the order probe's 2 and 6, what the children said, and the check sums
    (a child's answer plus the second number). The answer is allowed only for the style that may
    state it."""
    a, b = problem.a, problem.b
    out: set[int] = {a, b, 2, 6, *range(1, 11), *range(10, 100, 10)}
    out |= {a // 10, a % 10, b // 10, b % 10, a // 10 * 10, b // 10 * 10}
    said = {n for line in child_lines for n in extract_numbers(line)}
    out |= said | {n + b for n in said}
    answer = a - b if problem.kind == "sub" else a + b
    if may_state_answer:
        out.add(answer)
    elif answer not in said:
        out.discard(answer)
    return frozenset(out)


def _validate(
    out: DemoTeacherTurn,
    *,
    style: StyleDef,
    language: str,
    allowed: frozenset[int],
    problem: Problem,
    turn: int,
) -> list[ValidatorResult]:
    move: list[Violation] = []
    if out.move_id not in style.moves:
        move.append(Violation("move_not_approved", out.move_id))
    if out.move_id == "pose_problem" and turn != 1:
        move.append(Violation("pose_only_first_turn"))
    if out.move_id == "pose_problem" and not {problem.a, problem.b} <= set(
        extract_numbers(out.line)
    ):
        move.append(Violation("pose_needs_both_numbers"))
    pre = check_prefilter(out.line, language)
    return [
        ValidatorResult("move", tuple(move)),
        ValidatorResult("length", tuple(check_length(out.line, max_words=MAX_WORDS, min_chars=2))),
        ValidatorResult("numbers", tuple(check_numbers(out.line, allowed))),
        ValidatorResult("check_items", tuple(check_items(out.line))),
        ValidatorResult("digits_only", tuple(check_digits_only(out.line, language))),
        ValidatorResult("prefilter", tuple(pre)),
    ]


def _template(
    style: StyleDef,
    movelist: MoveList,
    *,
    language: str,
    allowed: frozenset[int],
    problem: Problem,
    turn: int,
) -> DemoTeacherTurn:
    """The script next move whose sample line passes the checks, else the numberless line."""
    by_id = {m.id: m for m in movelist.moves}
    order = [*style.script[max(turn - 1, 0) :], *style.script[: max(turn - 1, 0)]]
    for mid in order:
        move = by_id.get(mid)
        lines = (move.sample_lines.get(language) if move else None) or []
        if not lines or (mid == "pose_problem" and turn != 1):
            continue
        cand = DemoTeacherTurn(move_id=mid, addressed_child="class", line=lines[0])
        if all(
            r.ok
            for r in _validate(
                cand, style=style, language=language, allowed=allowed, problem=problem, turn=turn
            )
        ):
            return cand
    return DemoTeacherTurn(
        move_id=style.fallback_move,
        addressed_child="class",
        line=style.fallback_lines[language],
    )


def _narrow(model_moves: Sequence[str]) -> type[BaseModel]:
    moves = Literal[tuple(model_moves)]  # type: ignore[valid-type]
    return create_model("DemoTeacherChoice", __base__=DemoTeacherTurn, move_id=(moves, ...))


def demo_teacher_turn(
    *,
    style: str,
    movelist: MoveList,
    language: str,
    children: Sequence[str],
    transcript: Sequence[str],
    child_lines: Sequence[str],
    turn: int,
    problem: Problem,
    context: CallContext | None = None,
) -> DemoTurn:
    if not judge_mode():
        raise PermissionError("The demo teacher runs in judge mode only.")
    base = context or CallContext()
    sd = load_styles()[style]
    allowed = allowed_numbers(
        problem, may_state_answer=sd.may_state_answer, child_lines=child_lines
    )
    template = _template(
        sd, movelist, language=language, allowed=allowed, problem=problem, turn=turn
    )

    def check(out: BaseModel) -> list[ValidatorResult]:
        assert isinstance(out, DemoTeacherTurn)
        return _validate(
            out, style=sd, language=language, allowed=allowed, problem=problem, turn=turn
        )

    ctx = replace(
        base,
        judge=True,
        output_model=_narrow(sd.moves),
        validators=check,
        fallback=lambda: template,
    )
    by_id = {m.id: m for m in movelist.moves}
    payload = CallInput(
        trusted={
            "language": language,
            "style": sd.id,
            "style_description": sd.description,
            "approved_moves": [
                {
                    "id": m,
                    "description": by_id[m].description["en"],
                    "sample": (by_id[m].sample_lines.get(language) or [""])[0],
                }
                for m in sd.moves
                if m in by_id
            ],
            "turn": turn,
            "next_problem": {
                "a": problem.a,
                "op": "-" if problem.kind == "sub" else "+",
                "b": problem.b,
            },
            "allowed_numbers": sorted(allowed),
            "children": list(children),
            "script_if_unsure": list(sd.script),
        },
        untrusted={"transcript": "\n".join(transcript[-8:])},
    )
    run = run_call(10, payload, context=ctx)
    out = run.output
    assert isinstance(out, DemoTeacherTurn)
    name = out.addressed_child if out.addressed_child in children else None
    return DemoTurn(
        move_id=out.move_id,
        addressed=name,
        line=out.line.strip(),
        source="template" if run.fallback_used else "ai",
        run=run,
    )


def label_for(source: str) -> str:
    """The label every demo-teacher line carries, whatever its source."""
    return LABEL if source in ("ai", "template") else ""
