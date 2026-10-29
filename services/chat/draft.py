"""From a masked question to a checked draft, or to a clear reason there is none.

    approved sources for the cohort's error and language
      -> call 13 (every quote verbatim, sums, personal data, class numbers, Form items, scores)
      -> gates 1, 1b and call 7 (reading level, tone, fit)
      -> a draft with the sources it cited, or why not.

A draft that fails any check is dropped (its text is not kept, so no mentor is nudged to send
it); the reason codes are kept for the coach. Nothing here sends anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from ai.calls.c13_chat_reply import SourceText, draft_reply
from ai.client import CallContext, CallResult
from ai.guard.gates import ContentType, GateInput, run_gates
from ai.schemas import ChatReply
from services.chat import retrieve


@dataclass
class DraftOutcome:
    status: str  # drafted | no_answer | held | none
    text: str | None = None
    sources: list[dict[str, str]] = field(default_factory=list)
    checker: dict[str, Any] = field(default_factory=dict)
    held_codes: list[str] = field(default_factory=list)
    no_answer_reason: str | None = None
    model: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    ai_call_id: int | None = None
    runs: list[CallResult] = field(default_factory=list)


def make_draft(
    db: Session,
    *,
    error: str,
    language: str,
    masked_question: str,
    context: CallContext | None = None,
) -> DraftOutcome:
    sources = retrieve.rank(retrieve.approved_sources(db, error, language), masked_question)
    if not sources:
        return DraftOutcome("no_answer", no_answer_reason="no approved material for this error yet")
    offered = [SourceText(s.id, s.title, s.text) for s in sources]
    run = draft_reply(masked_question, language, error, offered, context=context)
    out = DraftOutcome(
        "none",
        model=run.model,
        tokens_in=run.usage.input_tokens,
        tokens_out=run.usage.output_tokens,
        ai_call_id=run.audit_id,
        runs=[run],
    )
    reply = run.output
    if reply is None:
        out.status = "held"
        out.held_codes = sorted({c for r in run.results for c in r.codes}) or ["no_valid_reply"]
        return out
    assert isinstance(reply, ChatReply)
    if not (reply.answer or "").strip():
        out.status, out.no_answer_reason = "no_answer", reply.no_answer_reason
        return out
    answer = reply.answer or ""
    gate = run_gates(
        GateInput(
            text=answer,
            content_type=ContentType.CHAT_REPLY,
            language=language,
            target_error=error,
            chat_mode=True,
            source_audit_id=run.audit_id,
        ),
        context=context,
    )
    if gate.checker is not None:
        out.runs.append(gate.checker.result)
    out.checker = {
        "passed": gate.passed_automatic,
        "stage_failed": gate.stage_failed,
        "failed_items": list(gate.verdict.failed_items) if gate.verdict else [],
        "explanation": gate.explanation,
    }
    if not gate.passed_automatic:
        out.status = "held"
        codes = [c for r in gate.results for c in r.codes]
        out.held_codes = codes or (out.checker["failed_items"] or ["checker"])
        return out
    by_id = {s.id: s for s in sources}
    out.sources = [
        {"id": c.source_id, "kind": by_id[c.source_id].kind, "title": by_id[c.source_id].title,
         "quote": c.quote}
        for c in reply.citations
    ]  # fmt: skip
    out.status, out.text = "drafted", answer
    return out
