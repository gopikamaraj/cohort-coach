"""The cohort lifecycle: proposed, active, closing, closed (cancelled from proposed or active).

Closing to closed needs the post-test sheets received or an explicit "closed without post-test"
with a reason. Every transition leaves an audit row. A coach or mentor sees only the cohorts
assigned to her; figures that cover fewer than 5 teachers are hidden (rule 3).
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.api.db import CohortAuditRow, CohortMember, CohortSpace

TRANSITIONS: dict[str, tuple[str, ...]] = {
    "proposed": ("active", "cancelled"),
    "active": ("closing", "cancelled"),
    "closing": ("closed",),
    "closed": (),
    "cancelled": (),
}
MIN_MEMBERS_FOR_THREAD = 5
MIN_FIGURE = 5  # a figure over fewer than 5 classes or teachers is hidden


class NotAllowed(Exception):
    """The actor may not do this (wrong role, or not assigned to this cohort)."""


class BadTransition(Exception):
    """The status change is not one the lifecycle allows."""


def audit(db: Session, cohort_id: str, role: str, actor: str, action: str, **detail: Any) -> None:
    """Ids, codes and counts only: never post text, names or transcripts."""
    db.add(
        CohortAuditRow(cohort_id=cohort_id, role=role, actor=actor, action=action, detail=detail)
    )


def create(
    db: Session,
    *,
    error: str,
    coach_id: str,
    mentor_ids: list[str],
    officer_id: str,
    school_count: int = 0,
    simulated: bool = True,
    cohort_id: str | None = None,
) -> CohortSpace:
    cohort = CohortSpace(
        id=cohort_id or "co-" + secrets.token_hex(6),
        error=error,
        status="proposed",
        coach_id=coach_id,
        officer_id=officer_id,
        mentor_ids=list(mentor_ids),
        school_count=school_count,
        simulated=simulated,
    )
    db.add(cohort)
    audit(db, cohort.id, "officer", officer_id, "created", error=error)
    db.commit()
    return cohort


def get(db: Session, cohort_id: str) -> CohortSpace:
    cohort = db.get(CohortSpace, cohort_id)
    if cohort is None:
        raise NotAllowed("That cohort does not exist.")
    return cohort


def assigned(cohort: CohortSpace, role: str, person: str) -> bool:
    """A coach works her assigned cohorts, a mentor those she mentors; an officer sees all."""
    if role == "officer":
        return True
    if role == "coach":
        return cohort.coach_id == person
    if role == "mentor":
        return person in (cohort.mentor_ids or [])
    return False


def require_assigned(cohort: CohortSpace, role: str, person: str) -> None:
    if not assigned(cohort, role, person):
        raise NotAllowed("That cohort is not assigned to you.")


def transition(
    db: Session,
    cohort_id: str,
    to: str,
    *,
    role: str,
    actor: str,
    reason: str | None = None,
    post_test_received: bool | None = None,
) -> CohortSpace:
    """Move a cohort one step. The officer approves, cancels and closes; the coach moves an
    active cohort to closing for her own cohort. Anything else is refused."""
    cohort = get(db, cohort_id)
    if to not in TRANSITIONS.get(cohort.status, ()):
        raise BadTransition(f"A {cohort.status} cohort cannot become {to}.")
    if role == "coach":
        require_assigned(cohort, role, actor)
        if not (cohort.status == "active" and to == "closing"):
            raise NotAllowed("A coach can only start closing her active cohort.")
    elif role != "officer":
        raise NotAllowed("Your role cannot change a cohort's status.")
    if post_test_received is not None:
        cohort.post_test_received = post_test_received
    if to == "closed" and not cohort.post_test_received:
        if not (reason and reason.strip()):
            raise BadTransition(
                "Closing needs the post-test sheets received, or 'closed without post-test' "
                "with a reason."
            )
        cohort.close_reason = f"closed without post-test: {reason.strip()[:40]}"
    if to == "cancelled":
        cohort.close_reason = (reason or "cancelled")[:60]
    now = datetime.now(UTC)
    if to == "active":
        cohort.started_at = now
    if to in ("closed", "cancelled"):
        cohort.ended_at = now
    before = cohort.status
    cohort.status = to
    audit(db, cohort.id, role, actor, f"to_{to}", **{"from": before})
    db.commit()
    return cohort


def member_count(db: Session, cohort_id: str) -> int:
    return int(
        db.execute(
            select(func.count())
            .select_from(CohortMember)
            .where(CohortMember.cohort_id == cohort_id)
        ).scalar_one()
    )


def thread_state(db: Session, cohort: CohortSpace) -> str:
    """open: active with at least 5 members; read_only: otherwise (the prompts still show)."""
    if cohort.status == "active" and member_count(db, cohort.id) >= MIN_MEMBERS_FOR_THREAD:
        return "open"
    return "read_only"


def summary(db: Session, cohort: CohortSpace) -> dict[str, Any]:
    """What a mentor or coach may see of a cohort: status and cohort-level figures, never a
    membership list. The member count is hidden under 5."""
    n = member_count(db, cohort.id)
    return {
        "id": cohort.id,
        "error": cohort.error,
        "status": cohort.status,
        "track_version": cohort.track_version,
        "schools": cohort.school_count if cohort.school_count >= MIN_FIGURE else None,
        "members": n if n >= MIN_FIGURE else None,
        "thread": thread_state(db, cohort),
        "simulated": cohort.simulated,
    }
