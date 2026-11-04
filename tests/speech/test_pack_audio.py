"""Download audio for the intervention pack (autopilot Part F): the endpoint makes an MP3 from the
text the teacher is reading, once, keeps one voice per file, caches, enforces a per-phone cap,
and never logs a key or the text. Every test uses a scripted provider; no network."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from services.api import pack_audio
from services.api.db import Base, make_engine
from services.api.main import create_app
from services.api.practice import get_speech
from services.api.profiles import get_session
from services.media.storage import get_audio_store
from services.speech import lessons
from tests.speech.test_lessons import Scripted, Speech, Store

DEV = f"{7:016x}"
HEAD = {"X-Role": "teacher", "X-User": DEV}
TEXT = "Take 703 − 468 with bundles. The child writes 365.\n\nThe correct answer is 235."


class World:
    def __init__(self, client: TestClient, speech: Speech, store: Store) -> None:
        self.client, self.speech, self.store = client, speech, store


@pytest.fixture(autouse=True)
def fake_mp3(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lessons, "encode_mp3", lambda wav, kbps: b"ID3" + wav[44:400])


def make(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *providers: Scripted) -> Iterator[World]:
    monkeypatch.setenv("JUDGE_MODE", "1")
    engine = make_engine(f"sqlite:///{tmp_path / 'api.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def session() -> Iterator[Session]:
        with factory() as s:
            yield s

    speech, store = Speech(*providers), Store()
    app = create_app()
    app.dependency_overrides[get_session] = session
    app.dependency_overrides[get_speech] = lambda: speech
    app.dependency_overrides[get_audio_store] = lambda: store
    yield World(TestClient(app), speech, store)


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[World]:
    yield from make(tmp_path, monkeypatch, Scripted("bodhan"))


def post(w: World, text: str = TEXT, language: str = "en", name: str = "intervention-sub-sfl-en"):  # type: ignore[no-untyped-def]
    return w.client.post(
        "/api/audio/pack", json={"text": text, "language": language, "name": name}, headers=HEAD
    )


def test_pressing_the_button_returns_an_mp3_named_for_the_error_and_language(world: World) -> None:
    r = post(world)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "audio/mpeg"
    assert 'filename="intervention-sub-sfl-en.mp3"' in r.headers["content-disposition"]
    assert r.content.startswith(b"ID3") and len(r.content) > 100
    assert r.headers["x-audio-provider"] == "bodhan" and float(r.headers["x-audio-seconds"]) > 0
    assert r.headers["cache-control"] == "no-store"


def test_a_sum_is_never_split_inside(world: World) -> None:
    post(world)
    said = " ".join(world.speech.chain.providers["bodhan"].said)  # type: ignore[attr-defined]
    assert "703 − 468" in said and "703." not in said


def test_a_repeat_press_makes_no_call_and_costs_no_characters(world: World) -> None:
    first = post(world)
    calls = world.speech.chain.providers["bodhan"].calls  # type: ignore[attr-defined]
    again = post(world)
    assert again.status_code == 200 and again.headers["x-audio-cached"] == "1"
    assert again.content == first.content
    assert world.speech.chain.providers["bodhan"].calls == calls  # type: ignore[attr-defined]
    cap = world.client.get("/api/audio/pack/cap", headers=HEAD).json()
    assert cap["used"] == int(first.headers["x-audio-chars"])


def test_the_cap_per_phone_is_enforced_and_said_plainly(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AUDIO_DOWNLOAD_CHARS_PER_DEVICE", "40")
    r = post(world)
    assert r.status_code == 429 and r.json()["detail"]["code"] == "cap"
    assert world.speech.chain.providers["bodhan"].calls == 0  # type: ignore[attr-defined]


def test_the_cap_falls_back_to_the_autopilot_variable_then_20000(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AUDIO_DOWNLOAD_CHARS_PER_DEVICE", raising=False)
    monkeypatch.delenv("AUTOPILOT_MAX_TTS_CHARS", raising=False)
    assert pack_audio.chars_cap() == 20000
    monkeypatch.setenv("AUTOPILOT_MAX_TTS_CHARS", "1234")
    assert pack_audio.chars_cap() == 1234


def test_if_the_first_provider_fails_midway_the_whole_file_is_made_again_on_the_next(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    long = " ".join(f"Sentence number {i} is here for the test." for i in range(14))
    for w in make(
        tmp_path, monkeypatch, Scripted("bodhan", fail_on={2, 3, 4, 5}), Scripted("sarvam")
    ):
        r = post(w, long)
        assert r.status_code == 200 and r.headers["x-audio-provider"] == "sarvam"
        said = w.speech.chain.providers["sarvam"].said  # type: ignore[attr-defined]
        assert (
            " ".join(said).count("Sentence number") == 14
        )  # every sentence, one voice, one provider


def test_when_every_provider_fails_the_answer_is_a_plain_503_and_nothing_is_kept(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    for w in make(tmp_path, monkeypatch, Scripted("bodhan", fail_on=set(range(1, 40)))):
        r = post(w)
        assert r.status_code == 503 and r.json()["detail"]["code"] == "unavailable"
        assert not w.store.data or all(not k.startswith("pack-audio/") for k in w.store.data)
        assert "703" not in caplog.text and "bundles" not in caplog.text  # the text is never logged


def test_a_bad_request_is_refused(world: World) -> None:
    assert post(world, text="").status_code == 422
    assert post(world, language="fr").status_code == 422
    assert post(world, text="x" * 9000).status_code == 422
    bad = post(world, name="../../etc/passwd")  # a hostile file name becomes the plain default
    assert 'filename="audio.mp3"' in bad.headers["content-disposition"]


def test_it_needs_the_device_id(world: World) -> None:
    r = world.client.post(
        "/api/audio/pack",
        json={"text": "Hello there.", "language": "en"},
        headers={"X-Role": "teacher"},
    )
    assert r.status_code == 422
