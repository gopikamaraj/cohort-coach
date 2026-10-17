"""POST /voice-turn with stub or mocked speech and the stub AI client: no network, no paid calls."""

from __future__ import annotations

import base64
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from ai.audit import SqlAuditSink
from ai.client import CallContext
from services.api import practice as api
from services.api.judge import get_sink
from services.api.main import app
from services.practice.stub_client import StubClient
from services.speech.health import CircuitBreaker
from services.speech.sarvam import SarvamClient, SpeechError
from services.speech.service import SpeechService
from services.speech.voices import Voice

AUDIO = {"audio": ("clip.webm", b"not-really-audio" * 50, "audio/webm")}


class Rows:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = []

    def __call__(self, **kw: Any) -> None:
        self.rows.append(kw)


@pytest.fixture
def rows() -> Rows:
    return Rows()


@pytest.fixture
def client(sink: SqlAuditSink, rows: Rows) -> Iterator[TestClient]:
    app.dependency_overrides[api.get_ai_context] = lambda: CallContext(
        mode="stub", sink=sink, client=StubClient()
    )
    app.dependency_overrides[get_sink] = lambda: sink
    app.dependency_overrides[api.get_speech] = lambda: SpeechService("stub", log=rows)
    api._SESSIONS.clear()
    yield TestClient(app)
    app.dependency_overrides.clear()
    api._SESSIONS.clear()


def session(client: TestClient, lang: str = "en") -> str:
    res = client.post(
        "/api/practice/sessions", json={"scenario": "SUB-SFL", "language": lang, "seed": 5}
    )
    return str(res.json()["session_id"])


def test_voice_turn_returns_heard_text_audio_and_stage_timings(
    client: TestClient, rows: Rows
) -> None:
    sid = session(client)
    res = client.post(f"/api/practice/sessions/{sid}/voice-turn", files=AUDIO)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["heard"] and body["child_text"] and body["speech_mode"] == "stub"
    assert body["audio_mime"] == "audio/ogg" and body["audio"]
    stages = body["layers"]["evaluation"]["stages"]
    assert set(stages) == {"stt_ms", "tts_wait_ms"}
    assert rows.rows[0]["stage"] == "stt" and "tts" in {r["stage"] for r in rows.rows}


def test_speech_rows_hold_metadata_only(client: TestClient, rows: Rows) -> None:
    sid = session(client)
    body = client.post(f"/api/practice/sessions/{sid}/voice-turn", files=AUDIO).json()
    assert rows.rows and {r["stage"] for r in rows.rows} <= {"stt", "tts"}
    blob = repr(rows.rows)
    assert body["heard"] not in blob and body["child_text"] not in blob
    allowed = {
        "stage", "mode", "language", "latency_ms", "audio_bytes", "characters", "seconds",
        "cost_inr", "from_cache", "error_kind",
    }  # fmt: skip
    assert all(set(r) <= allowed for r in rows.rows)


def test_no_speech_service_means_text_mode_not_a_hang(client: TestClient) -> None:
    app.dependency_overrides[api.get_speech] = lambda: SpeechService(
        "live", client=SarvamClient(""), log=lambda **kw: None
    )
    sid = session(client)
    res = client.post(f"/api/practice/sessions/{sid}/voice-turn", files=AUDIO)
    assert res.status_code == 503 and res.json()["detail"]["text_mode"] is True


