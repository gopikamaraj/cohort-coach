"""Both speech providers down: the demo path still plays lessons and template lines from the cache
and always shows the text. And nothing secret or personal reaches a log or a stored record: no
audio, no transcript, no key. Mock providers only; no network."""

from __future__ import annotations

import base64
import json
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ai.client import CallContext
from services.api import practice as practice_api
from services.api.db import Base, TrackManifest, make_engine
from services.api.flows.t4 import audio_url
from services.api.main import create_app
from services.api.profiles import get_session
from services.content import lesson_audio, publish, versions
from services.media.storage import LocalBlobStore, get_audio_store
from services.practice.stub_client import StubClient
from services.speech import audio, lessons, tts
from services.speech.bodhan import BodhanClient, BodhanProvider
from services.speech.chain import ProviderChain
from services.speech.service import SpeechService
from services.speech.voices import Voice
from tests.content.test_publish import COACH, OFFICER, approve_all, fake_mp3
from tests.speech.bodhan_mock import SPEAK_KEY, TRANSCRIBE_KEY, BodhanMock
from tests.speech.test_lessons import Scripted, Speech
from tests.speech.test_practice_voice import Voiced

BIG = "SUB-SFL-g3-hindi-X-1"


@pytest.fixture
def world(tmp_path: Path) -> Iterator[tuple[TestClient, Session, LocalBlobStore]]:
    engine = make_engine(f"sqlite:///{tmp_path / 'o.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    app = create_app()
    store = LocalBlobStore(b"o")

    def session() -> Iterator[Session]:
        with factory() as s:
            yield s

    app.dependency_overrides[get_session] = session
    app.dependency_overrides[get_audio_store] = lambda: store
    app.dependency_overrides[practice_api.get_ai_context] = lambda: CallContext(
        mode="stub", client=StubClient()
    )
    with factory() as db:
        yield TestClient(app), db, store


def test_with_both_providers_down_lessons_and_template_lines_play_and_the_text_shows(
    world: tuple[TestClient, Session, LocalBlobStore], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, db, store = world
    monkeypatch.setattr(lessons, "encode_mp3", fake_mp3)
    # before the outage: publish (lessons voiced and cached) and say one child line once
    v = approve_all(db)
    versions.coach_approve(db, v.id, *COACH)
    versions.officer_activate(db, v.id, *OFFICER)
    up = Speech(Scripted("bodhan"), Scripted("sarvam"))
    publish.publish_version(db, v.id, BIG, store=store, speech=up)
    tts.CACHE._items.clear()
    line_up = SpeechService(
        "live",
        log=lambda **kw: None,
        cache_store=store,
        providers=ProviderChain({"bodhan": Voiced("bodhan")}, order=lambda f, lang: ["bodhan"]),
    )
    line_up.synthesize_ex(
        "I think it is 23.", "en", Voice("anushka", 1.2, 1.0), bodhan_voice="Suhani"
    )

    # the outage: neither provider has a key
    down = Speech(Scripted("bodhan", configured=False), Scripted("sarvam", configured=False))
    tts.CACHE._items.clear()
    m = db.execute(select(TrackManifest)).scalar_one()
    part = next(p for p in m.body["parts"] if p["kind"] == "lesson")
    url = audio_url(m.id, part)
    assert url is not None
    res = client.get("/api/lessons/audio?" + url.split("?", 1)[1])
    assert res.status_code == 200 and res.content[:3] == b"ID3"  # the lesson plays from storage
    again = lessons.generate(part["script"], part["language"], down, store)
    assert again.from_cache  # a demo lesson rebuilt from its cached chunks with no provider
    line_down = SpeechService(
        "live",
        log=lambda **kw: None,
        cache_store=store,
        providers=ProviderChain({}, order=lambda f, lang: []),
    )
    _, who = line_down.synthesize_ex(
        "I think it is 23.", "en", Voice("anushka", 1.2, 1.0), bodhan_voice="Suhani"
    )
    assert who == "cache"  # a template line said before plays with no provider

    # Practice: voice falls back to typing, and the text is always shown
    client.app.dependency_overrides[practice_api.get_speech] = lambda: line_down  # type: ignore[attr-defined]
    sid = client.post(
        "/api/practice/sessions", json={"scenario": "SUB-SFL", "language": "en", "seed": 5}
    ).json()["session_id"]
    voice = client.post(
        f"/api/practice/sessions/{sid}/voice-turn",
        files={"audio": ("c.wav", audio.tone(1.0, 300), "audio/wav")},
    )
    assert voice.status_code == 503 and voice.json()["detail"]["text_mode"] is True
    typed = client.post(
        f"/api/practice/sessions/{sid}/turns", json={"text": "Priya, what is 52 minus 29?"}
    )
    assert typed.status_code == 200 and typed.json()["child_text"]


def test_no_audio_transcript_or_key_reaches_a_log_or_a_stored_record(
    world: tuple[TestClient, Session, LocalBlobStore],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    client, db, store = world
    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(lessons, "encode_mp3", fake_mp3)
    heard = "Rahul please open a bundle"  # what the mock "hears": must never be logged or stored
    mock = BodhanMock()
    bodhan = BodhanProvider(
        BodhanClient(
            speak_key=SPEAK_KEY,
            transcribe_key=TRANSCRIBE_KEY,
            client=mock.client(),
            sleep=lambda s: None,
        )
    )

    class Ears(Voiced):
        def transcribe(self, wav: bytes, language: str):  # type: ignore[no-untyped-def]
            return super().transcribe(wav, language)

    rows: list[dict[str, object]] = []
    chain = ProviderChain(
        {"bodhan": bodhan, "sarvam": Ears("sarvam", heard=heard)},
        order=lambda f, lang: ["bodhan", "sarvam"],
    )
    svc = SpeechService(
        "live", log=lambda **kw: rows.append(kw), providers=chain, cache_store=store
    )
    client.app.dependency_overrides[practice_api.get_speech] = lambda: svc  # type: ignore[attr-defined]
    sid = client.post(
        "/api/practice/sessions", json={"scenario": "SUB-SFL", "language": "en", "seed": 5}
    ).json()["session_id"]
    recording = audio.tone(1.2, 300)
    body = client.post(
        f"/api/practice/sessions/{sid}/voice-turn",
        files={"audio": ("c.wav", recording, "audio/wav")},
    ).json()
    assert body["heard"]  # what was heard comes back to her screen only
    logged = caplog.text
    for secret in (SPEAK_KEY, TRANSCRIBE_KEY, body["heard"], body["child_text"]):
        assert secret not in logged
    assert base64.b64encode(recording[:64]).decode()[:24] not in logged and "RIFF" not in logged
    allowed = {
        "stage",
        "mode",
        "language",
        "latency_ms",
        "audio_bytes",
        "characters",
        "seconds",
        "cost_inr",
        "from_cache",
        "error_kind",
    }
    assert rows and all(set(r) <= allowed for r in rows)  # metadata rows only
    assert all(
        not isinstance(v, (bytes, bytearray)) and v != body["heard"]
        for r in rows
        for v in r.values()
    )
    # stored records: lesson audio keeps the lesson text it voiced, never what a check heard back
    v = approve_all(db)
    versions.coach_approve(db, v.id, *COACH)
    versions.officer_activate(db, v.id, *OFFICER)
    publish.publish_version(
        db, v.id, BIG, store=store, speech=Speech(Scripted("bodhan", heard_as="garbled words"))
    )
    rec = db.execute(select(lesson_audio.LessonAudioRecord)).scalars().first()
    assert rec is not None
    stored = str(rec.checks) + str(rec.chunks) + str(rec.sentences)
    assert "garbled" not in stored
    assert all("cer" in c and "heard" not in c for c in rec.checks)
    for key in store.keys():
        if key.endswith(".check"):
            assert set(json.loads(store.get(key))) == {"cer"}  # a score, never the words heard
