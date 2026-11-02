"""Lesson audio: split a lesson script into sentences, voice it in chunks of one or two sentences,
check each chunk by transcribing it back, and stitch one MP3 with a timing map. Offline, in batch.

- Sentences end at . ? ! or । followed by a space, or at a line break; a blank line starts a new
  section. A full stop between digits (3.5) or the signs in a sum (703 − 468) never split.
- Chunks hold one or two sentences of the same section, up to a target length (220 characters by
  default, never more than 300). A chunk whose audio is longer than 28 s is split and voiced again.
- One voice per lesson: the providers are tried in order (Bodhan, then Sarvam), and if any chunk
  still fails after one retry, the WHOLE lesson is made again with the next provider and its voice.
  If every provider fails, the lesson is text only (LessonAudioUnavailable).
- Every chunk is cached in private storage by sha256 of (provider, model, voice, language, style,
  normalised text, pipeline version), so a repeated lesson makes no provider call, and a lesson
  whose chunks are all cached plays even with every provider down.
- Round trip: each chunk is transcribed back and compared with its text (character error rate after
  normalising punctuation and numbers). Above the threshold (0.25) it is made once more, then
  flagged. The check never blocks a lesson; a coach can listen to the flagged sentences.
- Stitching: 250 ms between sentences, 500 ms between sections, loudness normalised, MP3 mono at
  48 kbps (LESSON_MP3_KBPS). The timing map gives each sentence's start and end in seconds; inside
  a two-sentence chunk the split is by characters (an estimate; providers return no timestamps).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import unicodedata
from collections.abc import Callable, Collection
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from services.speech import audio, costs, textnorm
from services.speech.sarvam import SpeechError
from services.speech.voices import Voice
from services.usage import context as usage_context

log = logging.getLogger(__name__)

PIPELINE_VERSION = "lesson-audio-1"
RATE = 24000
VOICES = Path(__file__).resolve().parents[2] / "content" / "voices.yaml"
MAX_CHUNK_SECONDS = 28.0
LEGACY_VOICE = "ritu"  # the narrator when speech has no provider chain (stub mode, tests)


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "") or default)
    except ValueError:
        return default


def settings() -> dict[str, Any]:
    return {
        "target_chars": _int("LESSON_CHUNK_TARGET_CHARS", 220),
        "max_chars": _int("LESSON_CHUNK_MAX_CHARS", 300),
        "sentence_gap_ms": _int("LESSON_SENTENCE_GAP_MS", 250),
        "section_gap_ms": _int("LESSON_SECTION_GAP_MS", 500),
        "kbps": _int("LESSON_MP3_KBPS", 48),
        "max_cer": _float("LESSON_ROUNDTRIP_MAX_CER", 0.25),
        "concurrency": _int("LESSON_TTS_CONCURRENCY", 3),
    }


@cache
def lesson_voices() -> dict[str, dict[str, str]]:
    data = yaml.safe_load(VOICES.read_text(encoding="utf-8"))
    out: dict[str, dict[str, str]] = data["lessons"]
    return out


# --- sentences and chunks -------------------------------------------------------------------------


@dataclass(frozen=True)
class Sentence:
    index: int
    text: str
    section: int
    hard_break: bool = False  # a short pause follows: a chunk never runs on past it


@dataclass(frozen=True)
class Chunk:
    index: int
    text: str
    section: int
    sentences: tuple[int, ...]  # sentence indices it holds (one sentence may span several chunks)


_END = re.compile(r"(?<=[.?!।])\s+")


def split_sentences(script: str) -> list[Sentence]:
    """Sentences in order, with their section (a blank line starts a new one)."""
    out: list[Sentence] = []
    # spoken-layer pause tokens: a long pause is a section break, a short one ends the sentence
    script = re.sub(r"\s*\[pause:long\]\s*", "\n\n", script)
    script = re.sub(r"[ \t]*\[pause\][ \t]*", "\x1f\n", script)
    sections = [s for s in re.split(r"\n\s*\n", script.strip()) if s.strip()]
    for sec, block in enumerate(sections):
        for line in block.splitlines():
            hard = line.endswith("\x1f")
            parts = [p for p in _END.split(line.strip().rstrip("\x1f")) if p.strip()]
            for k, part in enumerate(parts):
                text = re.sub(r"\s+", " ", part).strip()
                if text:
                    out.append(Sentence(len(out), text, sec, hard and k == len(parts) - 1))
    return out


def _pieces(text: str, maximum: int) -> list[str]:
    """A sentence longer than `maximum`, cut at commas or semicolons, else at spaces."""
    if len(text) <= maximum:
        return [text]
    out: list[str] = []
    cur = ""
    for part in re.split(r"(?<=[,;:])\s+|\s+", text):
        if cur and len(cur) + 1 + len(part) > maximum:
            out.append(cur)
            cur = part
        else:
            cur = f"{cur} {part}".strip()
    if cur:
        out.append(cur)
    return out


def make_chunks(
    sentences: list[Sentence], target: int = 220, maximum: int = 300, max_sentences: int = 2
) -> list[Chunk]:
    """One or two sentences of one section per chunk, up to `target` characters (never over
    `maximum`; a longer sentence is cut into pieces)."""
    out: list[Chunk] = []
    cur: list[Sentence] = []

    def flush() -> None:
        if cur:
            out.append(
                Chunk(
                    len(out),
                    " ".join(s.text for s in cur),
                    cur[0].section,
                    tuple(s.index for s in cur),
                )
            )
            cur.clear()

    for s in sentences:
        if len(s.text) > maximum:
            flush()
            for piece in _pieces(s.text, maximum):
                out.append(Chunk(len(out), piece, s.section, (s.index,)))
            continue
        joined = len(" ".join(x.text for x in cur)) + 1 + len(s.text)
        if cur and (
            len(cur) >= max_sentences
            or cur[0].section != s.section
            or joined > target
            or cur[-1].hard_break
        ):
            flush()
        cur.append(s)
    flush()
    return out


# --- who voices it --------------------------------------------------------------------------------


@dataclass
class Voicer:
    """One provider with the lesson's voice and style for one language."""

    name: str
    voice: str
    style: str | None
    model: str
    configured: bool
    synth: Callable[[str], bytes]
    transcribe: Callable[[bytes], str] | None = None
    parallel_limit: Callable[[], int | None] = lambda: None
    price_name: str = ""


