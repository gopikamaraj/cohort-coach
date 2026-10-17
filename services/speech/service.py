"""The speech service the API uses: live Sarvam or a stub, behind a circuit breaker.

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
from services.speech import audio, stt, tts
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
    ) -> None:
        self.mode = mode
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
        return self.client.configured and self.breaker.state != "open"

    def _emit(self, **fields: Any) -> None:
        self.spent_inr += float(fields.get("cost_inr", 0.0))
        self._log(**fields)

    def _record(self, ok: bool, err: SpeechError | None) -> None:
        if ok:
            self.breaker.success()
        elif err is not None and err.kind != "bad_request":
            self.breaker.failure()

    def transcribe(self, recording: bytes, lang: str) -> str:
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

    def synthesize(self, text: str, lang: str, voice: Voice) -> bytes:
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
    return SpeechService(speech_mode(), log=_sql_log())
