# ruff: noqa: E501
"""The chat over HTTP: the server enforces every role; nothing returned names a person."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from services.api.cohorts import lifecycle
from services.api.db import Base, make_engine
from services.api.main import create_app
from services.api.profiles import get_session
from services.chat.draft import DraftOutcome
from services.cohort_chat import service

COACH, MENTOR, OFFICER = "coach-demo", "mentor-demo", "officer-demo"
DEV_A, DEV_B, DEV_X = f"{1:016x}", f"{2:016x}", f"{9:016x}"


def h(role: str, device: str | None = None) -> dict[str, str]:
    out = {"X-Role": role}
    who = device or (f"{role}-demo" if role != "teacher" else None)  # a staff account is a user too
    if who:
        out["X-User"] = who
    return out


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, sessionmaker[Session], str]]:
    monkeypatch.setenv("JUDGE_MODE", "1")
    monkeypatch.setenv("AI_MODE", "live")
    engine = make_engine(f"sqlite:///{tmp_path / 'api.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def session() -> Iterator[Session]:
        with factory() as s:
            yield s

    with factory() as s:
        c = lifecycle.create(s, error="SUB-SFL", coach_id=COACH, mentor_ids=[MENTOR], officer_id=OFFICER, simulated=False, cohort_id="co-api")
        lifecycle.transition(s, c.id, "active", role="officer", actor=OFFICER)
    app = create_app()
    app.dependency_overrides[get_session] = session
    client = TestClient(app)
    for dev in (DEV_A, DEV_B):
        assert client.post("/api/cohorts/co-api/join", json={"consent": True}, headers=h("teacher", dev)).status_code == 200
    yield client, factory, "co-api"


def test_a_teacher_asks_and_everyone_in_the_cohort_sees_it_with_labels_only(env) -> None:
    client, _f, cid = env
    r = client.post(f"/api/cohort-chat/{cid}/messages", json={"kind": "question", "text": "How do I show borrowing with bundles?", "language": "en"}, headers=h("teacher", DEV_A))
    assert r.status_code == 200, r.text
    for who, dev in (("teacher", DEV_B), ("mentor", None), ("coach", None)):
        view = client.get(f"/api/cohort-chat/{cid}", headers=h(who, dev)).json()
        assert [m["kind"] for m in view["messages"]] == ["question"]
        assert view["messages"][0]["author"].startswith("Teacher ")
        assert view["timeout"] == {"seconds": 5, "source": "demo"}
        assert DEV_A not in str(view) and DEV_B not in str(view)


def test_outsiders_and_officers_are_refused_and_the_roles_are_enforced_on_the_server(env) -> None:
    client, _f, cid = env
    assert client.get(f"/api/cohort-chat/{cid}", headers=h("teacher", DEV_X)).status_code == 403
    assert client.get(f"/api/cohort-chat/{cid}", headers=h("officer")).status_code == 403
    q = client.post(f"/api/cohort-chat/{cid}/messages", json={"kind": "question", "text": "A question about tens?"}, headers=h("teacher", DEV_A)).json()["id"]
    assert client.post(f"/api/cohort-chat/{cid}/messages/{q}/resolve", headers=h("teacher", DEV_A)).status_code == 403
    assert client.post(f"/api/cohort-chat/{cid}/messages/{q}/resolve", headers=h("mentor")).status_code == 200
    assert client.put(f"/api/cohort-chat/{cid}/timeout", json={"seconds": 30}, headers=h("mentor")).status_code == 403
    assert client.put(f"/api/cohort-chat/{cid}/timeout", json={"seconds": 3}, headers=h("coach")).status_code == 422
    assert client.put(f"/api/cohort-chat/{cid}/timeout", json={"seconds": 30}, headers=h("coach")).json() == {"seconds": 30}
    assert client.post(f"/api/cohort-chat/{cid}/messages", json={"kind": "tip", "text": "x" * 501}, headers=h("teacher", DEV_A)).status_code == 422


def test_the_ai_answers_a_question_nobody_answers_then_the_coach_corrects_it_and_the_mentor_cancels_a_second(env) -> None:
    client, factory, cid = env
    q1 = client.post(f"/api/cohort-chat/{cid}/messages", json={"kind": "question", "text": "How do I show borrowing with bundles?"}, headers=h("teacher", DEV_A)).json()["id"]
    q2 = client.post(f"/api/cohort-chat/{cid}/messages", json={"kind": "question", "text": "Do I teach place value first?"}, headers=h("teacher", DEV_A)).json()["id"]
    assert client.post(f"/api/cohort-chat/{cid}/messages", json={"kind": "reply", "text": "Start with bundles.", "reply_to": q2}, headers=h("mentor")).status_code == 200
    good = DraftOutcome("drafted", text="Open one bundle to get ten loose sticks.", sources=[{"id": "S.a.1", "kind": "strategy", "title": "Open a bundle", "quote": "x"}], checker={"passed": True})
    with factory() as s:
        made = service.tick(s, now=datetime.now(UTC) + timedelta(seconds=30), drafter=lambda db, **kw: good)
    assert len(made) == 1  # q2 was answered by the mentor in time
    view = client.get(f"/api/cohort-chat/{cid}", headers=h("teacher", DEV_B)).json()
    ai = next(m for m in view["messages"] if m["kind"] == "ai_reply")
    assert ai["reply_to"] == q1 and "Source: Open a bundle" in ai["text"] and ai["ai_label"] == "ai"
    assert client.post(f"/api/cohort-chat/{cid}/messages/{ai['id']}/correct", json={"text": "Use the strategy cards first."}, headers=h("mentor")).status_code == 403
    assert client.post(f"/api/cohort-chat/{cid}/messages/{ai['id']}/correct", json={"text": "Use the strategy cards first."}, headers=h("coach")).status_code == 200
    kinds = [m["kind"] for m in client.get(f"/api/cohort-chat/{cid}", headers=h("teacher", DEV_B)).json()["messages"]]
    assert kinds.count("correction") == 1 and kinds.count("ai_reply") == 1


def test_the_inbox_is_for_mentors_and_coaches(env) -> None:
    client, _f, cid = env
    client.post(f"/api/cohort-chat/{cid}/messages", json={"kind": "question", "text": "A question about tens?"}, headers=h("teacher", DEV_A))
    assert client.get("/api/cohort-chat/inbox", headers=h("teacher", DEV_A)).status_code == 403
    body = client.get("/api/cohort-chat/inbox", headers=h("coach")).json()
    assert body["count"] == 1 and body["items"][0]["author"].startswith("Teacher ")
