"""Call 7, the output checker: the last automatic gate before text reaches a teacher.

Fails closed: if the call fails or returns something inconsistent, the verdict is 'not passed'
and the content goes to a human or a template.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from pydantic import BaseModel

from ai.client import CallContext, CallInput, CallResult, run_call
from ai.guard.rejections import examples_block
from ai.schemas import Verdict
from ai.validators import ValidatorResult, Violation

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
        },
        untrusted={"candidate_text": text},
    )
    result = run_call(7, payload, context=ctx)
    verdict = result.output
    assert isinstance(verdict, Verdict)
    return CheckOutcome(verdict=verdict, result=result)
