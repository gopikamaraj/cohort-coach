# ruff: noqa: E501
"""The gated cohort chat: who may post, what is masked, when the AI answers, who may correct.

Code decides all of it; the AI only words an answer (call 13, from approved sources). One thread per
cohort, made of the existing `thread_posts` plus `chat_post_meta`.

Gates
1. Membership: a teacher must have joined; a mentor or coach must be assigned; nobody else posts.
2. Input: trim, 500 characters, a rate limit, links stripped, names / roll numbers / class codes /
   phone numbers / emails masked, and a post that still looks like an identifier is blocked.
3. Role: teachers ask, reply and share tips; mentors and coaches also reply and resolve; only the
   coach corrects an AI answer, hides, pins and sets the timeout.
4. AI output: at least one approved source, the checker passed (inside `draft.make_draft`), no
   personal data, at most about 120 words; otherwise the AI says it found no approved source.

The timer belongs to the server. A question gets `ai_due_at = created + timeout` when it is stored.
A reply from a role in CHAT_AI_CANCELLED_BY (default mentor, coach) cancels it; a peer's does not.
`tick` answers what is due and is safe to run twice (the question is claimed with one compare and
set); it runs from a poller and again whenever anyone loads the thread. Every gate decision is
audited with codes and ids, never text.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ai import config as ai_config
from ai.client import CallContext
from ai.validators.mask import mask_personal
from ai.validators.thread import check_personal, check_thread_post
from services.api.cohorts import lifecycle, thread
from services.api.db import ClassCohort, CohortMember, CohortSpace, ThreadPost
from services.chat import draft as chat_draft
from services.cohort_chat.models import ChatTimeout, PostMeta

MAX_CHARS = 500
MAX_AI_WORDS = 120
MIN_TIMEOUT, MAX_TIMEOUT = 5, 86400
DEFAULT_TIMEOUT = 1800  # production: 30 minutes until the team decides otherwise
DEMO_TIMEOUT = 5
AI_NAME = "AI assistant"
KINDS = ("question", "reply", "tip")
ROLE_KINDS = {"teacher": KINDS, "mentor": ("reply", "tip"), "coach": ("reply", "tip")}
_LINK = re.compile(r"(?:https?://|www\.)\S+", re.I)


class Refused(Exception):
    """A gate said no. `status` is the HTTP status; `codes` are rule codes, never text."""

    def __init__(self, status: int, message: str, codes: list[str] | None = None) -> None:
        super().__init__(message)
        self.status, self.codes = status, codes or []


@dataclass(frozen=True)
class Actor:
    role: str  # teacher | mentor | coach
    person: str  # a teacher id (kept server-side) or a pseudonymous role id


Drafter = Callable[..., "chat_draft.DraftOutcome"]


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def _now() -> datetime:
    return datetime.now(UTC)


def _cancelled_by() -> set[str]:
    raw = os.environ.get("CHAT_AI_CANCELLED_BY", "mentor,coach")
    return {r.strip() for r in raw.split(",") if r.strip()}


def _rate_limit() -> int:
    return int(os.environ.get("CHAT_RATE_PER_MINUTE", "10"))


# ---- the timeout -----------------------------------------------------------------------------


def _demo_mode() -> bool:
    from services.api.roles import judge_session

    return judge_session()


def timeout_seconds(db: Session, cohort_id: str) -> tuple[int, str]:
    """(seconds, where it came from): the coach's own for this cohort, CHAT_AI_TIMEOUT_SECONDS, the
    demo value (5) in demo mode, else the production default."""
    row = db.get(ChatTimeout, cohort_id)
    if row is not None:
        return row.seconds, "cohort"
    env = os.environ.get("CHAT_AI_TIMEOUT_SECONDS")
    if env:
        return max(MIN_TIMEOUT, min(MAX_TIMEOUT, int(env))), "env"
    if _demo_mode():
        return DEMO_TIMEOUT, "demo"
    return DEFAULT_TIMEOUT, "default"


def set_timeout(db: Session, cohort_id: str, actor: Actor, seconds: object) -> int:
    if actor.role != "coach":
        raise Refused(403, "Only the coach can change the timeout.", ["role"])
    try:
        lifecycle.require_assigned(lifecycle.get(db, cohort_id), "coach", actor.person)
    except lifecycle.NotAllowed as exc:
        raise Refused(403, str(exc), ["not_assigned"]) from exc
    if isinstance(seconds, bool) or not isinstance(seconds, int):
        raise Refused(422, "The timeout must be a whole number of seconds.", ["timeout_type"])
    if not MIN_TIMEOUT <= seconds <= MAX_TIMEOUT:
        raise Refused(422, f"The timeout must be from {MIN_TIMEOUT} to {MAX_TIMEOUT} seconds.", ["timeout_range"])
    row = db.get(ChatTimeout, cohort_id)
    if row is None:
        db.add(ChatTimeout(cohort_id=cohort_id, seconds=seconds, set_by=actor.person))
    else:
        row.seconds, row.set_by, row.set_at = seconds, actor.person, _now()
    lifecycle.audit(db, cohort_id, "coach", actor.person, "chat_timeout", seconds=seconds)
    db.commit()
    return seconds


# ---- gates -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Gated:
    text: str
    hidden: list[str]  # kinds masking or link removal took out


def input_gate(text: str, language: str) -> Gated:
    """Trim, limit, strip links, mask personal data; block what still looks like an identifier."""
    text = (text or "").strip()
    if not text:
        raise Refused(422, "Write something first.", ["empty"])
    if len(text) > MAX_CHARS:
        raise Refused(422, f"At most {MAX_CHARS} characters.", ["too_long"])
    hidden: list[str] = []
    if _LINK.search(text):
        text, hidden = _LINK.sub("", text).strip(), ["link"]
    masked = mask_personal(text)
    hidden += list(masked.kinds)
    text = " ".join(masked.text.split())
    if not text:
        raise Refused(422, "Nothing is left after hiding the details.", ["empty"])
    try:
        problems = check_thread_post(text, language)
    except Exception as exc:  # the check could not run: block, never pass
        raise Refused(503, "The check could not run. Try again.", ["check_unavailable"]) from exc
    if problems:
        raise Refused(422, "Please rewrite it without names or details.", [p.code for p in problems])
    return Gated(text, hidden)


def _members(db: Session, cohort_id: str) -> int:
    return lifecycle.member_count(db, cohort_id)


def _open(cohort: CohortSpace) -> None:
    if cohort.status not in ("active", "closing"):
        raise Refused(409, "This chat is read-only.", ["closed"])


def member_label(db: Session, cohort: CohortSpace, actor: Actor) -> str:
    """Membership gate: the label she posts under, or a refusal."""
    if actor.role == "teacher":
        m = db.get(CohortMember, (cohort.id, actor.person))
        if m is None:
            raise Refused(403, "Join the cohort first.", ["not_member"])
        return m.display_name
    if actor.role in ("mentor", "coach"):
        if not lifecycle.assigned(cohort, actor.role, actor.person):
            raise Refused(403, "That cohort is not assigned to you.", ["not_assigned"])
        return actor.role.capitalize()
    raise Refused(403, "This chat is not open to your role.", ["role"])


def _rate_check(db: Session, cohort_id: str, label: str, now: datetime) -> None:
    n = db.execute(
        select(func.count()).select_from(ThreadPost).where(
            ThreadPost.cohort_id == cohort_id,
            ThreadPost.author_name == label,
            ThreadPost.created_at >= now - timedelta(minutes=1),
        )
    ).scalar_one()  # fmt: skip
    if n >= _rate_limit():
        raise Refused(429, "Too many messages. Wait a moment.", ["rate"])


def _store(db: Session, cohort_id: str, kind_of_author: str, label: str, body: str, teacher_id: str | None = None) -> ThreadPost:
    post = thread._new_post(db, cohort_id, kind_of_author, label, body, teacher_id)
    db.flush()
    return post


def _meta(db: Session, post_id: str) -> PostMeta | None:
    return db.get(PostMeta, post_id)


# ---- posting ---------------------------------------------------------------------------------


def post_message(
    db: Session,
    cohort_id: str,
    actor: Actor,
    kind: str,
    text: str,
    language: str,
    *,
    reply_to: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or _now()
    cohort = lifecycle.get(db, cohort_id)
    label = member_label(db, cohort, actor)
    _open(cohort)
    if kind not in ROLE_KINDS.get(actor.role, ()):
        lifecycle.audit(db, cohort_id, actor.role, label, "chat_refused", why="role", kind=kind)
        db.commit()
        raise Refused(403, "Your role cannot post that.", ["role"])
    _rate_check(db, cohort_id, label, now)
    try:
        gated = input_gate(text, language)
    except Refused as exc:
        lifecycle.audit(db, cohort_id, actor.role, label, "chat_blocked", rules=exc.codes)
        db.commit()
        raise
    target: PostMeta | None = None
    if kind == "reply":
        target = _meta(db, reply_to) if reply_to else None
        if target is None or target.cohort_id != cohort_id or target.kind != "question":
            raise Refused(422, "Reply to a question in this chat.", ["reply_target"])
    post = _store(db, cohort_id, actor.role, label, gated.text, actor.person if actor.role == "teacher" else None)
    meta = PostMeta(post_id=post.id, cohort_id=cohort_id, kind=kind, reply_to=reply_to, language=language, masked=gated.hidden, created_at=now)
    if kind == "question":
        seconds, _src = timeout_seconds(db, cohort_id)
        meta.qstatus, meta.ai_due_at = "waiting", now + timedelta(seconds=seconds)
    db.add(meta)
    if target is not None and actor.role in _cancelled_by() and target.qstatus == "waiting":
        target.qstatus, target.answered_by = "answered_human", "human"
        lifecycle.audit(db, cohort_id, actor.role, label, "chat_ai_cancelled", question=target.post_id)
    lifecycle.audit(db, cohort_id, actor.role, label, "chat_post", kind=kind, masked=gated.hidden)
    db.commit()
    return {"id": post.id, "text": gated.text, "hidden": gated.hidden}


def resolve(db: Session, cohort_id: str, actor: Actor, question_id: str) -> None:
    cohort = lifecycle.get(db, cohort_id)
    label = member_label(db, cohort, actor)
    if actor.role not in ("mentor", "coach"):
        raise Refused(403, "Only a mentor or the coach can mark a question resolved.", ["role"])
    q = _meta(db, question_id)
    if q is None or q.cohort_id != cohort_id or q.kind != "question":
        raise Refused(404, "That question does not exist.", ["missing"])
    q.qstatus = "resolved"
    lifecycle.audit(db, cohort_id, actor.role, label, "chat_resolved", question=question_id)
    db.commit()


def correct_ai(db: Session, cohort_id: str, actor: Actor, ai_post_id: str, text: str, language: str, now: datetime | None = None) -> dict[str, Any]:
    """Only the coach. A new `correction` post points at the AI answer, which gets a badge. Nothing is deleted."""
    cohort = lifecycle.get(db, cohort_id)
    label = member_label(db, cohort, actor)
    if actor.role != "coach":
        lifecycle.audit(db, cohort_id, actor.role, label, "chat_refused", why="role", kind="correction")
        db.commit()
        raise Refused(403, "Only the coach can correct an AI answer.", ["role"])
    ai = _meta(db, ai_post_id)
    if ai is None or ai.cohort_id != cohort_id or ai.kind != "ai_reply":
        raise Refused(404, "That is not an AI answer in this chat.", ["missing"])
    gated = input_gate(text, language)
    post = _store(db, cohort_id, "coach", label, gated.text)
    db.add(PostMeta(post_id=post.id, cohort_id=cohort_id, kind="correction", reply_to=ai.reply_to, language=language, corrects=ai_post_id, masked=gated.hidden, created_at=now or _now()))
    ai.corrected = True
    q = _meta(db, ai.reply_to) if ai.reply_to else None
    if q is not None:
        q.qstatus = "corrected"
    lifecycle.audit(db, cohort_id, "coach", label, "chat_corrected", ai_post=ai_post_id)
    db.commit()
    return {"id": post.id, "text": gated.text, "hidden": gated.hidden}


def moderate(db: Session, cohort_id: str, actor: Actor, post_id: str, action: str) -> None:
    """Hide, restore, pin, unpin: the coach only, through the existing thread decision."""
    cohort = lifecycle.get(db, cohort_id)
    member_label(db, cohort, actor)
    if actor.role != "coach":
        raise Refused(403, "Only the coach can do that.", ["role"])
    post = db.get(ThreadPost, post_id)
    if post is None or post.cohort_id != cohort_id:
        raise Refused(404, "That message does not exist.", ["missing"])
    try:
        thread.decide(db, post_id, action, actor=actor.person)
    except ValueError as exc:
        raise Refused(422, str(exc), ["bad_action"]) from exc


def report(db: Session, cohort_id: str, actor: Actor, post_id: str) -> None:
    cohort = lifecycle.get(db, cohort_id)
    member_label(db, cohort, actor)
    post = db.get(ThreadPost, post_id)
    if post is None or post.cohort_id != cohort_id:
        raise Refused(404, "That message does not exist.", ["missing"])
    if post.status == "visible":
        post.status = "reported"
        post.decided_at = _now()
        lifecycle.audit(db, cohort_id, actor.role, "member", "post_reported", post=post_id)
        db.commit()


# ---- the AI answer ---------------------------------------------------------------------------


def default_drafter(db: Session, *, error: str, language: str, masked_question: str) -> chat_draft.DraftOutcome:
    return chat_draft.make_draft(db, error=error, language=language, masked_question=masked_question, context=CallContext())


def _source_line(sources: list[dict[str, str]]) -> str:
    titles: list[str] = []
    for s in sources:
        if s["title"] not in titles:
            titles.append(s["title"])
    return "Source: " + ", ".join(titles)


def _words(text: str) -> int:
    return len(text.split())


def tick(db: Session, *, now: datetime | None = None, cohort_id: str | None = None, drafter: Drafter | None = None) -> list[str]:
    """Answer every question whose time is up. Returns the ids of the AI posts made. Safe to run twice."""
    now = now or _now()
    made: list[str] = []
    q = select(PostMeta).where(PostMeta.kind == "question", PostMeta.qstatus == "waiting", PostMeta.ai_due_at.is_not(None))
    if cohort_id is not None:
        q = q.where(PostMeta.cohort_id == cohort_id)
    for meta in list(db.execute(q.order_by(PostMeta.ai_due_at)).scalars()):
        if _aware(meta.ai_due_at) > now:  # type: ignore[arg-type]
            continue
        if ai_config.ai_mode() == "off":
            continue  # the question keeps waiting; the coach inbox says the AI is off
        claimed = db.execute(update(PostMeta).where(PostMeta.post_id == meta.post_id, PostMeta.qstatus == "waiting").values(qstatus="answering"))
        if claimed.rowcount != 1:  # type: ignore[attr-defined]
            db.rollback()
            continue
        db.commit()
        post = _answer(db, meta, now, drafter or default_drafter)
        if post is not None:
            made.append(post)
    return made


def _answer(db: Session, q: PostMeta, now: datetime, drafter: Drafter) -> str | None:
    cohort = db.get(CohortSpace, q.cohort_id)
    question = db.get(ThreadPost, q.post_id)
    db.refresh(q)
    if cohort is None or question is None or not question.body:
        q.qstatus = "waiting"
        db.commit()
        return None
    try:
        out = drafter(db, error=cohort.error, language=q.language, masked_question=question.body)
    except Exception:  # noqa: BLE001 - the AI failing must leave the question waiting for a person
        out = None
    why = _why_not(out)
    if why is not None:
        notice = _store(db, q.cohort_id, "system", "System", NO_SOURCE_NOTICE)
        db.add(PostMeta(post_id=notice.id, cohort_id=q.cohort_id, kind="system", reply_to=q.post_id, language=q.language, created_at=now))
        q.qstatus, q.abstained, q.ai_due_at = "waiting", True, None
        lifecycle.audit(db, q.cohort_id, "system", "scheduler", "chat_ai_abstained", why=why, question=q.post_id)
        db.commit()
        return None
    assert out is not None and out.text is not None
    body = f"{out.text}\n\n{_source_line(out.sources)}"
    post = _store(db, q.cohort_id, "system", AI_NAME, body)
    seconds = max(0, int((now - _aware(q.created_at)).total_seconds()))
    db.add(
        PostMeta(
            post_id=post.id, cohort_id=q.cohort_id, kind="ai_reply", reply_to=q.post_id, language=q.language,
            answered_by="ai", after_seconds=seconds, ai_label="recorded" if ai_config.ai_mode() == "recorded" else "ai",
            sources=[{"id": s["id"], "title": s["title"]} for s in out.sources], ai_call_id=out.ai_call_id, created_at=now,
        )
    )  # fmt: skip
    q.qstatus, q.answered_by = "answered_ai", "ai"
    lifecycle.audit(db, q.cohort_id, "system", "scheduler", "chat_ai_answered", question=q.post_id, after=seconds)
    db.commit()
    return post.id


NO_SOURCE_NOTICE = "I could not find an approved source for that. A mentor or coach will see your question."


def _why_not(out: chat_draft.DraftOutcome | None) -> str | None:
    """The first AI output gate the draft fails, or None."""
    if out is None:
        return "ai_failed"
    if out.status != "drafted" or not out.text:
        return out.status if out.status != "drafted" else "empty"
    if not out.sources:
        return "no_source"
    if not out.checker.get("passed"):
        return "checker"
    if check_personal(out.text):
        return "personal_data"
    if _words(out.text) > MAX_AI_WORDS:
        return "too_long"
    return None


# ---- which cohorts she can chat in -----------------------------------------------------------

CLASS_SPACE = "co-"  # + the class cohort's id: the chat space made for a cohort of one class
DEMO_COACH, DEMO_MENTOR, DEMO_OFFICER = "coach-demo", "mentor-demo", "officer-demo"


def space_for_class_cohort(db: Session, cc: ClassCohort) -> CohortSpace:
    """A cohort of one class has no chat space of its own, so one is made for it (once): active, with the
    demo coach and mentor, simulated like the class. She still joins it with her own tap."""
    space = db.get(CohortSpace, CLASS_SPACE + cc.id)
    if space is not None:
        return space
    space = lifecycle.create(db, error=cc.errors[0], coach_id=DEMO_COACH, mentor_ids=[DEMO_MENTOR], officer_id=DEMO_OFFICER, school_count=1, simulated=cc.simulated, cohort_id=CLASS_SPACE + cc.id)
    lifecycle.transition(db, space.id, "active", role="officer", actor=DEMO_OFFICER)
    return space


def my_cohorts(db: Session, teacher_id: str) -> list[dict[str, Any]]:
    """Every cohort a teacher can chat in: the one made for each of her own classes, any cohort she has
    joined, and the open cohorts she may join. Counts and labels only."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(c: CohortSpace, name: str | None, kind: str) -> None:
        if c.id in seen:
            return
        seen.add(c.id)
        row = lifecycle.summary(db, c)
        row.update(name=name, kind=kind, joined=db.get(CohortMember, (c.id, teacher_id)) is not None)
        out.append(row)

    for cc in db.execute(select(ClassCohort).where(ClassCohort.teacher_id == teacher_id).order_by(ClassCohort.created_at)).scalars():
        add(space_for_class_cohort(db, cc), cc.name, "class")
    mine = select(CohortSpace).join(CohortMember, CohortMember.cohort_id == CohortSpace.id).where(CohortMember.teacher_id == teacher_id)
    for c in db.execute(mine).scalars():
        add(c, None, "cohort")
    for c in db.execute(select(CohortSpace).where(CohortSpace.status.in_(("proposed", "active")))).scalars():
        if not c.id.startswith((CLASS_SPACE + "cc-", "co-run-")):  # another teacher's class chat, or a run's own
            add(c, None, "cohort")
    return out


