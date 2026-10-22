"""Call 11, the sprite item author (offline only): draft the JSON spec of one new item.

It runs when someone authors a pack, never while a teacher or a visitor uses the product, and no art
is generated at run time. The draft passes the code gates (`services/api/sprite_gates.py`); a failed
rule goes back to the author on retry, and after the last retry the draft is dropped. A draft that
passes the code gates is then read by call 7 (the words only: it cannot see pixels), and lands in
`content/sprites/drafts/` as a draft. A coach looks at its contact-sheet tile and approves; a
programme officer enables the pack version that holds it. Every change is a new version.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Any

from pydantic import BaseModel

from ai.calls.c07_checker import CheckOutcome, check_output
from ai.client import CallContext, CallInput, CallResult, run_call
from ai.schemas import SpriteItemDraft
from ai.validators import ValidatorResult
from services.api.sprite_gates import gate_draft, spec_from_draft


@dataclass(frozen=True)
class AuthorOutcome:
    status: str  # awaiting_coach | rejected
    spec: dict[str, Any] | None  # present only when status is awaiting_coach
    alt_en: str
    failed: list[str]  # "rule:code" for every failed rule; empty when the draft passed
    run: CallResult
    checker: CheckOutcome | None


def author_item(
    brief: str,
    *,
    existing_ids: Sequence[str],
    context: CallContext | None = None,
) -> AuthorOutcome:
    """Draft one item from a brief. A rejected draft carries the failing rules and no spec."""
    base = context or CallContext()
    taken = set(existing_ids)

    def check(out: BaseModel) -> list[ValidatorResult]:
        assert isinstance(out, SpriteItemDraft)
        return gate_draft(out, existing=taken)

    ctx = replace(base, validators=check, fallback=None)
    payload = CallInput(
        trusted={"existing_item_ids": sorted(taken)},
        untrusted={"brief": brief},
    )
    run = run_call(11, payload, context=ctx)
    draft = run.output
    if draft is None:
        failed = [f"{r.name}:{c}" for r in run.results if not r.ok for c in r.codes]
        return AuthorOutcome("rejected", None, "", failed or ["no_valid_draft"], run, None)
    assert isinstance(draft, SpriteItemDraft)
    words = f"{draft.alt_en}. Topics: {', '.join(draft.topics)}."
    outcome = check_output(
        words,
        audience="child",
        language="en",
        target_error=None,
        code_checks=run.results,
        context=replace(base, validators=None, fallback=None, output_model=None),
    )
    if not outcome.passed:
        failed = [f"checker:{i}" for i in outcome.verdict.failed_items] or ["checker:failed"]
        return AuthorOutcome("rejected", None, draft.alt_en, failed, run, outcome)
    return AuthorOutcome("awaiting_coach", spec_from_draft(draft), draft.alt_en, [], run, outcome)