def voicers_for(speech: Any, language: str) -> list[Voicer]:
    """The providers in order for this language (configured or not: an unconfigured one can still
    serve its cached chunks). Without a provider chain (stub mode, tests), the speech object
    itself."""
    chain = getattr(speech, "chain", None)
    if chain is None:
        voice = Voice(LEGACY_VOICE, 1.0, 1.0)
        return [
            Voicer(
                "speech",
                LEGACY_VOICE,
                None,
                "legacy",
                True,
                lambda text: bytes(speech.synthesize(text, language, voice)),
            )
        ]
    cast = lesson_voices().get(language, lesson_voices()["en"])
    out: list[Voicer] = []
    for name in chain._order("tts", language):
        p = chain.providers.get(name)
        if p is None:
            continue
        narrator = cast.get(name, cast.get("sarvam", LEGACY_VOICE))
        style = cast.get("style") if name == "bodhan" else None
        out.append(_voicer(p, name, narrator, style, language))
    return out


def _voicer(p: Any, name: str, voice: str, style: str | None, language: str) -> Voicer:
    def synth(text: str) -> bytes:
        return bytes(p.synthesize(text, language, voice, style).data)

    def heard(wav: bytes) -> str:
        return str(p.transcribe(wav, language).text)

    def parallel() -> int | None:
        client = getattr(p, "client", None)
        raw = getattr(client, "last_rate_limits", {}).get("x-ratelimit-limit-parallel-requests")
        return int(raw) if raw and str(raw).isdigit() else None

    model = {"bodhan": "indic-speak", "sarvam": "bulbul:v3"}.get(name, name)
    return Voicer(
        name,
        voice,
        style,
        model,
        bool(p.configured_for("tts")),
        synth,
        heard if p.configured_for("stt") else None,
        parallel,
        name,
    )


# --- cache ----------------------------------------------------------------------------------------


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()


def chunk_key(v: Voicer, language: str, text: str) -> str:
    raw = json.dumps(
        [v.name, v.model, v.voice, language, v.style or "", _norm(text), PIPELINE_VERSION],
        ensure_ascii=False,
    )
    return f"lesson-chunks/{hashlib.sha256(raw.encode()).hexdigest()}"


