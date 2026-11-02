"""P10: the lesson journey reads the same in the web app and in Telegram and leaves the same state;
the Telegram adapter turns a lesson into a voice note; the audio link serves only listed audio."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from services.api.channels import telegram
from services.api.channels.base import Message
from services.api.channels.telegram.webhook import requests_for
from services.api.db import Base, LessonTap, make_engine
from services.api.main import create_app
from services.api.profiles import get_session
from services.media.storage import LocalBlobStore, get_audio_store
from tests.channels.test_golden import DEVICE, Fake, _msg, shape
from tests.flows.test_t4 import publish_fake

JOURNEY = [
    ("lang", "en"),
    ("consent_core", "agree"),
    ("consent_counts", "yes"),
    ("consent_practice", "no"),
    ("consent_feedback", "yes"),
    ("menu", "track"),
    ("tried", "yes"),
    ("how", "worked"),
    ("next", "next"),
    ("tried", "notyet"),
    ("next", "model"),
    ("next", "back"),
    ("menu", "result"),
]


@pytest.fixture
def world(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[tuple[TestClient, sessionmaker[Session], LocalBlobStore]]:
    monkeypatch.setenv("JUDGE_MODE", "1")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://api.example.test")
    engine = make_engine(f"sqlite:///{tmp_path / 't4.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    store = LocalBlobStore(b"s")

    def override() -> Iterator[Session]:
        with factory() as s:
            yield s

    app = create_app()
    app.dependency_overrides[get_session] = override
    app.dependency_overrides[get_audio_store] = lambda: store
    with factory() as db:
        publish_fake(db)
    yield TestClient(app), factory, store


def web(client: TestClient) -> list[list[tuple]]:  # type: ignore[type-arg]
    h = {"X-Device-Id": DEVICE, "X-Judge": "1"}
    out = [client.get("/api/flow/current", headers=h).json()["messages"]]
    for step_id, value in JOURNEY:
        r = client.post("/api/flow/answer", headers=h, json={"step_id": step_id, "value": value})
        assert r.status_code == 200, r.text
        out.append(r.json()["messages"])
    return [[shape(_msg(m)) for m in turn] for turn in out]


def tg(db: Session) -> list[list[tuple]]:  # type: ignore[type-arg]
    out = []
    fake = Fake()
    telegram.process(db, {"message": {"chat": {"id": 42}, "text": "/start judge"}}, fake)
    out.append([shape(m) for m in fake.sent])
    for i, (step_id, value) in enumerate(JOURNEY):
        fake = Fake()
        cb = {"id": str(i), "data": f"{step_id}:{value}", "message": {"chat": {"id": 42}}}
        telegram.process(db, {"callback_query": cb}, fake)
        out.append([shape(m) for m in fake.sent])
    return out


def test_the_lesson_journey_reads_the_same_in_the_web_app_and_in_telegram(world) -> None:  # type: ignore[no-untyped-def]
    client, factory, _ = world
    w = web(client)
    with factory() as db:
        t = tg(db)
    # the signed audio link differs per request (it carries an expiry): compare without it
    assert w == t and all(w)


def test_both_channels_leave_the_same_taps(world) -> None:  # type: ignore[no-untyped-def]
    client, factory, _ = world
    web(client)
    with factory() as db:
        tg(db)
        rows = db.query(LessonTap).order_by(LessonTap.teacher_id, LessonTap.lesson_day).all()
        shapes = {}
        for r in rows:
            shapes.setdefault(r.teacher_id, []).append((r.lesson_day, r.tried, r.outcome))
    assert len(shapes) == 2
    a, b = shapes.values()
    assert a == b == [(1, True, "worked"), (2, False, None)]


def test_telegram_sends_a_lesson_as_a_voice_note_with_its_words_as_the_caption() -> None:
    m = Message(
        step_id="lesson", kind="media", text="Lesson 1 of 6\n\nHello", audio="https://x.test/a.ogg"
    )
    ((method, fields, files),) = requests_for(m, "42")
    assert method == "sendVoice" and files == {}
    assert fields["voice"] == "https://x.test/a.ogg" and fields["caption"].startswith("Lesson 1")


def test_a_long_lesson_goes_as_a_voice_note_and_then_a_message() -> None:
    m = Message(step_id="lesson", kind="media", text="x" * 1500, audio="https://x.test/a.ogg")
    calls = requests_for(m, "42")
    assert [c[0] for c in calls] == ["sendVoice", "sendMessage"]
    assert "caption" not in calls[0][1] and calls[1][1]["text"] == "x" * 1500


def test_the_lesson_audio_link_serves_only_listed_audio_and_expires(world) -> None:  # type: ignore[no-untyped-def]
    client, factory, store = world
    store.put("k1", b"OggS-fake", "audio/ogg")
    from services.api.flows.links import sign

    good = sign({"m": 1, "p": "p1"})
    ok = client.get(f"/api/lessons/audio?t={good}")
    assert (
        ok.status_code == 200
        and ok.content == b"OggS-fake"
        and ok.headers["content-type"] == "audio/ogg"
    )
    assert client.get("/api/lessons/audio?t=junk").status_code == 404
    assert client.get(f"/api/lessons/audio?t={sign({'m': 1, 'p': 'nope'})}").status_code == 404
    assert (
        client.get(f"/api/lessons/audio?t={sign({'m': 1, 'p': 'pm'})}").status_code == 404
    )  # no audio
    assert client.get(f"/api/lessons/audio?t={sign({'m': 99, 'p': 'p1'})}").status_code == 404
    assert (
        client.get(f"/api/lessons/audio?t={sign({'m': 1, 'p': 'p1'}, ttl_s=-5)}").status_code == 404
    )
