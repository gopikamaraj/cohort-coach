"""The audio helpers of the speech layer, with generated tones and silence only (never a voice)."""

from __future__ import annotations

import json
import shutil
import subprocess

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from services.speech import audio
from services.speech.sarvam import SpeechError

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not on PATH")
RATE = 16000


def tone(seconds: float, hz: float = 300) -> bytes:
    return audio.tone(seconds, hz, rate=RATE)


def silence(seconds: float) -> bytes:
    return audio.tone(seconds, 0, rate=RATE)


def test_phone_formats_become_16k_mono_wav() -> None:
    src = audio.tone(1.5, 440, rate=44100)
    for fmt, args in (
        ("ogg", ["-c:a", "libopus", "-f", "ogg"]),
        ("webm", ["-c:a", "libopus", "-f", "webm"]),
        ("mp3", ["-c:a", "libmp3lame", "-f", "mp3"]),
        ("m4a", ["-c:a", "aac", "-movflags", "frag_keyframe+empty_moov", "-f", "mp4"]),
    ):
        encoded = audio._run(["-i", "pipe:0", *args, "pipe:1"], src)
        wav = audio.to_wav_16k_mono(encoded)
        assert wav[:4] == b"RIFF", fmt
        samples, rate = audio._samples(wav)
        assert rate == RATE and abs(audio.wav_seconds(wav) - 1.5) < 0.1, fmt


def test_duration_reads_the_header_and_survives_a_streamed_wav_with_no_size() -> None:
    wav = audio.tone(2.0, 440, rate=24000)
    assert audio.duration_seconds(wav) == pytest.approx(2.0)
    data_at = wav.index(b"data")
    streamed = wav[: data_at + 4] + b"\xff\xff\xff\xff" + wav[data_at + 8 :]
    assert audio.duration_seconds(streamed) == pytest.approx(2.0)
    with pytest.raises(SpeechError):
        audio.duration_seconds(b"not a wav at all")


def test_trim_silence_cuts_the_edges_and_long_pauses_but_keeps_the_sound() -> None:
    wav = audio.concat([silence(1.0), tone(1.0), silence(3.0), tone(1.0), silence(1.0)], 0)
    out = audio.trim_silence(wav, keep_ms=100, max_pause_ms=500)
    # 2 s of sound + the 500 ms pause + 100 ms each side
    assert audio.wav_seconds(out) == pytest.approx(2.7, abs=0.05)
    assert audio.wav_seconds(audio.trim_silence(silence(2.0))) == 0.0
    assert audio.wav_seconds(audio.trim_silence(tone(1.0))) == pytest.approx(1.0, abs=0.03)


@settings(max_examples=25, deadline=None)
@given(
    sound=st.lists(st.floats(min_value=0.5, max_value=20.0), min_size=1, max_size=5),
    gaps=st.lists(st.floats(min_value=0.0, max_value=2.0), min_size=5, max_size=5),
)
def test_no_piece_is_longer_than_28_seconds_and_no_sample_is_lost(
    sound: list[float], gaps: list[float]
) -> None:
    parts: list[bytes] = []
    for s, g in zip(sound, gaps, strict=False):
        parts += [tone(s), silence(g)]
    wav = audio.concat(parts, 0)
    pieces = audio.split_for_stt(wav)
    assert all(audio.wav_seconds(p) <= 28.0 for p in pieces)
    total = b"".join(audio._samples(p)[0].tobytes() for p in pieces)
    assert total == audio._samples(wav)[0].tobytes()


def test_a_long_tone_with_no_silence_is_cut_at_the_limit() -> None:
    pieces = audio.split_for_stt(tone(60.0))
    assert len(pieces) == 3 and all(audio.wav_seconds(p) <= 28.0 for p in pieces)


def test_concat_adds_the_gaps_and_refuses_mixed_rates() -> None:
    out = audio.concat([tone(1.0), tone(0.5), tone(0.25)], gap_ms=250)
    assert audio.wav_seconds(out) == pytest.approx(1.75 + 0.5)
    with pytest.raises(ValueError):
        audio.concat([tone(1.0), audio.tone(1.0, 300, rate=24000)])
    with pytest.raises(ValueError):
        audio.concat([])


def _probe(data: bytes) -> dict[str, object]:
    done = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-of", "json", "-i", "pipe:0"],
        input=data, capture_output=True, check=True,
    )  # fmt: skip
    stream: dict[str, object] = json.loads(done.stdout)["streams"][0]
    return stream


@pytest.mark.skipif(shutil.which("ffprobe") is None, reason="ffprobe not on PATH")
def test_mp3_is_mono_at_the_asked_bitrate() -> None:
    mp3 = audio.wav_to_mp3(audio.tone(3.0, 440, rate=24000), kbps=48)
    info = _probe(mp3)
    assert info["codec_name"] == "mp3" and info["channels"] == 1
    assert abs(int(str(info["bit_rate"])) - 48000) <= 2000


def test_loudness_normalisation_keeps_rate_and_length_and_raises_a_quiet_tone() -> None:
    import numpy as np

    quiet = audio._wav_bytes((audio._samples(tone(3.0))[0] * 0.05).astype("int16"), RATE)
    out = audio.loudness_normalise(quiet, -16.0)
    s_out, rate = audio._samples(out)
    assert rate == RATE and audio.wav_seconds(out) == pytest.approx(3.0, abs=0.1)
    assert np.abs(s_out).max() > np.abs(audio._samples(quiet)[0]).max()


def test_the_converted_wav_header_carries_the_true_length() -> None:
    """ffmpeg writing to a pipe leaves the size fields unset; a service that meters by the header
    would read a clip of hours. The conversion rewrites it."""
    import io
    import wave

    ogg = audio._run(
        ["-i", "pipe:0", "-c:a", "libopus", "-f", "ogg", "pipe:1"], audio.tone(2.0, 440)
    )
    wav = audio.to_wav_16k_mono(ogg)
    with wave.open(io.BytesIO(wav)) as w:
        assert abs(w.getnframes() / w.getframerate() - 2.0) < 0.1