# ---- views -----------------------------------------------------------------------------------

DEFAULT_PINNED = None  # the screen shows its own translated default note when a coach has pinned none


def _seed_demo(db: Session, cohort: CohortSpace, now: datetime) -> None:
    """A demo cohort never opens empty: one tip and one resolved question, marked Demo."""
    if not cohort.simulated or db.execute(select(func.count()).select_from(PostMeta).where(PostMeta.cohort_id == cohort.id)).scalar_one():
        return
    for kind, label, owner, body, qstatus in (
        ("tip", "Mentor", "mentor", "Tip: before you start, say the number out loud and let each child build it with bundles.", None),
        ("question", "Teacher 1", "teacher", "How do I show borrowing with bundles?", "resolved"),
    ):
        post = _store(db, cohort.id, owner, label, body)
        db.add(PostMeta(post_id=post.id, cohort_id=cohort.id, kind=kind, language="en", qstatus=qstatus, demo=True, created_at=now))
    db.commit()


def _legacy(p: ThreadPost) -> PostMeta:
    return PostMeta(post_id=p.id, cohort_id=p.cohort_id, kind="tip" if p.author_kind in ("teacher", "mentor") else "system", language="en", sources=[], masked=[], corrected=False, abstained=False, demo=False, created_at=p.created_at)


