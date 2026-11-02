# ruff: noqa: E501, F811
"""Part A: four answers, the not-tried HOLD with up to two deferrals, the tried -> worked migration."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy.orm import Session, sessionmaker

from services.modules import branch, jobs, library, migrate, service, states
from services.modules.branch import Done, Plan, Template, next_module
from services.modules.models import ModuleEvent, ModuleFeedback, Track, TrackModule
from services.modules.service import ModulesError
from tests.modules.test_service_and_jobs import T0, at, cohort, db, events, factory, mods  # noqa: F401

STRINGS = Path(__file__).resolve().parents[2] / "strings"
PLAN = Plan("SUB-SFL", (Template("a", ("x",)), Template("b", ())), ())


def started(db: Session, errors: list[str] | None = None) -> Track:
    err = (errors or ["SUB-SFL"])[0]
    return service.start_track(db, cohort(db, errors=errors or ["SUB-SFL"]), err, "en", T0)


# ---- the four answers ----------------------------------------------------------------------------


def test_the_four_answers_are_exactly_these() -> None:
    assert states.ANSWERS == ("worked", "partly", "not_yet", "not_tried")
    assert "tried" not in states.ANSWERS and "tried" not in states.BRANCHES


@pytest.mark.parametrize("answer", ["worked", "partly", "not_yet", "not_tried"])
def test_each_answer_is_accepted_and_saved(db: Session, answer: str) -> None:
    track = started(db)
    fb = service.give_feedback(db, track.id, 1, "t-one", answer, "", T0)
    assert fb.answer == answer


@pytest.mark.parametrize("bad", ["tried", "great", ""])
def test_any_other_answer_is_refused(db: Session, bad: str) -> None:
    track = started(db)
    with pytest.raises(ModulesError) as err:
        service.give_feedback(db, track.id, 1, "t-one", bad, "", T0)
    assert err.value.code == "bad_answer"


# ---- the branch function -------------------------------------------------------------------------


def test_not_tried_is_not_a_result_and_never_advances_by_itself() -> None:
    got = next_module(PLAN, [Done(1, "a")], "not_tried", 6)
    # if a next module is made anyway it is the planned one, recorded as no_feedback, with its own reason
    assert (got.approach, got.branch, got.reason.code) == ("b", "no_feedback", "not_tried")


def test_worked_is_the_next_planned_module() -> None:
    got = next_module(PLAN, [Done(1, "a")], "worked", 6)
    assert (got.approach, got.branch, got.reason.code) == ("b", "worked", "worked")


# ---- the hold ------------------------------------------------------------------------------------


def test_not_tried_keeps_the_module_open_and_moves_the_next_date_by_seven_days(db: Session) -> None:
    track = started(db)
    before = [m.due_date for m in mods(db, track)]
    end = track.end_date
    service.give_feedback(db, track.id, 1, "t-one", "not_tried", "no time this week", T0)
    rows = mods(db, track)
    assert rows[0].status in (states.READY, states.DOWNLOADED)  # not feedback_given, not completed
    assert rows[0].due_date == before[0]  # a made module keeps its date
    assert [m.due_date for m in rows[1:]] == [d + timedelta(days=7) for d in before[1:]]
    db.refresh(track)
    assert track.end_date == end + timedelta(days=7) and track.status == "active"
    assert [e.detail["n"] for e in events(db, track, "deferred")] == [1]
    assert events(db, track, "coach_notified") == []  # the coach hears after the second deferral


def test_the_hold_view_offers_a_shorter_version_and_the_new_date(db: Session) -> None:
    track = started(db)
    service.give_feedback(db, track.id, 1, "t-one", "not_tried", "", T0)
    mod = service.track_view(db, track, "en", T0)["modules"][0]
    assert mod["feedback"]["answer"] == "not_tried"
    assert mod["hold"]["deferrals"] == 1 and mod["hold"]["max"] == 2 and mod["hold"]["days"] == 7
    steps = next(p for p in mod["hold"]["short"]["parts"] if p["id"] == "steps")
    assert len(steps["list"]) == 1  # the shorter version: the first step only


def test_get_the_next_module_always_works_while_held(db: Session) -> None:
    track = started(db)
    service.give_feedback(db, track.id, 1, "t-one", "not_tried", "", T0)
    assert service.track_view(db, track, "en", T0)["can_next"]["enabled"] is True
    got = service.next_for_teacher(db, track.id, "t-one", at(1))
    assert got.module is not None and got.module.branch == "no_feedback"
    assert got.module.reason and got.module.reason["code"] == "not_tried"
    assert got.module.generated_by == "teacher"


def test_pressing_not_tried_twice_defers_once(db: Session) -> None:
    track = started(db)
    service.give_feedback(db, track.id, 1, "t-one", "not_tried", "", T0)
    service.give_feedback(db, track.id, 1, "t-one", "not_tried", "still not", at(1))
    assert len(events(db, track, "deferred")) == 1


def test_a_real_answer_after_a_hold_closes_it(db: Session) -> None:
    track = started(db)
    service.give_feedback(db, track.id, 1, "t-one", "not_tried", "", T0)
    service.give_feedback(db, track.id, 1, "t-one", "worked", "", at(2))
    assert mods(db, track)[0].status == states.FEEDBACK_GIVEN
    assert db.get(ModuleFeedback, mods(db, track)[0].id).answer == "worked"


def test_the_job_makes_the_second_deferral_then_the_planned_module_as_no_feedback(
    factory: sessionmaker[Session],
) -> None:
    with factory() as db:
        track = started(db)
        tid = track.id
        service.give_feedback(db, tid, 1, "t-one", "not_tried", "", T0)  # first deferral: 7 -> 14
    assert jobs.run_due(factory, at(7))["generated"] == 0  # not due any more
    # the (moved) due date arrives: the second deferral, and the coach is told
    out = jobs.run_due(factory, at(14))
    assert out["generated"] == 0
    with factory() as db:
        t = db.get(Track, tid)
        assert t is not None
        assert [e.detail["n"] for e in events(db, t, "deferred")] == [1, 2]
        assert [e.detail["reason"] for e in events(db, t, "coach_notified")] == ["deferred_twice"]
        assert service.modules_of(db, tid)[1].due_date == at(21).date()
    # the next date arrives: no more deferrals, the planned module is made as no_feedback
    assert jobs.run_due(factory, at(21))["generated"] == 1
    with factory() as db:
        m2 = service.modules_of(db, tid)[1]
        assert (m2.branch, m2.generated_by) == ("no_feedback", "due_date")
        assert m2.reason and m2.reason["code"] == "not_tried"
    assert jobs.run_due(factory, at(21))["generated"] == 0  # a repeated run changes nothing


def test_the_deferral_size_and_limit_can_be_set(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MODULE_DEFER_DAYS", "3")
    monkeypatch.setenv("MODULE_MAX_DEFERRALS", "1")
    assert (library.defer_days(), library.max_deferrals()) == (3, 1)
    track = started(db)
    due = mods(db, track)[1].due_date
    service.give_feedback(db, track.id, 1, "t-one", "not_tried", "", T0)
    assert mods(db, track)[1].due_date == due + timedelta(days=3)
    assert len(events(db, track, "coach_notified")) == 1  # the first is also the last


def test_not_tried_is_counted_apart_and_never_as_a_result(db: Session) -> None:
    track = started(db)
    service.give_feedback(db, track.id, 1, "t-one", "not_tried", "", T0)
    fb = service.coach_counts(db, "cc-1", T0)["modules"][0]["feedback"]
    assert fb == {"worked": 0, "partly": 0, "not_yet": 0, "not_tried": 1}


def test_a_held_track_is_not_finished_even_on_its_last_module(db: Session) -> None:
    track = service.start_track(db, cohort(db, errors=["PV-REVERSE"]), "PV-REVERSE", "en", T0)
    service.give_feedback(db, track.id, 1, "t-one", "not_tried", "", T0)
    db.refresh(track)
    assert track.status == "active"  # worked would have completed it


# ---- why not yet? --------------------------------------------------------------------------------


def test_a_reason_chip_is_kept_as_an_event_and_only_the_approved_ones(db: Session) -> None:
    track = started(db)
    with pytest.raises(ModulesError) as err:
        service.record_reason(db, track.id, 1, "t-one", "no_time", T0)  # not held yet
    assert err.value.code == "not_held"
    service.give_feedback(db, track.id, 1, "t-one", "not_tried", "", T0)
    service.record_reason(db, track.id, 1, "t-one", "materials", T0)
    assert events(db, track, "not_tried_reason")[0].detail == {"chip": "materials"}
    with pytest.raises(ModulesError):
        service.record_reason(db, track.id, 1, "t-one", "because", T0)
    assert set(service.CHIPS) == {"no_time", "materials", "not_sure", "absent", "other"}


# ---- the migration -------------------------------------------------------------------------------


def test_old_tried_rows_become_worked_and_a_second_run_changes_nothing(db: Session) -> None:
    track = started(db)
    first = mods(db, track)[0]
    db.add(ModuleFeedback(module_id=first.id, answer="tried", note=""))
    first.branch, first.reason = "tried", {"code": "tried", "n": 1, "prev": 0}
    db.add(
        ModuleEvent(
            track_id=track.id,
            module_id=first.id,
            event="feedback_given",
            detail={"answer": "tried"},
            actor="teacher",
        )
    )
    db.commit()
    assert migrate.tried_to_worked(db) == 4
    db.expire_all()
    assert db.get(ModuleFeedback, first.id).answer == "worked"
    row = db.get(TrackModule, first.id)
    assert row.branch == "worked" and row.reason["code"] == "worked"
    assert events(db, track, "feedback_given")[0].detail["answer"] == "worked"
    assert migrate.tried_to_worked(db) == 0


# ---- the API -------------------------------------------------------------------------------------


def test_the_why_endpoint_and_the_four_answers_over_http(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from collections.abc import Iterator

    from fastapi.testclient import TestClient

    from services.api.db import Base, make_engine
    from services.api.main import create_app
    from services.api.profiles import get_session
    from services.modules import api as modules_api
    from tests.modules.test_api import BODY, DEV1, h

    monkeypatch.setenv("JUDGE_MODE", "1")
    monkeypatch.setattr(modules_api, "clock", lambda: T0)
    engine = make_engine(f"sqlite:///{tmp_path / 'api.sqlite'}")
    Base.metadata.create_all(engine)
    fac = sessionmaker(engine, expire_on_commit=False)

    def session() -> Iterator[Session]:
        with fac() as s:
            yield s

    app = create_app()
    app.dependency_overrides[get_session] = session
    c = TestClient(app)
    cid = c.post("/api/cohorts/class-only", json=BODY, headers=h("teacher", DEV1)).json()["id"]
    tid = c.post(
        "/api/modules/tracks",
        json={"cohort_id": cid, "error": "ADD-NOCARRY"},
        headers=h("teacher", DEV1),
    ).json()["id"]
    r = c.post(
        f"/api/modules/tracks/{tid}/modules/1/why",
        json={"chip": "absent"},
        headers=h("teacher", DEV1),
    )
    assert r.status_code == 409 and r.json()["detail"]["code"] == "not_held"
    r = c.post(
        f"/api/modules/tracks/{tid}/modules/1/feedback",
        json={"answer": "not_tried", "note": ""},
        headers=h("teacher", DEV1),
    )
    assert r.status_code == 200 and r.json()["modules"][0]["hold"]["deferrals"] == 1
    r = c.post(
        f"/api/modules/tracks/{tid}/modules/1/why",
        json={"chip": "absent"},
        headers=h("teacher", DEV1),
    )
    assert r.status_code == 200
    assert (
        c.post(
            f"/api/modules/tracks/{tid}/modules/1/why",
            json={"chip": "zzz"},
            headers=h("teacher", DEV1),
        ).status_code
        == 422
    )
    assert (
        c.post(
            f"/api/modules/tracks/{tid}/modules/1/feedback",
            json={"answer": "tried"},
            headers=h("teacher", DEV1),
        ).status_code
        == 422
    )
    assert c.post(f"/api/modules/tracks/{tid}/next", headers=h("teacher", DEV1)).status_code == 200


# ---- three languages -----------------------------------------------------------------------------


@pytest.mark.parametrize("lang", ["en", "hi", "ta"])
def test_the_new_strings_exist_in_every_language(lang: str) -> None:
    t = json.loads((STRINGS / f"{lang}.json").read_text(encoding="utf-8"))
    for code in branch.REASONS:
        assert t.get(f"module.reason.{code}"), (lang, code)
    assert "{n}" in t["module.reason.not_tried"] and "{prev}" in t["module.reason.not_tried"]
    for a in states.ANSWERS:
        assert t.get(f"module.feedback.{a}"), (lang, a)
    for c in ("no_time", "materials", "not_sure", "absent", "other"):
        assert t.get(f"module.hold.chip.{c}"), (lang, c)
    for k in (
        "module.hold.title",
        "module.hold.intro",
        "module.hold.short",
        "module.hold.ask",
        "module.hold.again",
        "module.coach.not_tried",
    ):
        assert t.get(k), (lang, k)
    assert "{date}" in t["module.hold.intro"]
    assert "tried" not in {k.rsplit(".", 1)[-1] for k in t if k.startswith("module.")}


def test_the_not_tried_reason_names_both_modules_in_english() -> None:
    out = service.reason_text({"code": "not_tried", "n": 3, "prev": 2}, "en")
    assert "Module 3" in out and "Module 2" in out and "do not count" in out
