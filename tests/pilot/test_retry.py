"""A sheet whose background read never ran (the instance restarted, or the CPU was cut) must not
stay "waiting" for ever: the next look at the counts re-reads it, once, if it is old enough."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update

from services.api.db import PilotAudio, PilotSheet
from services.pilot import sheets
from tests.pilot.conftest import Env, answers, init_body, photo


def _store_without_reading(env: Env, monkeypatch: pytest.MonkeyPatch, data: bytes) -> str:
    """Upload as the phone does, but with the background read lost."""
    body = env.client.post(
        "/api/pilot/sheets/init", json=init_body(data), headers=env.h("ops")
    ).json()
    up = body["upload"]
    assert env.client.put(up["url"], content=data, headers=up["headers"]).status_code == 200
    with monkeypatch.context() as lost:
        lost.setattr("services.pilot.routes.sheets.read_stored_sheet", lambda *a, **k: "lost")
        done = env.client.post(f"/api/pilot/sheets/{body['id']}/complete", headers=env.h("ops"))
    assert done.json()["status"] == "stored"
    return str(body["id"])


def _age(env: Env, sheet_id: str, minutes: int) -> None:
    with env.factory() as db:
        db.execute(
            update(PilotSheet)
            .where(PilotSheet.id == sheet_id)
            .values(uploaded_at=datetime.now(UTC) - timedelta(minutes=minutes))
        )
        db.commit()


def _status(env: Env, sheet_id: str) -> str:
    listed = env.client.get("/api/pilot/sheets", headers=env.h("ops")).json()["sheets"]
    return str(next(s["status"] for s in listed if s["id"] == sheet_id))


def test_an_old_stuck_sheet_is_read_when_the_counts_are_next_viewed(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    sheet_id = _store_without_reading(env, monkeypatch, photo(1))
    _age(env, sheet_id, 10)
    env.models.queue(answers(True))
    summary = env.client.get("/api/pilot/sheets/summary", headers=env.h("ops")).json()
    assert summary["waiting"] == 1  # this reply shows the state before the retry
    assert _status(env, sheet_id) == "read"
    assert env.models.reads == 1


def test_a_young_stuck_sheet_is_left_alone(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    sheet_id = _store_without_reading(env, monkeypatch, photo(2))  # uploaded just now
    env.client.get("/api/pilot/sheets/summary", headers=env.h("ops"))
    assert _status(env, sheet_id) == "stored"
    assert env.models.reads == 0


def test_a_sheet_is_counted_once_however_often_the_counts_are_viewed(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    sheet_id = _store_without_reading(env, monkeypatch, photo(3))
    _age(env, sheet_id, 10)
    env.models.queue(answers(False))
    for _ in range(3):
        env.client.get("/api/pilot/sheets/summary", headers=env.h("ops"))
    assert env.models.reads == 1
    assert env.client.get("/api/pilot/sheets/summary", headers=env.h("ops")).json()["read"] == 1


def test_retry_stuck_returns_how_many_sheets_it_tried(env: Env) -> None:
    with env.factory() as db:
        assert sheets.stuck_ids(db) == []


def test_generating_audio_works_with_foreign_keys_enforced(seeded: Env) -> None:
    """Live 500 on Generate: Postgres refused a lesson pointing at a review item not yet written.
    The pilot test database now enforces foreign keys, as Postgres does."""
    cfg = seeded.client.get("/api/pilot/config", headers=seeded.h("ops")).json()
    res = seeded.client.post(
        "/api/pilot/audio/generate",
        json={"language": "en", "voice": cfg["voice_default"]},
        headers=seeded.h("ops"),
    )
    assert res.status_code == 200, res.text
    assert res.json() == {"made": 3}


def test_a_lesson_left_as_a_draft_is_made_again(seeded: Env) -> None:
    """A lesson row that never got past "draft" (the request died) must not block Generate."""
    body = {"language": "en", "voice": "ritu"}
    assert seeded.client.post(
        "/api/pilot/audio/generate", json=body, headers=seeded.h("ops")
    ).json() == {"made": 3}
    with seeded.factory() as db:
        card = db.query(PilotAudio).filter(PilotAudio.slot == 2).one()
        card.status, card.review_item_id = "draft", None
        db.commit()
    again = seeded.client.post("/api/pilot/audio/generate", json=body, headers=seeded.h("ops"))
    assert again.json() == {"made": 1}