def _message(db: Session, p: ThreadPost, m: PostMeta, moderator: bool) -> dict[str, Any]:
    hidden = p.status in ("hidden", "deleted", "reported") and not moderator
    return {
        "id": p.id,
        "kind": m.kind,
        "author": p.author_name,
        "role": "ai" if m.kind == "ai_reply" else p.author_kind,
        "text": None if hidden else p.body,
        "hidden": p.status != "visible",
        "created_at": _aware(p.created_at).isoformat(),
        "reply_to": m.reply_to,
        "qstatus": m.qstatus,
        "ai_due_at": _aware(m.ai_due_at).isoformat() if m.ai_due_at else None,
        "after_seconds": m.after_seconds,
        "ai_label": m.ai_label,
        "sources": m.sources,
        "corrected": m.corrected,
        "corrects": m.corrects,
        "abstained": m.abstained,
        "demo": m.demo,
        "pinned": p.pinned,
        "masked": m.masked,
    }


def thread_view(db: Session, cohort_id: str, actor: Actor, *, now: datetime | None = None, drafter: Drafter | None = None) -> dict[str, Any]:
    now = now or _now()
    cohort = lifecycle.get(db, cohort_id)
    me = member_label(db, cohort, actor)
    _seed_demo(db, cohort, now)
    tick(db, now=now, cohort_id=cohort_id, drafter=drafter)  # catch up: a restart loses nothing
    moderator = actor.role == "coach"
    rows = db.execute(
        select(ThreadPost, PostMeta).outerjoin(PostMeta, PostMeta.post_id == ThreadPost.id).where(ThreadPost.cohort_id == cohort_id).order_by(ThreadPost.created_at)
    ).all()
    # a post made before the gated chat (the older thread) has no meta row: it shows as a tip, or a notice from staff
    msgs = [_message(db, p, m or _legacy(p), moderator) for p, m in rows if moderator or p.status != "deleted"]
    teachers = _members(db, cohort_id)
    seconds, source = timeout_seconds(db, cohort_id)
    pinned = next((x for x in msgs if x["pinned"] and not x["hidden"]), None)
    return {
        "cohort": {"id": cohort.id, "error": cohort.error, "status": cohort.status, "teachers": teachers, "mentors": len(cohort.mentor_ids or []), "coaches": 1 if cohort.coach_id else 0},
        "me": me,
        "role": actor.role,
        "timeout": {"seconds": seconds, "source": source},
        "ai_mode": ai_config.ai_mode(),
        "state": "open" if cohort.status in ("active", "closing") else "read_only",
        "pinned": pinned,
        "messages": msgs,
        "server_time": now.isoformat(),
    }


