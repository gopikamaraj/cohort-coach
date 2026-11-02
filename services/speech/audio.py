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


PCM_RATE = 24000


def to_pcm(audio: bytes) -> bytes:
    """Any audio -> raw 16-bit mono PCM at 24 kHz."""
    return _run(
        ["-i", "pipe:0", "-ac", "1", "-ar", str(PCM_RATE), "-f", "s16le", "pipe:1"], audio, 60.0
    )


def join_to_file(
    clips: list[bytes], *, fmt: str = "m4a", kbps: int = 32, gap_s: float = 0.6
) -> tuple[bytes, float]:
    """Join speech clips with a short pause into one WhatsApp-friendly mono file.

    `fmt` is "m4a" (AAC), "mp3", or "ogg" (Opus, what Telegram plays as a voice note; 16 kbps
    mono keeps a 5 minute lesson near 0.6 MB). Returns (file bytes, seconds). 32 kbps mono keeps a
    3 minute m4a note near 0.7 MB, well under WhatsApp's 16 MB media limit.
    """
    import subprocess
    import tempfile
    from pathlib import Path

    if fmt not in ("m4a", "mp3", "ogg"):
        raise ValueError("fmt must be m4a, mp3 or ogg")
    silence = b"\x00\x00" * int(gap_s * PCM_RATE)
    pcm = silence.join(to_pcm(c) for c in clips)
    seconds = len(pcm) / 2 / PCM_RATE
    codec = {
        "m4a": ["-c:a", "aac", "-movflags", "+faststart"],
        "mp3": ["-c:a", "libmp3lame"],
        "ogg": ["-c:a", "libopus", "-application", "voip", "-f", "ogg"],
    }[fmt]
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / f"lesson.{fmt}"
        done = subprocess.run(
            [
                ffmpeg(),
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "s16le",
                "-ar",
                str(PCM_RATE),
                "-ac",
                "1",
                "-i",
                "pipe:0",
                *codec,
                "-b:a",
                f"{kbps}k",
                "-ac",
                "1",
                str(out),
            ],
            input=pcm,
            capture_output=True,
            timeout=120,
            check=False,
        )
        if done.returncode != 0 or not out.exists():
            raise SpeechError("bad_request", 0, "ffmpeg_failed")
        return out.read_bytes(), seconds


# --- The speech layer's helpers (Bodhan and Sarvam). Unit-tested with tones and silence only. ---

STT_MAX_SECONDS = MAX_CHUNK_SECONDS  # never send more than 28 s in one request (both limits are 30)


def to_wav_16k_mono(audio: bytes) -> bytes:
    """Whatever a phone records (WebM, M4A, OGG, MP3, WAV) -> 16 kHz mono 16-bit WAV. Bodhan refuses
    WebM and M4A (415), so speech to text always goes through this first. The WAV is rewritten so
    its header carries the true length: ffmpeg writing to a pipe leaves it unset, and a service that
    meters by duration would read a huge clip."""
    samples, rate = _samples(to_wav16k(audio))
    return _wav_bytes(samples, rate)


