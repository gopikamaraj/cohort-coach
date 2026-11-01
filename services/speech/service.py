"""The speech service the API uses: live speech through the provider chain (Bodhan first, Sarvam as
the fallback; services.speech.chain), a single Sarvam client behind a circuit breaker (the older
path, still used when a client is passed in), or a stub.

`SPEECH_MODE=stub` returns scripted transcripts and a generated tone, for tests and demos. It is
not speech recognition and says so in its `mode`. Every request writes one metadata-only row to
`speech_calls`: stage, latency, sizes, cost in INR, error kind. Never audio, never text.
"""

from __future__ import annotations

import itertools
import os
import time
from collections.abc import Callable
from datetime import date
from functools import cache
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy.orm import sessionmaker

from services.api.db import Base, SpeechCall, make_engine
from services.speech import audio, costs, stt, tts
from services.speech.bodhan import DEFAULT_VOICE as BODHAN_DEFAULT_VOICE
from services.speech.chain import ProviderChain
from services.speech.health import CircuitBreaker
from services.speech.sarvam import SarvamClient, SpeechError
from services.speech.voices import Voice

_PRICES = yaml.safe_load((Path(__file__).parent / "pricing.yaml").read_text(encoding="utf-8"))

# Scripted teacher lines for stub mode: the stub cannot hear, it plays these in turn.
STUB_LINES = {
    "en": [
        "Show me with the bundles",
        "Can you explain how you got that",
        "Let us add it back to check",
        "Well done",
    ],
    "hi": ["बंडल से दिखाओ", "तुमने कैसे किया बताओ", "जोड़कर जाँचो", "शाबाश"],
    "ta": ["கட்டுகளால் காட்டு", "எப்படி செய்தாய் சொல்", "கூட்டி சரிபார்", "நன்றாகச் செய்தாய்"],
}
_counter = itertools.count()


def speech_mode() -> str:
    return os.environ.get("SPEECH_MODE", "live")


