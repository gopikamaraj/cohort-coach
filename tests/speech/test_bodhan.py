"""The Bodhan adapter against a mock of the documented API: request building, status mapping,
retries, and nothing secret in the logs. No network."""

from __future__ import annotations

import json
import logging

import httpx
import pytest

from services.speech import audio
from services.speech.bodhan import (
    DEFAULT_VOICE,
    STT_MODEL,
    TTS_MODEL,
    BodhanClient,
    BodhanProvider,
    speech_body,
)
from services.speech.sarvam import SpeechError
from tests.speech.bodhan_mock import SPEAK_KEY, TRANSCRIBE_KEY, BodhanMock, _multipart


def provider(mock: BodhanMock, **kw: object) -> BodhanProvider:
    client = BodhanClient(
        speak_key=kw.pop("speak_key", SPEAK_KEY),  # type: ignore[arg-type]
        transcribe_key=kw.pop("transcribe_key", TRANSCRIBE_KEY),  # type: ignore[arg-type]
        client=mock.client(),
        sleep=lambda s: None,
        jitter=lambda: 0.0,
    )
    return BodhanProvider(client)


def clip(seconds: float = 2.0) -> bytes:
    return audio.tone(seconds, 300, rate=16000)


class FakeTime:
    """A clock that only moves when the client sleeps, so waits are exact and instant."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.waits: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, s: float) -> None:
        self.waits.append(round(s, 2))
        self.now += s


# --- request building -----------------------------------------------------------------------------


def test_instructions_is_a_json_string_and_style_is_left_out_when_there_is_none() -> None:
    body = speech_body("नमस्ते", "hi", "Kavya", None)
    assert body["model"] == TTS_MODEL and body["voice"] == "Kavya" and body["input"] == "नमस्ते"
    assert isinstance(body["instructions"], str)
    assert json.loads(body["instructions"]) == {"lang": "hi"}
    styled = speech_body("x", "ta", "Anitha", "educational lecture")
    assert json.loads(styled["instructions"]) == {"lang": "ta", "style": "educational lecture"}


def test_speech_to_text_sends_the_file_the_model_and_always_the_language() -> None:
    mock = BodhanMock()
    got = provider(mock).transcribe(clip(), "ta")
    fields = _multipart(mock.requests[0])
    assert fields["model"].decode() == STT_MODEL and fields["language"].decode() == "ta"
    assert fields["file"][:4] == b"RIFF"
    assert mock.requests[0].headers["authorization"] == f"Bearer {TRANSCRIBE_KEY}"
    assert got.text == "heard in ta" and got.provider == "bodhan" and got.request_id == "req-0001"
    assert got.seconds_billed == pytest.approx(2.0, abs=0.01)


def test_text_to_speech_returns_wav_with_its_real_length_and_uses_the_speak_key() -> None:
    mock = BodhanMock()
    got = provider(mock).synthesize("Ravi has 23 sticks.", "en", "Kavya", None)
    assert mock.requests[0].headers["authorization"] == f"Bearer {SPEAK_KEY}"
    assert got.format == "wav" and got.sample_rate == 24000 and got.data[:4] == b"RIFF"
    assert got.seconds == pytest.approx(0.06 * len("Ravi has 23 sticks."), abs=0.01)
    assert got.chars_billed == len("Ravi has 23 sticks.") and got.request_id == "req-0001"


def test_empty_or_over_long_input_is_refused_before_any_request() -> None:
    mock = BodhanMock()
    p = provider(mock)
    for text, code in (("", "empty_input"), ("   ", "empty_input"), ("x" * 301, "input_too_long")):
        with pytest.raises(SpeechError) as e:
            p.synthesize(text, "hi", "Kavya", None)
        assert e.value.kind == "bad_request" and e.value.code == code
    assert mock.requests == []


def test_audio_over_28_seconds_is_never_sent() -> None:
    mock = BodhanMock()
    with pytest.raises(SpeechError) as e:
        provider(mock).transcribe(clip(29.0), "hi")
    assert e.value.code == "too_long" and mock.requests == []


def test_an_unknown_voice_becomes_the_language_default_and_an_unknown_style_is_refused() -> None:
    mock = BodhanMock()
    provider(mock).synthesize("Hello", "ta", "ritu", None)  # a Sarvam speaker name
    assert json.loads(mock.requests[0].content)["voice"] == DEFAULT_VOICE["ta"]
    with pytest.raises(SpeechError, match="bad_request"):
        provider(mock).synthesize("Hello", "ta", "Anitha", "whisper")


# --- the documented constraints, through the mock -------------------------------------------------


@pytest.mark.parametrize(
    "head",
    [
        b"\x1a\x45\xdf\xa3" + b"\x00" * 60,
        b"\x00\x00\x00\x18ftypM4A " + b"\x00" * 60,
        b"#!AMR\n" + b"\x00" * 60,
    ],
    ids=["webm", "m4a", "amr"],
)
def test_the_mock_refuses_phone_containers_with_415_like_bodhan(head: bytes) -> None:
    """Why speech to text always converts first: these formats are refused as they come."""
    client = BodhanClient(
        speak_key=SPEAK_KEY,
        transcribe_key=TRANSCRIBE_KEY,
        client=BodhanMock().client(),
        sleep=lambda s: None,
    )
    with pytest.raises(SpeechError) as e:
        client.transcribe(head, "hi")
    assert e.value.status == 415 and e.value.kind == "bad_request"


def test_a_bad_voice_or_language_at_the_service_is_a_422_bad_request_not_retried() -> None:
    mock = BodhanMock()
    client = BodhanClient(speak_key=SPEAK_KEY, client=mock.client(), sleep=lambda s: None)
    with pytest.raises(SpeechError) as e:
        client.synthesize("Hello", "xx", "Kavya", None)
    assert e.value.status == 422 and e.value.kind == "bad_request" and mock.count == 1


# --- status mapping and retries ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "kind", "requests"),
    [
        (401, "auth", 1),
        (403, "auth", 1),
        (415, "bad_request", 1),
        (422, "bad_request", 1),
        (400, "bad_request", 1),
        (429, "rate", 2),
        (500, "unavailable", 2),
        (503, "unavailable", 2),
    ],
)
def test_each_status_maps_to_a_kind_and_only_429_and_5xx_are_retried(
    status: int, kind: str, requests: int
) -> None:
    mock = BodhanMock(fail=[status, status])
    with pytest.raises(SpeechError) as e:
        provider(mock).transcribe(clip(), "hi")
    assert e.value.kind == kind and e.value.status == status and mock.count == requests


def test_one_retry_recovers_from_a_429_or_a_500_or_a_timeout() -> None:
    for first in (429, 500, "slow"):
        mock = BodhanMock(fail=[first])
        assert provider(mock).transcribe(clip(), "hi").text == "heard in hi"
        assert mock.count == 2


def test_two_timeouts_are_a_timeout_error() -> None:
    mock = BodhanMock(fail=["slow", "slow"])
    with pytest.raises(SpeechError) as e:
        provider(mock).synthesize("Hello", "en", "Kavya", None)
    assert e.value.kind == "timeout" and mock.count == 2


def test_the_retry_waits_for_retry_after_and_rate_limit_headers_are_kept() -> None:
    t = FakeTime()
    mock = BodhanMock(fail=[429], retry_after="3")
    client = BodhanClient(
        speak_key=SPEAK_KEY,
        transcribe_key=TRANSCRIBE_KEY,
        client=mock.client(),
        sleep=t.sleep,
        jitter=lambda: 0.0,
        clock=t.clock,
    )
    client.transcribe(clip(), "hi")
    assert t.waits == [3.0]
    still = BodhanClient(
        transcribe_key=TRANSCRIBE_KEY,
        client=BodhanMock(fail=[429, 429]).client(),
        sleep=lambda s: None,
    )
    with pytest.raises(SpeechError, match="rate"):
        still.transcribe(clip(), "hi")
    assert still.last_rate_limits == {
        "x-ratelimit-limit-requests": "60"
    }  # read for the next caller


def test_no_key_means_no_request_and_an_auth_error() -> None:
    mock = BodhanMock()
    p = provider(mock, speak_key="", transcribe_key="")
    assert not p.configured_for("stt") and not p.configured_for("tts")
    with pytest.raises(SpeechError) as e:
        p.transcribe(clip(), "hi")
    assert e.value.code == "no_key" and mock.requests == []


def test_each_function_needs_its_own_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BODHAN_SPEAK_API_KEY", "s")
    p = BodhanProvider(BodhanClient(client=BodhanMock().client()))
    assert p.configured_for("tts") and not p.configured_for("stt")
    monkeypatch.setenv("BODHAN_API_KEY", "shared")  # the fallback for an unset function key
    p = BodhanProvider(BodhanClient(client=BodhanMock().client()))
    assert p.configured_for("tts") and p.configured_for("stt")


def test_the_logs_hold_no_key_no_text_and_no_audio(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    mock = BodhanMock(fail=[500, 422])
    p = provider(mock)
    secret_text = "Meena has 46 marbles"
    with pytest.raises(SpeechError):
        p.synthesize(secret_text, "en", "Kavya", None)
    p.transcribe(clip(), "hi")
    logged = caplog.text
    assert SPEAK_KEY not in logged and TRANSCRIBE_KEY not in logged
    assert secret_text not in logged and "heard in hi" not in logged and "RIFF" not in logged
    assert "request_id=req-0003" in logged and "model=indic-transcribe" in logged


def test_a_422_logs_the_unknown_value_and_a_415_logs_loudly(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    client = BodhanClient(
        speak_key=SPEAK_KEY,
        transcribe_key=TRANSCRIBE_KEY,
        client=BodhanMock().client(),
        sleep=lambda s: None,
    )
    with pytest.raises(SpeechError):
        client.synthesize("Hello", "en", "Nobody", None)
    assert "unknown voice 'Nobody'" in caplog.text
    with pytest.raises(SpeechError):
        client.transcribe(b"\x1a\x45\xdf\xa3" + b"\x00" * 60, "hi")
    assert any(r.levelno == logging.ERROR and "415" in r.getMessage() for r in caplog.records)


def test_timeouts_are_set_explicitly(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[httpx.Timeout] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.extensions["timeout"])
        return httpx.Response(200, json={"text": "ok"})

    monkeypatch.setenv("BODHAN_STT_TIMEOUT_S", "12")
    c = BodhanClient(
        transcribe_key="k", client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    c.transcribe(clip(), "en")
    assert seen[0]["connect"] == 5.0 and seen[0]["read"] == 12.0


def test_a_429_without_retry_after_waits_longer_before_its_one_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bodhan's limit is per minute and it sends no Retry-After (seen live on 1 Nov), so the
    retry waits BODHAN_RATE_BACKOFF_S (8 s by default) instead of half a second."""
    t = FakeTime()
    client = BodhanClient(
        transcribe_key=TRANSCRIBE_KEY,
        client=BodhanMock(fail=[429]).client(),
        sleep=t.sleep,
        jitter=lambda: 0.0,
        clock=t.clock,
    )
    client.transcribe(clip(), "hi")
    assert t.waits == [8.0]
    monkeypatch.setenv("BODHAN_RATE_BACKOFF_S", "2")
    t2 = FakeTime()
    BodhanClient(
        transcribe_key=TRANSCRIBE_KEY,
        client=BodhanMock(fail=[429]).client(),
        sleep=t2.sleep,
        jitter=lambda: 0.0,
        clock=t2.clock,
    ).transcribe(clip(), "hi")
    assert t2.waits == [2.0]


