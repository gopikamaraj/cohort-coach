# ruff: noqa: E501
"""The improvement plan belongs to the cohort; each teacher keeps her own progress.

A `CohortPlan` holds the module templates and due dates for one (cohort, error). A teacher's `Track` follows it:
her modules, her feedback and her branch stay hers (so her next module is still chosen from her own
feedback), but the calendar and the starting templates are the cohort's. A teacher who joins late gets the
cohort's calendar as it stands. Counts and text only; no child, no name.
"""

from __future__ import annotations

import secrets
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.db import ClassCohort
from services.modules import library
from services.modules.models import CohortPlan, CohortPlanModule, Track, TrackModule


def group_key(cohort: ClassCohort) -> str:
    """The cohort a plan hangs from: the group a teacher's copy points at, else the cohort itself."""
    return cohort.group_id or cohort.id


def plan_of(db: Session, group_id: str, error: str) -> CohortPlan | None:
    return db.execute(select(CohortPlan).where(CohortPlan.group_id == group_id, CohortPlan.error == error)).scalar_one_or_none()


def modules_of_plan(db: Session, plan_id: str) -> list[CohortPlanModule]:
    return list(db.execute(select(CohortPlanModule).where(CohortPlanModule.plan_id == plan_id).order_by(CohortPlanModule.number)).scalars())


def ensure_plan(db: Session, cohort: ClassCohort, error: str, language: str, start: date, end_date: date | None, created_by: str) -> CohortPlan:
    """The cohort's plan for this error, made from the library the first time any member starts it."""
    gid = group_key(cohort)
    have = plan_of(db, gid, error)
    if have is not None:
        return have
    length = library.planned_length(error)
    gap = library.gap_days()
    plan = CohortPlan(
        id="plan-" + secrets.token_hex(6),
        group_id=gid,
        error=error,
        language=language if language in library.LANGS else "en",
        start_date=start,
        end_date=end_date or start + timedelta(days=gap * length),
        cap=library.cap(),
        created_by=created_by,
    )
    db.add(plan)
    db.flush()
    for i, t in enumerate(library.plan_for(error).templates[:length]):
        db.add(
            CohortPlanModule(
                plan_id=plan.id,
                number=i + 1,
                template_id=f"{error}:{t.approach}",
                approach_id=t.approach,
                title=library.title(error, t.approach, plan.language),
                due_date=start + timedelta(days=gap * i),
            )
        )
    db.flush()
    return plan


def due_for(db: Session, track: Track, number: int) -> date | None:
    """The cohort's due date for module `number`, if the track follows a plan that has one."""
    if not track.plan_id:
        return None
    m = db.execute(select(CohortPlanModule).where(CohortPlanModule.plan_id == track.plan_id, CohortPlanModule.number == number)).scalar_one_or_none()
    return m.due_date if m else None


def tracks_in_group(db: Session, cohort_id: str) -> list[Track]:
    """Every teacher's track in a cohort: those on the cohort itself and on each member's copy of it."""
    ids = {cohort_id} | set(db.execute(select(ClassCohort.id).where(ClassCohort.group_id == cohort_id)).scalars())
    return list(db.execute(select(Track).where(Track.class_cohort_id.in_(ids))).scalars())


def shift_plan(db: Session, cohort_id: str, days: int) -> int:
    """A holiday moves the cohort's calendar: plan modules no track has made yet, and the end date."""
    moved = 0
    for plan in db.execute(select(CohortPlan).where(CohortPlan.group_id == cohort_id)).scalars():
        furthest = 0
        for t in tracks_in_group(db, cohort_id):
            if t.plan_id == plan.id:
                furthest = max(furthest, len([m for m in db.execute(select(TrackModule).where(TrackModule.track_id == t.id)).scalars() if m.status not in ("planned", "skipped")]))
        for m in modules_of_plan(db, plan.id):
            if m.number > furthest:
                m.due_date = m.due_date + timedelta(days=days)
                moved += 1
        plan.end_date = plan.end_date + timedelta(days=days)
    return moved


