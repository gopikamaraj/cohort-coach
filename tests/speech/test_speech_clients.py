"""Speech clients: mocked HTTP (respx), real ffmpeg, no network."""

from __future__ import annotations

import base64
import io
import wave

import httpx
import numpy as np
import pytest
import respx

from services.speech import audio, stt, tts, voices
from services.speech.health import CircuitBreaker
from services.speech.sarvam import SarvamClient, SpeechError

pytestmark = pytest.mark.skipif(audio.shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def _client(**kw: object) -> SarvamClient:
    return SarvamClient("k", sleep=lambda s: None, **kw)  # type: ignore[arg-type]


def _peak_hz(wav: bytes) -> float:
    with wave.open(io.BytesIO(wav)) as w:
        rate = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(float)
    spec = np.abs(np.fft.rfft(x))
    return float(np.argmax(spec) * rate / len(x))


def test_chunks_never_exceed_the_limit_and_cut_at_quiet_points() -> None:
    rate = 16000
    t = np.arange(70 * rate) / rate
    x = 0.3 * 32767 * np.sin(2 * np.pi * 300 * t)
    # a quiet gap at 20 s and at 45 s
    for g in (20, 45):
        x[int(g * rate) : int((g + 0.3) * rate)] = 0
    wav = audio._wav_bytes(x.astype(np.int16), rate)
    chunks = audio.split_at_silences(wav)
    assert len(chunks) >= 3
    assert all(audio.wav_seconds(c) <= audio.MAX_CHUNK_SECONDS + 1e-6 for c in chunks)
    assert sum(audio.wav_seconds(c) for c in chunks) == pytest.approx(70, abs=0.01)
    assert audio.wav_seconds(chunks[0]) == pytest.approx(20.15, abs=0.3)


def test_short_audio_is_one_chunk() -> None:
    wav = audio.tone(2, 200, 16000)
    chunks = audio.split_at_silences(wav)
    assert len(chunks) == 1 and audio.wav_seconds(chunks[0]) == pytest.approx(2, abs=0.01)


def test_the_length_of_ffmpeg_piped_audio_is_read_from_the_samples() -> None:
    wav = audio.to_wav16k(audio.tone(3, 200))  # a pipe: the header's length is unset
    assert audio.wav_seconds(wav) == pytest.approx(3, abs=0.05)


def test_pitch_goes_up_and_duration_is_kept() -> None:
    src = audio.tone(2, 200)
    flat = audio.to_wav16k(audio.to_ogg_opus(src))
    high = audio.to_wav16k(audio.to_ogg_opus(src, pitch_ratio=1.3))
    assert _peak_hz(flat) == pytest.approx(200, abs=8)
    assert _peak_hz(high) == pytest.approx(260, abs=10)
    assert audio.wav_seconds(high) == pytest.approx(audio.wav_seconds(flat), abs=0.15)


def test_pitch_ratio_out_of_range_is_refused() -> None:
    with pytest.raises(ValueError):
        audio.to_ogg_opus(audio.tone(1, 200), pitch_ratio=2.5)


def test_opus_output_is_small() -> None:
    ogg = audio.to_ogg_opus(audio.tone(5, 200))
    assert len(ogg) < 5 * 3500  # about 3 KB a second at 24 kbps


@respx.mock
def test_transcribe_sends_key_model_and_language_and_joins_chunks() -> None:
    route = respx.post("https://api.sarvam.ai/speech-to-text").mock(
        side_effect=[
            httpx.Response(200, json={"transcript": "one two"}),
            httpx.Response(200, json={"transcript": "three"}),
        ]
    )
    rate = 16000
    x = np.zeros(29 * rate, dtype=np.int16)
    x[:] = (0.3 * 32767 * np.sin(2 * np.pi * 300 * np.arange(len(x)) / rate)).astype(np.int16)
    x[int(15 * rate) : int(15.3 * rate)] = 0
    got = stt.transcribe(_client(), audio._wav_bytes(x, rate), "hi")
    assert got.text == "one two three"
    assert got.chunks == 2
    req = route.calls[0].request
    assert req.headers["api-subscription-key"] == "k"
    body = req.content
    assert b"saaras:v4" in body and b"hi-IN" in body


@respx.mock
def test_errors_are_mapped_and_429_is_retried_once() -> None:
    respx.post("https://api.sarvam.ai/speech-to-text").mock(
        side_effect=[httpx.Response(429, json={}), httpx.Response(200, json={"transcript": "ok"})]
    )
    assert _client().transcribe(audio.tone(1, 200, 16000), "en-IN").transcript == "ok"
    respx.post("https://api.sarvam.ai/text-to-speech").mock(
        return_value=httpx.Response(403, json={"error": {"code": "invalid_api_key_error"}})
    )
    with pytest.raises(SpeechError) as e:
        _client().synthesize("hi", "en-IN", "priya")
    assert e.value.kind == "auth" and e.value.code == "invalid_api_key_error"


@respx.mock
def test_timeout_and_missing_key() -> None:
    respx.post("https://api.sarvam.ai/text-to-speech").mock(side_effect=httpx.ReadTimeout("t"))
    with pytest.raises(SpeechError) as e:
        _client().synthesize("hi", "en-IN", "priya")
    assert e.value.kind == "timeout"
    with pytest.raises(SpeechError) as e2:
        SarvamClient("").synthesize("hi", "en-IN", "priya")
    assert e2.value.code == "no_key"


@respx.mock
def test_synthesis_request_shape_and_cache_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SARVAM_DICT_EN", raising=False)
    wav = audio.tone(1, 200)
    mp3 = audio._run(["-i", "pipe:0", "-f", "mp3", "pipe:1"], wav)
    route = respx.post("https://api.sarvam.ai/text-to-speech").mock(
        return_value=httpx.Response(200, json={"audios": [base64.b64encode(mp3).decode()]})
    )
    cache = tts.SpeechCache()
    v = voices.voice_for("meena")
    first, hit1 = tts.synthesize(_client(), "forty-three", "en", v, cache=cache)
    second, hit2 = tts.synthesize(_client(), "forty-three", "en", v, cache=cache)
    assert (hit1, hit2) == (False, True) and first == second
    assert route.call_count == 1
    sent = route.calls[0].request.content
    assert b'"output_audio_codec":"mp3"' in sent.replace(b" ", b"")
    assert b"language_code" in sent and b"target_language_code" not in sent
    assert first[:4] == b"OggS"


def test_every_persona_has_a_distinct_voice() -> None:
    allv = voices.all_voices()
    assert len(allv) == 12
    assert len({v.speaker for v in allv.values()}) == 12
    assert all(1.0 <= v.pitch <= 2.0 for v in allv.values())
    assert voices.voice_for("nobody") in allv.values()


def test_breaker_opens_after_three_failures_and_recovers() -> None:
    now = [0.0]
    b = CircuitBreaker(clock=lambda: now[0])
    for _ in range(2):
        b.failure()
    assert b.allow() and b.state == "closed"
    b.failure()
    assert b.state == "open" and not b.allow()
    now[0] = 31
    assert b.state == "half_open"
    assert b.allow() and not b.allow()  # one trial only
    b.failure()  # the trial failed: open again
    assert b.state == "open"
    now[0] = 62
    assert b.allow()
    b.success()
    assert b.state == "closed" and b.allow()
