# ruff: noqa: E501
"""Tracks, modules, feedback, idempotency, the daily job on a frozen clock, and one whole track end to end.

No paid API, no speech: the module text is the library's own. The clock is always passed in."""

from __future__ import annotations

import threading
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from services.api.db import Base, ClassCohort, make_engine
from services.modules import branch, jobs, library, service, states
from services.modules.models import ModuleEvent, ModuleFeedback, Track, TrackModule
from services.modules.service import IST, ModulesError

T0 = datetime(2026, 11, 2, 10, 0, tzinfo=IST)  # a Monday, 10:00 in India


def at(days: int, hour: int = 6, minute: int = 0) -> datetime:
    return datetime.combine(T0.date() + timedelta(days=days), datetime.min.time(), IST).replace(
        hour=hour, minute=minute
    )


@pytest.fixture
def factory(tmp_path: Path) -> Iterator[sessionmaker[Session]]:
    engine = make_engine(f"sqlite:///{tmp_path / 'modules.sqlite'}")
    Base.metadata.create_all(engine)
    yield sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
def db(factory: sessionmaker[Session]) -> Iterator[Session]:
    with factory() as s:
        yield s


def cohort(
    db: Session, teacher: str = "t-one", errors: list[str] | None = None, cid: str = "cc-1"
) -> ClassCohort:
    row = ClassCohort(
        id=cid,
        teacher_id=teacher,
        check_id=f"chk-{cid}",
        name="My class",
        errors=errors or ["ADD-NOCARRY"],
        counts={e: 4 for e in (errors or ["ADD-NOCARRY"])},
        children_checked=20,
    )
    db.add(row)
    db.commit()
    return row


def mods(db: Session, track: Track) -> list[TrackModule]:
    db.expire_all()
    return service.modules_of(db, track.id)


def events(db: Session, track: Track, kind: str) -> list[ModuleEvent]:
    return list(
        db.execute(
            select(ModuleEvent).where(ModuleEvent.track_id == track.id, ModuleEvent.event == kind)
        ).scalars()
    )


# ---- starting ------------------------------------------------------------------------------------


def test_a_track_plans_every_module_with_a_due_date_and_makes_only_the_first(db: Session) -> None:
    track = service.start_track(db, cohort(db, errors=["SUB-SFL"]), "SUB-SFL", "en", T0)
    rows = mods(db, track)
    assert [m.number for m in rows] == [1, 2, 3, 4]
    assert rows[0].status == states.READY and rows[0].generated_by == "start" and rows[0].text
    assert all(m.status == states.PLANNED and m.text is None for m in rows[1:])
    assert [m.due_date for m in rows] == [T0.date() + timedelta(days=7 * i) for i in range(4)]
    assert all(m.title for m in rows)


def test_starting_twice_returns_the_same_track_and_one_first_module(db: Session) -> None:
    c = cohort(db)
    a = service.start_track(db, c, "ADD-NOCARRY", "en", T0)
    b = service.start_track(db, c, "ADD-NOCARRY", "en", T0 + timedelta(hours=1))
    assert a.id == b.id and len(mods(db, a)) == 3
    assert len(events(db, a, "module_generated")) == 1


def test_an_error_the_cohort_did_not_choose_is_refused(db: Session) -> None:
    with pytest.raises(ModulesError):
        service.start_track(db, cohort(db), "SUB-SFL", "en", T0)


def test_an_error_with_no_plan_keeps_one_module_and_logs_it(db: Session) -> None:
    c = cohort(db, errors=["ADD-WHOLE-ONES"])
    track = service.start_track(db, c, "ADD-WHOLE-ONES", "en", T0)
    assert track.note and "no plan" in track.note and len(events(db, track, "no_plan")) == 1


def test_the_first_module_is_the_plans_first_and_says_why(db: Session) -> None:
    track = service.start_track(db, cohort(db), "ADD-NOCARRY", "en", T0)
    first = mods(db, track)[0]
    assert first.branch == "first" and first.reason == {"code": "first", "n": 1, "prev": 0}
    assert first.approach_id == library.plan_for("ADD-NOCARRY").templates[0].approach


