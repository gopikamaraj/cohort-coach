"""Tester profiles and usage stats: consent, hashing, masking, exclusion, deletion, retention."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from services.api.db import make_engine
from services.api.main import create_app
from services.api.profiles import get_session
from services.tester.evidence import purge_older_than, sync_change_log
from services.tester.models import (
    ChangeLog,
    TesterDevice,
    TesterEvent,
    TesterFeedback,
    ensure_tester_schema,
)
from services.tester.routes import _DropTesterAccess, mask_contacts

H1 = "a" * 64
H2 = "b" * 64
H3 = "c" * 64
TOKEN = "team-secret"
NOW_MS = int(datetime.now(UTC).timestamp() * 1000)


def profile(h: str = H1, **kw: Any) -> dict[str, Any]:
    return {
        "device_hash": h,
        "consent_stats": True,
        "nickname": "Asha",
        "nickname_public": True,
        "device_class": "phone",
        "language": "en",
        **kw,
    }


def ev(
    i: int, type: str = "screen_viewed", ts: int = NOW_MS, session: str = "sess-0001", **kw: Any
) -> dict[str, Any]:
    return {"event_id": f"ev-{i:06d}", "session_id": session, "ts": ts, "type": type, **kw}


@pytest.fixture
def api(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    monkeypatch.setenv("TESTER_STATS", "1")
    monkeypatch.setenv("JUDGE_MODE", "1")
    monkeypatch.setenv("TESTER_TEAM_TOKEN", TOKEN)
    monkeypatch.setenv("RATE_LIMIT_TESTER_EVENTS_PER_MIN", "0")
    monkeypatch.setenv("RATE_LIMIT_TESTER_OTHER_PER_MIN", "0")
    engine = make_engine(f"sqlite:///{tmp_path / 't.sqlite'}")
    ensure_tester_schema(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def override() -> Iterator[Session]:
        with factory() as s:
            yield s

    app = create_app()
    app.dependency_overrides[get_session] = override
    yield TestClient(app), factory


JUDGE = {"X-Role": "judge"}


def test_no_profile_no_events_no_feedback_without_consent(api: Any) -> None:
    c, factory = api
    assert c.post("/api/tester/profile", json=profile(consent_stats=False)).status_code == 403
    assert (
        c.post("/api/tester/events", json={"device_hash": H1, "events": [ev(1)]}).status_code == 403
    )
    assert c.post("/api/tester/feedback", json={"device_hash": H1, "rating": 4}).status_code == 403
    with factory() as s:
        assert (
            s.query(TesterDevice).count()
            == s.query(TesterEvent).count()
            == s.query(TesterFeedback).count()
            == 0
        )


def test_only_a_64_hex_hash_is_accepted(api: Any) -> None:
    c, _ = api
    uuid = "3f2b8c1e-9d4a-4e6b-8a1f-2c5d7e9b0a13"
    assert c.post("/api/tester/profile", json=profile(uuid)).status_code == 422


def test_profile_rejects_unknown_fields_and_personal_nicknames(api: Any) -> None:
    c, _ = api
    assert c.post("/api/tester/profile", json={**profile(), "email": "a@b.co"}).status_code == 422
    assert (
        c.post("/api/tester/profile", json=profile(nickname="call 98765 43210")).status_code == 422
    )
    assert c.post("/api/tester/profile", json=profile(nickname="a@b.com")).status_code == 422


def test_events_are_idempotent_and_batch_limited(api: Any) -> None:
    c, factory = api
    c.post("/api/tester/profile", json=profile())
    batch = {"device_hash": H1, "events": [ev(1), ev(2), ev(2)]}
    assert c.post("/api/tester/events", json=batch).json() == {"accepted": 2, "duplicates": 1}
    assert c.post("/api/tester/events", json=batch).json() == {"accepted": 0, "duplicates": 3}
    with factory() as s:
        assert s.query(TesterEvent).count() == 2
    big = {"device_hash": H1, "events": [ev(i) for i in range(100, 151)]}
    assert c.post("/api/tester/events", json=big).status_code == 422


def test_events_hold_codes_never_typed_text(api: Any) -> None:
    c, _ = api
    c.post("/api/tester/profile", json=profile())
    bad = {
        "device_hash": H1,
        "events": [
            ev(1, "feature_used", feature_id="chat_question", value={"q": "my phone is 9876543210"})
        ],
    }
    assert c.post("/api/tester/events", json=bad).status_code == 422
    assert (
        c.post(
            "/api/tester/events",
            json={"device_hash": H1, "events": [ev(2, "feature_used", feature_id="has space")]},
        ).status_code
        == 422
    )


def test_comments_are_masked_before_saving(api: Any) -> None:
    c, factory = api
    c.post("/api/tester/profile", json=profile())
    r = c.post(
        "/api/tester/feedback",
        json={
            "device_hash": H1,
            "rating": 5,
            "tags": ["easy", "easy"],
            "comment": "call me on 98765 43210 or mail asha@example.com",
        },
    )
    assert r.status_code == 200
    with factory() as s:
        row = s.query(TesterFeedback).one()
    assert "98765" not in (row.comment or "") and "asha@" not in (row.comment or "")
    assert row.tags == ["easy"]
    assert mask_contacts("+91 98765-43210") == "[number hidden]"


def test_judge_endpoint_refuses_every_other_role(api: Any) -> None:
    c, _ = api
    for role in (None, "teacher", "mentor", "coach", "officer", "admin"):
        h = {"X-Role": role} if role else {}
        assert c.get("/api/judge/testing-evidence", headers=h).status_code == 403
    assert c.get("/api/judge/testing-evidence", headers=JUDGE).status_code == 200


def test_judge_endpoint_needs_the_judge_deployment(
    api: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    c, _ = api
    monkeypatch.setenv("JUDGE_MODE", "0")
    assert c.get("/api/judge/testing-evidence", headers=JUDGE).status_code == 403


def test_team_export_refuses_a_bad_token(api: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    c, _ = api
    assert c.get("/api/team/testing-export").status_code == 403
    assert c.get("/api/team/testing-export", headers={"X-Team-Token": "wrong"}).status_code == 403
    ok = c.get("/api/team/testing-export", headers={"X-Team-Token": TOKEN})
    assert ok.status_code == 200 and ok.text.startswith("date,device6")
    monkeypatch.delenv("TESTER_TEAM_TOKEN")
    assert c.get("/api/team/testing-export", headers={"X-Team-Token": ""}).status_code == 403


def test_empty_state_is_honest(api: Any) -> None:
    c, _ = api
    d = c.get("/api/judge/testing-evidence", headers=JUDGE).json()
    cards = d["cards"]
    assert cards["testers"] == cards["sessions"] == cards["feedback_received"] == 0
    assert (
        cards["date_from"] is None
        and cards["average_rating"] is None
        and cards["offline_share"] is None
    )
    assert (
        d["testers"] == []
        and d["feedback"] == []
        and d["testers_by_day"] == []
        and d["changes"] == []
    )


def _populate(c: TestClient) -> None:
    c.post(
        "/api/tester/profile",
        json=profile(H1, nickname="Asha", nickname_public=True, invite_source="teachers"),
    )
    c.post(
        "/api/tester/profile",
        json=profile(
            H2,
            nickname="Hidden",
            nickname_public=False,
            invite_source="edu-mentor",
            device_class="desktop",
        ),
    )
    c.post("/api/tester/profile", json=profile(H3, nickname="Judy", is_judge=True))
    day = 86_400_000
    c.post(
        "/api/tester/events",
        json={
            "device_hash": H1,
            "events": [
                ev(1, "role_selected", role="teacher"),
                ev(2, "screen_viewed", screen_id="home"),
                ev(3, "feature_used", feature_id="practice_turn"),
                ev(4, "tour_started", tour_id="main"),
                ev(5, "tour_step_viewed", tour_id="main", step_id="1"),
                ev(6, "tour_completed", tour_id="main"),
                ev(7, "offline_session", value={"offline": True}),
                ev(8, "screen_viewed", screen_id="home", ts=NOW_MS - day, session="sess-0002"),
            ],
        },
    )
    c.post(
        "/api/tester/events",
        json={
            "device_hash": H2,
            "events": [ev(20, "role_selected", role="coach", session="sess-0003")],
        },
    )
    c.post(
        "/api/tester/events",
        json={
            "device_hash": H3,
            "events": [
                ev(30, "role_selected", role="judge", session="sess-0004"),
                ev(31, "feature_used", feature_id="x", session="sess-0004"),
            ],
        },
    )
    c.post(
        "/api/tester/feedback",
        json={
            "device_hash": H1,
            "rating": 4,
            "role": "teacher",
            "tags": ["useful"],
            "comment": "Clear",
        },
    )
    c.post("/api/tester/feedback", json={"device_hash": H3, "rating": 1, "comment": "judge note"})


def test_judge_and_team_devices_are_excluded_by_default_and_counted_apart(api: Any) -> None:
    c, _ = api
    _populate(c)
    d = c.get("/api/judge/testing-evidence", headers=JUDGE).json()
    assert d["cards"]["testers"] == 2
    assert d["cards"]["feedback_received"] == 1
    assert d["excluded"] == {"judge_devices": 1, "team_devices": 0}
    assert all(f["comment"] != "judge note" for f in d["feedback"])
    both = c.get("/api/judge/testing-evidence?include_flagged=true", headers=JUDGE).json()
    assert both["cards"]["testers"] == 3 and both["cards"]["feedback_received"] == 2


def test_team_token_tags_a_device_and_a_wrong_token_does_not(api: Any) -> None:
    c, factory = api
    c.post("/api/tester/profile", json=profile(H1, team_token="nope"))
    c.post("/api/tester/profile", json=profile(H2, team_token=TOKEN))
    with factory() as s:
        assert s.get(TesterDevice, H1).is_team is False  # type: ignore[union-attr]
        assert s.get(TesterDevice, H2).is_team is True  # type: ignore[union-attr]


def test_declining_listing_hides_the_nickname_everywhere_a_judge_sees(api: Any) -> None:
    c, _ = api
    _populate(c)
    body = c.get("/api/judge/testing-evidence", headers=JUDGE).text
    assert "Hidden" not in body and "Asha" in body
    names = [
        t["name"] for t in c.get("/api/judge/testing-evidence", headers=JUDGE).json()["testers"]
    ]
    assert "Anonymous tester 01" in names
    csv_text = c.get("/api/team/testing-export", headers={"X-Team-Token": TOKEN}).text
    assert "Hidden" not in csv_text and "Asha" not in csv_text


def test_aggregates_come_from_the_rows(api: Any) -> None:
    c, _ = api
    _populate(c)
    d = c.get("/api/judge/testing-evidence", headers=JUDGE).json()
    k = d["cards"]
    assert (k["sessions"], k["returning_testers"], k["tours_completed"], k["average_rating"]) == (
        3,
        1,
        1,
        4.0,
    )
    assert k["offline_share"] == 0.5 and k["roles_tried_avg"] == 1.0
    assert {s["stage"]: s["testers"] for s in d["role_funnel"]} == {
        "selected": 2,
        "screen": 1,
        "feature": 1,
    }
    assert [x["label"] for x in d["by_source"]] == ["edu-mentor", "teachers"]
    row = next(t for t in d["testers"] if t["listed"])
    assert (
        row["name"] == "Asha"
        and row["hash6"] == "aaaaaa"
        and row["features_used"] == 1
        and row["rating"] == 4.0
    )


def test_delete_my_data_removes_every_row_for_that_hash(api: Any) -> None:
    c, factory = api
    _populate(c)
    assert c.delete("/api/tester/me", headers={"X-Device-Hash": "short"}).status_code == 400
    assert c.delete("/api/tester/me", headers={"X-Device-Hash": H1}).status_code == 200
    with factory() as s:
        for model in (TesterDevice, TesterEvent, TesterFeedback):
            assert s.query(model).filter(model.device_hash == H1).count() == 0
        assert s.query(TesterDevice).count() == 2  # other devices untouched


def test_retention_deletes_records_past_90_days(api: Any) -> None:
    c, factory = api
    c.post("/api/tester/profile", json=profile())
    old = int((datetime.now(UTC) - timedelta(days=91)).timestamp() * 1000)
    c.post("/api/tester/events", json={"device_hash": H1, "events": [ev(1, ts=old), ev(2)]})
    with factory() as s:
        s.add(TesterFeedback(device_hash=H1, ts=datetime.now(UTC) - timedelta(days=95), rating=3))
        s.add(TesterFeedback(device_hash=H1, rating=5))
        s.commit()
        assert purge_older_than(s, datetime.now(UTC), 90) == {"events": 1, "feedback": 1}
        assert s.query(TesterEvent).count() == 1 and s.query(TesterFeedback).count() == 1


def test_nothing_is_mounted_without_the_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TESTER_STATS", "0")
    assert TestClient(create_app()).get("/api/tester/config").status_code == 404
    from services.tester import tester_stats_enabled

    assert tester_stats_enabled() is False


def test_the_view_queries_run(api: Any) -> None:
    c, factory = api
    _populate(c)
    with factory() as s:
        for v in ("v_tester_summary", "v_role_funnel", "v_tour_funnel", "v_daily_activity"):
            s.execute(text(f"SELECT * FROM {v}")).all()
        assert len(s.execute(text("SELECT * FROM v_tester_summary")).all()) == 2


def test_access_log_lines_for_tester_paths_are_dropped() -> None:
    f = _DropTesterAccess()
    mk = lambda msg: logging.LogRecord("uvicorn.access", logging.INFO, "", 0, msg, None, None)  # noqa: E731
    assert f.filter(mk('1.2.3.4 - "POST /api/tester/events HTTP/1.1" 200')) is False
    assert f.filter(mk('1.2.3.4 - "GET /api/health HTTP/1.1" 200')) is True


def test_change_log_loads_from_the_markdown_table(api: Any, tmp_path: Path) -> None:
    _, factory = api
    md = tmp_path / "c.md"
    md.write_text(
        "| date | what we heard | what we changed | commit reference |\n| --- | --- | --- | --- |\n| 2026-10-31 | Text too small | Bigger text | abc1234 |\n",
        encoding="utf-8",
    )
    with factory() as s:
        assert sync_change_log(s, md) == 1
        row = s.query(ChangeLog).one()
        assert (row.feedback_summary, row.commit_ref) == ("Text too small", "abc1234")


def _snapshot_module() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "export_testing_stats",
        Path(__file__).resolve().parents[2] / "scripts" / "export_testing_stats.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def test_snapshot_says_nothing_collected_when_empty(api: Any) -> None:
    _, factory = api
    with factory() as s:
        text = _snapshot_module().snapshot(s)
    assert "Nothing has been collected yet" in text and "| Testers | 0 |" in text
    assert "none yet" in text


def test_snapshot_has_counts_and_dates_but_no_names_hashes_or_comments(api: Any) -> None:
    c, factory = api
    _populate(c)
    with factory() as s:
        text = _snapshot_module().snapshot(s)
    assert "Collected between" in text and "| Testers | 2 |" in text
    for private in ("Asha", "Hidden", "Judy", "aaaaaa", H1, "Clear", "judge note"):
        assert private not in text
