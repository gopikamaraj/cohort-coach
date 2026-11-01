"""A Practice Class session: one teacher, five fictional children, a seeded engine, three calls.

One turn: teacher line -> labeller (call 2) -> engine plans the turn -> child voice (call 1)
-> gates (validators, pre-filter, call 7) -> reply. At the end: feedback (call 3). The state
lives in memory only and is never persisted; the full transcript goes back to the client,
which keeps it on the phone. A session ends when every child with the error has been right
twice in a row, or at the turn cap (40, also the judge-mode cap).
"""

from __future__ import annotations

import logging
import random
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from typing import Any

from ai.calls.c01_child_voice import ChildLineResult, child_line
from ai.calls.c02_move_label import LabelResult, label_move
from ai.calls.c03_feedback import FeedbackCard, TurnLine, give_feedback
from ai.client import CallContext, CallResult
from ai.config import practice_ai_intents, practice_skip_checker
from ai.validators.mask import mask_personal
from engine.model import ErrorCode
from engine.simulator import (
    Problem,
    SessionState,
    TurnPlan,
    fill_seats,
    new_session,
    plan_turn,
)
from services.practice.content import LoadedScenario, PersonaChild, load_personas, load_scenario
from services.practice.faces import face
from services.practice.templates import render_line

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScriptedMove:
    """A move chosen outside the labeller: the AI teacher's move in a Watch run."""

    move_id: str
    addressed: str | None
    posed: Problem | None = None


class SessionFinished(RuntimeError):
    """The session has ended (all children right twice in a row, or the turn cap)."""


@dataclass
class TurnRecord:
    turn: int
    teacher_text: str
    move_id: str
    addressed: str | None
    speaker: str | None
    child_text: str
    intent: str
    source: str
    others: list[tuple[str, str]] = field(default_factory=list)  # (speaker, line) who joined in


@dataclass
class PracticeSession:
    id: str
    error: str
    language: str
    judge: bool
    seed: int
    loaded: LoadedScenario
    state: SessionState
    personas: dict[str, PersonaChild]
    records: list[TurnRecord] = field(default_factory=list)
    plan_numbers: set[int] = field(default_factory=set)
    last_addressed: str | None = None
    ended: bool = False
    created: float = field(default_factory=time.time)


@dataclass
class TurnResult:
    turn: int
    speaker: str | None
    child_text: str
    intent: str
    numbers: list[int]
    label: dict[str, Any] | None
    badge: str
    explanation: str
    layers: dict[str, Any]
    latency_ms: int
    cost_usd: float
    finished: bool
    finished_reason: str | None
    child_text_en: str = ""  # the English subtitle, same digits as child_text
    written: int | None = None  # what the speaking child wrote on her slate
    answer: int | None = None  # what she said
    move: dict[str, Any] = field(default_factory=dict)  # the teacher's move as a tag
    children: list[dict[str, Any]] = field(default_factory=list)  # the confusion meter
    # The other children who spoke this turn (the engine's template lines): speaker, line, subtitle,
    # what she said and wrote. The first speaker's fields stay above.
    others: list[dict[str, Any]] = field(default_factory=list)
    source: str = ""  # how the first line was made: ai, template (a fallback), engine (by choice)


def confusion_band(strength: float) -> str:
    """A word for how strongly a child still holds the mistake. Computed by code from the engine."""
    return "high" if strength >= 0.66 else "medium" if strength >= 0.33 else "low"


def children_view(
    session: PracticeSession, kids: Sequence[Any], plan: TurnPlan | None = None
) -> list[dict[str, Any]]:
    """The five children as the screen needs them: the confusion meter, who they are (a sprite
    persona id) and the expression their faces show. All of it is computed here, by code."""
    out = []
    talking: dict[str | None, TurnPlan] = {}
    if plan is not None:
        talking = {p.speaker: p for p in (plan, *plan.chorus)}
    for c in kids:
        persona = session.personas.get(c.name)
        mine = talking.get(c.name)
        speaking = mine is not None
        out.append(
            {
                "name": c.name,
                "level": round(c.strength, 2),
                "band": confusion_band(c.strength),
                "has_error": c.error is not None,
                "persona": persona.id if persona else None,
                "speaking": speaking,
                "expression": face(
                    speaking=speaking,
                    intent=(mine or plan).intent if (mine or plan) else "",
                    correct=(mine or plan).correct if (mine or plan) else None,
                    engagement=c.engagement,
                    strength=c.strength,
                    quiet=c.quiet_turns > 0,
                    shy=c.shy,
                ),
            }
        )
    return out


