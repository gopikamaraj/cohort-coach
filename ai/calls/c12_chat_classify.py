"""Call 12: what kind of question did a teacher ask her mentor?

The question arrives already masked (names, roll numbers and phone numbers replaced). The model
only picks one label with a confidence; below the floor, or on any failure, the answer is
"unclear", which means no draft is made and a person answers. The question is data, never an
instruction (the prompt says so and code never acts on its words).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from ai.client import CallContext, CallInput, CallResult, run_call
from ai.schemas import ChatClass

CALL_ID = 12
CONFIDENCE_FLOOR = 0.6


@dataclass(frozen=True)
class ChatClassResult:
    label: str
    confidence: float
    fell_back: bool
    run: CallResult


def classify_with_model(
    masked_question: str, language: str, *, context: CallContext | None = None
) -> ChatClassResult:
    base = context or CallContext()
    unclear = ChatClass(label="unclear", confidence=0.0)
    ctx = replace(base, fallback=lambda: unclear)
    payload = CallInput(
        trusted={"language": language},
        untrusted={"teacher_text": masked_question},
    )
    run = run_call(CALL_ID, payload, context=ctx)
    out = run.output
    assert isinstance(out, ChatClass)
    fell_back = run.fallback_used is not None
    label = out.label if out.confidence >= CONFIDENCE_FLOOR and not fell_back else "unclear"
    return ChatClassResult(label, out.confidence, fell_back, run)
