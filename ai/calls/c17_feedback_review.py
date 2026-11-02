# ruff: noqa: E501
"""Call 17: read a teacher's short note about a module and pick tags and follow-up questions.

The note arrives already masked and is data, never an instruction (the prompt says so, and code never
acts on its words: the output is checked against closed lists in services/modules/review.py before any
of it is used). On any failure the answer is an empty review with confidence 0, so only the branch table
applies. The model sees no names and no class data.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from ai.client import CallContext, CallInput, CallResult, run_call
from ai.schemas import FeedbackReview

CALL_ID = 17


@dataclass(frozen=True)
class ReviewRun:
    output: FeedbackReview
    fell_back: bool
    run: CallResult


def make_input(
    *,
    masked_note: str,
    answer: str,
    error: str,
    approach: str,
    sections: list[str],
    approaches_used: list[str],
    language: str,
    barrier_ids: list[str],
    focus_ids: list[str],
    bank: dict[str, str],
) -> CallInput:
    """`bank`: follow-up id -> the question in English (so the model can choose by meaning)."""
    trusted: dict[str, Any] = {
        "language": language,
        "answer": answer,
        "error": error,
        "approach": approach,
        "sections": sections,
        "approaches_used": approaches_used,
        "barrier_ids": barrier_ids,
        "focus_ids": focus_ids,
        "bank": bank,
    }
    return CallInput(trusted=trusted, untrusted={"teacher_note": masked_note})


def review_note(*, context: CallContext | None = None, **facts: Any) -> ReviewRun:
    base = context or CallContext()
    empty = FeedbackReview(confidence=0.0)
    ctx = replace(base, fallback=lambda: empty)
    run = run_call(CALL_ID, make_input(**facts), context=ctx)
    out = run.output
    assert isinstance(out, FeedbackReview)
    return ReviewRun(out, run.fallback_used is not None, run)