class SpeechService:
    def __init__(
        self,
        mode: str,
        client: SarvamClient | None = None,
        breaker: CircuitBreaker | None = None,
        log: Callable[..., None] | None = None,
        budget_inr_daily: float | None = None,
        providers: ProviderChain | None = None,
        cache_store: Any = None,
    ) -> None:
        self.mode = mode
        self.chain = providers
        # A private store for synthesized lines (practice-pregen fills it with the engine's
        # template lines), so a repeated line is free even after a restart. None: memory only.
        self.cache_store = cache_store
        self.budget_inr_daily = (
            budget_inr_daily
            if budget_inr_daily is not None
            else float(os.environ.get("SPEECH_BUDGET_INR_DAILY", "200"))
        )
        self.spent_inr = 0.0
        self._day = date.today()
        self.client = client or SarvamClient()
        self.breaker = breaker or CircuitBreaker()
        self._log = log or (lambda **kw: None)

    @property
    def available(self) -> bool:
        """False when the breaker is open, live speech has no key, or today's speech budget is
        spent: the client goes to text."""
        if date.today() != self._day:
            self._day, self.spent_inr = date.today(), 0.0
        if self.spent_inr >= self.budget_inr_daily:
            return False
        if self.mode == "stub":
            return True
        if self.chain is not None:
            return self.chain.available("stt") or self.chain.available("tts")
        return self.client.configured and self.breaker.state != "open"

    def _emit(self, **fields: Any) -> None:
        self.spent_inr += float(fields.get("cost_inr", 0.0))
        self._log(**fields)

    def _record(self, ok: bool, err: SpeechError | None) -> None:
        if ok:
            self.breaker.success()
        elif err is not None and err.kind != "bad_request":
            self.breaker.failure()

    def transcribe(
        self, recording: bytes, lang: str, budget: costs.SessionSpeechBudget | None = None
    ) -> str:
        if self.mode != "stub" and self.chain is not None:
            return self._chain_transcribe(recording, lang, budget)
        t0 = time.monotonic()
        seconds, err = 0.0, None
        try:
            if self.mode == "stub":
                text = STUB_LINES.get(lang, STUB_LINES["en"])[next(_counter) % 4]
            else:
                if not self.breaker.allow():
                    raise SpeechError("unavailable", 0, "breaker_open")
                got = stt.transcribe(self.client, recording, lang)
                text, seconds = got.text, got.seconds
                self._record(True, None)
            return text
        except SpeechError as exc:
            err = exc
            if exc.code != "breaker_open":
                self._record(False, exc)
            raise
        finally:
            self._emit(
                stage="stt",
                mode=self.mode,
                language=lang,
                latency_ms=int((time.monotonic() - t0) * 1000),
                audio_bytes=len(recording),
                seconds=seconds,
                cost_inr=seconds / 3600 * _PRICES["stt_per_hour_of_audio"],
                error_kind=err.kind if err else None,
            )

    def synthesize(
        self,
        text: str,
        lang: str,
        voice: Voice,
        budget: costs.SessionSpeechBudget | None = None,
        style: str | None = None,
        bodhan_voice: str | None = None,
        order: list[str] | None = None,
    ) -> bytes:
        return self.synthesize_ex(text, lang, voice, budget, style, bodhan_voice, order)[0]

    def synthesize_ex(
        self,
        text: str,
        lang: str,
        voice: Voice,
        budget: costs.SessionSpeechBudget | None = None,
        style: str | None = None,
        bodhan_voice: str | None = None,
        order: list[str] | None = None,
    ) -> tuple[bytes, str]:
        """(OGG/Opus bytes, who made it: a provider name, "cache", "stub" or "sarvam")."""
        if self.mode != "stub" and self.chain is not None:
            return self._chain_synthesize(text, lang, voice, budget, style, bodhan_voice, order)
        return self._legacy_synthesize(
            text, lang, voice
        ), self.mode if self.mode == "stub" else "sarvam"

    def _legacy_synthesize(self, text: str, lang: str, voice: Voice) -> bytes:
        t0 = time.monotonic()
        err, cached, size = None, False, 0
        try:
            if self.mode == "stub":
                wav = audio.tone(min(0.4 + 0.05 * len(text.split()), 3.0), 400 * voice.pitch)
                try:
                    out = audio.to_ogg_opus(wav)
                except SpeechError:
                    out = wav
            else:
                if not self.breaker.allow():
                    raise SpeechError("unavailable", 0, "breaker_open")
                out, cached = tts.synthesize(self.client, text, lang, voice)
                self._record(True, None)
            size = len(out)
            return out
        except SpeechError as exc:
            err = exc
            if exc.code != "breaker_open":
                self._record(False, exc)
            raise
        finally:
            self._emit(
                stage="tts",
                mode=self.mode,
                language=lang,
                latency_ms=int((time.monotonic() - t0) * 1000),
                audio_bytes=size,
                characters=len(text),
                cost_inr=0.0 if cached else len(text) / 10000 * _PRICES["tts_per_10k_characters"],
                from_cache=cached,
                error_kind=err.kind if err else None,
            )

    # --- The provider chain (Bodhan first, Sarvam as the fallback) --------------------------------

    def _chain_transcribe(
        self, recording: bytes, lang: str, budget: costs.SessionSpeechBudget | None
    ) -> str:
        """Any phone format -> 16 kHz mono WAV -> trim silence -> pieces of at most 28 s -> the
        chain -> one transcript joined with spaces. The audio is never kept."""
        assert self.chain is not None
        t0 = time.monotonic()
        seconds, cost, err = 0.0, 0.0, None
        try:
            wav = audio.to_wav_16k_mono(recording)
            if audio.wav_seconds(wav) > stt.MAX_SECONDS:
                raise SpeechError("bad_request", 0, "too_long")
            wav = audio.trim_silence(wav)
            heard = audio.wav_seconds(wav)
            if heard == 0.0:
                return ""  # nothing but silence: nothing sent, nothing paid
            if budget is not None and not budget.allows_stt(heard):
                raise SpeechError("rate", 0, "session_cap")
            texts = []
            for part in audio.split_for_stt(wav):
                got = self.chain.transcribe(part, lang)
                seconds += got.seconds_billed
                cost += costs.cost_inr(got.provider, "stt", seconds=got.seconds_billed)
                texts.append(got.text)
            if budget is not None:
                budget.charge_stt(seconds)
            return " ".join(t for t in texts if t)
        except SpeechError as exc:
            err = exc
            raise
        finally:
            self._emit(
                stage="stt",
                mode=self.mode,
                language=lang,
                latency_ms=int((time.monotonic() - t0) * 1000),
                audio_bytes=len(recording),
                seconds=seconds,
                cost_inr=cost,
                error_kind=err.kind if err else None,
            )

    def _chain_synthesize(
        self,
        text: str,
        lang: str,
        voice: Voice,
        budget: costs.SessionSpeechBudget | None,
        style: str | None,
        bodhan_voice: str | None = None,
        order: list[str] | None = None,
    ) -> tuple[bytes, str]:
        """One line through the chain -> OGG/Opus, pitch-shifted for a child's voice. Cached (in
        memory and, when there is one, in the private store) by text, language, voice and style, so
        a repeated line costs nothing."""
        assert self.chain is not None
        t0 = time.monotonic()
        err, cached, size, cost = None, False, 0, 0.0
        bodhan = bodhan_voice or BODHAN_DEFAULT_VOICE.get(lang, "Kavya")
        key = tts.cache_key(text, lang, voice, f"chain:{style or ''}:{bodhan}")
        stored = f"line-cache/{key}.ogg"
        try:
            hit = tts.CACHE.get(key)
            if hit is None and self.cache_store is not None and self.cache_store.size(stored):
                hit = self.cache_store.get(stored)
                tts.CACHE.put(key, hit)
            if hit is not None:
                cached, size = True, len(hit)
                return hit, "cache"
            if budget is not None and not budget.allows_tts(len(text)):
                raise SpeechError("rate", 0, "session_cap")

            def voice_for(provider: str) -> str:
                return bodhan if provider == "bodhan" else voice.speaker

            got = self.chain.synthesize(text, lang, voice_for, style, order=order)
            cost = costs.cost_inr(got.provider, "tts", chars=got.chars_billed)
            if budget is not None:
                budget.charge_tts(got.chars_billed)
            out = audio.to_ogg_opus(got.data, pitch_ratio=voice.pitch, input_rate=got.sample_rate)
            tts.CACHE.put(key, out)
            if self.cache_store is not None:
                self.cache_store.put(stored, out, "audio/ogg")
            size = len(out)
            return out, got.provider
        except SpeechError as exc:
            err = exc
            raise
        finally:
            self._emit(
                stage="tts",
                mode=self.mode,
                language=lang,
                latency_ms=int((time.monotonic() - t0) * 1000),
                audio_bytes=size,
                characters=len(text),
                cost_inr=cost,
                from_cache=cached,
                error_kind=err.kind if err else None,
            )