def test_three_failed_transcriptions_open_the_breaker(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Broken(SarvamClient):
        def transcribe(self, *a: Any, **k: Any) -> Any:
            raise SpeechError("unavailable", 503)

    svc = SpeechService("live", client=Broken("k"), log=lambda **kw: None)
    svc.breaker = CircuitBreaker()
    app.dependency_overrides[api.get_speech] = lambda: svc
    sid = session(client)
    from services.speech import audio as audio_mod

    wav = audio_mod.tone(1, 200, 16000)  # skip ffmpeg: the client is the thing under test
    monkeypatch.setattr(audio_mod, "to_wav16k", lambda b: wav)
    for _ in range(3):
        res = client.post(f"/api/practice/sessions/{sid}/voice-turn", files=AUDIO)
        assert res.status_code == 503
    assert svc.breaker.state == "open" and not svc.available
    res = client.post(f"/api/practice/sessions/{sid}/voice-turn", files=AUDIO)
    assert res.status_code == 503 and res.json()["detail"]["text_mode"] is True


def test_a_failed_synthesis_still_returns_the_text(client: TestClient) -> None:
    class NoVoice(SpeechService):
        def synthesize(self, text: str, lang: str, voice: Voice) -> bytes:
            raise SpeechError("timeout")

    app.dependency_overrides[api.get_speech] = lambda: NoVoice("stub", log=lambda **kw: None)
    sid = session(client)
    res = client.post(f"/api/practice/sessions/{sid}/voice-turn", files=AUDIO)
    body = res.json()
    assert res.status_code == 200 and body["child_text"] and body["audio"] is None


def test_audio_is_released_only_when_the_line_passes_the_checker(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    spoken: list[str] = []

    class Spy(SpeechService):
        def synthesize(self, text: str, lang: str, voice: Voice) -> bytes:
            spoken.append(text)
            return (
                b"OggS-" + text.encode()
            )  # distinct bytes per line, so the audio says what was voiced

    app.dependency_overrides[api.get_speech] = lambda: Spy("stub", log=lambda **kw: None)
    sid = session(client)
    ok = client.post(f"/api/practice/sessions/{sid}/voice-turn", files=AUDIO).json()
    assert ok["badge"] == "checked"
    assert base64.b64decode(ok["audio"]) == b"OggS-" + ok["child_text"].encode()

    held = SimpleNamespace(
        releasable=False, verdict=None, checker=None, explanation="Held back.", badge=None
    )
    monkeypatch.setattr("ai.calls.c01_child_voice.run_gates", lambda *a, **k: held)
    monkeypatch.setattr("ai.calls.c01_child_voice.render_line", lambda *a, **k: "Template line.")
    spoken.clear()
    out = client.post(f"/api/practice/sessions/{sid}/voice-turn", files=AUDIO).json()
    assert out["badge"] == "none"
    sent = base64.b64decode(out["audio"])
    assert out["child_text"] == "Template line."
    assert sent == b"OggS-Template line."  # the template line is what she hears
    assert sent != b"OggS-" + ok["child_text"].encode()  # never the AI candidate


def test_a_finished_session_does_not_pay_for_speech_to_text(client: TestClient) -> None:
    class Counting(SpeechService):
        calls = 0

        def transcribe(self, recording: bytes, lang: str) -> str:
            Counting.calls += 1
            return "Well done"

    app.dependency_overrides[api.get_speech] = lambda: Counting("stub", log=lambda **kw: None)
    sid = session(client)
    api._SESSIONS[sid][0].ended = True
    res = client.post(f"/api/practice/sessions/{sid}/voice-turn", files=AUDIO)
    assert res.status_code == 409 and Counting.calls == 0


def test_over_long_audio_is_refused_before_it_is_sent(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from services.speech import audio as audio_mod

    long_wav = audio_mod.tone(31, 200, 16000)
    monkeypatch.setattr(audio_mod, "to_wav16k", lambda b: long_wav)
    sent: list[int] = []

    class Counting(SarvamClient):
        def transcribe(self, *a: Any, **k: Any) -> Any:
            sent.append(1)

    app.dependency_overrides[api.get_speech] = lambda: SpeechService(
        "live", client=Counting("k"), log=lambda **kw: None
    )
    sid = session(client)
    res = client.post(f"/api/practice/sessions/{sid}/voice-turn", files=AUDIO)
    assert res.status_code == 422 and sent == []


def test_an_unexpected_error_in_the_speech_path_means_text_mode_not_a_500(
    client: TestClient,
) -> None:
    class Odd(SpeechService):
        def transcribe(self, recording: bytes, lang: str) -> str:
            raise EOFError("odd")

    app.dependency_overrides[api.get_speech] = lambda: Odd("stub", log=lambda **kw: None)
    sid = session(client)
    res = client.post(f"/api/practice/sessions/{sid}/voice-turn", files=AUDIO)
    assert res.status_code == 503 and res.json()["detail"]["text_mode"] is True


def test_the_daily_speech_budget_turns_speech_off() -> None:
    svc = SpeechService("stub", log=lambda **kw: None, budget_inr_daily=1.0)
    assert svc.available
    svc.spent_inr = 1.0
    assert not svc.available


def test_oversize_or_empty_recordings_are_refused(client: TestClient) -> None:
    sid = session(client)
    res = client.post(
        f"/api/practice/sessions/{sid}/voice-turn", files={"audio": ("c.webm", b"", "audio/webm")}
    )
    assert res.status_code == 422
