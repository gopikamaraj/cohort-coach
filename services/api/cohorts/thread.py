"""The cohort thread: pseudonymous, moderated, never sent to a model.

Display names are system labels ("Teacher 7"), unique in the cohort, never typed; "Mentor",
"Coach" and "System" are assigned only to those roles. Every post goes through the posting check
(ai/validators/thread.py); a failed check asks her to rewrite and nothing is stored. A reported
post is held and invisible to others until the coach restores or hides it. Held, hidden and
reported posts lose their body within 7 days (at once if the coach marks a child's identifier);
thread text goes 30 days after the cohort closes and never later than 90 days after the last post
or cancellation. No handle or phone number is ever shown: responses carry a display name only.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.validators.thread import check_thread_post
from services.api.cohorts import lifecycle
from services.api.db import CohortMember, CohortSpace, ThreadPost

HELD_BODY_DAYS = 7
AFTER_CLOSE_DAYS = 30
HARD_LIMIT_DAYS = 90
SYSTEM_NAMES = {"mentor", "coach", "system", "teacher"}  # roles: never given to a member


class ThreadClosed(Exception):
    """The thread is read-only: not active, or fewer than 5 members."""


class NotMember(Exception):
    pass


class PostRejected(Exception):
    """The posting check failed: she is asked to rewrite. Carries the rule codes, never her text."""

    def __init__(self, codes: list[str]) -> None:
        super().__init__(", ".join(codes))
        self.codes = codes


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def join(db: Session, cohort_id: str, teacher_id: str) -> CohortMember:
    """Join with a system label. Joining is a separate consent (the caller asked for it)."""
    existing = db.get(CohortMember, (cohort_id, teacher_id))
    if existing is not None:
        return existing
    taken = {
        n
        for (n,) in db.execute(
            select(CohortMember.display_name).where(CohortMember.cohort_id == cohort_id)
        )
    }
    number = len(taken) + 1
    while f"Teacher {number}" in taken:
        number += 1
    member = CohortMember(
        cohort_id=cohort_id, teacher_id=teacher_id, display_name=f"Teacher {number}"
    )
    db.add(member)
    lifecycle.audit(db, cohort_id, "teacher", "member", "joined")
    db.commit()
    return member


def leave(db: Session, cohort_id: str, teacher_id: str) -> None:
    """Leave the cohort: her membership goes, and so do her posts' links to her."""
    member = db.get(CohortMember, (cohort_id, teacher_id))
    if member is None:
        return
    for post in db.execute(
        select(ThreadPost).where(
            ThreadPost.cohort_id == cohort_id, ThreadPost.author_teacher_id == teacher_id
        )
    ).scalars():
        post.author_teacher_id = None
    db.delete(member)
    lifecycle.audit(db, cohort_id, "teacher", "member", "left")
    db.commit()


def _new_post(
    db: Session, cohort_id: str, kind: str, name: str, body: str, teacher_id: str | None = None
) -> ThreadPost:
    post = ThreadPost(
        id=secrets.token_hex(8),
        cohort_id=cohort_id,
        author_kind=kind,
        author_teacher_id=teacher_id,
        author_name=name,
        body=body,
    )
    db.add(post)
    return post


def post_as_teacher(
    db: Session, cohort_id: str, teacher_id: str, body: str, language: str
) -> ThreadPost:
    cohort = lifecycle.get(db, cohort_id)
    member = db.get(CohortMember, (cohort_id, teacher_id))
    if member is None:
        raise NotMember("Join the cohort first.")
    if lifecycle.thread_state(db, cohort) != "open":
        raise ThreadClosed("This thread is read-only.")
    try:
        problems = check_thread_post(body, language)
    except Exception as exc:  # the check could not run: hold, never pass
        raise PostRejected(["check_unavailable"]) from exc
    if problems:
        lifecycle.audit(
            db, cohort_id, "teacher", "member", "post_blocked", rules=[p.code for p in problems]
        )
        db.commit()
        raise PostRejected([p.code for p in problems])
    post = _new_post(db, cohort_id, "teacher", member.display_name, body, teacher_id)
    db.commit()
    return post


ANONYMOUS_NAME = "A teacher in this cohort"


def post_checkin(
    db: Session, cohort_id: str, teacher_id: str, body: str, language: str, *, anonymous: bool
) -> ThreadPost:
    """A check-in summary the teacher confirmed. Same rules as any post (member, open thread, the
    posting check); the author shows as "A teacher in this cohort" unless she chose her chat
    name."""
    cohort = lifecycle.get(db, cohort_id)
    member = db.get(CohortMember, (cohort_id, teacher_id))
    if member is None:
        raise NotMember("Join the cohort first.")
    if lifecycle.thread_state(db, cohort) != "open":
        raise ThreadClosed("This thread is read-only.")
    try:
        problems = check_thread_post(body, language)
    except Exception as exc:  # the check could not run: hold, never pass
        raise PostRejected(["check_unavailable"]) from exc
    if problems:
        raise PostRejected([p.code for p in problems])
    name = ANONYMOUS_NAME if anonymous else member.display_name
    post = _new_post(db, cohort_id, "teacher", name, body, teacher_id)
    return post


