"""Asking, answering and correcting in the cohort Q&A chat.

A teacher's question is masked when it is posted and only the masked text is stored. If she ticked
AI help, the question is classified and (for teaching, child-specific and discipline questions) a
draft is made for her mentor; a safety or welfare word sends it to the coach with no draft and no
model. A mentor or coach sends the draft as it is, edits it, writes her own, discards it,
escalates, or rates it. An answer the AI sent on its own (services/chat/scheduler.py) can be
corrected afterwards: the AI message becomes Corrected and a correction is posted under it.

Everything a screen needs is returned as plain dicts with display names, never a teacher id.
Audit rows (the cohort audit) hold ids, codes and counts, never text.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ai.client import CallContext
from ai.validators.mask import check_masked, mask_personal
from ai.validators.prefilter import check_prefilter
from services.api.cohorts import lifecycle
from services.api.cohorts.thread import NotMember, PostRejected, ThreadClosed
from services.api.db import AiReplyDraft, ChatMessage, ChatThread, CohortMember
from services.chat import classify, config, draft, labels

MAX_QUESTION_CHARS = 500
MAX_ANSWER_CHARS = 1500
EDIT_TAGS = ("wrong_content", "too_long", "not_practical", "wrong_language", "unsafe")
OPEN = ("pending", "ai_draft_ready")


class BadState(ValueError):
    """The message is not in a state that allows this step."""


@dataclass
class Asked:
    message: ChatMessage
    replaced: tuple[str, ...]  # kinds of personal data replaced (codes, never the text)


def _now() -> datetime:
    return datetime.now(UTC)


def _id() -> str:
    return secrets.token_hex(8)


def _thread(db: Session, cohort_id: str, teacher_id: str) -> ChatThread:
    row = db.execute(
        select(ChatThread).where(
            ChatThread.cohort_id == cohort_id, ChatThread.teacher_id == teacher_id
        )
    ).scalar_one_or_none()
    if row is None:
        row = ChatThread(id=_id(), cohort_id=cohort_id, teacher_id=teacher_id)
        db.add(row)
        db.flush()
    return row


def _member(db: Session, cohort_id: str, teacher_id: str) -> CohortMember:
    member = db.get(CohortMember, (cohort_id, teacher_id))
    if member is None:
        raise NotMember("Join the cohort first.")
    return member


def _check_text(text: str, language: str, limit: int) -> None:
    problems = [*check_masked(text), *check_prefilter(text, language, max_chars=limit)]
    if problems:
        raise PostRejected([p.code for p in problems])


def _draft_of(db: Session, message_id: str) -> AiReplyDraft | None:
    return db.execute(
        select(AiReplyDraft).where(AiReplyDraft.message_id == message_id)
    ).scalar_one_or_none()


# ---- the teacher -------------------------------------------------------------------------------


def ask(
    db: Session,
    *,
    cohort_id: str,
    teacher_id: str,
    text: str,
    language: str,
    ai_consent: bool,
    now: datetime | None = None,
    context: CallContext | None = None,
) -> Asked:
    now = now or _now()
    cohort = lifecycle.get(db, cohort_id)
    _member(db, cohort_id, teacher_id)
    if cohort.status != "active":
        raise ThreadClosed("This cohort is not taking questions.")
    text = text.strip()
    if not text or len(text) > MAX_QUESTION_CHARS:
        raise PostRejected(["empty_or_too_long"])
    masked = mask_personal(text)
    _check_text(masked.text, language, MAX_QUESTION_CHARS)
    member = _member(db, cohort_id, teacher_id)
    thread_row = _thread(db, cohort_id, teacher_id)
    # Never hold a write open across a model call: the call's audit row is written on its own
    # connection, and on SQLite (dev and tests) an open write here would lock it out.
    db.commit()
    cls = classify.classify(masked, language, use_model=ai_consent, context=context)
    safety = cls.label == "safety_or_welfare"
    msg = ChatMessage(
        id=_id(),
        thread_id=thread_row.id,
        cohort_id=cohort_id,
        kind="question",
        author_role="teacher",
        author_label=member.display_name,
        body=masked.text,
        language=language,
        status="pending",
        ai_consent=ai_consent,
        question_class=cls.label,
        flag="safety" if safety else None,
        ai_due_at=None if (safety or not ai_consent) else config.due_at(db, cohort_id, now),
        created_at=now,
    )
    db.add(msg)
    db.commit()  # the question is kept even if drafting fails; and no write is open during it
    made = False
    if ai_consent and cls.label in classify.DRAFTABLE:
        out = draft.make_draft(
            db,
            error=cohort.error,
            language=language,
            masked_question=masked.text,
            context=context,
        )
        db.add(
            AiReplyDraft(
                id=_id(),
                message_id=msg.id,
                draft_text=out.text,
                sources=out.sources,
                question_class=cls.label,
                checker_result=out.checker,
                model=out.model,
                tokens_in=out.tokens_in,
                tokens_out=out.tokens_out,
                status="drafted" if out.status == "drafted" else "discarded",
                decided_by=None if out.status == "drafted" else "system",
                decided_at=None if out.status == "drafted" else now,
                no_reply_reason=(out.no_answer_reason or "")[:60] or None,
                held_codes=out.held_codes,
                ai_call_id=out.ai_call_id,
                created_at=now,
            )
        )
        if out.status == "drafted":
            msg.status, made = "ai_draft_ready", True
    lifecycle.audit(
        db, cohort_id, "teacher", "member", "chat_question",
        cls=cls.label, consent=ai_consent, replaced=list(masked.kinds), drafted=made,
        flagged=safety,
    )  # fmt: skip
    db.commit()
    return Asked(msg, masked.kinds)


def _auto_possible(db: Session, q: ChatMessage, d: AiReplyDraft | None) -> bool:
    if q.status != "ai_draft_ready" or d is None or d.status != "drafted" or q.escalated:
        return False
    return (
        q.question_class == "content_question"
        and bool(d.checker_result.get("passed"))
        and config.effective(db, q.cohort_id).auto_send
    )


def answers_for(db: Session, question_id: str) -> list[ChatMessage]:
    return list(
        db.execute(
            select(ChatMessage)
            .where(ChatMessage.reply_to == question_id)
            .order_by(ChatMessage.created_at, ChatMessage.id)
        ).scalars()
    )


def _answer_view(m: ChatMessage) -> dict[str, Any]:
    return {
        "id": m.id,
        "kind": m.kind,
        "author_label": m.author_label,
        "body": m.body,
        "label": labels.answer_label(m),
        "status": m.status,
        "seen": m.seen,
        "created_at": labels.aware(m.created_at).isoformat(),
    }


def my_questions(db: Session, cohort_id: str, teacher_id: str) -> dict[str, Any]:
    """Her own thread: each question with its answers, labels and what it is waiting for."""
    _member(db, cohort_id, teacher_id)
    thread_row = _thread(db, cohort_id, teacher_id)
    db.commit()
    rows = db.execute(
        select(ChatMessage)
        .where(ChatMessage.thread_id == thread_row.id, ChatMessage.kind == "question")
        .order_by(ChatMessage.created_at)
    ).scalars()
    out = []
    unseen = 0
    for q in rows:
        answers = answers_for(db, q.id)
        unseen += sum(1 for a in answers if not a.seen)
        out.append(
            {
                "id": q.id,
                "body": q.body,
                "status": q.status,
                "ai_consent": q.ai_consent,
                "created_at": labels.aware(q.created_at).isoformat(),
                "waiting": labels.waiting(
                    q, ai_may_answer=_auto_possible(db, q, _draft_of(db, q.id))
                ),
                "answers": [_answer_view(a) for a in answers],
            }
        )
    return {"questions": out, "unseen": unseen}


def mark_seen(db: Session, cohort_id: str, teacher_id: str) -> int:
    thread_row = _thread(db, cohort_id, teacher_id)
    n = db.execute(
        update(ChatMessage)
        .where(ChatMessage.thread_id == thread_row.id, ChatMessage.kind != "question",
               ChatMessage.seen.is_(False))
        .values(seen=True)
    ).rowcount  # fmt: skip
    db.commit()
    return int(n or 0)


# ---- the mentor and the coach -----------------------------------------------------------------


def _visible_cohorts(db: Session, role: str, person: str) -> list[str]:
    from services.api.db import CohortSpace

    return [
        c.id
        for c in db.execute(select(CohortSpace)).scalars()
        if role in ("mentor", "coach") and lifecycle.assigned(c, role, person)
    ]


def _question(db: Session, message_id: str, role: str, person: str) -> ChatMessage:
    q = db.get(ChatMessage, message_id)
    if q is None or q.kind != "question":
        raise BadState("That question does not exist.")
    cohort = lifecycle.get(db, q.cohort_id)
    lifecycle.require_assigned(cohort, role, person)
    if q.flag == "safety" and role != "coach":
        raise lifecycle.NotAllowed("This question goes to the coach.")
    return q


def _display_name(db: Session, q: ChatMessage) -> str:
    return q.author_label


def _draft_view(d: AiReplyDraft | None) -> dict[str, Any] | None:
    if d is None or d.status != "drafted" or not d.draft_text:
        return None
    return {
        "text": d.draft_text,
        "sources": d.sources,
        "checker_passed": bool(d.checker_result.get("passed")),
        "quality": d.quality,
    }


def inbox(db: Session, *, role: str, person: str, now: datetime | None = None) -> dict[str, Any]:
    """What a mentor or coach has to do: open questions by due time, auto-sent answers nobody has
    looked at yet, and (coach only) what needs attention."""
    now = now or _now()
    cohorts = _visible_cohorts(db, role, person)
    questions = list(
        db.execute(
            select(ChatMessage).where(
                ChatMessage.kind == "question",
                ChatMessage.cohort_id.in_(cohorts),
                ChatMessage.status.in_(OPEN),
            )
        ).scalars()
    )
    if role != "coach":
        questions = [q for q in questions if q.flag != "safety"]

    def due_key(q: ChatMessage) -> tuple[int, datetime]:
        return (0, labels.aware(q.ai_due_at)) if q.ai_due_at else (1, labels.aware(q.created_at))

    questions.sort(key=due_key)
    pending = []
    for q in questions:
        d = _draft_of(db, q.id)
        pending.append(
            {
                "id": q.id,
                "cohort_id": q.cohort_id,
                "from": _display_name(db, q),
                "body": q.body,
                "language": q.language,
                "question_class": q.question_class,
                "flag": q.flag,
                "escalated": q.escalated,
                "alert_reason": q.alert_reason,
                "ai_consent": q.ai_consent,
                "created_at": labels.aware(q.created_at).isoformat(),
                "due_at": labels.aware(q.ai_due_at).isoformat() if q.ai_due_at else None,
                "seconds_left": int((labels.aware(q.ai_due_at) - now).total_seconds())
                if q.ai_due_at else None,
                "ai_may_answer": _auto_possible(db, q, d),
                "draft": _draft_view(d),
                "draft_held": d.held_codes if d and d.status == "discarded" else [],
            }
        )  # fmt: skip
    review = []
    for a in db.execute(
        select(ChatMessage).where(
            ChatMessage.kind == "answer",
            ChatMessage.author_role == "ai",
            ChatMessage.status == "ai_sent",
            ChatMessage.reviewed_at.is_(None),
            ChatMessage.cohort_id.in_(cohorts),
        ).order_by(ChatMessage.created_at)
    ).scalars():  # fmt: skip
        q = db.get(ChatMessage, a.reply_to) if a.reply_to else None
        d = _draft_of(db, a.reply_to) if a.reply_to else None
        review.append(
            {
                "id": a.id,
                "question_id": a.reply_to,
                "from": q.author_label if q else "",
                "question": q.body if q else None,
                "answer": a.body,
                "sources": d.sources if d else [],
                "sent_at": labels.aware(a.created_at).isoformat(),
            }
        )
    out: dict[str, Any] = {"pending": pending, "needs_review": review}
    if role == "coach":
        out["needs_attention"] = [
            p for p in pending if p["flag"] or p["escalated"] or p["alert_reason"]
        ]
    return out


def _finish(q: ChatMessage, db: Session) -> None:
    """Claim the question: only one answer can ever be sent for it (a second try is refused)."""
    claimed = db.execute(
        update(ChatMessage)
        .where(ChatMessage.id == q.id, ChatMessage.status.in_(OPEN))
        .values(status="answered_by_human")
    )
    if claimed.rowcount != 1:  # type: ignore[attr-defined]
        db.rollback()
        raise BadState("This question has already been answered.")


def reply(
    db: Session,
    message_id: str,
    *,
    role: str,
    person: str,
    mode: str,
    text: str | None = None,
    tags: tuple[str, ...] = (),
    now: datetime | None = None,
) -> ChatMessage:
    """Send an answer: the draft as it is ("as_is"), the draft changed ("edit", with at least one
    reason tag), or her own words ("own")."""
    now = now or _now()
    if mode not in ("as_is", "edit", "own"):
        raise ValueError("mode must be as_is, edit or own")
    q = _question(db, message_id, role, person)
    if q.status not in OPEN:
        raise BadState("This question has already been answered.")
    d = _draft_of(db, q.id)
    live = d if d is not None and d.status == "drafted" and d.draft_text else None
    if mode in ("as_is", "edit") and live is None:
        raise BadState("There is no draft to send or change.")
    if mode == "as_is":
        assert live is not None
        body = live.draft_text or ""
    else:
        body = (text or "").strip()
        if not body or len(body) > MAX_ANSWER_CHARS:
            raise PostRejected(["empty_or_too_long"])
        _check_text(body, q.language, MAX_ANSWER_CHARS)
    if mode == "edit":
        bad = [t for t in tags if t not in EDIT_TAGS]
        if bad or not tags:
            raise ValueError("Give at least one reason from: " + ", ".join(EDIT_TAGS))
    _finish(q, db)
    answer = ChatMessage(
        id=_id(), thread_id=q.thread_id, cohort_id=q.cohort_id, reply_to=q.id, kind="answer",
        author_role=role, author_label=role.capitalize(), body=body, language=q.language,
        status="sent", ai_assisted=mode != "own" and live is not None, created_at=now,
    )  # fmt: skip
    db.add(answer)
    if d is not None and live is not None:
        d.decided_by, d.decided_at, d.reply_message_id = person, now, answer.id
        d.status = {"as_is": "sent_as_is", "edit": "edited_and_sent", "own": "discarded"}[mode]
        if mode == "edit":
            d.edited_text, d.edit_reason_tags = body, list(tags)
    lifecycle.audit(
        db, q.cohort_id, role, person, "chat_reply",
        mode=mode, tags=list(tags), ai_assisted=answer.ai_assisted,
    )  # fmt: skip
    db.commit()
    return answer


def discard_draft(db: Session, message_id: str, *, role: str, person: str) -> None:
    q = _question(db, message_id, role, person)
    d = _draft_of(db, q.id)
    if q.status not in OPEN or d is None or d.status != "drafted":
        raise BadState("There is no draft to discard.")
    d.status, d.decided_by, d.decided_at = "discarded", person, _now()
    q.status = "pending"  # no draft left: nothing can go out on its own
    lifecycle.audit(db, q.cohort_id, role, person, "chat_draft_discarded")
    db.commit()


def escalate(db: Session, message_id: str, *, role: str, person: str) -> None:
    q = _question(db, message_id, role, person)
    if q.status not in OPEN:
        raise BadState("This question has already been answered.")
    q.escalated = True
    q.alert_reason = q.alert_reason or "escalated"
    q.alerted_at = q.alerted_at or _now()
    lifecycle.audit(db, q.cohort_id, role, person, "chat_escalated")
    db.commit()


def rate_draft(db: Session, message_id: str, quality: str, *, role: str, person: str) -> None:
    if quality not in ("good", "not_good"):
        raise ValueError("quality must be good or not_good")
    q = _question(db, message_id, role, person)
    d = _draft_of(db, q.id)
    if d is None:
        raise BadState("There is no draft to rate.")
    d.quality = quality
    lifecycle.audit(db, q.cohort_id, role, person, "chat_draft_rated", quality=quality)
    db.commit()


def mark_reviewed(db: Session, answer_id: str, *, role: str, person: str) -> None:
    """A person has looked at an answer the AI sent and it is fine."""
    a = db.get(ChatMessage, answer_id)
    if a is None or a.author_role != "ai" or a.status != "ai_sent":
        raise BadState("That is not an AI answer waiting to be looked at.")
    lifecycle.require_assigned(lifecycle.get(db, a.cohort_id), role, person)
    a.reviewed_at = _now()
    lifecycle.audit(db, a.cohort_id, role, person, "chat_ai_answer_reviewed")
    db.commit()


def correct(
    db: Session,
    answer_id: str,
    *,
    role: str,
    person: str,
    text: str,
    tags: tuple[str, ...],
    now: datetime | None = None,
) -> ChatMessage:
    """Correct an answer the AI sent: the AI message becomes Corrected and "Correction from your
    mentor" is posted under it. The teacher gets an in-app notice (an unseen message)."""
    now = now or _now()
    a = db.get(ChatMessage, answer_id)
    if a is None or a.author_role != "ai" or a.status != "ai_sent":
        raise BadState("Only an answer the AI sent can be corrected.")
    lifecycle.require_assigned(lifecycle.get(db, a.cohort_id), role, person)
    body = text.strip()
    if not body or len(body) > MAX_ANSWER_CHARS:
        raise PostRejected(["empty_or_too_long"])
    _check_text(body, a.language, MAX_ANSWER_CHARS)
    bad = [t for t in tags if t not in EDIT_TAGS]
    if bad or not tags:
        raise ValueError("Give at least one reason from: " + ", ".join(EDIT_TAGS))
    q = db.get(ChatMessage, a.reply_to) if a.reply_to else None
    fixed = db.execute(
        update(ChatMessage).where(ChatMessage.id == a.id, ChatMessage.status == "ai_sent")
        .values(status="corrected", reviewed_at=now)
    )  # fmt: skip
    if fixed.rowcount != 1:  # type: ignore[attr-defined]
        db.rollback()
        raise BadState("This answer has already been corrected.")
    note = ChatMessage(
        id=_id(), thread_id=a.thread_id, cohort_id=a.cohort_id, reply_to=a.reply_to,
        kind="correction", author_role=role, author_label=role.capitalize(), body=body,
        language=a.language, status="sent", created_at=now,
    )  # fmt: skip
    db.add(note)
    if q is not None:
        q.status = "corrected"
        d = _draft_of(db, q.id)
        if d is not None:
            d.edited_text, d.edit_reason_tags = body, list(tags)
    lifecycle.audit(
        db, a.cohort_id, role, person, "chat_ai_answer_corrected", tags=list(tags)
    )  # fmt: skip
    db.commit()
    return note
