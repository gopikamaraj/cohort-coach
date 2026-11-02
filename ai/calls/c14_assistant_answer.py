"""Call 14: the role-scoped assistant's answer, from the passages that role may read.

The model sees the question as data and a short list of passages, each with an id. It writes at
most 120 words, quotes the passage behind each statement, and names the rubric rows it rests on, or
returns no answer. Code checks every quote word for word, the rows, length, personal data, scores,
pressure words and claims of an action; if the model breaks a rule it is told which and tries once
more; then there is no model answer and the caller falls back to an extract. Which role, which
passages and which status labels is never the model's decision: that is services/assistant.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from pydantic import BaseModel

from ai.client import CallContext, CallInput, CallResult, run_call
from ai.schemas import AssistantAnswer
from ai.validators import ValidatorResult, Violation
from ai.validators.length import check_length
from ai.validators.mask import check_masked
from ai.validators.quotes import quote_in_transcript
from ai.validators.scores import check_no_scores
from services.assistant.tone import ROLES_WITH_TONE_RULES, check_pressure, check_read_only
from services.content.slots import literal_class_counts

CALL_ID = 14
MAX_WORDS = 120
MIN_QUOTE_WORDS = 3
MAX_FOLLOW_UP_WORDS = 14


@dataclass(frozen=True)
class Passage:
    id: str  # S1, S2 ... for a document passage; R:<id> for a rubric row
    title: str
    text: str


def answer_results(
    reply: AssistantAnswer, passages: Sequence[Passage], role: str
) -> list[ValidatorResult]:
    """Every code check on a reply. All must pass; the empty answer passes by being honest."""
    by_id = {p.id: p for p in passages}
    offered_rows = {p.id[2:] for p in passages if p.id.startswith("R:")}
    shape: list[Violation] = []
    citations: list[Violation] = []
    rows: list[Violation] = []
    answer = (reply.answer or "").strip()
    reason = (reply.no_answer_reason or "").strip()
    if bool(answer) == bool(reason):
        shape.append(Violation("answer_xor_reason", "give an answer, or no answer and why"))
    follow: list[Violation] = []
    for f in reply.follow_ups:
        if len(f.split()) > MAX_FOLLOW_UP_WORDS or not f.strip().endswith("?"):
            follow.append(
                Violation(
                    "follow_up_shape", f"a short question of at most {MAX_FOLLOW_UP_WORDS} words"
                )
            )
        follow += check_masked(f)
    if not answer:
        if reply.citations or reply.rubric_rows:
            citations.append(Violation("citation_without_answer"))
        return [
            ValidatorResult("shape", tuple(shape)),
            ValidatorResult("citations", tuple(citations)),
            ValidatorResult("follow_ups", tuple(follow)),
        ]
    if not reply.citations:
        citations.append(Violation("no_citation", "an answer must cite a passage"))
    for c in reply.citations:
        src = by_id.get(c.source_id)
        if src is None:
            citations.append(
                Violation("citation_unknown_source", "a cited passage was not offered")
            )
        elif len(c.quote.split()) < MIN_QUOTE_WORDS:
            citations.append(Violation("quote_too_short", f"fewer than {MIN_QUOTE_WORDS} words"))
        elif not quote_in_transcript(c.quote, src.text):
            citations.append(Violation("quote_not_verbatim", "a quote is not in its passage"))
    for r in reply.rubric_rows:
        if r not in offered_rows:
            rows.append(Violation("unknown_row", "a rubric row that was not offered"))
    if role == "judge" and offered_rows and not reply.rubric_rows:
        rows.append(Violation("no_row", "a judge answer rests on at least one rubric row"))
    results = [
        ValidatorResult("shape", tuple(shape)),
        ValidatorResult("citations", tuple(citations)),
        ValidatorResult("rubric_rows", tuple(rows)),
        ValidatorResult("length", tuple(check_length(answer, max_words=MAX_WORDS))),
        ValidatorResult("personal", tuple(check_masked(answer))),
        ValidatorResult("read_only", tuple(check_read_only(answer))),
        ValidatorResult("follow_ups", tuple(follow)),
    ]
    if (
        role != "judge"
    ):  # the demo's own simulated counts may be quoted to a judge, labelled simulated
        results.append(ValidatorResult("class_numbers", tuple(literal_class_counts(answer))))
    if role in ROLES_WITH_TONE_RULES:
        plain = answer.replace("Grade 3", "Class 3").replace("grade 3", "Class 3")
        results.append(ValidatorResult("scores", tuple(check_no_scores(plain))))
        results.append(ValidatorResult("pressure", tuple(check_pressure(answer))))
    return results


def answer_question(
    question: str,
    role: str,
    language: str,
    passages: Sequence[Passage],
    *,
    context: CallContext | None = None,
) -> CallResult:
    """Run call 14. The result's output is None when the model could not give an answer that passed
    the code checks twice (no fallback text is invented here: the caller extracts or abstains)."""
    base = context or CallContext()

    def validate(out: BaseModel) -> list[ValidatorResult]:
        assert isinstance(out, AssistantAnswer)
        return answer_results(out, passages, role)

    ctx: CallContext = replace(base, validators=validate, fallback=None)
    # The passages are document text: data, never instructions, so they travel in a tagged block
    # with the question, not in the trusted facts.
    shown = "\n\n".join(f"[{p.id}] {p.title}\n{p.text}" for p in passages)
    payload = CallInput(
        trusted={"role": role, "language": language, "passage_ids": [p.id for p in passages]},
        untrusted={"question": question, "passages": shown},
    )
    return run_call(CALL_ID, payload, context=ctx)
