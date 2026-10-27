"""P10: T4 (track and lessons, two taps), T6 (my result), the schedule, the time budget, lesson
audio links, and what the content gate rejects."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api import strings
from services.api.db import LessonTap, ProfileSync, Teacher, TrackManifest
from services.api.flows.engine import FlowEngine
from services.api.flows.links import verify
from services.api.time_budget import (
    WEEKLY_CAP_MINUTES,
    WeekMinutes,
    check_lesson_length,
    median_minutes,
    weekly_minutes,
)
from services.content import lessons_view
from tests.flows.test_engine import CLASS, DEVICE, add_profile, onboard

SCRIPT = "Take 52 minus 29 with bundles of ten. Open one bundle and count again."
COUNTS = {"SUB-SFL": 11, "PV-HEARD": 0, "SUB-NODEC": 0, "ADD-NOCARRY": 0, "PV-REVERSE": 0}


def publish_fake(db: Session, language: str = "en", *, simulated: bool = True) -> TrackManifest:
    parts = [
        {
            "id": f"p{d}", "kind": "lesson", "day": d, "language": language,
            "audio_key": f"k{d}", "mime": "audio/ogg", "bytes": 100_000, "seconds": 120.0,
            "sha256": "x", "script": f"Lesson {d}. {SCRIPT}", "badge": "checked_reviewed",
        }
        for d in range(1, 7)
    ] + [
        {
            "id": "pm", "kind": "model_lesson", "day": 0, "language": language,
            "audio_key": None, "mime": None, "bytes": 0, "seconds": 0.0, "sha256": "y",
            "script": "Model lesson. " + SCRIPT, "badge": "checked_reviewed",
        }
    ]  # fmt: skip
    row = TrackManifest(
        version_id="v1",
        cohort_id="c1",
        body={"error": "SUB-SFL", "track_id": "sub-sfl.v1", "simulated": simulated, "parts": parts},
    )
    db.add(row)
    db.commit()
    return row


def judge(db: Session, lang: str = "en") -> tuple[FlowEngine, Teacher]:
    eng = FlowEngine(db)
    t = eng.teacher_for("telegram", "555", judge=True)
    onboard(eng, t, lang)
    return eng, t


def option_ids(eng: FlowEngine, t: Teacher) -> list[str]:
    return [o.id for o in eng.start(t).steps[-1].options]


def test_the_menu_offers_the_track_only_when_one_is_published(db: Session) -> None:
    eng, t = judge(db)
    assert "track" not in option_ids(eng, t)
    publish_fake(db)
    assert "track" in option_ids(eng, t)


def test_a_track_that_is_not_published_says_it_is_being_prepared(db: Session) -> None:
    from services.api.flows.t4 import _intro_build  # entered by hand: there is no menu option

    eng, t = judge(db)
    from services.api.flows.engine import Ctx

    step = _intro_build(Ctx(db, t, {}, eng))
    assert step.copy == "t4.none"
    assert "coach has to approve" in strings.render(step, "en")


def test_a_judge_gets_lesson_one_at_once_with_the_voice_note_and_the_badge(db: Session) -> None:
    publish_fake(db)
    eng, t = judge(db)
    steps = eng.answer(t, "menu", "track").steps
    assert [s.id for s in steps] == ["intro", "lesson", "tried"]
    lesson = steps[1]
    assert lesson.kind == "media" and lesson.audio and "/api/lessons/audio?t=" in lesson.audio
    assert lesson.badge == "lesson.badge" and lesson.simulated  # simulated data is labelled
    text = strings.render(lesson, "en")
    assert "Lesson 1 of 6" in text and "52 minus 29" in text and "%" not in text
    assert verify(lesson.audio.split("t=", 1)[1]) == {"m": 1, "p": "p1"}  # no person in a link


def test_two_taps_are_stored_per_lesson_as_self_report(db: Session) -> None:
    publish_fake(db)
    eng, t = judge(db)
    eng.answer(t, "menu", "track")
    assert eng.answer(t, "tried", "yes").steps[-1].id == "how"
    steps = eng.answer(t, "how", "partly").steps
    assert [s.id for s in steps] == ["thanks", "next"]
    row = db.execute(select(LessonTap)).scalar_one()
    assert (row.teacher_id, row.track_id, row.lesson_day, row.tried, row.outcome) == (
        t.teacher_id, "SUB-SFL", 1, True, "partly",
    )  # fmt: skip
    assert "your own report" in strings.render(steps[0], "en")
    steps = eng.answer(t, "next", "next").steps
    assert steps[0].params["day"] == 2 and steps[-1].id == "tried"
    eng.answer(t, "tried", "notyet")  # "not yet" stores no outcome
    rows = db.execute(select(LessonTap).order_by(LessonTap.lesson_day)).scalars().all()
    assert [(r.lesson_day, r.tried, r.outcome) for r in rows] == [
        (1, True, "partly"),
        (2, False, None),
    ]


def test_no_flow_text_says_listened_or_watched_or_scores_the_teacher() -> None:
    for lang in ("en", "hi", "ta"):
        for key in ("t4.thanks", "t4.tried", "t4.how", "t6.fail", "t6.result", "t4.intro"):
            text = strings.text(lang, key).lower()
            assert "listened" not in text and "watched" not in text and "score" not in text
            assert "%" not in text


def test_the_last_lesson_ends_at_the_next_check_and_offers_the_model_lesson(db: Session) -> None:
    publish_fake(db)
    eng, t = judge(db)
    eng.answer(t, "menu", "track")
    last = eng.start(t).steps[-1]
    for day in range(1, 7):
        steps = eng.answer(t, "tried", "notyet").steps
        last = steps[-1]
        assert last.id == "next"
        if day < 6:
            eng.answer(t, "next", "next")
    ids = [o.id for o in last.options]
    assert "next" not in ids and "model" in ids and last.copy == "t4.done"
    model = eng.answer(t, "next", "model").steps
    assert model[0].id == "model" and "Model lesson" in strings.render(model[0], "en")
    rehearse = eng.answer(t, "next", "rehearse").steps[-1]
    assert rehearse.kind == "link" and rehearse.link and "/practice?t=" in (rehearse.link.url or "")


def test_a_real_teacher_gets_two_lessons_a_week() -> None:
    started = datetime(2026, 11, 2, tzinfo=UTC)
    cases = [(1, 0), (2, 2), (2, 3), (3, 6), (3, 7), (4, 10), (5, 14), (6, 16), (6, 17)]
    due = [lessons_view.due_day(d, started, started + timedelta(days=n)) for d, n in cases]
    assert due == [True, False, True, False, True, True, True, False, True]
    assert lessons_view.days_until(2, started, started) == 3
    assert lessons_view.days_until(2, started, started + timedelta(days=5)) == 0


def test_a_real_teacher_is_told_when_the_next_lesson_comes(db: Session) -> None:
    publish_fake(db)
    eng = FlowEngine(db)
    t = eng.teacher_for("pwa", DEVICE)
    onboard(eng, t, "en")
    t.class_id = CLASS
    add_profile(db, COUNTS)
    steps = eng.answer(t, "menu", "track").steps
    assert steps[-1].id == "tried"
    eng.answer(t, "tried", "notyet")
    steps = eng.answer(t, "next", "next").steps
    assert [s.id for s in steps][-2:] == ["later", "next"]
    assert "Lesson 2 comes in 3 days" in strings.render(steps[-2], "en")


def test_my_result_is_counts_with_no_percentage_and_no_comparison(db: Session) -> None:
    eng, t = judge(db)
    assert "result" in option_ids(eng, t)
    steps = eng.answer(t, "menu", "result").steps
    assert [s.id for s in steps][-3:-1] == ["result", "fail_note"]
    text = " ".join(strings.render(s, "en") for s in steps)
    assert re.search(r"\d+ of \d+ children", text) and "%" not in text
    assert "A failed track counts against the track, not you." in text
    assert not re.search(r"other teachers|average|compared|better than", text, re.I)
    assert steps[-1].id == "menu"


def test_a_real_teacher_sees_her_result_only_after_two_checks(db: Session) -> None:
    eng = FlowEngine(db)
    t = eng.teacher_for("pwa", DEVICE)
    onboard(eng, t, "en")
    t.class_id = CLASS
    add_profile(db, COUNTS)
    assert "result" not in option_ids(eng, t)
    db.add(
        ProfileSync(class_id=CLASS, term="T2", form="B", children_checked=27,
                    counts={"SUB-SFL": 4}, anchor_wrong_count=0, untracked={}, simulated=False)
    )  # fmt: skip
    db.commit()
    assert "result" in option_ids(eng, t)
    text = " ".join(strings.render(s, "en") for s in eng.answer(t, "menu", "result").steps)
    assert "11 of 28 children" in text and "4 of 27" in text and "%" not in text


def test_deleting_my_data_removes_my_taps(db: Session) -> None:
    publish_fake(db)
    eng, t = judge(db)
    eng.answer(t, "menu", "track")
    eng.answer(t, "tried", "yes")
    assert db.execute(select(LessonTap)).first() is not None
    eng.delete(t)
    assert db.execute(select(LessonTap)).first() is None


def test_the_content_gate_rejects_a_lesson_over_five_minutes() -> None:
    assert check_lesson_length(299.0) == []
    assert [v.code for v in check_lesson_length(301.0)] == ["lesson_too_long"]


def test_weekly_minutes_add_up_the_lessons_she_tapped_this_week(db: Session) -> None:
    now = datetime(2026, 11, 4, 10, tzinfo=UTC)  # a Wednesday
    secs = {("SUB-SFL", 1): 240.0, ("SUB-SFL", 2): 180.0, ("SUB-SFL", 3): 200.0}

    def tap(day: int, tried: bool, when: datetime) -> None:
        db.add(
            LessonTap(
                teacher_id="t-a", track_id="SUB-SFL", lesson_day=day, tried=tried, updated_at=when
            )
        )

    tap(1, True, now)
    tap(2, True, now - timedelta(days=1))
    tap(3, False, now)  # not tried: no minutes
    tap(4, True, now - timedelta(days=10))  # last week: not counted
    db.commit()
    w = weekly_minutes(db, "t-a", secs, now=now, practice_seconds=300.0)
    assert (w.lessons_minutes, w.practice_minutes, w.total) == (7.0, 5.0, 12.0)
    assert not w.over_cap and WEEKLY_CAP_MINUTES == 20
    assert weekly_minutes(db, "t-a", secs, now=now, practice_seconds=900.0).over_cap
    assert median_minutes([]) is None
    two = [WeekMinutes("a", 0, 0, 10.0, False), WeekMinutes("b", 0, 0, 14.0, False)]
    assert median_minutes(two) == 12.0
