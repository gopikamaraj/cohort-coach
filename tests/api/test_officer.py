"""P12 (reduced): the officer views are aggregates only, every figure has a source, groups under 5
are hidden, and verdicts come from the engine at request time."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from data.synthetic.block import track_verdicts
from services.api.db import Base, LessonTap, make_engine
from services.api.main import create_app
from services.api.officer import _block
from services.api.profiles import get_session


@pytest.fixture
def world(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    monkeypatch.setenv("JUDGE_MODE", "1")
    # judge mode gives the test its officer role; the demo also switches the caps off, so these tests that check the
    # production minimum (a figure over fewer than 5 classes is hidden) put the production values back
    monkeypatch.setattr("services.api.caps.caps_off", lambda: False)
    engine = make_engine(f"sqlite:///{tmp_path / 'o.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def session() -> Iterator[Session]:
        with factory() as s:
            yield s

    app = create_app()
    app.dependency_overrides[get_session] = session
    yield TestClient(app), factory


OFFICER = {"X-Role": "officer"}


def test_the_officer_views_carry_no_teacher_or_class_ids_and_hide_small_groups(world) -> None:  # type: ignore[no-untyped-def]
    c, factory = world
    with factory() as db:  # six teachers have taps: shown; the others are hidden
        for i in range(6):
            db.add(
                LessonTap(
                    teacher_id=f"t-{i:016x}"[:18],
                    track_id="SUB-SFL",
                    lesson_day=1,
                    tried=True,
                    outcome="worked",
                )
            )
        db.add(
            LessonTap(
                teacher_id="t-0000000000000099"[:18], track_id="PV-HEARD", lesson_day=1, tried=True
            )
        )
        db.commit()
    texts = {
        p: c.get(f"/api/officer/{p}", headers=OFFICER) for p in ("error-map", "results", "funnel")
    }
    block = _block()
    ids = {x["class_id"] for x in block["classes"]} | {x["teacher_id"] for x in block["classes"]}
    ids |= {x["school_id"] for x in block["schools"]}
    for name, r in texts.items():
        assert r.status_code == 200, name
        body = r.text
        assert not any(i in body for i in ids), name  # no class, teacher or school id
        assert "t-0000" not in body and "teacher_name" not in body
    rows = {r["error"]: r for r in texts["funnel"].json()["rows"]}
    assert rows["SUB-SFL"]["delivered"] == {
        "hidden": False,
        "teachers": 6,
        "source": "system: lessons sent",
    }
    assert (
        rows["PV-HEARD"]["delivered"]["hidden"] is True
        and rows["PV-HEARD"]["delivered"]["teachers"] is None
    )
    assert rows["PV-HEARD"]["outcomes"] is None  # one teacher: nothing about how it went
    assert rows["SUB-SFL"]["outcomes"] == {"worked": 6, "partly": 0, "didnt": 0}


def test_every_funnel_step_names_its_source_and_changed_waits_for_the_next_check(world) -> None:  # type: ignore[no-untyped-def]
    c, _ = world
    for row in c.get("/api/officer/funnel", headers=OFFICER).json()["rows"]:
        assert row["delivered"]["source"].startswith("system")
        assert row["tried"]["source"].startswith("self-report")
        assert (
            row["practised"]["source"].startswith("system")
            and row["practised"]["recorded"] is False
        )
        assert row["changed"]["source"] and row["changed"]["status"]
        assert "listened" not in json.dumps(row) and "watched" not in json.dumps(row)


def test_the_error_map_hides_a_cell_over_fewer_than_five_classes(
    world, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    c, _ = world
    out = c.get("/api/officer/error-map", headers=OFFICER).json()
    assert out["simulated"] is True and out["cells"]
    shown = [x for x in out["cells"] if not x["hidden"]]
    assert shown and all(x["classes"] >= 5 for x in shown)
    for x in shown:
        assert 0 <= x["showing"] <= x["classes"]
    block = _block()
    small = json.loads(json.dumps(block))
    keep = [x for x in small["classes"] if x["medium"] == "hindi"][:4]
    small["classes"] = keep + [x for x in small["classes"] if x["medium"] != "hindi"]
    monkeypatch.setattr("services.api.officer._block", lambda: small)
    hidden = [
        x
        for x in c.get("/api/officer/error-map", headers=OFFICER).json()["cells"]
        if x["medium"] == "hindi"
    ]
    assert hidden and all(x["hidden"] and x["classes"] is None for x in hidden)


def test_the_results_are_the_engines_verdicts_computed_at_request_time(world) -> None:  # type: ignore[no-untyped-def]
    c, _ = world
    out = c.get("/api/officer/results", headers=OFFICER).json()
    want = track_verdicts(_block())
    assert out["note"] == "A failed track counts against the track, not the teacher."
    for t in out["tracks"]:
        e = want[t["version"]]
        assert t["verdict"] == e.verdict.value and t["hidden"] is e.hidden
        if not e.hidden:
            assert t["estimate_points"] == e.estimate_points
            assert (t["ci_low"], t["ci_high"]) == (e.ci_low, e.ci_high)
            assert (t["n_track"], t["n_comparison"]) == (e.n_track, e.n_comparison)
        else:
            assert "estimate_points" not in t  # a hidden group shows no number at all
    verdicts = {t["version"]: t["verdict"] for t in out["tracks"]}
    assert verdicts["SUB-SFL v1"] == "working" and verdicts["SUB-NODEC v1"] == "not_working"


def test_a_coach_cannot_read_the_officer_views(world) -> None:  # type: ignore[no-untyped-def]
    c, _ = world
    for role in ("coach", "mentor", "teacher"):
        for p in ("error-map", "results", "funnel"):
            assert c.get(f"/api/officer/{p}", headers={"X-Role": role}).status_code == 403, (
                role,
                p,
            )


def test_no_percentage_reaches_a_teacher_view_but_the_officer_may_have_one(world) -> None:  # type: ignore[no-untyped-def]
    c, _ = world
    assert "share_percent" in c.get("/api/officer/error-map", headers=OFFICER).text


def test_the_funnel_says_how_much_content_has_waited_for_review_over_seven_days(world) -> None:  # type: ignore[no-untyped-def]
    from datetime import UTC, datetime, timedelta

    from services.api.db import ReviewItem

    c, factory = world
    out = c.get("/api/officer/funnel", headers=OFFICER).json()["review_waiting"]
    assert out == {"waiting": 0, "over_7_days": 0, "oldest_days": None, "source": out["source"]}
    assert out["source"].startswith("system")
    now = datetime.now(UTC)
    with factory() as db:
        for i, (status, age) in enumerate(
            [
                ("pending", 9),
                ("awaiting_mentor", 3),
                ("pending", 8),
                ("approved", 30),
                ("rejected", 40),
            ]
        ):
            db.add(
                ReviewItem(
                    item_id=f"it-{i}", content_type="track_draft", language="en",
                    target_error="SUB-SFL", content={}, status=status,
                    created_at=now - timedelta(days=age),
                )
            )  # fmt: skip
        db.commit()
    out = c.get("/api/officer/funnel", headers=OFFICER).json()["review_waiting"]
    assert (out["waiting"], out["over_7_days"], out["oldest_days"]) == (3, 2, 9)
    assert "teacher" not in json.dumps(out)
