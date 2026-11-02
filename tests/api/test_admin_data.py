"""Admin: what data exists, the testers' own inputs, and deleting by scope to start fresh. The AI
audit log (the budget's ledger) and the demo's paid-read cache are never deleted from here."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from ai.audit import SqlAuditSink
from services.api.db import AiCall, Base, Feedback, SimObservation, make_engine
from services.api.main import app
from services.api.profiles import get_session
from services.demo.models import DemoAiRead, DemoReadCache, DemoSession
from services.tester.models import TesterDevice, TesterEvent, TesterFeedback


@pytest.fixture
def api(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    monkeypatch.delenv("ADMIN_KEY", raising=False)
    monkeypatch.setenv("ADMIN_OPEN", "1")
    engine = make_engine(f"sqlite:///{tmp_path / 'a.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def override() -> Iterator[Session]:
        with factory() as s:
            yield s

    app.dependency_overrides[get_session] = override
    with factory() as s:
        s.add(Feedback(kind="app", rating=4, text="ok", language="en", role="teacher"))
        s.add(SimObservation(scenario="SUB-SFL", language="en", likeness="like", differences=[]))
        s.add(TesterDevice(device_hash="a" * 64, nickname="Asha"))
        s.add(
            TesterEvent(
                event_id="e1", device_hash="a" * 64, session_id="s", ts=datetime.now(UTC), type="x"
            )
        )
        s.add(
            TesterFeedback(
                device_hash="a" * 64, rating=5, tags=["clear"], comment="easy", role="teacher"
            )
        )
        s.add(DemoSession(id="demo-1", scenario="SUB-SFL", seed=1, class_code="3A", state={}))
        s.add(DemoReadCache(image_hash="h" * 64, cells=[]))
        s.add(
            DemoAiRead(session_id="demo-1", image_hash="h" * 64, sheet="x", boxes=10, boxes_right=9)
        )
        s.commit()
    SqlAuditSink(factory).write(
        call_id=1, call_key="c01_child_voice", prompt_version=1, model="m", mode="live",
        judge=False, metadata_only=True, tokens_in=1, tokens_out=1, tokens_cache_read=0,
        tokens_cache_write=0, cost_usd=0.5, latency_ms=1, validator_results=[],
        checker_verdict=None, checker_reason=None, retries=0, fallback_used=None, input_hash="x",
    )  # fmt: skip
    yield TestClient(app), factory
    app.dependency_overrides.clear()


def counts(client: TestClient) -> dict[str, Any]:
    return dict(client.get("/api/admin/data").json()["scopes"])


def test_the_data_page_counts_each_scope_and_says_what_stays(api: Any) -> None:
    client, _ = api
    body = client.get("/api/admin/data").json()
    assert {k: v["rows"] for k, v in body["scopes"].items()} == {
        "feedback": 1, "observations": 1, "testers": 3, "demo": 2,
    }  # fmt: skip
    assert (
        "audit" in body["kept"]["ai_audit_log"].lower() and "budget" in body["kept"]["ai_audit_log"]
    )
    assert "paid" in body["kept"]["demo_read_cache"]


def test_testers_own_inputs_are_listed_without_a_device_id(api: Any) -> None:
    client, _ = api
    body = client.get("/api/admin/testers").json()
    assert body["devices"] == 1 and body["events"] == 1
    fb = body["feedback"][0]
    assert (fb["rating"], fb["tags"], fb["comment"]) == (5, ["clear"], "easy")
    assert "device_hash" not in fb and "nickname" not in str(body)


def test_deleting_needs_the_word_and_a_known_scope(api: Any) -> None:
    client, _ = api
    assert (
        client.request("DELETE", "/api/admin/data/feedback", json={"confirm": "no"}).status_code
        == 422
    )
    assert client.request("DELETE", "/api/admin/data/feedback", json={}).status_code == 422
    assert (
        client.request("DELETE", "/api/admin/data/ai_calls", json={"confirm": "DELETE"}).status_code
        == 404
    )
    assert counts(client)["feedback"]["rows"] == 1


@pytest.mark.parametrize(
    "scope,gone",
    [("feedback", {"feedback"}), ("observations", {"observations"}), ("testers", {"testers"}),
     ("demo", {"demo"}), ("all", {"feedback", "observations", "testers", "demo"})],
)  # fmt: skip
def test_each_scope_deletes_only_its_own_rows(api: Any, scope: str, gone: set[str]) -> None:
    client, factory = api
    r = client.request("DELETE", f"/api/admin/data/{scope}", json={"confirm": "DELETE"})
    assert r.status_code == 200 and set(r.json()["deleted"]) == gone
    after = counts(client)
    for name, info in after.items():
        assert (info["rows"] == 0) == (name in gone), name
    with factory() as s:  # never touched: the budget's ledger and the paid-read cache
        assert s.query(AiCall).count() == 1
        assert s.query(DemoReadCache).count() == 1


def test_the_admin_key_still_guards_delete(api: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    client, _ = api
    monkeypatch.setenv("ADMIN_KEY", "secret")
    bad = client.request("DELETE", "/api/admin/data/all", json={"confirm": "DELETE"})
    assert bad.status_code == 401
    ok = client.request(
        "DELETE",
        "/api/admin/data/all",
        json={"confirm": "DELETE"},
        headers={"X-Admin-Key": "secret"},
    )
    assert ok.status_code == 200