class LessonAudioUnavailable(RuntimeError):
    """Every provider failed: the lesson stays text only until someone tries again."""

    def __init__(self, reasons: dict[str, str]) -> None:
        super().__init__("; ".join(f"{k}: {v}" for k, v in reasons.items()) or "no provider")
        self.reasons = reasons


# --- the result ----------------------------------------------------------------------------------


@dataclass
class LessonAudio:
    mp3: bytes
    seconds: float
    sentences: list[str]
    sections: list[int]
    timing: list[dict[str, float]]  # [{"i": sentence index, "start": s, "end": s}]
    checks: list[dict[str, Any]]  # per sentence: {"i", "cer", "flagged"} (cer None when unchecked)
    chunks: list[dict[str, Any]]  # [{"key", "sentences", "seconds", "cer", "flagged"}]
    provider: str
    voice: str
    style: str | None
    chars_billed: int = 0
    stt_seconds: float = 0.0
    cost_inr: float = 0.0
    from_cache: bool = False
    fallbacks: list[str] = field(default_factory=list)

    @property
    def summary(self) -> dict[str, int]:
        checked = [c for c in self.checks if c["cer"] is not None]
        flagged = sum(1 for c in checked if c["flagged"])
        return {
            "sentences": len(self.checks),
            "checked": len(checked),
            "passed": len(checked) - flagged,
            "flagged": flagged,
        }


# --- generating -----------------------------------------------------------------------------------


def _pcm(raw: bytes) -> np.ndarray:
    """Mono 16-bit samples at 24 kHz from whatever a provider returned (WAV read directly when it is
    already 24 kHz; anything else through ffmpeg)."""
    if raw[:4] == b"RIFF":
        try:
            samples, rate = audio._samples(raw)
            if rate == RATE:
                return samples
        except Exception:  # noqa: BLE001 - a WAV the wave module cannot read goes to ffmpeg
            pass
    return np.frombuffer(audio.to_pcm(raw), dtype=np.int16)


def _synth_once_or_twice(v: Voicer, text: str) -> bytes:
    try:
        return v.synth(text)
    except SpeechError as exc:
        if exc.kind == "bad_request":
            raise
        return v.synth(text)  # one retry


def _voice_all(
    v: Voicer,
    language: str,
    chunks: list[Chunk],
    store: Any,
    fresh: Collection[int],
    concurrency: int,
) -> tuple[list[bytes], list[bool], int]:
    """(raw audio per chunk, which came from the cache, characters billed). Raises on a failure."""
    raws: list[bytes | None] = [None] * len(chunks)
    cached = [False] * len(chunks)
    todo: list[int] = []
    for c in chunks:
        key = chunk_key(v, language, c.text)
        if c.index not in fresh and store.size(key) is not None:
            raws[c.index] = store.get(key)
            cached[c.index] = True
        else:
            todo.append(c.index)
    if todo and not v.configured:
        raise SpeechError("auth", 0, "no_key")
    billed = 0

    def run(i: int) -> tuple[int, bytes]:
        return i, _synth_once_or_twice(v, chunks[i].text)

    if todo:
        first_i, first = run(todo[0])  # one call first, so its rate-limit headers can be read
        results = [(first_i, first)]
        limit = min(concurrency, v.parallel_limit() or concurrency)
        with ThreadPoolExecutor(max_workers=max(1, limit)) as pool:
            futures = [usage_context.submit(pool, run, i) for i in todo[1:]]
            results += [f.result() for f in futures]
        for i, raw in results:
            store.put(chunk_key(v, language, chunks[i].text), raw, "application/octet-stream")
            raws[i] = raw
            billed += len(chunks[i].text)
    return [r for r in raws if r is not None], cached, billed


def _resplit_long(
    chunks: list[Chunk], pcms: list[np.ndarray], sentences: list[Sentence]
) -> list[Chunk] | None:
    """Chunks to make again because their audio is longer than 28 s (only those with two or more
    sentences can be split). None when nothing needs splitting."""
    out: list[Chunk] = []
    changed = False
    for c, pcm in zip(chunks, pcms, strict=True):
        if len(pcm) / RATE > MAX_CHUNK_SECONDS and len(c.sentences) > 1:
            changed = True
            for si in c.sentences:
                s = sentences[si]
                out.append(Chunk(0, s.text, s.section, (si,)))
        else:
            out.append(c)
    if not changed:
        return None
    return [Chunk(i, c.text, c.section, c.sentences) for i, c in enumerate(out)]