def duration_seconds(wav: bytes) -> float:
    """The real length of a WAV. Reads the fmt and data chunks itself, and when the data chunk's
    size is missing or wrong (streamed WAVs leave it 0 or 0xFFFFFFFF) uses the bytes present."""
    if len(wav) < 12 or wav[:4] != b"RIFF" or wav[8:12] != b"WAVE":
        raise SpeechError("bad_request", 0, "not_wav")
    pos, rate, block = 12, 0, 0
    while pos + 8 <= len(wav):
        cid, size = wav[pos : pos + 4], int.from_bytes(wav[pos + 4 : pos + 8], "little")
        body = pos + 8
        if cid == b"fmt ":
            channels = int.from_bytes(wav[body + 2 : body + 4], "little")
            rate = int.from_bytes(wav[body + 4 : body + 8], "little")
            bits = int.from_bytes(wav[body + 14 : body + 16], "little")
            block = max(1, channels * bits // 8)
        elif cid == b"data":
            present = len(wav) - body
            data = present if size in (0, 0xFFFFFFFF) or size > present else size
            return data / block / rate if rate else 0.0
        pos = body + size + (size & 1)
    return 0.0


def _frame_energy(samples: np.ndarray, frame: int) -> np.ndarray:
    n = len(samples) // frame
    if n == 0:
        return np.zeros(0)
    x = samples[: n * frame].reshape(n, frame).astype(np.float64)
    return np.sqrt(np.mean(x**2, axis=1))


def trim_silence(
    wav: bytes, *, threshold: float = 500.0, keep_ms: int = 150, max_pause_ms: int = 600
) -> bytes:
    """Cut the silence before the first and after the last sound (keeping `keep_ms` either side),
    and shorten any pause longer than `max_pause_ms` to that length. Fewer seconds billed; nothing
    that is louder than `threshold` (RMS of 16-bit samples, about -36 dBFS) is removed."""
    samples, rate = _samples(wav)
    frame = int(rate * FRAME_MS / 1000)
    energy = _frame_energy(samples, frame)
    loud = np.flatnonzero(energy >= threshold)
    if len(loud) == 0:
        return _wav_bytes(samples[:0], rate)  # nothing but silence
    keep, max_pause = keep_ms // FRAME_MS, max_pause_ms // FRAME_MS
    first, last = max(0, loud[0] - keep), min(len(energy), loud[-1] + 1 + keep)
    out: list[np.ndarray] = []
    quiet_run = 0
    for i in range(first, last):
        if energy[i] >= threshold:
            quiet_run = 0
        else:
            quiet_run += 1
            if quiet_run > max_pause:
                continue
        out.append(samples[i * frame : (i + 1) * frame])
    tail = samples[last * frame :] if last == len(energy) else np.zeros(0, dtype=np.int16)
    return _wav_bytes(np.concatenate([*out, tail]) if out else samples[:0], rate)


def split_for_stt(
    wav: bytes, max_seconds: float = STT_MAX_SECONDS, *, threshold: float = 500.0
) -> list[bytes]:
    """Pieces of at most `max_seconds`. Each cut is at the quietest silent frame (RMS below
    `threshold`) in the second half of the window; when there is no silence there, the cut is at the
    limit. Together the pieces hold every sample of the input, in order."""
    samples, rate = _samples(wav)
    limit = int(max_seconds * rate)
    frame = int(rate * FRAME_MS / 1000)
    pieces: list[bytes] = []
    start = 0
    while len(samples) - start > limit:
        lo, hi = start + limit // 2, start + limit
        energy = _frame_energy(samples[lo:hi], frame)
        quiet = np.flatnonzero(energy < threshold)
        if len(quiet):
            best = quiet[np.argmin(energy[quiet])]
            cut = min(lo + int(best) * frame + frame // 2, hi)
        else:
            cut = hi
        pieces.append(_wav_bytes(samples[start:cut], rate))
        start = cut
    pieces.append(_wav_bytes(samples[start:], rate))
    return pieces


def wav_to_mp3(wav: bytes, kbps: int = 48, mono: bool = True) -> bytes:
    """MP3 for stored lessons and offline downloads (48 kbps mono by default)."""
    args = ["-i", "pipe:0"]
    if mono:
        args += ["-ac", "1"]
    return _run([*args, "-c:a", "libmp3lame", "-b:a", f"{kbps}k", "-f", "mp3", "pipe:1"], wav, 60.0)


def loudness_normalise(wav: bytes, target_lufs: float = -16.0) -> bytes:
    """EBU R128 loudness normalisation to about `target_lufs`, keeping the sample rate."""
    _, rate = _samples(wav)
    return _run(
        [
            "-i", "pipe:0", "-af", f"loudnorm=I={target_lufs:g}:TP=-1.5:LRA=11", "-ar", str(rate),
            "-ac", "1", "-f", "wav", "pipe:1",
        ],
        wav,
        60.0,
    )  # fmt: skip


def concat(pieces: list[bytes], gap_ms: int = 250) -> bytes:
    """Join WAV pieces with `gap_ms` of silence between them. All pieces must share a sample
    rate."""
    if not pieces:
        raise ValueError("nothing to join")
    decoded = [_samples(p) for p in pieces]
    rates = {r for _, r in decoded}
    if len(rates) != 1:
        raise ValueError(f"pieces have different sample rates: {sorted(rates)}")
    rate = rates.pop()
    gap = np.zeros(int(rate * gap_ms / 1000), dtype=np.int16)
    parts: list[np.ndarray] = []
    for i, (s, _) in enumerate(decoded):
        if i:
            parts.append(gap)
        parts.append(s)
    return _wav_bytes(np.concatenate(parts), rate)