def test_requests_are_paced_to_the_per_minute_allowance_per_model() -> None:
    """Measured live on 1 Nov: about 8 requests a minute per model. The ninth waits for a slot."""
    t = FakeTime()
    mock = BodhanMock()
    client = BodhanClient(
        speak_key=SPEAK_KEY,
        transcribe_key=TRANSCRIBE_KEY,
        client=mock.client(),
        sleep=t.sleep,
        clock=t.clock,
        requests_per_minute=8,
    )
    for _ in range(8):
        client.synthesize("Ten.", "en", "Kavya", None)
    client.transcribe(clip(), "en")  # another model: its own allowance
    assert t.waits == []
    client.synthesize("Ten.", "en", "Kavya", None)
    assert t.waits == [60.05] and mock.count == 10


def test_a_wait_longer_than_the_limit_fails_at_once_so_the_chain_can_fall_back() -> None:
    t = FakeTime()
    client = BodhanClient(
        speak_key=SPEAK_KEY,
        client=BodhanMock().client(),
        sleep=t.sleep,
        clock=t.clock,
        requests_per_minute=2,
        pace_max_wait_s=5,
    )
    client.synthesize("One.", "en", "Kavya", None)
    client.synthesize("Two.", "en", "Kavya", None)
    with pytest.raises(SpeechError) as e:
        client.synthesize("Three.", "en", "Kavya", None)
    assert e.value.kind == "rate" and e.value.code == "paced" and t.waits == []


def test_a_long_retry_after_is_not_waited_out_when_it_exceeds_the_limit() -> None:
    t = FakeTime()
    mock = BodhanMock(fail=[429], retry_after="48")
    client = BodhanClient(
        speak_key=SPEAK_KEY,
        client=mock.client(),
        sleep=t.sleep,
        clock=t.clock,
        pace_max_wait_s=10,
    )
    with pytest.raises(SpeechError) as e:
        client.synthesize("Ten.", "en", "Kavya", None)
    assert e.value.kind == "rate" and mock.count == 1 and t.waits == []