def stitch(
    pcms: list[np.ndarray],
    chunks: list[Chunk],
    sentences: list[Sentence],
    sentence_gap_ms: int = 250,
    section_gap_ms: int = 500,
) -> tuple[bytes, float, list[dict[str, float]]]:
    """(WAV bytes at 24 kHz, seconds, timing map). Gaps go between chunks: the section gap when the
    section changes, else the sentence gap."""
    parts: list[np.ndarray] = []
    spans: dict[int, list[float]] = {}
    t = 0.0
    for k, (c, pcm) in enumerate(zip(chunks, pcms, strict=True)):
        if k:
            gap_ms = section_gap_ms if c.section != chunks[k - 1].section else sentence_gap_ms
            gap = np.zeros(int(RATE * gap_ms / 1000), dtype=np.int16)
            parts.append(gap)
            t += len(gap) / RATE
        dur = len(pcm) / RATE
        weights = [len(sentences[i].text) for i in c.sentences]
        total = sum(weights) or 1
        start = t
        for i, w in zip(c.sentences, weights, strict=True):
            end = start + dur * w / total
            span = spans.setdefault(i, [start, end])
            span[1] = end  # a sentence cut into several chunks spans all of them
            start = end
        parts.append(pcm)
        t += dur
    samples = np.concatenate(parts) if parts else np.zeros(0, dtype=np.int16)
    timing = [
        {"i": i, "start": round(s, 3), "end": round(e, 3)} for i, (s, e) in sorted(spans.items())
    ]
    return audio._wav_bytes(samples, RATE), len(samples) / RATE, timing


def encode_mp3(wav: bytes, kbps: int) -> bytes:
    """Loudness to about -16 LUFS, then MP3 mono."""
    return audio.wav_to_mp3(audio.loudness_normalise(wav, -16.0), kbps=kbps)


def _check(
    v: Voicer, language: str, chunk: Chunk, raw: bytes, store: Any, max_cer: float
) -> tuple[float | None, float]:
    """(character error rate, seconds of audio sent) for one chunk; the result is cached beside the
    chunk so a cached chunk is not checked twice."""
    if v.transcribe is None:
        return None, 0.0
    key = chunk_key(v, language, chunk.text) + ".check"
    if store.size(key) is not None:
        return float(json.loads(store.get(key))["cer"]), 0.0
    wav = audio.to_wav_16k_mono(raw)
    seconds = audio.wav_seconds(wav)
    heard = v.transcribe(wav) if seconds <= MAX_CHUNK_SECONDS else ""
    rate = textnorm.cer(chunk.text, heard, language)
    store.put(key, json.dumps({"cer": rate}).encode(), "application/json")
    return rate, seconds


def generate(
    script: str,
    language: str,
    speech: Any,
    store: Any,
    *,
    fresh: Collection[int] = (),
    only_provider: str | None = None,
    check: bool = True,
    max_sentences: int = 2,
) -> LessonAudio:
    """Voice one lesson. `fresh` = chunk indices to make again even if cached (regenerate a
    sentence); `only_provider` keeps a lesson on the provider it already uses."""
    cfg = settings()
    sentences = split_sentences(script)
    if not sentences:
        raise ValueError("the lesson has no text to voice")
    chunks = make_chunks(sentences, cfg["target_chars"], cfg["max_chars"], max_sentences)
    voicers = voicers_for(speech, language)
    if only_provider:
        voicers = [v for v in voicers if v.name == only_provider] or voicers
    reasons: dict[str, str] = {}
    fallbacks: list[str] = []
    for v in voicers:
        try:
            raws, cached, billed = _voice_all(v, language, chunks, store, fresh, cfg["concurrency"])
            pcms = [_pcm(r) for r in raws]
            again = _resplit_long(chunks, pcms, sentences)
            if again is not None:
                chunks = again
                raws, cached, more = _voice_all(v, language, chunks, store, (), cfg["concurrency"])
                billed += more
                pcms = [_pcm(r) for r in raws]
        except SpeechError as exc:
            reasons[v.name] = exc.code or exc.kind
            if v.configured:
                fallbacks.append(f"{v.name}:{exc.code or exc.kind}")
                log.warning("lesson audio: %s failed (%s); next provider", v.name, exc.kind)
            continue
        return _finish(
            v, language, sentences, chunks, raws, pcms, cached, billed, store, cfg, check, fallbacks
        )
    raise LessonAudioUnavailable(reasons)


