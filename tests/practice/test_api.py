from __future__ import annotations

import time
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ai.audit import SqlAuditSink
from ai.client import BudgetExceeded, CallContext
from services.api import practice as api
from services.api.judge import get_sink
from services.api.main import app
from services.practice.stub_client import StubClient


@pytest.fixture
def client(sink: SqlAuditSink) -> Iterator[TestClient]:
    app.dependency_overrides[api.get_ai_context] = lambda: CallContext(
        mode="stub", sink=sink, client=StubClient()
    )
    app.dependency_overrides[get_sink] = lambda: sink
    api._SESSIONS.clear()
    yield TestClient(app)
    app.dependency_overrides.clear()
    api._SESSIONS.clear()


def create(client: TestClient, **kw: object) -> dict:  # type: ignore[type-arg]
    body = {"scenario": "SUB-SFL", "language": "en", "seed": 5, **kw}
    res = client.post("/api/practice/sessions", json=body)
    assert res.status_code == 200, res.text
    return res.json()  # type: ignore[no-any-return]


def test_create_session_returns_children_materials_and_the_cap(client: TestClient) -> None:
    body = create(client)
    assert len(body["children"]) == 5 and sum(c["shy"] for c in body["children"]) == 1
    assert "error" not in str(body["children"])  # the teacher is not told who has which error
    assert body["materials"] == ["bundles", "sticks", "chart"] and body["turn_cap"] == 40
    assert {"id": "ask_explain", "label": "Asks the child to explain her steps"} in body["moves"]


def test_a_full_rehearsal_over_the_api(client: TestClient) -> None:
    s = create(client)
    sid, name = s["session_id"], s["children"][1]["name"]
    for text in (f"{name}, what is 52 minus 29?", "Tell me how you got that.",
                 "Here is 52 as 5 bundles and 2 sticks."):  # fmt: skip
        res = client.post(f"/api/practice/sessions/{sid}/turns", json={"text": text})
        assert res.status_code == 200, res.text
        turn = res.json()
        assert turn["child_text"] and set(turn["layers"]) == {
            "input", "processing", "guardrails", "evaluation", "output",
        }  # fmt: skip
        assert turn["badge"] == "checked" and "latency_ms" in turn and turn["turns_left"] > 0
    res = client.post(f"/api/practice/sessions/{sid}/end")
    assert res.status_code == 200, res.text
    out = res.json()
    assert len(out["card"]["strengths"]) == 2 and out["card"]["badge"] == "checked"
    assert [t["turn"] for t in out["transcript"]] == [1, 2, 3]
    assert "gate" not in out["card"]


def test_taps_work_and_unknown_materials_are_422(client: TestClient) -> None:
    sid = create(client)["session_id"]
    res = client.post(f"/api/practice/sessions/{sid}/turns", json={"material": "bundles"})
    assert res.status_code == 200 and res.json()["label"]["source"] == "material tap"
    assert (
        client.post(f"/api/practice/sessions/{sid}/turns", json={"material": "laser"}).status_code
        == 422
    )
    assert client.post(f"/api/practice/sessions/{sid}/turns", json={}).status_code == 422


def test_unknown_inputs_get_plain_errors(client: TestClient) -> None:
    assert client.post("/api/practice/sessions", json={"scenario": "NOPE"}).status_code == 422
    assert client.post("/api/practice/sessions", json={"language": "fr"}).status_code == 422
    assert client.post("/api/practice/sessions/nope/turns", json={"text": "x"}).status_code == 404
    assert client.post("/api/practice/sessions/nope/end").status_code == 404
    long = client.post("/api/practice/sessions/x/turns", json={"text": "a" * 1001})
    assert long.status_code == 422


def test_the_session_caps_at_40_turns_and_then_says_so(client: TestClient) -> None:
    sid = create(client, judge=True)["session_id"]
    for _ in range(40):
        res = client.post(
            f"/api/practice/sessions/{sid}/turns", json={"text": "well done, good job"}
        )
        assert res.status_code == 200
    assert res.json()["finished"] and res.json()["finished_reason"] == "turn_cap"
    res = client.post(f"/api/practice/sessions/{sid}/turns", json={"text": "more"})
    assert res.status_code == 409 and "finished" in res.json()["detail"]
    assert (
        client.post(f"/api/practice/sessions/{sid}/end").status_code == 200
    )  # feedback still works


def test_class_counts_seat_the_children(client: TestClient) -> None:
    create(client, counts={"SUB-SFL": 10}, checked=25)
    session = next(iter(api._SESSIONS.values()))[0]
    assert (
        sum(c.error is not None and c.error.value == "SUB-SFL" for c in session.state.children) == 2
    )


def test_sessions_expire(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    sid = create(client)["session_id"]
    real = time.time
    monkeypatch.setattr(api.time, "time", lambda: real() + api.SESSION_TTL_S + 5)
    res = client.post(f"/api/practice/sessions/{sid}/turns", json={"text": "hello"})
    assert res.status_code == 404 and "expired" in res.json()["detail"]


def test_a_spent_budget_returns_a_plain_503(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    sid = create(client)["session_id"]

    def boom(*a: object, **k: object) -> None:
        raise BudgetExceeded("daily")

    monkeypatch.setattr(api, "take_turn", boom)
    res = client.post(f"/api/practice/sessions/{sid}/turns", json={"text": "hello"})
    assert res.status_code == 503 and "paused" in res.json()["detail"]


def test_nothing_is_written_to_disk_but_audit_metadata(
    client: TestClient, sink: SqlAuditSink
) -> None:
    sid = create(client)["session_id"]
    secret = "my private words 9876543210"
    client.post(f"/api/practice/sessions/{sid}/turns", json={"text": secret})
    audit = client.get("/api/judge/audit?limit=20")
    assert (
        audit.status_code == 200 and "9876543210" not in audit.text and "private" not in audit.text
    )
