"""Call 13: a short reply to a teacher's question, from approved sources only.

The model sees the masked question and a short list of approved sentences, each with an id. It must
quote the sentence behind every statement, or return no answer. Code checks every quote word for
word, the length, sums, personal data, class numbers, pilot-test items and scores; if the model
breaks a rule it is told which and tries once more; then nothing is drafted and a person answers.
The call never decides who sees the draft: that is services/chat.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

from pydantic import BaseModel

from ai.client import CallContext, CallInput, CallResult, run_call
from ai.guard.explain import error_name
from ai.schemas import ChatReply
from ai.validators import ValidatorResult, Violation
from ai.validators.arithmetic import check_arithmetic
from ai.validators.check_items import check_items
from ai.validators.length import check_length
from ai.validators.mask import check_masked
from ai.validators.quotes import quote_in_transcript
from ai.validators.scores import check_no_scores
from services.content.slots import literal_class_counts

CALL_ID = 13
MAX_WORDS = 120
MIN_QUOTE_WORDS = 3
_GRADE = ("Grade 3", "grade 3", "Grade-3")


@dataclass(frozen=True)
class SourceText:
    id: str
    title: str
    text: str


def reply_results(reply: ChatReply, sources: Sequence[SourceText]) -> list[ValidatorResult]:
    """Every code check on a reply. All must pass; the empty-answer reply passes by being honest."""
    by_id = {s.id: s for s in sources}
    shape: list[Violation] = []
    citations: list[Violation] = []
    answer = (reply.answer or "").strip()
    reason = (reply.no_answer_reason or "").strip()
    if bool(answer) == bool(reason):
        shape.append(Violation("answer_xor_reason", "give an answer, or no answer and why"))
    if not answer:
        if reply.citations:
            citations.append(Violation("citation_without_answer"))
        return [
            ValidatorResult("shape", tuple(shape)),
            ValidatorResult("citations", tuple(citations)),
        ]
    if not reply.citations:
        citations.append(Violation("no_citation", "an answer must cite an approved source"))
    for c in reply.citations:
        src = by_id.get(c.source_id)
        if src is None:
            citations.append(Violation("citation_unknown_source", "a cited source was not offered"))
        elif len(c.quote.split()) < MIN_QUOTE_WORDS:
            citations.append(Violation("quote_too_short", f"fewer than {MIN_QUOTE_WORDS} words"))
        elif not quote_in_transcript(c.quote, src.text):
            citations.append(Violation("quote_not_verbatim", "a quote is not in its source"))
    plain = answer
    for g in _GRADE:  # "Grade 3" is the class, not a grade given to a teacher
        plain = plain.replace(g, "Class 3")
    return [
        ValidatorResult("shape", tuple(shape)),
        ValidatorResult("citations", tuple(citations)),
        ValidatorResult("length", tuple(check_length(answer, max_words=MAX_WORDS))),
        ValidatorResult("arithmetic", tuple(check_arithmetic(answer))),
        ValidatorResult("personal", tuple(check_masked(answer))),
        ValidatorResult("class_numbers", tuple(literal_class_counts(answer))),
        ValidatorResult("check_items", tuple(check_items(answer))),
        ValidatorResult("scores", tuple(check_no_scores(plain))),
    ]


def draft_reply(
    masked_question: str,
    language: str,
    error: str,
    sources: Sequence[SourceText],
    *,
    context: CallContext | None = None,
) -> CallResult:
    """Run call 13. The result's output is None when the model could not give a reply that passed
    the code checks twice (no fallback text is ever invented)."""
    base = context or CallContext()

    def validate(out: BaseModel) -> list[ValidatorResult]:
        assert isinstance(out, ChatReply)
        return reply_results(out, sources)

    ctx: CallContext = replace(base, validators=validate, fallback=None)
    payload = CallInput(
        trusted={
            "language": language,
            "error": error,
            "error_name": error_name(error, language),
            "sources": [{"id": s.id, "title": s.title, "text": s.text} for s in sources],
        },
        untrusted={"teacher_text": masked_question},
    )
    return run_call(CALL_ID, payload, context=ctx)


Validator = Callable[[BaseModel], list[ValidatorResult]]
