"""Mentor items: a recording or method-card step on its way to teachers (gate 3 for mentors).

draft, awaiting_coach, changes_requested | approved | rejected; approved becomes in_use only when
a published track version includes it, then retired. Editing an in_use item makes a new draft
version; the old version stays in use until the new one is approved. Every decision records the
coach, a reason code and a screened note. Nothing reaches a teacher unless it is approved.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.validators.pii import check_pii
from services.api.cohorts import lifecycle
from services.api.db import MentorItem

KINDS = ("recording", "method_card")
REASONS = (
    "wrong_maths",
    "culturally_off",
    "too_complex_for_medium",
    "tone_issue",
    "factually_shaky",
    "unclear_audio",
    "missing_step",
)
TRANSITIONS: dict[str, tuple[str, ...]] = {
    "draft": ("awaiting_coach",),
    "awaiting_coach": ("changes_requested", "approved", "rejected"),
    "changes_requested": ("awaiting_coach",),
    "approved": ("in_use",),
    "in_use": ("retired",),
    "rejected": (),
    "retired": (),
}


class BadState(Exception):
    pass


def _touch(item: MentorItem) -> None:
    item.updated_at = datetime.now(UTC)


def create(db: Session, cohort_id: str, mentor_id: str, kind: str) -> MentorItem:
    cohort = lifecycle.get(db, cohort_id)
    lifecycle.require_assigned(cohort, "mentor", mentor_id)
    if kind not in KINDS:
        raise ValueError("Unknown item kind.")
    item = MentorItem(id=secrets.token_hex(8), mentor_id=mentor_id, cohort_id=cohort_id, kind=kind)
    db.add(item)
    lifecycle.audit(db, cohort_id, "mentor", mentor_id, "item_created", item=item.id, kind=kind)
    db.commit()
    return item


def _get(db: Session, item_id: str) -> MentorItem:
    item = db.get(MentorItem, item_id)
    if item is None:
        raise BadState("That item does not exist.")
    return item


def _move(item: MentorItem, to: str) -> None:
    if to not in TRANSITIONS.get(item.status, ()):
        raise BadState(f"A {item.status} item cannot become {to}.")
    item.status = to
    _touch(item)


def submit(db: Session, item_id: str, mentor_id: str) -> MentorItem:
    item = _get(db, item_id)
    if item.mentor_id != mentor_id:
        raise lifecycle.NotAllowed("That item is not yours.")
    _move(item, "awaiting_coach")
    lifecycle.audit(db, item.cohort_id, "mentor", mentor_id, "item_submitted", item=item.id)
    db.commit()
    return item


def decide(
    db: Session,
    item_id: str,
    decision: str,
    *,
    coach_id: str,
    reason: str | None = None,
    note: str = "",
) -> MentorItem:
    """Approve, request changes or reject. The coach must be assigned to the item's cohort; a
    request for changes or a rejection needs a reason code and the note is screened."""
    item = _get(db, item_id)
    lifecycle.require_assigned(lifecycle.get(db, item.cohort_id), "coach", coach_id)
    to = {"approve": "approved", "request_changes": "changes_requested", "reject": "rejected"}.get(
        decision
    )
    if to is None:
        raise ValueError("Unknown decision.")
    if to != "approved":
        if reason not in REASONS:
            raise ValueError("Choose one of the reason codes.")
        if check_pii(note):
            raise ValueError("Remove phone numbers, emails and ID numbers from the note.")
    _move(item, to)
    item.reason_code = reason if to != "approved" else None
    item.note = note[:300] or None
    item.decided_by = coach_id
    lifecycle.audit(
        db, item.cohort_id, "coach", coach_id, f"item_{to}", item=item.id, reason=item.reason_code
    )
    db.commit()
    return item


def mark_in_use(db: Session, item_id: str, version_id: str) -> MentorItem:
    """Called when a published track version includes the approved item; not before."""
    item = _get(db, item_id)
    _move(item, "in_use")
    item.in_use_version_id = version_id
    lifecycle.audit(
        db, item.cohort_id, "system", "publisher", "item_in_use", item=item.id, version=version_id
    )
    db.commit()
    return item


def edit(db: Session, item_id: str, mentor_id: str) -> MentorItem:
    """Edit an in_use item: a new draft version is made, the old one stays in use until the new one
    is approved. Editing a draft or changes-requested item changes it in place."""
    item = _get(db, item_id)
    if item.mentor_id != mentor_id:
        raise lifecycle.NotAllowed("That item is not yours.")
    if item.status in ("draft", "changes_requested"):
        return item
    if item.status != "in_use":
        raise BadState(f"A {item.status} item cannot be edited.")
    new = MentorItem(
        id=secrets.token_hex(8),
        mentor_id=item.mentor_id,
        cohort_id=item.cohort_id,
        kind=item.kind,
        version=item.version + 1,
        parent_id=item.id,
    )
    db.add(new)
    lifecycle.audit(
        db, item.cohort_id, "mentor", mentor_id, "item_new_version", item=new.id, parent=item.id
    )
    db.commit()
    return new


def retire_replaced(db: Session, item_id: str) -> None:
    """When a new version is in use, the version it replaced is retired."""
    item = _get(db, item_id)
    if item.parent_id:
        old = _get(db, item.parent_id)
        if old.status == "in_use":
            _move(old, "retired")
            db.commit()


def list_for_mentor(db: Session, mentor_id: str) -> list[MentorItem]:
    return list(
        db.execute(
            select(MentorItem)
            .where(MentorItem.mentor_id == mentor_id)
            .order_by(MentorItem.created_at)
        ).scalars()
    )


def awaiting_for_coach(db: Session, coach_id: str) -> list[MentorItem]:
    """Items waiting for this coach: only those in her assigned cohorts, oldest first."""
    from services.api.db import CohortSpace

    mine = [
        c.id
        for c in db.execute(select(CohortSpace).where(CohortSpace.coach_id == coach_id)).scalars()
    ]
    if not mine:
        return []
    return list(
        db.execute(
            select(MentorItem)
            .where(MentorItem.cohort_id.in_(mine), MentorItem.status == "awaiting_coach")
            .order_by(MentorItem.updated_at)
        ).scalars()
    )
