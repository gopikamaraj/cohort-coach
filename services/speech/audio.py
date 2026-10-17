"""Audio helpers on top of ffmpeg: decode to 16 kHz mono WAV, cut at silences, pitch-shift and
encode to OGG/Opus. ffmpeg must be on PATH (WinGet, apt or brew)."""

from __future__ import annotations

import io
import shutil
import subprocess
import wave

import numpy as np

from services.speech.sarvam import SpeechError

MAX_CHUNK_SECONDS = 28.0  # Sarvam's real-time limit is 30 s; keep a margin
SAMPLE_RATE = 16000
FRAME_MS = 20


def ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise SpeechError("unavailable", 0, "ffmpeg_missing")
    return path


def _run(args: list[str], data: bytes | None = None, timeout: float = 30.0) -> bytes:
    try:
        done = subprocess.run(
            [ffmpeg(), "-hide_banner", "-loglevel", "error", *args],
            input=data,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SpeechError("timeout", 0, "ffmpeg_timeout") from exc
    if done.returncode != 0:
        raise SpeechError("bad_request", 0, "ffmpeg_failed")
    return done.stdout


def to_wav16k(audio: bytes) -> bytes:
    """Any audio the phone sends (WebM/Opus, OGG, MP3, WAV) -> 16 kHz mono 16-bit WAV."""
    return _run(["-i", "pipe:0", "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "wav", "pipe:1"], audio)


def wav_seconds(wav: bytes) -> float:
    """Length from the samples actually present: ffmpeg writing to a pipe leaves the header's
    length unset, so the header cannot be trusted."""
    samples, rate = _samples(wav)
    return float(len(samples) / rate)


def _samples(wav: bytes) -> tuple[np.ndarray, int]:
    with wave.open(io.BytesIO(wav)) as w:
        rate = w.getframerate()
        raw = w.readframes(w.getnframes())
    return np.frombuffer(raw, dtype=np.int16), rate


def _wav_bytes(samples: np.ndarray, rate: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(samples.astype(np.int16).tobytes())
    return buf.getvalue()


def split_at_silences(wav: bytes, max_seconds: float = MAX_CHUNK_SECONDS) -> list[bytes]:
    """Cut a WAV into chunks no longer than `max_seconds`, at the quietest point near the end
    of each window (the second half of it), or at the limit if there is no quiet point."""
    samples, rate = _samples(wav)
    limit = int(max_seconds * rate)
    if len(samples) <= limit:
        return [_wav_bytes(samples, rate)]  # rewritten so the header carries the true length
    frame = int(rate * FRAME_MS / 1000)
    chunks: list[bytes] = []
    start = 0
    while len(samples) - start > limit:
        lo, hi = start + limit // 2, start + limit
        window = samples[lo:hi]
        n = len(window) // frame
        energy = np.sqrt(
            np.mean(window[: n * frame].reshape(n, frame).astype(np.float64) ** 2, axis=1)
        )
        cut = lo + int(np.argmin(energy)) * frame + frame // 2 if n else hi
        cut = min(max(cut, start + frame), hi)
        chunks.append(_wav_bytes(samples[start:cut], rate))
        start = cut
    chunks.append(_wav_bytes(samples[start:], rate))
    return chunks


def to_ogg_opus(
    audio: bytes, *, pitch_ratio: float = 1.0, input_rate: int = 24000, kbps: int = 24
) -> bytes:
    """Encode speech as OGG/Opus mono, optionally raising the pitch without changing the speed.

    asetrate raises pitch and speed together; atempo takes the speed back. The ratio must be in
    [1.0, 2.0] (atempo's range).
    """
    if not 1.0 <= pitch_ratio <= 2.0:
        raise ValueError("pitch_ratio must be between 1.0 and 2.0")
    args = ["-i", "pipe:0", "-ac", "1"]
    if pitch_ratio != 1.0:
        args += [
            "-af",
            f"asetrate={input_rate * pitch_ratio:g},aresample={input_rate},"
            f"atempo={1 / pitch_ratio:.6f}",
        ]
    args += [
        "-c:a",
        "libopus",
        "-b:a",
        f"{kbps}k",
        "-application",
        "voip",
        "-vbr",
        "constrained",
        "-f",
        "ogg",
        "pipe:1",
    ]
    return _run(args, audio)


def tone(seconds: float, hz: float, rate: int = 24000) -> bytes:
    """A sine tone as WAV, for the stub voice and for tests."""
    t = np.arange(int(seconds * rate)) / rate
    return _wav_bytes((0.3 * 32767 * np.sin(2 * np.pi * hz * t)).astype(np.int16), rate)