def post_as_staff(
    db: Session, cohort_id: str, kind: str, actor: str, body: str, language: str
) -> ThreadPost:
    """A mentor, the coach or the system posts under its role name. Staff text is checked too."""
    if kind not in ("mentor", "coach", "system"):
        raise ValueError("Unknown author kind.")
    cohort = lifecycle.get(db, cohort_id)
    if cohort.status not in ("active", "closing"):
        raise ThreadClosed("This thread is read-only.")
    problems = check_thread_post(body, language)
    if problems:
        raise PostRejected([p.code for p in problems])
    post = _new_post(db, cohort_id, kind, kind.capitalize(), body)
    lifecycle.audit(db, cohort_id, kind, actor, "staff_post")
    db.commit()
    return post


def report(db: Session, post_id: str, teacher_id: str) -> ThreadPost:
    """Any member can report a post: it is held (invisible to others) until the coach decides."""
    post = _get(db, post_id)
    if db.get(CohortMember, (post.cohort_id, teacher_id)) is None:
        raise NotMember("Only members can report.")
    if post.status == "visible":
        post.status = "reported"
        post.decided_at = datetime.now(UTC)
        lifecycle.audit(db, post.cohort_id, "teacher", "member", "post_reported", post=post.id)
        db.commit()
    return post


def decide(
    db: Session, post_id: str, action: str, *, actor: str, identifier: bool = False
) -> ThreadPost:
    """The coach's call on a post: hide, restore, pin, unpin. `identifier` marks a post that holds
    a child's identifier: its body is erased at once."""
    post = _get(db, post_id)
    now = datetime.now(UTC)
    if action == "hide":
        post.status = "hidden"
        post.decided_at = now
        if identifier:
            post.body = None
            post.rule_id = "child_identifier"
    elif action == "restore":
        if post.body is None:
            raise ValueError("A post whose text was erased cannot be restored.")
        post.status = "visible"
        post.decided_at = now
    elif action in ("pin", "unpin"):
        post.pinned = action == "pin"
    else:
        raise ValueError("Unknown action.")
    lifecycle.audit(
        db, post.cohort_id, "coach", actor, f"post_{action}", post=post.id, identifier=identifier
    )
    db.commit()
    return post


def delete_own(db: Session, post_id: str, teacher_id: str) -> None:
    post = _get(db, post_id)
    if post.author_teacher_id != teacher_id:
        raise NotMember("You can only delete your own posts.")
    post.body = None
    post.status = "deleted"
    post.decided_at = datetime.now(UTC)
    lifecycle.audit(db, post.cohort_id, "teacher", "member", "post_deleted", post=post.id)
    db.commit()


def _get(db: Session, post_id: str) -> ThreadPost:
    post = db.get(ThreadPost, post_id)
    if post is None:
        raise ValueError("That post does not exist.")
    return post


def view(post: ThreadPost) -> dict[str, Any]:
    """What an API returns about a post: a display name, never a teacher id."""
    return {
        "id": post.id,
        "author_kind": post.author_kind,
        "author_name": post.author_name,
        "body": post.body,
        "status": post.status,
        "pinned": post.pinned,
        "created_at": _aware(post.created_at).isoformat(),
    }


def posts_for(db: Session, cohort_id: str, *, moderator: bool = False) -> list[dict[str, Any]]:
    """Visible posts for a member; the coach also sees held, reported and hidden ones."""
    rows = db.execute(
        select(ThreadPost).where(ThreadPost.cohort_id == cohort_id).order_by(ThreadPost.created_at)
    ).scalars()
    shown = [p for p in rows if moderator or p.status == "visible"]
    shown.sort(key=lambda p: (not p.pinned, _aware(p.created_at)))
    from services.modules.checkin import card_for  # a check-in summary shows as a card

    out = []
    for p in shown:
        v = view(p)
        card = card_for(db, p.id)
        if card is not None:
            v["kind"] = "checkin_summary"
            v["checkin"] = card
        out.append(v)
    return out


def purge(db: Session, *, now: datetime | None = None) -> dict[str, int]:
    """The retention job. Bodies go: 7 days after a hold, hide or report; 30 days after a cohort
    closes; and in every case 90 days after the last post or after cancellation."""
    now = now or datetime.now(UTC)
    held = erased_closed = 0
    for post in db.execute(select(ThreadPost).where(ThreadPost.body.is_not(None))).scalars():
        cohort = db.get(CohortSpace, post.cohort_id)
        age = now - _aware(post.created_at)
        decided = _aware(post.decided_at) if post.decided_at else None
        if (
            post.status in ("reported", "hidden")
            and decided
            and now - decided >= timedelta(days=HELD_BODY_DAYS)
        ):
            post.body, held = None, held + 1
            continue
        ended = _aware(cohort.ended_at) if cohort and cohort.ended_at else None
        closed_long = ended is not None and now - ended >= timedelta(days=AFTER_CLOSE_DAYS)
        if closed_long or age >= timedelta(days=HARD_LIMIT_DAYS):
            post.body, erased_closed = None, erased_closed + 1
    if held or erased_closed:
        db.commit()
    return {"held_bodies_erased": held, "thread_text_erased": erased_closed}
