"""Gate pipelines per content type.

Gate 1 code validators -> gate 1b rule-based pre-filter -> gate 2 call 7 (only if the earlier
gates pass, so a bad line never costs a checker call) -> gate 3 human approval (track content and
method cards) -> gate 4 teacher flag (see flags.py).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from enum import StrEnum

from ai.calls.c07_checker import CheckOutcome, check_output
from ai.client import CallContext
from ai.guard.badges import Badge, badge_line, compute_badge
from ai.guard.explain import explain
from ai.schemas import Verdict
from ai.validators import ValidatorResult
from ai.validators.arithmetic import check_arithmetic, check_child_tags, normalise_child_tags
from ai.validators.check_items import check_items
from ai.validators.length import check_length
from ai.validators.numbers import check_digits_only, check_numbers
from ai.validators.prefilter import check_prefilter
from ai.validators.quotes import check_quotes
from ai.validators.readability import check_readability
from services.content.slots import check_slots, literal_class_counts, sample_fill


class ContentType(StrEnum):
    CHILD_LINE = "child_line"
    FEEDBACK_CARD = "feedback_card"
    METHOD_CARD = "method_card"
    TRACK_DRAFT = "track_draft"
    DIGEST = "digest"


# Track content and method cards also need human approval (reviewer, then mentor).
NEEDS_HUMAN = {ContentType.METHOD_CARD, ContentType.TRACK_DRAFT}
AUDIENCE = {
    ContentType.CHILD_LINE: "child",
    ContentType.FEEDBACK_CARD: "teacher",
    ContentType.METHOD_CARD: "teacher",
    ContentType.TRACK_DRAFT: "teacher",
    ContentType.DIGEST: "teacher",
}
CHILD_LINE_MAX_WORDS = 30

# violation code -> explanation key, in priority order
_CODE_TO_REASON: tuple[tuple[str, str], ...] = (
    ("arithmetic_wrong", "held_maths"),
    ("child_tag_is_correct", "held_maths"),
    ("slot_unknown", "held_slots"),
    ("class_number_literal", "held_slots"),
    ("check_item", "held_check_item"),
    ("number_not_allowed", "held_number"),
    ("number_word", "held_number"),
    ("quote_not_found", "held_quote"),
    ("script_mismatch", "held_language"),
    ("sentence_too_long", "held_reading"),
    ("word_too_long", "held_reading"),
    ("jargon", "held_reading"),
)


@dataclass
class GateInput:
    text: str
    content_type: ContentType
    language: str
    target_error: str | None = None
    allowed_numbers: Iterable[int] | None = None  # child lines: the engine's answer
    quotes: list[str] = field(default_factory=list)
    transcript: str = ""
    roster_names: tuple[str, ...] = ()
    human_approved: bool = False
    source_audit_id: int | None = None  # the audit row of the call that made the text
    checker_facts: dict[str, object] | None = None  # what call 7 needs to judge a child line
    # A track draft written with {{slots}} and [child: n] tags (P09). Class numbers must come only
    # through slots, and no Form A or Form B item may appear. Pilot scripts are built by code from
    # real counts and leave this off.
    slots_mode: bool = False


@dataclass
class GateResult:
    passed_automatic: bool
    stage_failed: str | None  # gate1 | gate1b | gate2
    results: list[ValidatorResult]
    verdict: Verdict | None
    needs_human: bool
    badge: Badge
    releasable: bool  # gates 1-2 passed and, where required, a human approved
    explanation: str
    badge_text: str
    checker: CheckOutcome | None = None


def gate1(inp: GateInput) -> list[ValidatorResult]:
    """Gate 1 (code validators) then gate 1b (pre-filter), as named results."""
    audience = AUDIENCE[inp.content_type]
    results: list[ValidatorResult] = []
    child = inp.content_type is ContentType.CHILD_LINE
    raw_text = inp.text
    if inp.slots_mode:
        results.append(ValidatorResult("slots", tuple(check_slots(raw_text))))
        results.append(ValidatorResult("class_numbers", tuple(literal_class_counts(raw_text))))
        # the text as a teacher will hear it: slots filled with sample values, tags normalised
        inp = replace(inp, text=normalise_child_tags(sample_fill(raw_text)))
        results.append(ValidatorResult("child_tags", tuple(check_child_tags(inp.text))))
        results.append(ValidatorResult("check_items", tuple(check_items(inp.text))))
    if child:
        allowed = set(inp.allowed_numbers or ())
        results.append(ValidatorResult("numbers", tuple(check_numbers(inp.text, allowed))))
        results.append(
            ValidatorResult("number_words", tuple(check_digits_only(inp.text, inp.language)))
        )
        results.append(
            ValidatorResult("length", tuple(check_length(inp.text, max_words=CHILD_LINE_MAX_WORDS)))
        )
    elif inp.allowed_numbers is not None:
        results.append(
            ValidatorResult("numbers", tuple(check_numbers(inp.text, set(inp.allowed_numbers))))
        )
    if inp.quotes:
        results.append(ValidatorResult("quotes", tuple(check_quotes(inp.quotes, inp.transcript))))
    if not child:  # a child's wrong answer is on purpose; her numbers are checked against the plan
        results.append(ValidatorResult("arithmetic", tuple(check_arithmetic(inp.text))))
    results.append(
        ValidatorResult("readability", tuple(check_readability(inp.text, inp.language, audience)))
    )
    results.append(
        ValidatorResult(
            "prefilter",
            tuple(
                check_prefilter(
                    inp.text,
                    inp.language,
                    max_words=CHILD_LINE_MAX_WORDS if child else None,
                    max_chars=None if inp.content_type is ContentType.TRACK_DRAFT else 4000,
                    roster_names=inp.roster_names,
                )
            ),
        )
    )
    return results


def _audit_reason(verdict: Verdict) -> str:
    """Only the fixed rubric item codes go to the audit row: the free-text reason can quote text."""
    return ",".join(verdict.failed_items) if verdict.failed_items else "pass"


def _reason_key(results: list[ValidatorResult]) -> str:
    codes = {c for r in results for c in r.codes}
    for code, key in _CODE_TO_REASON:
        if code in codes:
            return key
    return "held_filter"


def run_gates(inp: GateInput, *, context: CallContext | None = None) -> GateResult:
    needs_human = inp.content_type in NEEDS_HUMAN
    results = gate1(inp)
    failed = [r for r in results if not r.ok]
    if failed:
        # The pre-filter is gate 1b; everything else is gate 1.
        stage = "gate1b" if all(r.name == "prefilter" for r in failed) else "gate1"
        return GateResult(
            passed_automatic=False,
            stage_failed=stage,
            results=results,
            verdict=None,
            needs_human=False,
            badge=Badge.NONE,
            releasable=False,
            explanation=explain(_reason_key(failed), inp.language),
            badge_text="",
        )

    outcome = check_output(
        inp.text,
        audience=AUDIENCE[inp.content_type],
        language=inp.language,
        target_error=inp.target_error,
        code_checks=results,
        context=context,
        facts=inp.checker_facts,
    )
    verdict = outcome.verdict
    if not outcome.passed:
        down = "checker_unavailable" in verdict.failed_items
        key = "held_checker_down" if down else "held_checker"
        reason = verdict.reason_for_user if not down else ""
        if inp.source_audit_id is not None and context is not None and context.sink is not None:
            context.sink.update(
                inp.source_audit_id,
                checker_verdict="fail",
                checker_reason=_audit_reason(verdict),
            )
        return GateResult(
            passed_automatic=False,
            stage_failed="gate2",
            results=results,
            verdict=verdict,
            needs_human=down,
            badge=Badge.NONE,
            releasable=False,
            explanation=explain(key, inp.language, reason=reason),
            badge_text="",
            checker=outcome,
        )

    if inp.source_audit_id is not None and context is not None and context.sink is not None:
        context.sink.update(
            inp.source_audit_id, checker_verdict="pass", checker_reason=_audit_reason(verdict)
        )
    approved = inp.human_approved and needs_human
    badge = compute_badge(gates_1_2_passed=True, human_approved=approved)
    releasable = (not needs_human) or inp.human_approved
    if needs_human and not inp.human_approved:
        key = "waiting_review"
    else:
        key = "passed_reviewed" if approved else "passed"
    return GateResult(
        passed_automatic=True,
        stage_failed=None,
        results=results,
        verdict=verdict,
        needs_human=False,
        badge=badge,
        releasable=releasable,
        explanation=explain(key, inp.language),
        badge_text=badge_line(badge, inp.language),
        checker=outcome,
    )
