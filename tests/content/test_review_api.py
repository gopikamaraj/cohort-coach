"""P09 T06: the review API. The coach's key and the officer's key are separate routes; a role that
does not hold a key cannot turn it; every other role is refused."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from ai.calls.c05_track_draft import draft_part
from ai.client import CallContext
from ai.schemas import TrackPart
from services.api import practice as practice_api
from services.api.db import Base, make_engine
from services.api.main import create_app
from services.api.profiles import get_session
from services.content import drafting, rejections
from services.content.track import load_track
from tests.ai.test_c05_track_draft import GOOD, PASS
from tests.support_ai import FakeClient


@pytest.fixture
def api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, Session]]:
    monkeypatch.setattr(rejections, "PENDING_DIR", tmp_path / "pending")
    engine = make_engine(f"sqlite:///{tmp_path / 'api.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    app = create_app(pilot=False)

    def session() -> Iterator[Session]:
        with factory() as s:
            yield s

    app.dependency_overrides[get_session] = session
    app.dependency_overrides[practice_api.get_ai_context] = lambda: CallContext(
        mode="stub",
        client=FakeClient([PASS] * 20),  # type: ignore[arg-type]
    )
    with factory() as seed:
        yield TestClient(app), seed


def h(role: str) -> dict[str, str]:
    return {"X-Role": role}


def queue(db: Session, day: int = 1) -> str:
    track = load_track("sub-sfl.v1")
    part = TrackPart(kind="lesson", day=day, script=GOOD)
    ctx = CallContext(mode="stub", client=FakeClient([part, PASS]))  # type: ignore[arg-type]
    item = drafting.store_draft(db, draft_part(track, "lesson", day, "en", context=ctx), track)
    assert item is not None
    return item.item_id


def test_a_teacher_or_mentor_cannot_open_the_queue(api: tuple[TestClient, Session]) -> None:
    client, db = api
    queue(db)
    for role in ("teacher", "mentor"):
        assert client.get("/api/review/items", headers=h(role)).status_code == 403


def test_the_coach_and_officer_can_list_and_open_an_item(api: tuple[TestClient, Session]) -> None:
    client, db = api
    item = queue(db)
    for role in ("coach", "officer"):
        rows = client.get("/api/review/items?status=pending", headers=h(role)).json()
        assert [r["item_id"] for r in rows] == [item]
        detail = client.get(f"/api/review/items/{item}", headers=h(role)).json()
        assert detail["script"] == GOOD and detail["results"]


def test_only_the_coach_approves_and_the_officer_cannot(api: tuple[TestClient, Session]) -> None:
    client, db = api
    item = queue(db)
    assert client.post(f"/api/review/items/{item}/approve", headers=h("officer")).status_code == 403
    ok = client.post(f"/api/review/items/{item}/approve", headers=h("coach"))
    assert ok.status_code == 200 and ok.json()["status"] == "approved"


def test_a_rejection_without_a_valid_reason_is_refused(api: tuple[TestClient, Session]) -> None:
    client, db = api
    item = queue(db)
    url = f"/api/review/items/{item}/reject"
    assert client.post(url, json={}, headers=h("coach")).status_code == 422
    assert client.post(url, json={"reason": "meh"}, headers=h("coach")).status_code == 422
    done = client.post(url, json={"reason": "tone_issue", "note": "stern"}, headers=h("coach"))
    assert done.status_code == 200 and done.json()["status"] == "rejected"


def test_an_edit_that_fails_a_check_comes_back_with_the_codes(
    api: tuple[TestClient, Session],
) -> None:
    client, db = api
    item = queue(db)
    bad = GOOD.replace("63 - 28 = 35", "45 - 19 = 26")
    res = client.post(f"/api/review/items/{item}/edit", json={"script": bad}, headers=h("coach"))
    assert res.status_code == 422 and "check_item" in res.json()["detail"]["codes"]
    good = client.post(
        f"/api/review/items/{item}/edit", json={"script": GOOD + " Ok."}, headers=h("coach")
    )
    assert good.status_code == 200 and good.json()["original_script"] == GOOD


def test_the_two_keys_over_http(api: tuple[TestClient, Session]) -> None:
    client, db = api
    track = load_track("sub-sfl.v1")
    for day in range(1, 7):
        item = queue(db, day)
        client.post(f"/api/review/items/{item}/approve", headers=h("coach"))
    model = TrackPart(kind="model_lesson", day=0, script=GOOD)
    ctx = CallContext(mode="stub", client=FakeClient([model, PASS]))  # type: ignore[arg-type]
    part = drafting.store_draft(db, draft_part(track, "model_lesson", 0, "en", context=ctx), track)
    assert part is not None
    client.post(f"/api/review/items/{part.item_id}/approve", headers=h("coach"))

    made = client.post(
        f"/api/review/tracks/{track.id}/assemble", json={"languages": ["en"]}, headers=h("coach")
    )
    assert made.status_code == 200 and made.json()["status"] == "in_review"
    vid = made.json()["id"]
    # the officer cannot activate before the coach approves the set, and the coach cannot activate
    assert (
        client.post(f"/api/review/versions/{vid}/activate", headers=h("officer")).status_code == 409
    )
    assert (
        client.post(f"/api/review/versions/{vid}/approve", headers=h("officer")).status_code == 403
    )
    assert client.post(f"/api/review/versions/{vid}/approve", headers=h("coach")).status_code == 200
    assert (
        client.post(f"/api/review/versions/{vid}/activate", headers=h("coach")).status_code == 403
    )
    on = client.post(f"/api/review/versions/{vid}/activate", headers=h("officer"))
    assert on.status_code == 200 and on.json()["status"] == "active"
    audit = client.get("/api/review/audit", headers=h("officer")).json()
    activate = next(a for a in audit if a["action"] == "activate")
    assert activate["detail"]["coach"] and activate["detail"]["officer"]


def test_assembling_with_a_part_missing_is_refused(api: tuple[TestClient, Session]) -> None:
    client, db = api
    item = queue(db, 1)
    client.post(f"/api/review/items/{item}/approve", headers=h("coach"))
    res = client.post(
        "/api/review/tracks/sub-sfl.v1/assemble", json={"languages": ["en"]}, headers=h("coach")
    )
    assert res.status_code == 409 and "Missing" in res.json()["detail"]


def test_settings_show_their_ranges_and_refuse_a_value_outside(
    api: tuple[TestClient, Session],
) -> None:
    client, _ = api
    shown = client.get("/api/review/settings", headers=h("coach")).json()
    cap = next(s for s in shown["settings"] if s["key"] == "practice_turn_cap")
    assert (cap["low"], cap["high"], cap["value"]) == (20, 40, 40)
    assert {f["key"] for f in shown["fixed"]} >= {"eligibility_min_children", "verdict_rules"}
    out = client.post(
        "/api/review/settings", json={"key": "practice_turn_cap", "value": 90}, headers=h("coach")
    )
    assert out.status_code == 422
    fixed = client.post(
        "/api/review/settings",
        json={"key": "eligibility_min_children", "value": 5},
        headers=h("coach"),
    )
    assert fixed.status_code == 422
    ok = client.post(
        "/api/review/settings", json={"key": "practice_turn_cap", "value": 30}, headers=h("coach")
    )
    assert ok.status_code == 200 and ok.json()["status"] == "in_review"
    # a proposal changes nothing until both keys turn
    again = client.get("/api/review/settings", headers=h("coach")).json()
    assert next(s for s in again["settings"] if s["key"] == "practice_turn_cap")["value"] == 40


def test_the_stats_route_reports_counts_computed_by_code(api: tuple[TestClient, Session]) -> None:
    client, db = api
    item = queue(db)
    client.post(f"/api/review/items/{item}/approve", headers=h("coach"))
    s = client.get("/api/review/stats", headers=h("officer")).json()
    assert s["approved"] == 1 and s["decided"] == 1 and s["acceptance_with_minor_edits"] == 1.0


def test_the_review_routes_do_not_exist_in_pilot_mode(tmp_path: Path) -> None:
    client = TestClient(create_app(pilot=True))
    assert client.get("/api/review/items", headers=h("coach")).status_code == 404


def test_a_rejection_can_be_promoted_to_a_checker_example_by_the_coach_only(
    api: tuple[TestClient, Session], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ai.guard import rejections as guard

    monkeypatch.setattr(guard, "APPROVED_DIR", tmp_path / "approved")
    client, db = api
    item = queue(db)
    client.post(
        f"/api/review/items/{item}/reject", json={"reason": "wrong_maths"}, headers=h("coach")
    )
    waiting = client.get("/api/review/rejections", headers=h("officer")).json()
    assert len(waiting) == 1 and waiting[0]["reason"] == "wrong_maths"
    name = waiting[0]["name"]
    denied = client.post(f"/api/review/rejections/{name}/promote", json={}, headers=h("officer"))
    assert denied.status_code == 403
    ok = client.post(f"/api/review/rejections/{name}/promote", json={}, headers=h("coach"))
    assert ok.status_code == 200 and "wrong_maths" in guard.examples_block()
    assert client.get("/api/review/rejections", headers=h("coach")).json() == []


def test_a_rejection_name_cannot_reach_another_file(api: tuple[TestClient, Session]) -> None:
    client, _ = api
    for bad in ("..%2Fsecret", "x", "2026-10-26-001.yaml"):
        res = client.post(f"/api/review/rejections/{bad}/discard", headers=h("coach"))
        assert res.status_code in (404, 422), bad
    assert (
        client.post("/api/review/rejections/2026-10-26-001/discard", headers=h("coach")).status_code
        == 404
    )


def test_the_officer_publishes_an_active_version_for_a_cohort(
    api: tuple[TestClient, Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    from services.content import publish
    from services.pilot.storage import LocalBlobStore, get_audio_store
    from services.speech.service import SpeechService
    from tests.content.test_publish import approve_all, fake_join

    client, db = api
    monkeypatch.setattr(publish, "join_to_file", fake_join)
    store = LocalBlobStore(b"audio")
    speech = SpeechService("stub")
    speech.synthesize = lambda text, lang, voice: b"clip"  # type: ignore[method-assign]
    app = client.app  # type: ignore[attr-defined]
    app.dependency_overrides[get_audio_store] = lambda: store
    app.dependency_overrides[practice_api.get_speech] = lambda: speech
    v = approve_all(db)
    cohort = publish.cohorts_for_error("SUB-SFL")[0]
    url = f"/api/review/versions/{v.id}/publish"
    assert client.post(url, json={"cohort_id": cohort}, headers=h("officer")).status_code == 409
    client.post(f"/api/review/versions/{v.id}/approve", headers=h("coach"))
    client.post(f"/api/review/versions/{v.id}/activate", headers=h("officer"))
    assert client.post(url, json={"cohort_id": cohort}, headers=h("coach")).status_code == 403
    done = client.post(url, json={"cohort_id": cohort}, headers=h("officer"))
    assert done.status_code == 200 and len(done.json()["parts"]) == 7
    listed = client.get(f"/api/review/manifests?version_id={v.id}", headers=h("coach")).json()
    assert listed[0]["cohort_id"] == cohort