def seating(session: PracticeSession) -> list[dict[str, Any]]:
    """The children as she first sees them. Nothing here says who holds the error."""
    out = []
    for c in session.state.children:
        persona = session.personas.get(c.name)
        out.append(
            {
                "name": c.name,
                "shy": c.shy,
                "persona": persona.id if persona else None,
                "expression": face(
                    speaking=False, intent="", correct=None, engagement=0.5, strength=0.0,
                    quiet=False, shy=c.shy,
                ),
            }
        )  # fmt: skip
    return out


def _move_tag(session: PracticeSession, move_id: str) -> dict[str, Any]:
    for m in session.loaded.movelist.moves:
        if m.id == move_id:
            return {
                "id": m.id, "label": m.label[session.language], "quality": m.quality,
                "strategy": m.strategy,
            }  # fmt: skip
    return {"id": move_id, "label": move_id, "quality": "neutral", "strategy": False}


def _pick_names(language: str, seed: int) -> list[PersonaChild]:
    """Five distinct fictional children, balanced by gender (3+2 either way), seeded."""
    rng = random.Random(f"names:{seed}")
    kids = load_personas().children
    girls = [k for k in kids if k.gender == "f"]
    boys = [k for k in kids if k.gender == "m"]
    rng.shuffle(girls)
    rng.shuffle(boys)
    pick = [*girls[:3], *boys[:2]] if seed % 2 == 0 else [*girls[:2], *boys[:3]]
    rng.shuffle(pick)
    return pick


def start_session(
    error: str,
    language: str,
    *,
    counts: Mapping[ErrorCode, int] | None = None,
    checked: int = 0,
    seed: int | None = None,
    judge: bool = False,
    session_id: str | None = None,
) -> PracticeSession:
    loaded = load_scenario(error)
    seed = random.SystemRandom().randrange(1, 2**31) if seed is None else seed
    kids = _pick_names(language, seed)
    names = [k.names[language] for k in kids]
    seats = fill_seats(
        counts or {},
        checked,
        loaded.scenario.error,
        loaded.scenario.seat_mix,
        names=names,
        stage_mix=loaded.scenario.stage_mix,
    )
    return PracticeSession(
        id=session_id or uuid.uuid4().hex[:12],
        error=error,
        language=language,
        judge=judge,
        seed=seed,
        loaded=loaded,
        state=new_session(loaded.config, seats, seed),
        personas={k.names[language]: k for k in kids},
    )


def _history(session: PracticeSession) -> list[str]:
    lines: list[str] = []
    for r in session.records[-6:]:
        lines.append(f"teacher: {r.teacher_text}")
        if r.child_text:
            lines.append(f"{r.speaker}: {r.child_text}")
        lines.extend(f"{who}: {said}" for who, said in r.others)
    return lines


def _run_stats(runs: list[CallResult | None]) -> dict[str, Any]:
    done = [r for r in runs if r is not None]
    return {
        "calls": [f"call {r.audit_id}" for r in done],
        "tokens": {
            "in": sum(r.usage.input_tokens for r in done),
            "out": sum(r.usage.output_tokens for r in done),
            "cache_read": sum(r.usage.cache_read_tokens for r in done),
        },
        "cost_usd": sum(r.cost_usd for r in done),
        "retries": sum(r.retries for r in done),
    }


def _engine_layer(plan: TurnPlan) -> dict[str, Any]:
    return {
        "speaker": plan.speaker,
        "intent": plan.intent,
        "answer": plan.answer,
        "correct": plan.correct,
        "error_code": plan.error_code.value if plan.error_code else None,
        "problem": (
            {"kind": plan.problem.kind, "a": plan.problem.a, "b": plan.problem.b}
            if plan.problem
            else None
        ),
        "steps": [{"op": s.op, "numbers": list(s.numbers)} for s in plan.steps],
        "mood": plan.mood,
        "strength_before": dict(plan.strength_before),
        "strength_after": dict(plan.strength_after),
        "chorus": [
            {"speaker": c.speaker, "intent": c.intent, "answer": c.answer, "correct": c.correct}
            for c in plan.chorus
        ],
    }