def _finish(
    v: Voicer,
    language: str,
    sentences: list[Sentence],
    chunks: list[Chunk],
    raws: list[bytes],
    pcms: list[np.ndarray],
    cached: list[bool],
    billed: int,
    store: Any,
    cfg: dict[str, Any],
    check: bool,
    fallbacks: list[str],
) -> LessonAudio:
    stt_seconds = 0.0
    rates: list[float | None] = [None] * len(chunks)
    if check and v.transcribe is not None and v.configured:
        for c in chunks:
            rate, sent = _check(v, language, c, raws[c.index], store, cfg["max_cer"])
            stt_seconds += sent
            if rate is not None and rate > cfg["max_cer"]:
                # made once more; then the result stands and the sentence is flagged if still off
                raw = _synth_once_or_twice(v, c.text)
                billed += len(c.text)
                key = chunk_key(v, language, c.text)
                store.put(key, raw, "application/octet-stream")
                store.delete(key + ".check")
                raws[c.index], pcms[c.index] = raw, _pcm(raw)
                rate, sent = _check(v, language, c, raw, store, cfg["max_cer"])
                stt_seconds += sent
            rates[c.index] = rate
    wav, seconds, timing = stitch(
        pcms, chunks, sentences, cfg["sentence_gap_ms"], cfg["section_gap_ms"]
    )
    mp3 = encode_mp3(wav, cfg["kbps"])
    checks: list[dict[str, Any]] = []
    for s in sentences:
        mine = [rates[c.index] for c in chunks if s.index in c.sentences]
        known = [r for r in mine if r is not None]
        rate = max(known) if known else None
        checks.append(
            {
                "i": s.index,
                "cer": None if rate is None else round(rate, 3),
                "flagged": rate is not None and rate > cfg["max_cer"],
            }
        )
    chunk_rows = [
        {
            "key": chunk_key(v, language, c.text),
            "sentences": list(c.sentences),
            "seconds": round(len(pcms[c.index]) / RATE, 3),
            "cer": None if rates[c.index] is None else round(float(rates[c.index] or 0), 3),
            "flagged": rates[c.index] is not None and float(rates[c.index] or 0) > cfg["max_cer"],
            "cached": cached[c.index],
        }
        for c in chunks
    ]
    price = v.price_name or v.name
    cost = costs.cost_inr(price, "tts", chars=billed) + costs.cost_inr(
        price, "stt", seconds=stt_seconds
    )
    return LessonAudio(
        mp3=mp3,
        seconds=round(seconds, 3),
        sentences=[s.text for s in sentences],
        sections=[s.section for s in sentences],
        timing=timing,
        checks=checks,
        chunks=chunk_rows,
        provider=v.name,
        voice=v.voice,
        style=v.style,
        chars_billed=billed,
        stt_seconds=round(stt_seconds, 2),
        cost_inr=round(cost, 4),
        from_cache=billed == 0 and stt_seconds == 0,
        fallbacks=fallbacks,
    )


def chunk_of_sentence(script: str, sentence_index: int) -> int:
    """Which chunk holds a sentence (for "regenerate this sentence")."""
    cfg = settings()
    for c in make_chunks(split_sentences(script), cfg["target_chars"], cfg["max_chars"]):
        if sentence_index in c.sentences:
            return c.index
    raise IndexError(sentence_index)


def estimate(script: str, language: str, provider: str = "bodhan") -> dict[str, float]:
    """Characters and estimated cost (text to speech plus the round trip at ~15 characters a
    second)."""
    chars = sum(len(s.text) for s in split_sentences(script))
    seconds = chars / 15.0
    cost = costs.cost_inr(provider, "tts", chars=chars) + costs.cost_inr(
        provider, "stt", seconds=seconds
    )
    return {"chars": float(chars), "cost_inr": round(cost, 4)}