def default_chain(*, live: bool = True) -> ProviderChain:
    """Bodhan and Sarvam with keys from the environment, in the SPEECH_*_PROVIDERS order.

    `live` (the API: a teacher is waiting) lets a Bodhan call wait for its rate allowance at most
    BODHAN_LIVE_PACE_MAX_WAIT_S (2 s) before the chain moves to Sarvam; batch work (lessons,
    pre-generation) waits up to BODHAN_PACE_MAX_WAIT_S (90 s)."""
    from services.speech.bodhan import BodhanClient, BodhanProvider, _float_env
    from services.speech.provider import SarvamProvider

    wait = _float_env("BODHAN_LIVE_PACE_MAX_WAIT_S", 2.0) if live else None
    client = BodhanClient(pace_max_wait_s=wait)
    return ProviderChain({"bodhan": BodhanProvider(client), "sarvam": SarvamProvider()})


def _audio_store_or_none() -> Any:
    from services.media.storage import StorageNotConfigured, audio_store

    try:
        return audio_store()
    except StorageNotConfigured:
        return None


def _sql_log() -> Callable[..., None]:
    engine = make_engine()
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def log(**fields: Any) -> None:
        with factory() as s:
            s.add(SpeechCall(**fields))
            s.commit()

    return log


@cache
def default_service() -> SpeechService:
    from ai import config

    config.load_env()
    mode = speech_mode()
    chain = default_chain() if mode != "stub" else None
    store = _audio_store_or_none() if mode != "stub" else None
    return SpeechService(mode, log=_sql_log(), providers=chain, cache_store=store)