# ---- feedback and the next module ---------------------------------------------------------------


def test_get_next_is_refused_until_feedback_is_given(db: Session) -> None:
    c = cohort(db)
    track = service.start_track(db, c, "ADD-NOCARRY", "en", T0)
    view = service.track_view(db, track, "en", T0)
    assert view["can_next"]["enabled"] is False and view["can_next"]["code"] == "needs_feedback"
    assert view["can_next"]["due_date"] == (T0.date() + timedelta(days=7)).isoformat()
    with pytest.raises(ModulesError) as err:
        service.next_for_teacher(db, track.id, "t-one", T0)
    assert err.value.code == "needs_feedback"
    assert len(mods(db, track)) == 3 and mods(db, track)[1].status == states.PLANNED


@pytest.mark.parametrize(
    ("answer", "branch_", "smaller", "same_approach"),
    [
        ("worked", "worked", False, False),
        ("partly", "partly", True, True),
        ("not_yet", "not_yet", False, False),
    ],
)
def test_feedback_leads_to_the_right_next_module(
    db: Session, answer: str, branch_: str, smaller: bool, same_approach: bool
) -> None:
    track = service.start_track(db, cohort(db, errors=["SUB-SFL"]), "SUB-SFL", "en", T0)
    first = mods(db, track)[0]
    service.give_feedback(db, track.id, 1, "t-one", answer, "", T0)
    got = service.next_for_teacher(db, track.id, "t-one", at(1))
    assert (
        got.module is not None
        and got.module.branch == branch_
        and got.module.generated_by == "teacher"
    )
    assert got.module.template_id and got.module.template_id.endswith(":small") is smaller
    assert (got.module.approach_id == first.approach_id) is same_approach
    assert mods(db, track)[0].status == states.COMPLETED


def test_partly_adds_a_module_the_plan_did_not_have(db: Session) -> None:
    track = service.start_track(db, cohort(db, errors=["PV-HEARD"]), "PV-HEARD", "en", T0)
    assert len(mods(db, track)) == 2
    service.give_feedback(db, track.id, 1, "t-one", "partly", "", T0)
    service.next_for_teacher(db, track.id, "t-one", at(1))  # 2: smaller step of module 1's approach
    service.give_feedback(db, track.id, 2, "t-one", "worked", "", at(2))
    got = service.next_for_teacher(db, track.id, "t-one", at(3))
    assert [m.number for m in mods(db, track)] == [1, 2, 3] and got.module is not None
    assert got.module.branch == "worked" and got.module.approach_id == "show_bundles"


def test_not_yet_with_nothing_left_stops_and_tells_the_coach(db: Session) -> None:
    track = service.start_track(db, cohort(db, errors=["PV-REVERSE"]), "PV-REVERSE", "en", T0)
    service.give_feedback(db, track.id, 1, "t-one", "not_yet", "", T0)
    db.refresh(track)
    assert track.status == "stopped" and track.stop_reason == branch.STOP_EXHAUSTED
    assert len(events(db, track, "coach_notified")) == 1
    view = service.track_view(db, track, "en", T0)
    assert view["can_next"]["enabled"] is False and view["can_next"]["code"] == "track_exhausted"


