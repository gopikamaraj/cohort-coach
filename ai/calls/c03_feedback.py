"""Call 3, rehearsal feedback: two strengths and one thing to try, each quoting her own words.

Guards: every quote is verbatim in the turn it cites (and that turn is hers, not a child's);
rubric points come only from the rubric; a strength's turn must carry one of that point's
moves; no scores; numbers only from the transcript and the engine's plans; the usual gates and
call 7. If anything fails twice, a deterministic card is built from the rubric and her own
lines. The AI never scores a teacher, and the feedback is private.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

import yaml
from pydantic import BaseModel

from ai.client import CallContext, CallInput, CallResult, run_call
from ai.guard.badges import Badge
from ai.guard.gates import ContentType, GateInput, GateResult, gate1, run_gates
from ai.schemas import Feedback, FeedbackPoint, TryNext
from ai.validators import ValidatorResult, Violation
from ai.validators.numbers import extract_numbers
from ai.validators.quotes import quote_in_transcript
from ai.validators.scores import check_no_scores
from services.practice.content import CONTENT, Rubric

QUOTE_WORDS = 12


@dataclass(frozen=True)
class TurnLine:
    turn: int
    teacher_text: str
    move_id: str
    child_text: str = ""


@dataclass(frozen=True)
class StrengthItem:
    point: str
    text: str  # the rubric's words for this point, in her language
    comment: str
    quote: str
    turn_id: int


@dataclass(frozen=True)
class TryItem:
    point: str
    text: str
    suggestion: str
    quote: str | None
    turn_id: int | None


@dataclass(frozen=True)
class FeedbackCard:
    strengths: tuple[StrengthItem, ...]
    try_next: TryItem
    note: str | None  # a gentle note added by the app (for example after scolding)
    source: str  # ai | template
    badge: Badge
    gate: GateResult | None


def transcript_text(turns: Sequence[TurnLine]) -> str:
    out = []
    for t in turns:
        out.append(f"T{t.turn} teacher: {t.teacher_text}")
        if t.child_text:
            out.append(f"T{t.turn} child: {t.child_text}")
    return "\n".join(out)


def card_text(fb: Feedback) -> str:
    return "\n".join([*(s.comment for s in fb.strengths), fb.try_next.suggestion])


def _quotes(fb: Feedback) -> list[tuple[str, int | None]]:
    items: list[tuple[str, int | None]] = [(s.quote, s.turn_id) for s in fb.strengths]
    if fb.try_next.quote:
        items.append((fb.try_next.quote, fb.try_next.turn_id))
    return items


def feedback_results(
    fb: Feedback,
    turns: Sequence[TurnLine],
    rubric: Rubric,
    language: str,
    allowed_numbers: frozenset[int],
) -> list[ValidatorResult]:
    by_turn = {t.turn: t for t in turns}
    points = {p.id: p for p in rubric.points}
    problems: list[Violation] = []
    quote_problems: list[Violation] = []
    seen: set[str] = set()
    for s in fb.strengths:
        point = points.get(s.rubric_point)
        if point is None:
            problems.append(Violation("rubric_point_unknown"))
            continue
        if s.rubric_point in seen:
            problems.append(Violation("rubric_point_repeated"))
        seen.add(s.rubric_point)
        turn = by_turn.get(s.turn_id)
        if turn is None or turn.move_id not in point.move_ids:
            problems.append(Violation("strength_without_evidence"))
    if fb.try_next.rubric_point not in points:
        problems.append(Violation("rubric_point_unknown"))
    for quote, turn_id in _quotes(fb):
        turn = by_turn.get(turn_id) if turn_id is not None else None
        if turn is None or not quote_in_transcript(quote, turn.teacher_text):
            quote_problems.append(Violation("quote_not_in_her_turn"))
    text = card_text(fb)
    teacher_words = "\n".join(t.teacher_text for t in turns)
    results = [
        ValidatorResult("rubric", tuple(problems)),
        ValidatorResult("quotes", tuple(quote_problems)),
        ValidatorResult("no_scores", tuple(check_no_scores(text))),
    ]
    results += gate1(
        GateInput(
            text=text,
            content_type=ContentType.FEEDBACK_CARD,
            language=language,
            allowed_numbers=allowed_numbers,
            transcript=teacher_words,
        )
    )
    return results


def _note(language: str) -> str:
    data = yaml.safe_load((CONTENT / "templates/feedback_notes.yaml").read_text(encoding="utf-8"))
    return str(data["scold"][language])


def _short_quote(text: str) -> str:
    return " ".join(text.split()[:QUOTE_WORDS])


def template_feedback(turns: Sequence[TurnLine], rubric: Rubric, language: str) -> Feedback:
    """A deterministic card from the rubric and her own lines (no AI)."""
    used: list[tuple[str, int]] = []
    for p in rubric.points:
        turn = next((t for t in turns if t.move_id in p.move_ids and t.teacher_text.strip()), None)
        if turn is not None:
            used.append((p.id, turn.turn))
    by_turn = {t.turn: t for t in turns}
    by_id = {p.id: p for p in rubric.points}
    strengths = [
        FeedbackPoint(
            rubric_point=pid,
            turn_id=tid,
            quote=_short_quote(by_turn[tid].teacher_text),
            comment=by_id[pid].text[language],
        )
        for pid, tid in used[:2]
    ]
    unused = [p for p in rubric.points if p.id not in {u[0] for u in used}]
    pick = unused[0] if unused else rubric.points[0]
    return Feedback.model_construct(  # strengths may be empty here; the card handles that
        strengths=strengths,
        try_next=TryNext(rubric_point=pick.id, suggestion=pick.try_next[language]),
    )


def _card(fb: Feedback, rubric: Rubric, language: str, scolded: bool, source: str,
          badge: Badge, gate: GateResult | None) -> FeedbackCard:  # fmt: skip
    by_id = {p.id: p for p in rubric.points}
    return FeedbackCard(
        strengths=tuple(
            StrengthItem(
                s.rubric_point, by_id[s.rubric_point].text[language], s.comment, s.quote, s.turn_id
            )  # fmt: skip
            for s in fb.strengths
        ),
        try_next=TryItem(
            fb.try_next.rubric_point,
            by_id[fb.try_next.rubric_point].try_next[language],
            fb.try_next.suggestion,
            fb.try_next.quote,
            fb.try_next.turn_id,
        ),
        note=_note(language) if scolded else None,
        source=source,
        badge=badge,
        gate=gate,
    )


def give_feedback(
    turns: Sequence[TurnLine],
    *,
    rubric: Rubric,
    language: str,
    allowed_numbers: frozenset[int],
    scolded: bool,
    target_error: str | None = None,
    context: CallContext | None = None,
) -> tuple[FeedbackCard, CallResult | None]:
    base = context or CallContext()
    template = template_feedback(turns, rubric, language)
    nums = frozenset(extract_numbers(transcript_text(turns))) | allowed_numbers

    def check(out: BaseModel) -> list[ValidatorResult]:
        assert isinstance(out, Feedback)
        return feedback_results(out, turns, rubric, language, nums)

    ctx = replace(base, validators=check, fallback=lambda: template)
    payload = CallInput(
        trusted={
            "language": language,
            "rubric": [
                {
                    "id": p.id,
                    "text": p.text[language],
                    "try_next": p.try_next[language],
                    "moves": p.move_ids,
                }
                for p in rubric.points
            ],
            "labels": [{"turn": t.turn, "move_id": t.move_id} for t in turns],
            "scolded": scolded,
        },
        untrusted={"transcript": transcript_text(turns)},
    )
    run = run_call(3, payload, context=ctx)
    fb = run.output
    assert isinstance(fb, Feedback)
    if run.fallback_used:
        return _card(fb, rubric, language, scolded, "template", Badge.NONE, None), run
    teacher_words = "\n".join(t.teacher_text for t in turns)
    gate = run_gates(
        GateInput(
            text=card_text(fb),
            content_type=ContentType.FEEDBACK_CARD,
            language=language,
            allowed_numbers=nums,
            target_error=target_error,
            quotes=[q for q, _ in _quotes(fb)],
            transcript=teacher_words,
            source_audit_id=run.audit_id,
        ),
        context=base,
    )
    if not gate.releasable:
        return _card(template, rubric, language, scolded, "template", Badge.NONE, gate), run
    return _card(fb, rubric, language, scolded, "ai", gate.badge, gate), run