def take_turn(
    session: PracticeSession,
    *,
    text: str | None = None,
    material: str | None = None,
    stt_confidence: float | None = None,
    context: CallContext | None = None,
    on_candidate: Callable[[str, str], None] | None = None,
    scripted: ScriptedMove | None = None,
) -> TurnResult:
    """One teacher turn: typed or spoken text, or a tap on the materials tray.

    `scripted` is the demo teacher's move (judge mode only): the move is already chosen, so the
    labeller (call 2) is not used."""
    if session.state.finished or session.ended:
        raise SessionFinished(session.state.finished_reason or "ended")
    if scripted is None and (text is None) == (material is None):
        raise ValueError("give either text or a material tap")
    started = time.monotonic()
    ctx = replace(context or CallContext(), judge=session.judge)
    loaded = session.loaded
    children = [c.name for c in session.state.children]
    label: LabelResult | None = None
    if scripted is not None:
        if text is None:
            raise ValueError("a scripted move needs its line")
        teacher_text = text.strip()
        move_id, addressed, posed = scripted.move_id, scripted.addressed, scripted.posed
        if addressed is None:
            addressed = session.last_addressed
    elif material is not None:
        if material not in loaded.config.material_moves:
            raise ValueError(f"unknown material {material!r}")
        move_id, addressed, posed = loaded.config.material_moves[material], None, None
        teacher_text = f"[tapped {material}]"
        addressed = session.last_addressed
    else:
        assert text is not None
        # A real child's name, a roll number or a phone number never reaches a model or the record;
        # the five pretend children are fictional, so their names stay.
        teacher_text = mask_personal(text.strip(), keep=children).text
        label = label_move(
            teacher_text,
            moves=[(m.id, m.description["en"]) for m in loaded.movelist.moves],
            children=children,
            language=session.language,
            context=ctx,
        )
        move_id, addressed, posed = label.move_id, label.addressed, label.posed
        if label.scope == "none":  # she named nobody: the child she was talking to continues
            addressed = session.last_addressed
    plan, new_state = plan_turn(
        session.state, loaded.config, move_id, addressed=addressed, posed=posed
    )
    # Bayesian child model only: the five fictional children's beliefs, in the debug log only.
    if plan.trace:
        log.debug("bayes trace turn %d: %s", plan.turn, [asdict(r) for r in plan.trace])
    persona = session.personas.get(plan.speaker or "")
    skip_checker = practice_skip_checker()
    ai_intents = practice_ai_intents()
    if plan.speaker is not None and ai_intents is not None and plan.intent not in ai_intents:
        # Not a kind of line the deployment asks the AI for: the engine's own template line.
        line: ChildLineResult = ChildLineResult(
            render_line(plan, session.language), "engine", None, None, render_line(plan, "en")
        )
    else:
        line = child_line(
            plan,
            name=plan.speaker or "",
            temperament=persona.temperament if persona else "",
            language=session.language,
            teacher_line=teacher_text,
            history=_history(session),
            target_error=session.error,
            context=ctx,
            on_candidate=on_candidate,
            skip_checker=skip_checker,
        )
    # The other children who speak in the same turn answer or react in the engine's template words:
    # they say their own answer to the problem on the board, which a template carries whole. Only a
    # child explaining her working needs the AI, and that is always the first speaker.
    others = [
        {
            "speaker": sub.speaker,
            "child_text": render_line(sub, session.language),
            "child_text_en": render_line(sub, "en"),
            "intent": sub.intent,
            "answer": sub.answer,
            "written": sub.written,
            "source": "engine",
        }
        for sub in plan.chorus
    ]
    session.state = new_state
    if addressed:
        session.last_addressed = addressed
    session.plan_numbers |= set(plan.allowed_numbers)
    for sub in plan.chorus:
        session.plan_numbers |= set(sub.allowed_numbers)
    session.records.append(
        TurnRecord(
            plan.turn,
            teacher_text,
            move_id,
            addressed,
            plan.speaker,
            line.text,
            plan.intent,
            line.source,
            [(o["speaker"], o["child_text"]) for o in others],
        )
    )
    latency_ms = int((time.monotonic() - started) * 1000)
    checker_run = line.gate.checker.result if line.gate and line.gate.checker else None
    stats = _run_stats([label.run if label else None, line.run, checker_run])
    verdict = line.gate.verdict if line.gate else None
    if line.source == "ai":
        badge, explanation = (
            (line.gate.badge.value, line.gate.explanation) if line.gate else ("none", "")
        )
    elif line.source == "engine":
        badge, explanation = "none", ""
    elif line.source == "template":
        badge = "none"
        explanation = line.gate.explanation if line.gate else "A safe template line was used."
    else:
        badge, explanation = "none", ""
    validators = [
        {"name": r.name, "ok": r.ok, "codes": r.codes}
        for r in (line.run.results if line.run else [])
    ]
    layers = {
        "input": {
            "teacher_text": teacher_text if material is None else None,
            "material": material,
            "stt_confidence": stt_confidence,
        },
        "processing": {
            "label": (
                {"move_id": move_id, "source": "demo teacher", "addressed": addressed}
                if scripted is not None
                else {
                    "move_id": label.move_id,
                    "addressed": addressed,
                    "confidence": label.confidence,
                    "forced": label.forced,
                }  # fmt: skip
                if label
                else {"move_id": move_id, "source": "material tap"}
            ),
            "posed_problem": ({"kind": posed.kind, "a": posed.a, "b": posed.b} if posed else None),
            "engine": _engine_layer(plan),
        },
        "guardrails": {
            "validators": validators,
            "checker": (
                {"passed": verdict.passed, "failed_items": verdict.failed_items}
                if verdict
                else None
            ),
            "retries": stats["retries"],
            "fallback_used": line.run.fallback_used if line.run else None,
            # call 7 was left out by the deployment's choice: the code checks alone released it
            "checker_skipped": bool(skip_checker and line.source == "ai"),
        },
        "evaluation": {
            "latency_ms": latency_ms,
            "tokens": stats["tokens"],
            "cost_usd": stats["cost_usd"],
            "calls": stats["calls"],
            "call_ms": {
                k: v.latency_ms
                for k, v in (
                    ("label", label.run if label else None),
                    ("child", line.run),
                    ("check", checker_run),
                )
                if v is not None
            },  # fmt: skip
        },
        "output": {"child_line": line.text, "source": line.source, "badge": badge},
    }
    return TurnResult(
        turn=plan.turn,
        speaker=plan.speaker,
        child_text=line.text,
        intent=plan.intent,
        numbers=sorted(plan.allowed_numbers),
        label=layers["processing"]["label"],
        badge=badge,
        explanation=explanation,
        layers=layers,
        latency_ms=latency_ms,
        cost_usd=stats["cost_usd"],
        finished=new_state.finished,
        finished_reason=new_state.finished_reason,
        child_text_en=line.english,
        others=others,
        source=line.source,
        written=plan.written,
        answer=plan.answer,
        move=_move_tag(session, move_id),
        children=children_view(session, new_state.children, plan),
    )