def test_the_cap_stops_the_track(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODULE_CAP", "2")
    track = service.start_track(db, cohort(db, errors=["SUB-SFL"]), "SUB-SFL", "en", T0)
    assert len(mods(db, track)) == 2
    service.give_feedback(db, track.id, 1, "t-one", "worked", "", T0)
    service.next_for_teacher(db, track.id, "t-one", at(1))
    service.give_feedback(db, track.id, 2, "t-one", "worked", "", at(2))
    db.refresh(track)
    assert track.status == "stopped" and track.stop_reason == branch.STOP_CAP
    assert len(events(db, track, "coach_notified")) == 1


def test_finishing_the_plan_completes_the_track_without_a_referral(db: Session) -> None:
    track = service.start_track(db, cohort(db, errors=["PV-REVERSE"]), "PV-REVERSE", "en", T0)
    service.give_feedback(db, track.id, 1, "t-one", "worked", "", T0)
    db.refresh(track)
    assert track.status == "completed" and track.stop_reason == branch.STOP_DONE
    assert events(db, track, "coach_notified") == []
    assert mods(db, track)[0].status == states.COMPLETED


def test_late_feedback_attaches_to_its_module_and_changes_nothing_made(db: Session) -> None:
    track = service.start_track(db, cohort(db), "ADD-NOCARRY", "en", T0)
    service.coach_generate(db, track.id, at(1))  # module 2 made with no feedback on 1
    before = [(m.number, m.approach_id, m.branch) for m in mods(db, track)]
    service.give_feedback(db, track.id, 1, "t-one", "not_yet", "", at(2))
    assert [(m.number, m.approach_id, m.branch) for m in mods(db, track)][:2] == before[:2]
    assert db.get(ModuleFeedback, mods(db, track)[0].id).answer == "not_yet"
    assert events(db, track, "feedback_given")[0].detail["late"] is True


def test_a_note_is_masked_and_a_name_never_reaches_the_record(db: Session) -> None:
    track = service.start_track(db, cohort(db), "ADD-NOCARRY", "en", T0)
    fb = service.give_feedback(db, track.id, 1, "t-one", "worked", "call me on a.b@example.com", T0)
    assert "example.com" not in fb.note


def test_a_teacher_cannot_touch_another_teachers_track(db: Session) -> None:
    track = service.start_track(db, cohort(db), "ADD-NOCARRY", "en", T0)
    with pytest.raises(ModulesError) as err:
        service.give_feedback(db, track.id, 1, "t-two", "worked", "", T0)
    assert err.value.code == "not_hers"


def test_download_moves_a_module_to_downloaded_once(db: Session) -> None:
    track = service.start_track(db, cohort(db), "ADD-NOCARRY", "en", T0)
    service.mark_downloaded(db, track.id, 1, "t-one", "pack-audio/abc.mp3", T0)
    service.mark_downloaded(db, track.id, 1, "t-one", "pack-audio/abc.mp3", at(1))
    assert (
        mods(db, track)[0].status == states.DOWNLOADED and len(events(db, track, "downloaded")) == 1
    )


def test_a_module_cannot_be_downloaded_before_it_is_made(db: Session) -> None:
    track = service.start_track(db, cohort(db), "ADD-NOCARRY", "en", T0)
    with pytest.raises(ModulesError):
        service.mark_downloaded(db, track.id, 2, "t-one", "x", T0)


# ---- idempotency ---------------------------------------------------------------------------------


def test_a_repeated_generate_returns_the_same_module(db: Session) -> None:
    track = service.start_track(db, cohort(db), "ADD-NOCARRY", "en", T0)
    a = service.generate_module(db, track.id, 2, "due_date", at(7))
    b = service.generate_module(db, track.id, 2, "due_date", at(7))
    assert a.created and not b.created and a.module and b.module and a.module.id == b.module.id
    assert len(events(db, track, "module_generated")) == 2  # modules 1 and 2, once each


def test_two_simultaneous_presses_make_one_module(factory: sessionmaker[Session]) -> None:
    with factory() as db:
        track = service.start_track(db, cohort(db), "ADD-NOCARRY", "en", T0)
        service.give_feedback(db, track.id, 1, "t-one", "worked", "", T0)
        tid = track.id
    barrier = threading.Barrier(2)
    results: list[object] = []

    def press() -> None:
        with factory() as s:
            barrier.wait()
            try:
                results.append(service.next_for_teacher(s, tid, "t-one", at(1)))
            except Exception as exc:  # noqa: BLE001
                results.append(exc)

    threads = [threading.Thread(target=press) for _ in range(2)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    with factory() as db:
        rows = service.modules_of(db, tid)
        made = [m for m in rows if m.number == 2]
        assert len(made) == 1 and made[0].status == states.READY
        assert (
            db.execute(
                select(func.count())
                .select_from(ModuleEvent)
                .where(ModuleEvent.track_id == tid, ModuleEvent.event == "module_generated")
            ).scalar_one()
            == 2
        )
    assert not [r for r in results if isinstance(r, Exception)], results


def test_the_unique_constraint_is_there() -> None:
    names = {
        tuple(c.name for c in u.columns)
        for u in TrackModule.__table__.constraints
        if hasattr(u, "columns")
    }
    assert ("track_id", "number") in names


# ---- the daily job -------------------------------------------------------------------------------


def test_the_job_day_changes_at_six_in_the_morning_indian_time() -> None:
    d = T0.date() + timedelta(days=7)
    assert service.job_day(at(7, 5, 59)) == d - timedelta(days=1)
    assert service.job_day(at(7, 6, 0)) == d
    utc = at(7, 6, 0).astimezone(UTC)  # the same moment written in UTC
    assert service.job_day(utc) == d


def test_a_due_module_is_made_with_no_feedback_and_the_record_says_so(
    factory: sessionmaker[Session],
) -> None:
    with factory() as db:
        track = service.start_track(db, cohort(db), "ADD-NOCARRY", "en", T0)
        tid = track.id
    out = jobs.run_due(factory, at(7, 6, 0))
    assert out["generated"] == 1
    with factory() as db:
        m2 = service.modules_of(db, tid)[1]
        assert (m2.status, m2.branch, m2.generated_by) == (states.READY, "no_feedback", "due_date")
        assert m2.reason and m2.reason["code"] == "no_feedback"
        assert service.modules_of(db, tid)[0].status == states.EXPIRED


def test_the_job_does_nothing_one_minute_before_six(factory: sessionmaker[Session]) -> None:
    with factory() as db:
        service.start_track(db, cohort(db), "ADD-NOCARRY", "en", T0)
    assert jobs.run_due(factory, at(7, 5, 59))["generated"] == 0
    assert jobs.run_due(factory, at(7, 6, 0))["generated"] == 1


def test_a_module_with_feedback_uses_its_real_branch(factory: sessionmaker[Session]) -> None:
    with factory() as db:
        track = service.start_track(db, cohort(db, errors=["SUB-SFL"]), "SUB-SFL", "en", T0)
        service.give_feedback(db, track.id, 1, "t-one", "not_yet", "", T0)
        tid = track.id
    jobs.run_due(factory, at(7))
    with factory() as db:
        m2 = service.modules_of(db, tid)[1]
        assert m2.branch == "not_yet" and m2.generated_by == "due_date"


def test_a_missed_run_is_caught_up_in_order(factory: sessionmaker[Session]) -> None:
    with factory() as db:
        track = service.start_track(db, cohort(db, errors=["SUB-SFL"]), "SUB-SFL", "en", T0)
        tid = track.id
    out = jobs.run_due(factory, at(15))  # days 7 and 14 were never run
    assert out["generated"] == 2
    with factory() as db:
        rows = service.modules_of(db, tid)
        assert [m.status for m in rows[:3]] == [states.EXPIRED, states.EXPIRED, states.READY]
        assert rows[3].status == states.PLANNED


def test_running_the_job_twice_changes_nothing_the_second_time(
    factory: sessionmaker[Session],
) -> None:
    with factory() as db:
        service.start_track(db, cohort(db), "ADD-NOCARRY", "en", T0)
    assert jobs.run_due(factory, at(7))["generated"] == 1
    assert jobs.run_due(factory, at(7))["generated"] == 0


def test_a_failure_is_retried_with_a_growing_wait(
    factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    with factory() as db:
        service.start_track(db, cohort(db), "ADD-NOCARRY", "en", T0)
    real, calls, waits = service.generate_module, [], []

    def flaky(*a: object, **k: object) -> object:
        calls.append(1)
        if len(calls) < 3:
            raise RuntimeError("boom")
        return real(*a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(service, "generate_module", flaky)
    out = jobs.run_due(factory, at(7), sleep=waits.append)
    assert out["generated"] == 1 and out["failed"] == 0 and waits == [1, 2]


def test_a_module_that_keeps_failing_is_marked_and_the_coach_is_told(
    factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    with factory() as db:
        track = service.start_track(db, cohort(db), "ADD-NOCARRY", "en", T0)
        tid = track.id
    monkeypatch.setattr(
        service, "generate_module", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x"))
    )
    out = jobs.run_due(factory, at(7), sleep=lambda s: None)
    assert out["failed"] == 1
    with factory() as db:
        t = db.get(Track, tid)
        assert t is not None
        assert service.modules_of(db, tid)[1].failures == 1
        assert (
            len(events(db, t, "generate_failed")) == 1 and len(events(db, t, "coach_notified")) == 1
        )
        counts = service.coach_counts(db, "cc-1", at(7))
        assert counts["modules"][1]["failed"] == 1 and counts["modules"][1]["overdue"] == 1


def test_one_failing_track_does_not_stop_the_others(
    factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    with factory() as db:
        a = service.start_track(db, cohort(db, "t-a", cid="cc-a"), "ADD-NOCARRY", "en", T0)
        b = service.start_track(db, cohort(db, "t-b", cid="cc-b"), "ADD-NOCARRY", "en", T0)
        bad = a.id
    real = service.generate_module

    def pick(db: Session, track_id: str, *a: object, **k: object) -> object:
        if track_id == bad:
            raise RuntimeError("boom")
        return real(db, track_id, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(service, "generate_module", pick)
    out = jobs.run_due(factory, at(7), sleep=lambda s: None)
    assert out["failed"] == 1 and out["generated"] == 1
    with factory() as db:
        assert service.modules_of(db, b.id)[1].status == states.READY


def test_a_module_never_downloaded_is_flagged_to_the_coach_once(
    factory: sessionmaker[Session],
) -> None:
    with factory() as db:
        track = service.start_track(db, cohort(db), "ADD-NOCARRY", "en", T0)
        tid = track.id
    assert jobs.run_due(factory, at(3))["flagged"] == 0
    assert jobs.run_due(factory, at(5, 12))["flagged"] == 1
    assert jobs.run_due(factory, at(6))["flagged"] == 0
    with factory() as db:
        assert service.coach_counts(db, "cc-1", at(6))["modules"][0]["not_downloaded_flag"] == 1
        assert tid


def test_the_track_closes_after_its_end_date(factory: sessionmaker[Session]) -> None:
    with factory() as db:
        track = service.start_track(db, cohort(db, errors=["PV-HEARD"]), "PV-HEARD", "en", T0)
        tid, end = track.id, track.end_date
    jobs.run_due(factory, at((end - T0.date()).days + 1))
    with factory() as db:
        t = db.get(Track, tid)
        assert t is not None and t.status == "completed" and t.stop_reason == "end_date"


# ---- the coach: dates, counts, edge cases -------------------------------------------------------


def test_a_coach_can_move_a_planned_date_but_not_a_made_one(db: Session) -> None:
    track = service.start_track(db, cohort(db), "ADD-NOCARRY", "en", T0)
    new = T0.date() + timedelta(days=9)
    service.set_due_date(db, track.id, 2, new, "school holiday", T0)
    assert mods(db, track)[1].due_date == new
    ev = events(db, track, "due_changed")
    assert ev and ev[0].actor == "coach" and ev[0].detail["reason"] == "school holiday"
    with pytest.raises(ModulesError) as err:
        service.set_due_date(db, track.id, 1, new, "x", T0)
    assert err.value.code == "fixed_date"
    with pytest.raises(ModulesError):
        service.set_due_date(db, track.id, 2, new, "   ", T0)  # a reason is required


def test_a_date_cannot_jump_over_its_neighbours(db: Session) -> None:
    track = service.start_track(db, cohort(db), "ADD-NOCARRY", "en", T0)
    with pytest.raises(ModulesError):
        service.set_due_date(
            db, track.id, 3, T0.date() + timedelta(days=3), "x", T0
        )  # before module 2
    with pytest.raises(ModulesError):
        service.set_due_date(
            db, track.id, 2, T0.date() + timedelta(days=20), "x", T0
        )  # after module 3


def test_shifting_moves_only_what_is_not_made_and_extends_the_end(db: Session) -> None:
    c = cohort(db)
    track = service.start_track(db, c, "ADD-NOCARRY", "en", T0)
    end = track.end_date
    moved = service.shift_dates(db, c.id, 3, "Diwali week", T0)
    rows = mods(db, track)
    assert moved == 2 and rows[0].due_date == T0.date()
    assert [r.due_date for r in rows[1:]] == [
        T0.date() + timedelta(days=10),
        T0.date() + timedelta(days=17),
    ]
    db.refresh(track)
    assert track.end_date == end + timedelta(days=3)
    earlier = service.shift_dates(db, c.id, -30, "pull forward", T0)
    assert earlier == 2 and all(
        r.due_date >= T0.date() for r in mods(db, track)
    )  # never before a made one


def test_a_missing_template_keeps_the_text_that_was_generated(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    track = service.start_track(db, cohort(db), "ADD-NOCARRY", "en", T0)
    stored = mods(db, track)[0].text
    monkeypatch.setattr(service, "_gone", lambda error, approach: True)
    view = service.track_view(db, track, "hi", T0)
    assert view["modules"][0]["text"] == stored and view["modules"][0]["title"] == stored["title"]


def test_the_text_follows_the_language_asked_for_with_english_fallback(db: Session) -> None:
    track = service.start_track(db, cohort(db), "ADD-NOCARRY", "ta", T0)
    ta = service.track_view(db, track, "ta", T0)["modules"][0]
    assert ta["language"] == "ta" and any(p["fallback"] for p in ta["text"]["parts"])
    assert ta["spoken"].startswith("2") or "தொகுதி" in ta["spoken"]


def test_two_teachers_in_one_cohort_can_be_at_different_modules(db: Session) -> None:
    a = service.start_track(db, cohort(db, "t-a", cid="cc-a"), "ADD-NOCARRY", "en", T0)
    b = service.start_track(db, cohort(db, "t-b", cid="cc-b"), "ADD-NOCARRY", "en", T0)
    service.give_feedback(db, a.id, 1, "t-a", "worked", "", T0)
    service.next_for_teacher(db, a.id, "t-a", at(1))
    assert service.track_view(db, a, "en", at(1))["current"] == 2
    assert service.track_view(db, b, "en", at(1))["current"] == 1


def test_a_teacher_sees_only_her_own_tracks(db: Session) -> None:
    service.start_track(db, cohort(db, "t-a", cid="cc-a"), "ADD-NOCARRY", "en", T0)
    service.start_track(db, cohort(db, "t-b", cid="cc-b"), "ADD-NOCARRY", "en", T0)
    assert [t.teacher_id for t in service.tracks_of(db, "t-a")] == ["t-a"]


def test_the_coach_numbers_hold_no_teacher_id_or_name(db: Session) -> None:
    c = cohort(db)
    track = service.start_track(db, c, "ADD-NOCARRY", "en", T0)
    service.give_feedback(db, track.id, 1, "t-one", "partly", "", T0)
    counts = service.coach_counts(db, c.id, T0)
    flat = repr(counts)
    assert "t-one" not in flat and "teacher" not in flat
    first = counts["modules"][0]
    assert first["generated"] == 1 and first["feedback"] == {
        "worked": 0,
        "partly": 1,
        "not_yet": 0,
        "not_tried": 0,
    }


# ---- a whole track, end to end -------------------------------------------------------------------


def test_a_three_module_track_from_start_to_the_coach_screen(
    factory: sessionmaker[Session],
) -> None:
    # 1. start: Module 1 now, 2 and 3 only planned, with due dates
    with factory() as db:
        c = cohort(db)
        track = service.start_track(db, c, "ADD-NOCARRY", "en", T0)
        tid = track.id
        v = service.track_view(db, track, "en", T0)
        assert [m["status"] for m in v["modules"]] == ["ready", "planned", "planned"]
        assert "text" in v["modules"][0] and "text" not in v["modules"][1]
        assert [m["due_date"] for m in v["modules"]] == [
            at(d).date().isoformat() for d in (0, 7, 14)
        ]
        # 2. feedback "worked", then she gets Module 2
        service.give_feedback(db, tid, 1, "t-one", "worked", "worked with the sticks", at(2))
        got = service.next_for_teacher(db, tid, "t-one", at(3))
        assert got.module is not None and got.module.number == 2 and got.module.branch == "worked"
        # 3. a coach moves Module 3 from day 14 to day 16 (audited)
        service.set_due_date(db, tid, 3, at(16).date(), "school function", at(4))
    # 4. no feedback on Module 2: nothing on day 14, Module 3 on day 16 with no_feedback
    assert jobs.run_due(factory, at(14, 6))["generated"] == 0
    assert jobs.run_due(factory, at(16, 6))["generated"] == 1
    with factory() as db:
        track = db.get(Track, tid)
        assert track is not None
        rows = service.modules_of(db, tid)
        assert [m.status for m in rows] == [states.COMPLETED, states.EXPIRED, states.READY]
        assert [m.branch for m in rows] == ["first", "worked", "no_feedback"]
        assert [m.generated_by for m in rows] == ["start", "teacher", "due_date"]
        assert rows[2].reason and rows[2].reason["code"] == "no_feedback"
        # the timeline the teacher sees
        v = service.track_view(db, track, "en", at(16))
        assert v["current"] == 3 and v["total"] == 3 and v["can_next"]["enabled"] is False
        assert v["can_next"]["code"] == "no_more"
        assert v["modules"][2]["reason_text"].startswith("Module 3 came on its due date")
        # the coach's counts: one teacher at Module 3, Module 1 answered "worked", the date change audited
        counts = service.coach_counts(db, "cc-1", at(16))
        by = {m["number"]: m for m in counts["modules"]}
        assert (
            by[3]["at"] == 1
            and by[1]["feedback"]["worked"] == 1
            and by[2]["feedback"]["worked"] == 0
        )
        assert by[1]["downloaded"] == 0 and by[3]["overdue"] == 0
        assert [e.detail["new"] for e in events(db, track, "due_changed")] == [
            at(16).date().isoformat()
        ]
        # 5. she answers Module 3 (the last): the track completes and says it is time for the next check
        service.give_feedback(db, tid, 3, "t-one", "worked", "", at(17))
        db.refresh(track)
        assert track.status == "completed" and track.stop_reason == "done"
        assert service.track_view(db, track, "en", at(17))["can_next"]["code"] == "track_done"


def test_the_start_date_is_an_indian_calendar_date(db: Session) -> None:
    late = datetime(2026, 11, 2, 20, 0, tzinfo=UTC)  # 01:30 on the 3rd in India
    track = service.start_track(db, cohort(db), "ADD-NOCARRY", "en", late)
    assert track.start_date == date(2026, 11, 3)


def test_the_spoken_text_pauses_after_the_module_line_and_has_no_none_or_off_error_example() -> None:
    from services.api import strings
    from services.modules import library

    intro = strings.text("en", "module.spoken.intro", n=1, total=2, title="Ask the child to explain her steps")
    mt = library.module_text("PV-HEARD", "ask_explain", False, "en")
    spoken = library.spoken(mt, intro)
    assert spoken.startswith("Module 1 of 2. [pause] Ask the child")
    assert "None" not in spoken and "No materials needed." in spoken
    assert "62 - 29" not in spoken and "sixty-two" in spoken
