"""Call 5, track drafting: one voice lesson (or the model lesson) in one language per request.

The strongest model drafts offline (a Message Batch, or one synchronous call for an urgent part).
The draft holds slots for class numbers and tags for a child's intentional mistake; code fills and
checks them. It then goes through gate 1 (slots only, no class counts, arithmetic, no Form A or B
item, reading level), gate 1b (pre-filter) and call 7. A draft that fails code is blocked before
the review queue; one that passes waits there for the coach, then the officer switches it on.

Nothing here approves anything: a person does that (CLAUDE.md rule 4).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Any

from ai.client import CallContext, CallInput, CallResult, run_call
from ai.guard.explain import error_name
from ai.guard.gates import ContentType, GateInput, GateResult, gate1, run_gates
from ai.schemas import TrackPart
from ai.validators import ValidatorResult
from services.content.slots import SLOT_SOURCES, slots_used
from services.content.track import Track, load_strategies, load_template

CALL_ID = 5
MAX_METHOD_CARDS = 3
KINDS = ("lesson", "model_lesson")
TODO_HUMAN = "TODO-HUMAN(Seema): review this draft; Hindi and Tamil wording needs a native reader."


@dataclass
class PartDraft:
    kind: str
    day: int
    language: str
    # needs_review | held_by_code | held_by_checker | no_output
    status: str
    part: TrackPart | None
    gate: GateResult | None
    results: list[ValidatorResult]
    explanation: str
    run: CallResult | None = None


def _pick(mapping: dict[str, str], language: str) -> str:
    return mapping.get(language) or mapping["en"]


def build_payload(
    track: Track,
    kind: str,
    day: int,
    language: str,
    *,
    method_cards: Sequence[str] = (),
    variant: str | None = None,
    practice_level: int | None = None,
) -> CallInput:
    """`variant` and `practice_level` are set by code for a next lesson ("smaller_step": the same
    approach as a smaller step with more practice); they are added only when set, so every other
    request is unchanged."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    library = load_strategies()
    if kind == "lesson":
        lesson = next((x for x in track.lessons if x.day == day), None)
        if lesson is None:
            raise ValueError(f"the track has no lesson for day {day}")
        topic, strategy_ids, level = (
            _pick(lesson.topic, language),
            lesson.strategies,
            lesson.practice_level,
        )
        template = "voice_lesson.v1.md"
    else:
        if day != 0:
            raise ValueError("the model lesson has day 0")
        topic, strategy_ids, level = "Model lesson", track.model_strategies, None
        template = "model_lesson.v1.md"
    strategies = [
        {
            "id": sid,
            "label": _pick(library[sid].label, language),
            "description": _pick(library[sid].description, language),
            "worked_examples": list(library[sid].worked_examples),
        }
        for sid in strategy_ids
    ]
    trusted: dict[str, Any] = {
        "error": track.error,
        "error_name": error_name(track.error, language),
        "language": language,
        "part": {"kind": kind, "day": day, "topic": topic, "total_days": len(track.lessons)},
        "strategies": strategies,
        "practice_level": level,
        "slots": dict(SLOT_SOURCES),
        "structure": load_template(template),
    }
    if practice_level is not None:
        trusted["practice_level"] = practice_level
    if variant is not None:
        trusted["variant"] = variant
    cards = list(method_cards)[:MAX_METHOD_CARDS]
    untrusted = {"mentor_text": "\n\n".join(cards)} if cards else {}
    return CallInput(trusted=trusted, untrusted=untrusted)


def _gate_input(script: str, language: str, error: str, audit_id: int | None = None) -> GateInput:
    return GateInput(
        text=script,
        content_type=ContentType.TRACK_DRAFT,
        language=language,
        target_error=error,
        slots_mode=True,
        source_audit_id=audit_id,
    )