def set_plan_due(db: Session, cohort_id: str, number: int, new: date) -> None:
    for plan in db.execute(select(CohortPlan).where(CohortPlan.group_id == cohort_id)).scalars():
        m = db.execute(select(CohortPlanModule).where(CohortPlanModule.plan_id == plan.id, CohortPlanModule.number == number)).scalar_one_or_none()
        if m is not None:
            m.due_date = new
            if new > plan.end_date:
                plan.end_date = new


# ---- migration of the plans that were one per teacher ---------------------------------------------


def backfill_groups(db: Session) -> int:
    """A teacher's copy of a coach or officer cohort did not record its group. The group lists its members (user
    id -> the check each class entered), so match each copy by owner and check, and set `group_id`."""
    n = 0
    groups = db.execute(select(ClassCohort).where(ClassCohort.teacher_id == "coach-cohorts", ClassCohort.scope == "coach")).scalars().all()
    for g in groups:
        for uid, check in (g.counts.get("_members") or {}).items():
            copy = db.execute(select(ClassCohort).where(ClassCohort.teacher_id == uid, ClassCohort.check_id == check, ClassCohort.scope == "member")).scalar_one_or_none()
            if copy is not None and copy.group_id != g.id:
                copy.group_id = g.id
                n += 1
    db.flush()
    return n


def merge_teacher_plans(db: Session) -> dict[str, int]:
    """Give every existing track a cohort plan. Tracks of one cohort and error (a coach's group, through each
    member's copy) share one plan; a teacher's own single-class cohort gets a plan of its own. Nobody's modules,
    feedback or branch are touched: only `Track.plan_id` is set and the plan rows are made. The plan takes the
    earliest start, the latest end, the largest cap, and for each module number the earliest due date and the
    template of the track that got furthest. Returns counts for the report."""
    out = {"group_links": backfill_groups(db), "tracks": 0, "plans": 0, "plans_merged": 0, "tracks_already": 0}
    cohorts = {c.id: c for c in db.execute(select(ClassCohort)).scalars()}
    buckets: dict[tuple[str, str], list[Track]] = {}
    for t in db.execute(select(Track).order_by(Track.created_at)).scalars():
        if t.plan_id:
            out["tracks_already"] += 1
            continue
        c = cohorts.get(t.class_cohort_id)
        gid = group_key(c) if c else t.class_cohort_id
        buckets.setdefault((gid, t.error), []).append(t)
    for (gid, error), tracks in buckets.items():
        plan = plan_of(db, gid, error)
        rows = {t.id: list(db.execute(select(TrackModule).where(TrackModule.track_id == t.id).order_by(TrackModule.number)).scalars()) for t in tracks}
        if plan is None:
            plan = CohortPlan(
                id="plan-" + secrets.token_hex(6),
                group_id=gid,
                error=error,
                language=tracks[0].language,
                start_date=min(t.start_date for t in tracks),
                end_date=max(t.end_date for t in tracks),
                cap=max(t.cap for t in tracks),
                created_by="migration",
            )
            db.add(plan)
            db.flush()
            lead = max(tracks, key=lambda t: len(rows[t.id]))
            numbers = sorted({m.number for r in rows.values() for m in r})
            for n in numbers:
                everyone = [m for r in rows.values() for m in r if m.number == n]
                chosen = next((m for m in rows[lead.id] if m.number == n), everyone[0])
                db.add(
                    CohortPlanModule(
                        plan_id=plan.id,
                        number=n,
                        template_id=chosen.template_id,
                        approach_id=chosen.approach_id,
                        title=chosen.title,
                        due_date=min(m.due_date for m in everyone),
                    )
                )
            out["plans"] += 1
            if len(tracks) > 1:
                out["plans_merged"] += 1
        for t in tracks:
            t.plan_id = plan.id
            out["tracks"] += 1
    db.flush()
    return out