def inbox(db: Session, actor: Actor, *, now: datetime | None = None) -> dict[str, Any]:
    """Open questions in the cohorts a mentor or coach is assigned to, waiting first."""
    now = now or _now()
    if actor.role not in ("mentor", "coach"):
        raise Refused(403, "The inbox is for mentors and coaches.", ["role"])
    cohorts = [c for c in db.execute(select(CohortSpace)).scalars() if lifecycle.assigned(c, actor.role, actor.person)]
    items: list[dict[str, Any]] = []
    for c in cohorts:
        for p, m in db.execute(
            select(ThreadPost, PostMeta).join(PostMeta, PostMeta.post_id == ThreadPost.id).where(PostMeta.cohort_id == c.id, PostMeta.kind == "question", PostMeta.qstatus.in_(("waiting", "answering", "answered_ai")))
        ).all():
            due = _aware(m.ai_due_at) if m.ai_due_at else None
            items.append({
                "id": p.id, "cohort_id": c.id, "error": c.error, "author": p.author_name, "text": p.body, "qstatus": m.qstatus,
                "abstained": m.abstained, "seconds_left": max(0, int((due - now).total_seconds())) if due else None,
                "created_at": _aware(p.created_at).isoformat(),
            })  # fmt: skip
    items.sort(key=lambda i: (i["qstatus"] != "waiting", not i["abstained"], i["created_at"]))
    return {"items": items, "count": sum(1 for i in items if i["qstatus"] == "waiting"), "ai_mode": ai_config.ai_mode()}
