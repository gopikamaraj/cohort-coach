"""Feedback, the admin review page, consent records and erasure (DPDP): anonymous, no child data."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from services.api.db import Base, Consent, Feedback, ProfileSync, make_engine
from services.api.main import app
from services.api.profiles import get_session

GOOD: dict[str, Any] = {
    "kind": "app",
    "rating": 4,
    "text": "The keypad is easy",
    "language": "en",
    "role": "teacher",
}
PROFILE = {
    "term": "T1", "form": "A", "children_checked": 12, "counts": {"SUB-SFL": 5},
    "anchor_wrong_count": 0, "untracked": {}, "simulated": False,
}  # fmt: skip


@pytest.fixture
def api(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    monkeypatch.delenv("ADMIN_KEY", raising=False)
    monkeypatch.setenv("ADMIN_OPEN", "1")  # the open demo mode; the closed default is tested below
    engine = make_engine(f"sqlite:///{tmp_path / 'f.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def override() -> Iterator[Session]:
        with factory() as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app), factory
    app.dependency_overrides.clear()


def test_feedback_is_stored_with_no_identity(api: Any) -> None:
    client, factory = api
    assert client.post("/api/feedback", json=GOOD).json()["stored"] is True
    with factory() as s:
        row = s.query(Feedback).one()
    assert (row.kind, row.rating, row.status, row.text) == ("app", 4, "new", "The keypad is easy")
    assert not hasattr(row, "user_id") and not hasattr(row, "class_id")


@pytest.mark.parametrize(
    "bad",
    [
        {**GOOD, "kind": "other"},
        {**GOOD, "rating": 9},
        {**GOOD, "text": "x" * 501},
        {**GOOD, "role": "root"},
        {**GOOD, "text": "call me on 9876543210"},
        {**GOOD, "text": "mail ravi@example.com"},
        {**GOOD, "extra": "field"},
    ],
)
def test_bad_or_personal_feedback_is_refused(api: Any, bad: dict[str, Any]) -> None:
    client, _ = api
    assert client.post("/api/feedback", json=bad).status_code == 422


def test_a_card_flag_carries_only_the_card(api: Any) -> None:
    client, factory = api
    body = {"kind": "card_flag", "language": "hi", "role": "teacher", "context": "SUB-SFL"}
    assert client.post("/api/feedback", json=body).status_code == 200
    assert client.post("/api/feedback", json={**body, "text": "hi"}).status_code == 422
    with factory() as s:
        assert s.query(Feedback).one().context == "SUB-SFL"


def test_the_admin_sees_feedback_and_simulation_reports_and_can_review(api: Any) -> None:
    client, _ = api
    client.post("/api/feedback", json=GOOD)
    client.post("/api/feedback", json={**GOOD, "kind": "simulation", "rating": 2})
    client.post(
        "/api/practice/observations",
        json={
            "scenario": "SUB-SFL",
            "language": "ta",
            "likeness": "not_like",
            "differences": ["quieter"],
        },
    )
    items = client.get("/api/admin/feedback").json()["items"]
    assert {i["kind"] for i in items} == {"app", "simulation"} and all(
        i["status"] == "new" for i in items
    )
    only = client.get("/api/admin/feedback", params={"kind": "simulation"}).json()["items"]
    assert len(only) == 1
    done = client.patch(
        f"/api/admin/feedback/{only[0]['id']}", json={"status": "reviewed", "note": "tune strength"}
    )
    assert done.json()["status"] == "reviewed"
    assert (
        client.get("/api/admin/feedback", params={"status": "new"}).json()["items"][0]["kind"]
        == "app"
    )
    obs = client.get("/api/admin/observations").json()["items"]
    assert obs == [
        {
            "id": obs[0]["id"],
            "scenario": "SUB-SFL",
            "language": "ta",
            "likeness": "not_like",
            "differences": ["quieter"],
            "created_at": obs[0]["created_at"],
        }
    ]
    summary = client.get("/api/admin/summary").json()
    assert summary["feedback"]["new"] == 1 and summary["feedback"]["reviewed"] == 1
    assert summary["observations"] == 1 and summary["by_kind"] == {"app": 1, "simulation": 1}
    assert client.patch("/api/admin/feedback/9999", json={"status": "reviewed"}).status_code == 404
    assert (
        client.patch(f"/api/admin/feedback/{only[0]['id']}", json={"status": "bogus"}).status_code
        == 422
    )


def test_admin_is_closed_unless_a_key_or_an_explicit_open_flag_is_set(
    api: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _ = api
    monkeypatch.delenv("ADMIN_OPEN")
    assert client.get("/api/admin/feedback").status_code == 503
    assert client.get("/api/admin/summary").status_code == 503
    assert client.patch("/api/admin/feedback/1", json={"status": "reviewed"}).status_code == 503
    monkeypatch.setenv("ADMIN_KEY", "k")  # a key is enough; open mode is ignored once a key exists
    monkeypatch.setenv("ADMIN_OPEN", "1")
    assert client.get("/api/admin/feedback").status_code == 401


def test_admin_endpoints_need_the_key_when_one_is_set(
    api: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _ = api
    monkeypatch.setenv("ADMIN_KEY", "s3cret")
    assert client.get("/api/admin/feedback").status_code == 401
    assert client.get("/api/admin/feedback", headers={"X-Admin-Key": "wrong"}).status_code == 401
    assert client.get("/api/admin/feedback", headers={"X-Admin-Key": "s3cret"}).status_code == 200
    assert client.post("/api/feedback", json=GOOD).status_code == 200  # sending feedback stays open


def test_consent_records_are_kept_under_the_signed_in_user(api: Any) -> None:
    client, factory = api
    body = {"scope": "practice_ai", "granted": True, "version": 1}
    assert client.post("/api/consents", json=body).status_code == 200
    assert client.post("/api/consents", json={**body, "granted": False}).status_code == 200
    assert client.post("/api/consents", json={**body, "scope": "x"}).status_code == 422
    assert client.post("/api/consents", json={**body, "device_id": "a1b2c3d4e5f60718"}).status_code == 422  # a device id is no longer taken: the user is who signed in
    with factory() as s:
        rows = s.query(Consent).order_by(Consent.id).all()
    assert [r.granted for r in rows] == [True, False] and rows[0].scope == "practice_ai.v1"


def test_erasing_a_class_removes_its_counts_from_the_server(api: Any) -> None:
    client, factory = api
    client.post("/api/classes/c-4b7f21a9c3/profile", json=PROFILE)
    client.post("/api/classes/c-aaaaaaaaaa/profile", json=PROFILE)
    assert client.delete("/api/classes/c-4b7f21a9c3").json()["deleted"] == 1
    with factory() as s:
        assert [r.class_id for r in s.query(ProfileSync).all()] == ["c-aaaaaaaaaa"]
    assert client.delete("/api/classes/not-an-id").status_code == 422


def test_context_is_not_a_free_text_channel(api: Any) -> None:
    client, _ = api
    assert (
        client.post("/api/feedback", json={**GOOD, "context": "Ravi-Kumar-class-3"}).status_code
        == 422
    )
    assert client.post("/api/feedback", json={**GOOD, "context": "practice"}).status_code == 200
