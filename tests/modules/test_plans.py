# ruff: noqa: E501
"""The improvement plan belongs to the cohort; each teacher keeps her own progress, feedback and branch."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from services.api.db import Base, ClassCohort, make_engine
from services.api.main import create_app
from services.api.profiles import get_session
from services.modules import api as modules_api
from services.modules import plans
from services.modules.models import CohortPlan, CohortPlanModule, ModuleFeedback, Track, TrackModule
from services.modules.service import IST

NOW = {"t": datetime(2026, 11, 2, 10, 0, tzinfo=IST)}
ANA, BEN, CORA, MIRA = "ana", "ben", "cora", "mira"


def who(name: str, role: str = "teacher") -> dict[str, str]:
    return {"X-User": name, "X-Role": role}


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    monkeypatch.setenv("JUDGE_MODE", "1")
    NOW["t"] = datetime(2026, 11, 2, 10, 0, tzinfo=IST)
    monkeypatch.setattr(modules_api, "clock", lambda: NOW["t"])
    engine = make_engine(f"sqlite:///{tmp_path / 'p.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def session() -> Iterator[Session]:
        with factory() as s:
            yield s

    app = create_app()
    app.dependency_overrides[get_session] = session
    yield TestClient(app), factory


def enter_class(c: TestClient, user: str, code: str) -> None:
    c.put(f"/api/store/classes/{code}", json={"data": {"id": code, "name": code}}, headers=who(user))
    prof = {"id": f"{code}:1", "classId": code, "term": 1, "createdAt": 1, "childrenChecked": 20, "counts": {"ADD-NOCARRY": 5}, "anyCounts": {"ADD-NOCARRY": 5}}
    c.put(f"/api/store/profiles/{code}:1", json={"data": prof}, headers=who(user))


def cohort_of_two(c: TestClient) -> tuple[str, str, str]:
    enter_class(c, ANA, "c-0000000001")
    enter_class(c, BEN, "c-0000000002")
    made = c.post("/api/cohorts/class-only/coach", json={"name": "Carrying group", "error": "ADD-NOCARRY"}, headers=who(CORA, "coach"))
    assert made.status_code == 200, made.text
    group = made.json()["id"]
    copy_a = c.get("/api/cohorts/class-only", headers=who(ANA)).json()[0]["id"]
    copy_b = c.get("/api/cohorts/class-only", headers=who(BEN)).json()[0]["id"]
    return group, copy_a, copy_b


def start(c: TestClient, user: str, cohort: str) -> dict:  # type: ignore[type-arg]
    r = c.post("/api/modules/tracks", json={"cohort_id": cohort, "error": "ADD-NOCARRY", "language": "en"}, headers=who(user))
    assert r.status_code == 200, r.text
    return r.json()  # type: ignore[no-any-return]


def test_two_teachers_in_a_cohort_share_one_plan_and_one_calendar(world: tuple[TestClient, sessionmaker[Session]]) -> None:
    c, factory = world
    group, copy_a, copy_b = cohort_of_two(c)
    a, b = start(c, ANA, copy_a), start(c, BEN, copy_b)
    assert a["id"] != b["id"]  # each teacher has her own track
    with factory() as db:
        assert len(list(db.scalars(select(CohortPlan)))) == 1  # but one plan for the cohort
        plan = db.scalars(select(CohortPlan)).one()
        assert plan.group_id == group
        assert {t.plan_id for t in db.scalars(select(Track))} == {plan.id}
        due = {t.teacher_id: [m.due_date for m in db.scalars(select(TrackModule).where(TrackModule.track_id == t.id).order_by(TrackModule.number))] for t in db.scalars(select(Track))}
        assert due[ANA] == due[BEN] == [m.due_date for m in plans.modules_of_plan(db, plan.id)]


def test_each_teachers_next_module_follows_her_own_feedback_inside_the_cohort_plan(world: tuple[TestClient, sessionmaker[Session]]) -> None:
    c, factory = world
    _, copy_a, copy_b = cohort_of_two(c)
    a, b = start(c, ANA, copy_a), start(c, BEN, copy_b)
    c.post(f"/api/modules/tracks/{a['id']}/modules/1/feedback", json={"answer": "partly", "note": ""}, headers=who(ANA))
    c.post(f"/api/modules/tracks/{b['id']}/modules/1/feedback", json={"answer": "worked", "note": ""}, headers=who(BEN))
    NOW["t"] += timedelta(days=1)
    na = c.post(f"/api/modules/tracks/{a['id']}/next", headers=who(ANA)).json()
    nb = c.post(f"/api/modules/tracks/{b['id']}/next", headers=who(BEN)).json()
    assert na["modules"][1]["branch"] == "partly" and nb["modules"][1]["branch"] == "worked"  # her feedback chose her branch
    assert na["modules"][1]["due_date"] == nb["modules"][1]["due_date"]  # the cohort's calendar
    with factory() as db:
        fb = {m.track_id: f.answer for m, f in db.execute(select(TrackModule, ModuleFeedback).join(ModuleFeedback, ModuleFeedback.module_id == TrackModule.id))}
        assert sorted(fb.values()) == ["partly", "worked"]
    # neither can read the other's track
    assert c.get(f"/api/modules/tracks/{b['id']}", headers=who(ANA)).status_code in (403, 404)


def test_a_coach_moves_the_whole_cohorts_dates_and_only_her_own_cohort(world: tuple[TestClient, sessionmaker[Session]]) -> None:
    c, factory = world
    group, copy_a, copy_b = cohort_of_two(c)
    start(c, ANA, copy_a)
    start(c, BEN, copy_b)
    with factory() as db:
        before = {m.number: m.due_date for m in plans.modules_of_plan(db, db.scalars(select(CohortPlan)).one().id)}
    ok = c.post(f"/api/modules/coach/cohorts/{group}/shift", json={"days": 7, "reason": "Diwali holiday"}, headers=who(CORA, "coach"))
    assert ok.status_code == 200, ok.text
    with factory() as db:
        after = {m.number: m.due_date for m in plans.modules_of_plan(db, db.scalars(select(CohortPlan)).one().id)}
        assert after[2] == before[2] + timedelta(days=7) and after[1] == before[1]  # module 1 is already made
        for t in db.scalars(select(Track)):
            mods = {m.number: m.due_date for m in db.scalars(select(TrackModule).where(TrackModule.track_id == t.id))}
            assert mods[2] == after[2]  # every teacher's calendar moved with it
    # another coach, a mentor and a teacher are not assigned to it
    assert c.post(f"/api/modules/coach/cohorts/{group}/shift", json={"days": 1, "reason": "x"}, headers=who(MIRA, "coach")).status_code == 403
    assert c.get(f"/api/modules/mentor/cohorts/{group}", headers=who(MIRA, "mentor")).status_code == 403
    assert c.get(f"/api/modules/coach/cohorts/{group}", headers=who(ANA)).status_code == 403
    seen = c.get(f"/api/modules/coach/cohorts/{group}", headers=who(CORA, "coach")).json()
    assert seen["tracks"] == 2 and "ana" not in str(seen) and "ben" not in str(seen)  # counts, no names


def test_existing_per_teacher_plans_are_merged_without_losing_anyones_progress(world: tuple[TestClient, sessionmaker[Session]]) -> None:
    _, factory = world
    with factory() as db:
        group = ClassCohort(id="cc-group", teacher_id="coach-cohorts", check_id="coach:ADD-NOCARRY", name="G", scope="coach", errors=["ADD-NOCARRY"], counts={"_members": {ANA: "c1:1", BEN: "c2:1"}, "_coach": CORA}, children_checked=40)
        copies = [ClassCohort(id=f"cc-{u}", teacher_id=u, check_id=chk, name="G", scope="member", errors=["ADD-NOCARRY"], counts={}, children_checked=20) for u, chk in ((ANA, "c1:1"), (BEN, "c2:1"))]
        solo = ClassCohort(id="cc-solo", teacher_id="dev", check_id="c3:1", name="Own", errors=["ADD-NOCARRY"], counts={}, children_checked=10)
        db.add_all([group, *copies, solo])
        db.flush()
        d0 = date(2026, 11, 2)
        for (cohort, owner, shift, answers) in (("cc-ana", ANA, 0, ["partly", "worked"]), ("cc-ben", BEN, 3, ["worked"]), ("cc-solo", "dev", 0, [])):
            t = Track(id=f"trk-{owner}", class_cohort_id=cohort, teacher_id=owner, error="ADD-NOCARRY", language="en", start_date=d0 + timedelta(days=shift), end_date=d0 + timedelta(days=shift + 21), cap=6)
            db.add(t)
            for n in range(1, 4):
                db.add(TrackModule(id=f"mod-{owner}-{n}", track_id=t.id, number=n, template_id=f"ADD-NOCARRY:a{n}", approach_id=f"a{n}", title=f"T{n}", due_date=d0 + timedelta(days=shift + 7 * (n - 1)), status="ready" if n <= len(answers) + 1 else "planned"))
            for n, ans in enumerate(answers, start=1):
                db.add(ModuleFeedback(module_id=f"mod-{owner}-{n}", answer=ans, note=""))
        db.commit()
        feedback_before = sorted((f.module_id, f.answer) for f in db.scalars(select(ModuleFeedback)))
        modules_before = sorted((m.id, m.number, m.status, m.due_date) for m in db.scalars(select(TrackModule)))
        out = plans.merge_teacher_plans(db)
        db.commit()
        assert out["group_links"] == 2  # the copies now point at their group
        assert out["tracks"] == 3 and out["plans"] == 2 and out["plans_merged"] == 1  # ana + ben merged; dev has a plan of her own
        assert sorted((f.module_id, f.answer) for f in db.scalars(select(ModuleFeedback))) == feedback_before  # nobody's feedback lost
        assert sorted((m.id, m.number, m.status, m.due_date) for m in db.scalars(select(TrackModule))) == modules_before  # nor her modules or dates
        merged = db.scalars(select(CohortPlan).where(CohortPlan.group_id == "cc-group")).one()
        assert merged.start_date == d0 and merged.end_date == d0 + timedelta(days=24)  # earliest start, latest end
        assert [m.due_date for m in db.scalars(select(CohortPlanModule).where(CohortPlanModule.plan_id == merged.id).order_by(CohortPlanModule.number))] == [d0, d0 + timedelta(days=7), d0 + timedelta(days=14)]
        assert {t.plan_id for t in db.scalars(select(Track).where(Track.teacher_id.in_([ANA, BEN])))} == {merged.id}
        assert plans.merge_teacher_plans(db)["plans"] == 0  # running it again changes nothing
