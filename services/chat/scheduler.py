"""The auto-send gates: the one narrow exception to "a person approves what a teacher is sent".

When a question's due time passes with nobody having answered, the AI's draft may go to the
teacher on its own, labelled as AI-generated, only if EVERY one of these holds:

1. no person has replied (the question is still waiting, and not escalated);
2. auto-send is switched on for the cohort (off until the coach turns it on);
3. the question is a teaching question (content_question): never child-specific, discipline,
   safety, off-topic or unclear;
4. the draft exists and cites approved sources, and each quote is still in the approved text now;
5. call 7 passed it (and every code check, which a draft needs to exist at all);
6. the teacher has not already had the daily limit of AI replies.

If any gate fails the question keeps waiting for a person and the coach is alerted once. The sweep
is idempotent: the question is claimed with a single compare-and-set on its status, so two sweeps
(or a sweep and a mentor's reply) can never both send, and a second sweep finds nothing to do.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ai.validators.quotes import quote_in_transcript
from services.api.cohorts import lifecycle
from services.api.db import AiReplyDraft, ChatMessage, CohortSpace
from services.chat import config, retrieve


@dataclass
class TickResult:
    sent: list[str] = field(default_factory=list)  # ids of the AI answers just sent
    blocked: dict[str, str] = field(default_factory=dict)  # question id -> why it keeps waiting
    alerted: int = 0  # new alerts to the coach


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def blocker(db: Session, q: ChatMessage, d: AiReplyDraft | None, now: datetime) -> str | None:
    """The first gate this question fails, or None if the AI may send its draft."""
    cfg = config.effective(db, q.cohort_id)
    if q.status != "ai_draft_ready" or q.escalated or q.flag:
        return "needs_person"
    if not cfg.auto_send:
        return "auto_send_off"
    if q.question_class != "content_question":
        return "needs_person"
    if d is None or d.status != "drafted" or not d.draft_text:
        return "no_draft"
    if not d.checker_result.get("passed"):
        return "checker"
    if not d.sources:
        return "no_sources"
    cohort = db.get(CohortSpace, q.cohort_id)
    if cohort is None:
        return "no_cohort"
    now_text = {s.id: s.text for s in retrieve.approved_sources(db, cohort.error, q.language)}
    for src in d.sources:
        text = now_text.get(src.get("id", ""))
        if text is None or not quote_in_transcript(src.get("quote", ""), text):
            return "sources_changed"
    start = now - config.DAILY_WINDOW
    sent_today = db.execute(
        select(func.count()).select_from(ChatMessage).where(
            ChatMessage.thread_id == q.thread_id,
            ChatMessage.author_role == "ai",
            ChatMessage.kind == "answer",
            ChatMessage.created_at >= start,
        )
    ).scalar_one()  # fmt: skip
    if sent_today >= config.DAILY_AI_REPLY_LIMIT:
        return "daily_limit"
    return None


def _alert(db: Session, q: ChatMessage, reason: str, now: datetime, result: TickResult) -> None:
    if q.alert_reason is None:
        q.alert_reason, q.alerted_at = reason, now
        lifecycle.audit(db, q.cohort_id, "system", "scheduler", "chat_overdue", reason=reason)
        result.alerted += 1


def tick(
    db: Session, *, now: datetime | None = None, cohort_ids: list[str] | None = None
) -> TickResult:
    """Send what is due and allowed; alert the coach about what is due and not allowed."""
    now = now or datetime.now(UTC)
    result = TickResult()
    query = select(ChatMessage).where(
        ChatMessage.kind == "question",
        ChatMessage.status == "ai_draft_ready",
        ChatMessage.ai_due_at.is_not(None),
    )
    if cohort_ids is not None:
        query = query.where(ChatMessage.cohort_id.in_(cohort_ids))
    for q in list(db.execute(query.order_by(ChatMessage.ai_due_at)).scalars()):
        if _aware(q.ai_due_at) > now:  # type: ignore[arg-type]
            continue
        d = db.execute(
            select(AiReplyDraft).where(AiReplyDraft.message_id == q.id)
        ).scalar_one_or_none()
        why = blocker(db, q, d, now)
        if why is not None:
            result.blocked[q.id] = why
            _alert(db, q, why, now, result)
            continue
        assert d is not None
        claimed = db.execute(
            update(ChatMessage)
            .where(ChatMessage.id == q.id, ChatMessage.status == "ai_draft_ready")
            .values(status="ai_sent")
        )
        if claimed.rowcount != 1:  # type: ignore[attr-defined]
            db.rollback()  # a person (or another sweep) got there first
            continue
        answer = ChatMessage(
            id=secrets.token_hex(8), thread_id=q.thread_id, cohort_id=q.cohort_id, reply_to=q.id,
            kind="answer", author_role="ai", author_label="AI", body=d.draft_text,
            language=q.language, status="ai_sent", ai_assisted=True, created_at=now,
        )  # fmt: skip
        db.add(answer)
        d.status, d.decided_by, d.decided_at, d.reply_message_id = (
            "auto_sent",
            "system",
            now,
            answer.id,
        )
        lifecycle.audit(db, q.cohort_id, "system", "scheduler", "chat_auto_sent")
        db.commit()
        result.sent.append(answer.id)
    db.commit()
    return result


def summary(result: TickResult) -> dict[str, Any]:
    return {"sent": len(result.sent), "waiting": len(result.blocked), "alerted": result.alerted}
