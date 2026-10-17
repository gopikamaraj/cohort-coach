"""Call 1, child voices: put the engine's turn plan into a Grade 3 child's words.

Every number is the engine's: the validators reject any number not in the plan's allowed set,
any number word, and an `answer` line that does not contain the planned answer. One retry names
the violation, then a template line is used. After the validators, call 7 checks the line
(gate 2); a line that fails it is replaced by the template too (check-then-release).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from pydantic import BaseModel

from ai.client import CallContext, CallInput, CallResult, run_call
from ai.guard.gates import ContentType, GateInput, GateResult, gate1, run_gates
from ai.schemas import ChildLine
from ai.validators import ValidatorResult, Violation
from ai.validators.numbers import extract_numbers
from engine.simulator import TurnPlan
from services.practice.templates import render_line, step_text


@dataclass(frozen=True)
class ChildLineResult:
    text: str
    source: str  # ai | template | silent
    gate: GateResult | None
    run: CallResult | None


def _facts(plan: TurnPlan, name: str, temperament: str, language: str) -> dict[str, object]:
    return {
        "language": language,
        "speaker": {"name": name, "temperament": temperament},
        "intent": plan.intent,
        "mood": plan.mood,
        "answer": plan.answer,
        "steps": [
            {"op": s.op, "numbers": list(s.numbers), "meaning": step_text(s, "en")}
            for s in plan.steps
        ],
        "allowed_numbers": sorted(plan.allowed_numbers),
        "teacher_move": plan.move_id,
    }


def _validators(plan: TurnPlan, language: str, text: str) -> list[ValidatorResult]:
    results = gate1(
        GateInput(
            text=text,
            content_type=ContentType.CHILD_LINE,
            language=language,
            allowed_numbers=plan.allowed_numbers,
        )
    )
    if plan.intent == "answer" and plan.answer is not None:
        missing = plan.answer not in extract_numbers(text)
        results.append(
            ValidatorResult("answer_present", (Violation("answer_missing"),) if missing else ())
        )
    return results


def child_line(
    plan: TurnPlan,
    *,
    name: str,
    temperament: str,
    language: str,
    teacher_line: str,
    history: Sequence[str],
    target_error: str | None = None,
    context: CallContext | None = None,
) -> ChildLineResult:
    if plan.speaker is None:
        return ChildLineResult("", "silent", None, None)
    base = context or CallContext()
    template = render_line(plan, language)

    def check(out: BaseModel) -> list[ValidatorResult]:
        assert isinstance(out, ChildLine)
        return _validators(plan, language, out.text)

    ctx = replace(base, validators=check, fallback=lambda: ChildLine(text=template))
    payload = CallInput(
        trusted=_facts(plan, name, temperament, language),
        untrusted={"teacher_line": teacher_line, "history": "\n".join(history[-6:])},
    )
    run = run_call(1, payload, context=ctx)
    line = run.output
    assert isinstance(line, ChildLine)
    if run.fallback_used:
        return ChildLineResult(template, "template", None, run)
    gate = run_gates(
        GateInput(
            text=line.text,
            content_type=ContentType.CHILD_LINE,
            language=language,
            allowed_numbers=plan.allowed_numbers,
            target_error=target_error,
            source_audit_id=run.audit_id,
            checker_facts={
                "intent": plan.intent,
                "engine_answer": plan.answer,
                "answer_is_deliberately_wrong": plan.correct is False,
                "allowed_numbers": sorted(plan.allowed_numbers),
            },
        ),
        context=base,
    )
    if not gate.releasable:
        return ChildLineResult(template, "template", gate, run)
    return ChildLineResult(line.text, "ai", gate, run)
