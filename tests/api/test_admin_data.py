# ruff: noqa: E501
"""Admin: what data exists, the testers' own inputs, and deleting by scope to start fresh. The AI
audit log (the budget's ledger) and the demo's paid-read cache are never deleted from here."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime
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
    rows = {k: v["rows"] for k, v in body["scopes"].items()}
    assert {k: rows[k] for k in ("feedback", "observations", "testers", "demo")} == {
        "feedback": 1, "observations": 1, "testers": 3, "demo": 2,
    }  # fmt: skip
    assert set(rows) == {
        "feedback", "observations", "testers", "demo", "papers", "results", "modules",
        "cohorts", "cohort_chat", "cohort_spaces", "intervention",
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
    assert r.status_code == 200
    deleted = r.json()["deleted"]
    assert {k for k, n in deleted.items() if n} == gone  # only what was there is counted
    assert set(deleted) == (set(counts(client)) if scope == "all" else {scope})
    after = counts(client)
    for name in ("feedback", "observations", "testers", "demo"):  # the scopes this test seeded
        assert (after[name]["rows"] == 0) == (name in gone), name
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


def test_every_table_is_in_a_scope_or_kept_for_a_stated_reason(api: Any) -> None:
    from services.api.admin_data import KEPT_TABLES, SCOPES
    from services.api.db import Base

    scoped = {m.__tablename__ for models in SCOPES.values() for m in models}
    every = set(Base.metadata.tables)
    assert every - scoped - set(KEPT_TABLES) == set(), "a new table needs a scope or a reason to stay"
    assert scoped & set(KEPT_TABLES) == set() and (scoped | set(KEPT_TABLES)) <= every
    assert all(KEPT_TABLES.values())


def test_deleting_papers_frees_a_paper_with_a_sheet_entered_and_all_clears_every_scope(api: Any) -> None:
    from services.api.db import ClassCohort
    from services.modules.models import Track
    from services.papers.models import PaperEvent

    client, factory = api
    with factory() as s:
        s.add(PaperEvent(event="frozen", actor="t", paper_id="paper-x", detail="first sheet entered"))
        s.add(ClassCohort(id="cc-1", teacher_id="t-1", check_id="c:1", name="n", errors=["SUB-SFL"], counts={"SUB-SFL": 3}, children_checked=10))
        s.add(Track(id="tr-1", class_cohort_id="cc-1", teacher_id="t-1", error="SUB-SFL", language="en", start_date=date(2026, 11, 2), end_date=date(2026, 12, 2)))
        s.commit()
    before = counts(client)
    assert before["papers"]["rows"] == 1 and before["cohorts"]["rows"] == 1 and before["modules"]["rows"] == 1
    r = client.request("DELETE", "/api/admin/data/papers", json={"confirm": "DELETE"})
    assert r.status_code == 200 and r.json()["deleted"] == {"papers": 1}
    r = client.request("DELETE", "/api/admin/data/all", json={"confirm": "DELETE"})
    assert r.status_code == 200
    assert all(v["rows"] == 0 for v in counts(client).values())