def draft_part(
    track: Track,
    kind: str,
    day: int,
    language: str,
    *,
    context: CallContext | None = None,
    method_cards: Sequence[str] = (),
    variant: str | None = None,
    practice_level: int | None = None,
) -> PartDraft:
    payload = build_payload(
        track,
        kind,
        day,
        language,
        method_cards=method_cards,
        variant=variant,
        practice_level=practice_level,
    )
    base = context or CallContext()

    def validate(out: object) -> list[ValidatorResult]:
        assert isinstance(out, TrackPart)
        return gate1(_gate_input(out.script, language, track.error))

    # no fallback: a track part that fails code twice goes back to a person, never to a template
    ctx = replace(base, output_model=TrackPart, validators=validate, fallback=None)
    run = run_call(CALL_ID, payload, context=ctx)
    part = run.output
    if part is None:
        held = (run.fallback_used or "").endswith("validators")
        gate_results = [r for r in run.results if not r.ok]
        status = "held_by_code" if held else "no_output"
        return PartDraft(
            kind,
            day,
            language,
            status,
            None,
            None,
            gate_results or run.results,
            _explain(held, gate_results, language),
            run,
        )
    assert isinstance(part, TrackPart)
    return gate_part(track, kind, day, language, part, context=base, run=run)


def gate_script(
    script: str,
    language: str,
    error: str,
    *,
    context: CallContext | None = None,
    audit_id: int | None = None,
) -> GateResult:
    """Gates 1, 1b and call 7 on a track script: used for a fresh draft and again for every edit a
    reviewer makes, so a human edit cannot slip past the checks."""
    return run_gates(_gate_input(script, language, error, audit_id), context=context)


def gate_part(
    track: Track,
    kind: str,
    day: int,
    language: str,
    part: TrackPart,
    *,
    context: CallContext | None = None,
    run: CallResult | None = None,
) -> PartDraft:
    """Gates 1, 1b and call 7 on a drafted part, however it was drafted (synchronously or from a
    Message Batch result). The result says whether it may go to the review queue."""
    gate = gate_script(
        part.script, language, track.error, context=context, audit_id=run.audit_id if run else None
    )
    if gate.passed_automatic:
        status, kept = "needs_review", part
    elif gate.stage_failed == "gate2":
        status, kept = "held_by_checker", part  # kept so a person can see what was held and why
    else:
        status, kept = "held_by_code", None  # blocked before the queue
    return PartDraft(kind, day, language, status, kept, gate, gate.results, gate.explanation, run)


def _explain(held: bool, failed: list[ValidatorResult], language: str) -> str:
    from ai.guard.explain import explain

    if not held:
        return explain("held_checker_down", language)
    codes = {c for r in failed for c in r.codes}
    for code, key in (
        ("arithmetic_wrong", "held_maths"),
        ("check_item", "held_check_item"),
        ("class_number_literal", "held_slots"),
        ("slot_unknown", "held_slots"),
    ):
        if code in codes:
            return explain(key, language)
    return explain("held_filter", language)


def review_content(draft: PartDraft, track: Track) -> dict[str, Any]:
    """What a review item stores: the words, the slots they use, and every check result (the
    reviewer sees the machine's findings next to the text; details are facts, never a copy)."""
    assert draft.part is not None
    lesson = next((x for x in track.lessons if x.day == draft.day), None)
    return {
        "track_id": track.id,
        "track_version": track.version,
        "kind": draft.kind,
        "day": draft.day,
        "language": draft.language,
        "error": track.error,
        "script": draft.part.script,
        "slots_used": sorted(set(slots_used(draft.part.script))),
        "strategies": list(lesson.strategies) if lesson else list(track.model_strategies),
        "results": [
            {
                "name": r.name,
                "ok": r.ok,
                "codes": r.codes,
                "details": [v.detail for v in r.violations],
            }
            for r in draft.results
        ],
        "explanation": draft.explanation,
        "status": draft.status,
        "badge": draft.gate.badge.value if draft.gate else "none",
        "audit_id": draft.run.audit_id if draft.run else None,
        "prompt_version": draft.run.prompt_version if draft.run else None,
        "model": draft.run.model if draft.run else None,
        "todo_human": TODO_HUMAN,
    }
