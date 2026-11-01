"""Provider order, fallback, the circuit breaker, key skipping, the speech service on the chain,
costs and per-session caps, and the startup warning. Mock providers and the Bodhan mock only; no
network."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from services.speech import audio, costs, tts
from services.speech.bodhan import BodhanClient, BodhanProvider
from services.speech.chain import ProviderChain, gates_passed, order_from_env, startup_warning
from services.speech.provider import MockProvider
from services.speech.sarvam import SpeechError
from services.speech.service import SpeechService
from services.speech.voices import Voice
from tests.speech.bodhan_mock import SPEAK_KEY, TRANSCRIBE_KEY, BodhanMock

CLIP = audio.tone(2.0, 300, rate=16000)
VOICE = Voice("anushka", 1.0, 1.0)


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def chain(*providers: MockProvider, clock: Clock | None = None) -> ProviderChain:
    names = [p.name for p in providers]
    return ProviderChain({p.name: p for p in providers}, order=lambda f, lang: names, clock=clock)


# --- order ------------------------------------------------------------------------------------


def test_the_default_order_is_bodhan_then_sarvam_with_per_language_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert order_from_env("tts") == ["bodhan", "sarvam"] == order_from_env("stt", "hi")
    monkeypatch.setenv("SPEECH_TTS_PROVIDERS", "sarvam,bodhan")
    monkeypatch.setenv("SPEECH_STT_PROVIDERS_TA", "sarvam")
    assert order_from_env("tts") == ["sarvam", "bodhan"]
    assert order_from_env("stt", "ta") == ["sarvam"] and order_from_env("stt", "hi") == [
        "bodhan",
        "sarvam",
    ]


def test_a_provider_without_a_key_is_skipped() -> None:
    first = MockProvider("bodhan", configured=False)
    second = MockProvider("sarvam", text="from sarvam")
    c = chain(first, second)
    assert c.transcribe(CLIP, "hi").text == "from sarvam"
    assert first.calls == [] and not c.fallbacks  # skipping is not a fallback


def test_no_configured_provider_is_an_unavailable_error() -> None:
    with pytest.raises(SpeechError) as e:
        chain(MockProvider("bodhan", configured=False)).transcribe(CLIP, "hi")
    assert e.value.kind == "unavailable" and e.value.code == "no_provider"


# --- fallback -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fail",
    [
        SpeechError("timeout", 0, "timeout"),
        SpeechError("unavailable", 503),
        SpeechError("rate", 429),
        SpeechError("auth", 401),
    ],
    ids=["timeout", "5xx", "429", "401"],
)
def test_an_error_timeout_429_or_key_problem_moves_to_the_next_provider(fail: SpeechError) -> None:
    c = chain(MockProvider("bodhan", fail=fail), MockProvider("sarvam", text="fallback"))
    assert c.transcribe(CLIP, "hi").text == "fallback"
    assert sum(c.fallbacks.values()) == 1


@pytest.mark.parametrize("code", [400, 415, 422])
def test_a_request_error_does_not_fall_back(code: int) -> None:
    second = MockProvider("sarvam")
    c = chain(MockProvider("bodhan", fail=SpeechError("bad_request", code)), second)
    with pytest.raises(SpeechError) as e:
        c.synthesize("Hello", "en", lambda p: "Kavya")
    assert e.value.status == code and second.calls == [] and not c.fallbacks


def test_when_every_provider_fails_the_last_error_is_raised() -> None:
    c = chain(
        MockProvider("bodhan", fail=SpeechError("timeout")),
        MockProvider("sarvam", fail=SpeechError("unavailable", 503)),
    )
    with pytest.raises(SpeechError) as e:
        c.transcribe(CLIP, "hi")
    assert e.value.kind == "unavailable"


def test_each_provider_gets_its_own_voice() -> None:
    seen: list[str] = []
    c = chain(MockProvider("bodhan", fail=SpeechError("timeout")), MockProvider("sarvam"))
    c.synthesize(
        "Hello", "hi", lambda p: seen.append(p) or {"bodhan": "Kavya", "sarvam": "anushka"}[p]
    )
    assert seen == ["bodhan", "sarvam"]


def test_fallbacks_are_logged_by_name_and_kind_only(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)
    c = chain(MockProvider("bodhan", fail=SpeechError("rate", 429, "")), MockProvider("sarvam"))
    c.synthesize("Secret line 46", "en", lambda p: "v")
    assert "fell back from bodhan to sarvam (rate)" in caplog.text
    assert "Secret line" not in caplog.text
    assert c.fallbacks[("tts", "bodhan", "rate")] == 1


# --- circuit breaker ------------------------------------------------------------------------------


def test_the_breaker_opens_after_3_failures_in_60_seconds_and_tries_again_after_30() -> None:
    clock = Clock()
    bad = MockProvider("bodhan", fail=SpeechError("unavailable", 500))
    good = MockProvider("sarvam")
    c = chain(bad, good, clock=clock)
    for _ in range(3):
        c.transcribe(CLIP, "hi")
        clock.t += 10
    assert len(bad.calls) == 3 and c.breaker("bodhan", "stt").state == "open"
    c.transcribe(CLIP, "hi")
    assert len(bad.calls) == 3  # skipped while open
    assert c.breaker("bodhan", "tts").state == "closed"  # per function
    clock.t += 30
    bad.fail = None
    c.transcribe(CLIP, "hi")
    assert len(bad.calls) == 4 and c.breaker("bodhan", "stt").state == "closed"


def test_three_failures_spread_over_more_than_60_seconds_do_not_open_it() -> None:
    clock = Clock()
    bad = MockProvider("bodhan", fail=SpeechError("timeout"))
    c = chain(bad, MockProvider("sarvam"), clock=clock)
    for _ in range(3):
        c.transcribe(CLIP, "hi")
        clock.t += 31
    assert c.breaker("bodhan", "stt").state == "closed"


# --- the speech service on the chain, with the Bodhan mock first ----------------------------------


def bodhan(mock: BodhanMock) -> BodhanProvider:
    return BodhanProvider(
        BodhanClient(
            speak_key=SPEAK_KEY, transcribe_key=TRANSCRIBE_KEY, client=mock.client(),
            sleep=lambda s: None,
        )
    )  # fmt: skip


def test_the_service_uses_bodhan_first_and_sarvam_when_bodhan_is_down() -> None:
    rows: list[dict[str, object]] = []
    sarvam = MockProvider("sarvam", text="from sarvam")
    up = BodhanMock()
    svc = SpeechService(
        "live", log=lambda **kw: rows.append(kw),
        providers=ProviderChain({"bodhan": bodhan(up), "sarvam": sarvam}),
    )  # fmt: skip
    assert svc.transcribe(audio.tone(1.0, 300), "hi") == "heard in hi"
    assert sarvam.calls == []
    down = BodhanMock(fail=[503, 503])
    svc2 = SpeechService(
        "live", log=lambda **kw: rows.append(kw),
        providers=ProviderChain({"bodhan": bodhan(down), "sarvam": sarvam}),
    )  # fmt: skip
    assert svc2.transcribe(audio.tone(1.0, 300), "hi") == "from sarvam"
    assert svc2.chain is not None and sum(svc2.chain.fallbacks.values()) == 1
    assert all("text" not in r and "transcript" not in r for r in rows)  # metadata only


def test_the_service_converts_trims_and_splits_long_speech_into_pieces_of_at_most_28_seconds() -> (
    None
):
    sizes: list[float] = []

    class Measure(MockProvider):
        def transcribe(self, wav: bytes, language: str):  # type: ignore[no-untyped-def]
            sizes.append(audio.wav_seconds(wav))
            return super().transcribe(wav, language)

    svc = SpeechService("live", providers=chain(Measure("bodhan", text="part")))
    # 29.8 s recorded (under the 30 s refusal); after trimming the leading silence 29.65 s remain
    speech = audio.concat([audio.tone(0.3, 0, 16000), audio.tone(29.5, 300, 16000)], 0)
    assert svc.transcribe(speech, "ta") == "part part"
    assert len(sizes) == 2 and max(sizes) <= 28.0 and sum(sizes) == pytest.approx(29.65, abs=0.05)


def test_silence_alone_is_not_sent() -> None:
    p = MockProvider("bodhan")
    svc = SpeechService("live", providers=chain(p))
    assert svc.transcribe(audio.tone(2.0, 0, 16000), "hi") == "" and p.calls == []


def test_synthesis_goes_through_the_chain_to_ogg_and_is_cached() -> None:
    tts.CACHE._items.clear()
    rows: list[dict[str, object]] = []
    p = MockProvider("bodhan")
    svc = SpeechService("live", log=lambda **kw: rows.append(kw), providers=chain(p))
    first = svc.synthesize("Ravi has 23 sticks", "en", VOICE)
    again = svc.synthesize("Ravi has 23 sticks", "en", VOICE)
    assert first[:4] == b"OggS" and again == first and len(p.calls) == 1
    assert [r["from_cache"] for r in rows] == [False, True]


def test_an_explicit_sarvam_client_keeps_the_old_path() -> None:
    from services.speech.sarvam import SarvamClient

    svc = SpeechService("live", client=SarvamClient(""), log=lambda **kw: None)
    assert svc.chain is None and not svc.available


# --- costs and caps -------------------------------------------------------------------------------


def test_costs_come_from_the_price_file_and_every_paid_price_is_unverified() -> None:
    assert costs.cost_inr("bodhan", "tts", chars=10000) == 6.0
    assert costs.cost_inr("bodhan", "stt", seconds=60) == 0.10
    assert costs.cost_inr("sarvam", "tts", chars=10000) == 30.0
    assert costs.cost_inr("sarvam", "stt", seconds=3600) == pytest.approx(30.0)
    assert costs.cost_inr("nobody", "tts", chars=10) == 0.0
    for name in ("bodhan", "sarvam"):
        for fn in ("tts", "stt"):
            entry = costs.prices()["providers"][name][fn]
            assert entry["verified"] is False and entry["source"] and entry["as_of"]


def test_a_session_cap_turns_speech_off_and_says_why() -> None:
    p = MockProvider("bodhan")
    svc = SpeechService("live", providers=chain(p))
    budget = costs.SessionSpeechBudget(max_stt_seconds=3.0, max_tts_chars=20)
    svc.transcribe(audio.tone(2.0, 300, 16000), "hi", budget=budget)
    assert budget.stt_seconds == pytest.approx(2.0, abs=0.05)
    with pytest.raises(SpeechError) as e:
        svc.transcribe(audio.tone(2.0, 300, 16000), "hi", budget=budget)
    assert e.value.code == "session_cap"
    tts.CACHE._items.clear()
    svc.synthesize("x" * 15, "hi", VOICE, budget=budget)
    with pytest.raises(SpeechError) as e2:
        svc.synthesize("y" * 15, "hi", VOICE, budget=budget)
    assert e2.value.code == "session_cap" and budget.tts_chars == 15


def test_caps_come_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEECH_SESSION_MAX_STT_SECONDS", "90")
    monkeypatch.setenv("SPEECH_SESSION_MAX_TTS_CHARS", "1234")
    b = costs.SessionSpeechBudget()
    assert b.max_stt_seconds == 90.0 and b.max_tts_chars == 1234


# --- the startup warning --------------------------------------------------------------------------


def test_the_startup_warning_reads_the_gates_file(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING)
    missing = tmp_path / "speech_gates.md"
    assert gates_passed(missing) == {"bodhan_tts": False, "bodhan_stt": False}
    assert startup_warning(missing) is not None and "tts and stt" in caplog.text
    half = tmp_path / "half.md"
    half.write_text("---\nbodhan_tts: pass\nbodhan_stt: pending\n---\n", encoding="utf-8")
    msg = startup_warning(half)
    assert msg is not None and "for stt" in msg
    both = tmp_path / "both.md"
    both.write_text("---\nbodhan_tts: pass\nbodhan_stt: pass\n---\n", encoding="utf-8")
    assert startup_warning(both) is None


def test_no_warning_when_bodhan_is_not_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SPEECH_TTS_PROVIDERS", "sarvam,bodhan")
    monkeypatch.setenv("SPEECH_STT_PROVIDERS", "sarvam")
    assert startup_warning(tmp_path / "none.md") is None


def test_the_warning_never_stops_the_api(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from services.api.main import create_app

    monkeypatch.setenv("SPEECH_MODE", "live")
    assert TestClient(create_app()).get("/api/health").status_code == 200