def end_session(
    session: PracticeSession, *, context: CallContext | None = None
) -> tuple[FeedbackCard, dict[str, Any]]:
    """Feedback for the whole rehearsal (call 3). Private: the card goes to her phone only."""
    ctx = replace(context or CallContext(), judge=session.judge)
    # A tap on the materials tray is a move too ("[tapped bundles]"), so it counts as evidence.
    turns = [TurnLine(r.turn, r.teacher_text, r.move_id, r.child_text) for r in session.records]
    labelled = {r.turn: r.move_id for r in session.records}
    scolded = any(r.move_id == "scold" for r in session.records)
    started = time.monotonic()
    card, run = give_feedback(
        turns,
        rubric=session.loaded.rubric,
        language=session.language,
        allowed_numbers=frozenset(session.plan_numbers),
        scolded=scolded,
        target_error=session.error,
        context=ctx,
    )
    session.ended = True
    stats = _run_stats([run, card.gate.checker.result if card.gate and card.gate.checker else None])
    layers = {
        "input": {"turns": len(session.records), "labels": labelled},
        "processing": {"source": card.source},
        "guardrails": {
            "validators": [
                {"name": r.name, "ok": r.ok, "codes": r.codes} for r in (run.results if run else [])
            ],
            "fallback_used": run.fallback_used if run else None,
        },
        "evaluation": {
            "latency_ms": int((time.monotonic() - started) * 1000),
            "tokens": stats["tokens"],
            "cost_usd": stats["cost_usd"],
        },
        "output": {"badge": card.badge.value},
    }
    return card, layers
