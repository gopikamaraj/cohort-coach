# ruff: noqa: E501
"""Is this coach or mentor assigned to this cohort? One answer for every staff route that names a cohort.

A cohort a coach made from entered classes records her user id (`_coach`); a cohort space names its coach and
its mentors. A teacher's copy of a group cohort belongs to that group. Nothing else is assigned: a staff user
sees nothing of a cohort that is not hers, not even whether it exists (the routes answer 403 either way)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.db import ClassCohort, CohortMember, CohortSpace


def is_assigned(db: Session, uid: str, role: str, cohort_id: str) -> bool:
    group = db.get(ClassCohort, cohort_id)
    if group is not None:
        if group.group_id:  # a member's copy: judge by its group
            group = db.get(ClassCohort, group.group_id) or group
        if group.scope == "coach":
            return role == "coach" and group.counts.get("_coach") == uid
        # a teacher's own cohort: staff reach it only through a cohort space she belongs to that names them
        for sp in db.scalars(select(CohortSpace).join(CohortMember, CohortMember.cohort_id == CohortSpace.id).where(CohortMember.teacher_id == group.teacher_id)):
            if (role == "coach" and sp.coach_id == uid) or (role == "mentor" and uid in (sp.mentor_ids or [])):
                return True
        return False
    space = db.get(CohortSpace, cohort_id)
    if space is not None:
        return (role == "coach" and space.coach_id == uid) or (role == "mentor" and uid in (space.mentor_ids or []))
    return False
