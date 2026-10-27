"""Call 7, the output checker: the last automatic gate before text reaches a teacher.

Fails closed: if the call fails or returns something inconsistent, the verdict is 'not passed'
and the content goes to a human or a template.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace

from pydantic import BaseModel

from ai.client import CallContext, CallInput, CallResult, run_call
from ai.guard.rejections import examples_block, examples_version, latest_examples
from ai.schemas import Verdict
from ai.validators import ValidatorResult, Violation

log = logging.getLogger(__name__)

RUBRIC_ITEMS = frozenset(
    {
        "tone",
        "child_safety",
        "stereotypes",
        "language",
        "fit",
        "reading_level",
        "maths",
        "no_statistics",
        "injection",
        "checker_unavailable",
    }
)

SLOTS_NOTE = (
    "The class numbers in this text are sample values standing in for slots. Code fills each slot "
    "with the real count when a teacher receives the lesson, so the author stated no statistic. "
    "Do not fail the text for these numbers; judge everything else as usual."
)

UNAVAILABLE = {
    "en": "This could not be checked, so a person will look at it first.",
    "hi": "इसकी जाँच नहीं हो सकी, इसलिए पहले कोई व्यक्ति इसे देखेगा।",
    "ta": "இதைச் சரிபார்க்க முடியவில்லை, அதனால் முதலில் ஒருவர் பார்ப்பார்.",
}


@dataclass(frozen=True)
class CheckOutcome:
    verdict: Verdict
    result: CallResult

    @property
    def passed(self) -> bool:
        return self.verdict.passed and self.result.fallback_used is None


def _verdict_ok(output: BaseModel) -> list[ValidatorResult]:
    assert isinstance(output, Verdict)
    problems: list[Violation] = []
    unknown = set(output.failed_items) - RUBRIC_ITEMS
    if unknown:
        problems.append(Violation("unknown_rubric_item", f"{len(unknown)} unknown item(s)"))
    if output.passed and output.failed_items:
        problems.append(Violation("passed_with_failures"))
    if not output.passed and not output.failed_items:
        problems.append(Violation("failed_without_item"))
    return [ValidatorResult("verdict", tuple(problems))]


def check_output(
    text: str,
    *,
    audience: str,
    language: str,
    target_error: str | None,
    code_checks: list[ValidatorResult],
    context: CallContext | None = None,
    facts: dict[str, object] | None = None,
    slots_filled_by_code: bool = False,
) -> CheckOutcome:
    """Run call 7 on one candidate text. `audience` is 'child' or 'teacher'."""
    base = context or CallContext()
    unavailable = Verdict(
        passed=False,
        failed_items=["checker_unavailable"],
        reason_short="checker did not return a usable verdict",
        reason_for_user=UNAVAILABLE[language],
    )
    ctx = replace(
        base,
        validators=_verdict_ok,
        fallback=lambda: unavailable,
        extra_system=examples_block(),
    )
    payload = CallInput(
        trusted={
            "audience": audience,
            "language": language,
            "target_error": target_error,
            "code_checks": [{"name": r.name, "ok": r.ok} for r in code_checks],
            **({"simulated_child": facts} if facts else {}),
            **({"slots_note": SLOTS_NOTE} if slots_filled_by_code else {}),
        },
        untrusted={"candidate_text": text},
    )
    result = run_call(7, payload, context=ctx)
    _record_examples(base, result)
    verdict = result.output
    assert isinstance(verdict, Verdict)
    return CheckOutcome(verdict=verdict, result=result)


def _record_examples(base: CallContext, result: CallResult) -> None:
    """Add the example-set version to the call's audit row, so the trail says which rejected
    examples the checker was shown (version "none" and count 0 when it saw none)."""
    try:
        from ai.audit import default_sink

        sink = base.sink or default_sink()
        entries = [{"name": r.name, "ok": r.ok, "codes": r.codes} for r in result.results]
        entries.append(
            {
                "name": "checker_examples",
                "ok": True,
                "codes": [examples_version(), str(len(latest_examples()))],
            }
        )
        sink.update(result.audit_id, validator_results=entries)
    except Exception:  # the audit trail must never stop a check
        log.warning("could not record the checker example set", exc_info=True)
