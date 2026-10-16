"""Write a generated block into the database. Counts only, every row marked simulated."""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from services.api.db import Assignment, ClassRoom, ClassTermCount, Cohort, School


def seed_database(session: Session, block: dict[str, Any]) -> None:
    """Replace the simulated rows with this block. Safe to run twice."""
    for model in (Cohort, Assignment, ClassTermCount, ClassRoom, School):
        session.execute(delete(model).where(model.simulated))
    session.add_all(
        School(
            school_id=s["school_id"],
            name=s["name"],
            school_type=s["school_type"],
            medium=s["medium"],
            simulated=True,
        )
        for s in block["schools"]
    )
    session.flush()
    session.add_all(
        ClassRoom(
            class_id=c["class_id"],
            school_id=c["school_id"],
            block_id=block["block_id"],
            grade=block["grade"],
            section=c["section"],
            medium=c["medium"],
            teacher_id=c["teacher_id"],
            teacher_name=c["teacher_name"],
            simulated=True,
        )
        for c in block["classes"]
    )
    session.flush()
    for term, data in block["terms"].items():
        session.add_all(
            ClassTermCount(
                class_id=class_id,
                term=term,
                form_label=data["form_label"],
                children_checked=rec["children_checked"],
                counts=rec["counts"],
                anchor_wrong_count=rec["anchor_wrong_count"],
                untracked=rec["untracked"],
                simulated=True,
            )
            for class_id, rec in data["classes"].items()
        )
    session.add_all(
        Assignment(
            class_id=a["class_id"],
            track=a["track"],
            version=a["version"],
            arm=a["arm"],
            stratum=a["stratum"],
            reason=a["reason"],
            children_checked=a["children_checked"],
            children_showing=a["children_showing"],
            simulated=True,
        )
        for a in block["assignments"]
    )
    session.add_all(
        Cohort(
            cohort_id=c["cohort_id"],
            error=c["error"],
            medium=c["medium"],
            size=c["size"],
            class_ids=c["class_ids"],
            block_id=c["block_id"],
            cross_block=c["cross_block"],
            undersized=c["undersized"],
            mentor_slot=c["mentor_slot"],
            simulated=True,
        )
        for c in block["cohorts"]
    )
    session.commit()
