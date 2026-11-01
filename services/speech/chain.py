"""The provider order for speech, with fallback and a circuit breaker per provider and function.

Order comes from SPEECH_TTS_PROVIDERS and SPEECH_STT_PROVIDERS (default "bodhan,sarvam"), with
optional per-language overrides such as SPEECH_TTS_PROVIDERS_TA. A provider with no key is skipped.

Fallback: a timeout, a network or server error, a 429, a key problem (401/403) or an open circuit
moves to the next provider. A request error (400, 415, 422, input too long, empty) does not: it is
our bug and would fail the same way everywhere, so it is raised. Each provider and function has its
own breaker: it opens after 3 failures in 60 seconds and lets a trial through after 30. Every
fallback is logged (names and kinds only) and counted in `fallbacks`."""

from __future__ import annotations

import logging
import os
import re
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from services.speech.health import CircuitBreaker
from services.speech.provider import Audio, SpeechProvider, Transcript
from services.speech.sarvam import SpeechError

log = logging.getLogger(__name__)

DEFAULT_ORDER = ("bodhan", "sarvam")
MOVE_ON = frozenset({"timeout", "unavailable", "rate", "auth", "other"})
GATES = Path(__file__).resolve().parents[2] / "docs" / "evidence" / "speech_gates.md"


def order_from_env(function: str, language: str | None = None) -> list[str]:
    """SPEECH_<FUNCTION>_PROVIDERS[_<LANG>], comma-separated; default bodhan,sarvam."""
    base = f"SPEECH_{function.upper()}_PROVIDERS"
    raw = (os.environ.get(f"{base}_{language.upper()}") if language else None) or os.environ.get(
        base
    )
    if not raw:
        return list(DEFAULT_ORDER)
    return [p.strip().lower() for p in raw.split(",") if p.strip()]


class ProviderChain:
    def __init__(
        self,
        providers: Mapping[str, SpeechProvider],
        *,
        order: Callable[[str, str | None], Sequence[str]] = order_from_env,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.providers = dict(providers)
        self._order = order
        self._clock = clock
        self.breakers: dict[tuple[str, str], CircuitBreaker] = {}
        self.fallbacks: Counter[tuple[str, str, str]] = Counter()  # (function, from, kind)

    def breaker(self, name: str, function: str) -> CircuitBreaker:
        key = (name, function)
        if key not in self.breakers:
            kw = {"clock": self._clock} if self._clock else {}
            self.breakers[key] = CircuitBreaker(failures=3, cool_down_s=30.0, window_s=60.0, **kw)
        return self.breakers[key]

    def candidates(self, function: str, language: str | None) -> list[SpeechProvider]:
        """The configured providers for this function and language, in order."""
        out = []
        for name in self._order(function, language):
            p = self.providers.get(name)
            if p is not None and p.configured_for(function):
                out.append(p)
        return out

    def available(self, function: str, language: str | None = None) -> bool:
        return any(
            self.breaker(p.name, function).state != "open"
            for p in self.candidates(function, language)
        )

    def _run(
        self, function: str, language: str, call: Callable[[SpeechProvider], object]
    ) -> object:
        tried = self.candidates(function, language)
        if not tried:
            raise SpeechError("unavailable", 0, "no_provider")
        last: SpeechError | None = None
        for i, p in enumerate(tried):
            br = self.breaker(p.name, function)
            if not br.allow():
                last = SpeechError("unavailable", 0, "breaker_open")
            else:
                try:
                    result = call(p)
                except SpeechError as exc:
                    if exc.kind not in MOVE_ON:
                        raise  # our request is wrong; another provider would refuse it too
                    br.failure()
                    last = exc
                else:
                    br.success()
                    return result
            if i + 1 < len(tried):
                kind = last.code or last.kind
                self.fallbacks[(function, p.name, kind)] += 1
                log.warning(
                    "speech %s fell back from %s to %s (%s)",
                    function,
                    p.name,
                    tried[i + 1].name,
                    kind,
                )
        assert last is not None
        raise last

    def transcribe(self, wav: bytes, language: str) -> Transcript:
        result = self._run("stt", language, lambda p: p.transcribe(wav, language))
        assert isinstance(result, Transcript)
        return result

    def synthesize(
        self, text: str, language: str, voice_for: Callable[[str], str], style: str | None = None
    ) -> Audio:
        """`voice_for(provider name)` gives that provider's voice, so a fallback keeps a matching
        voice."""
        result = self._run(
            "tts", language, lambda p: p.synthesize(text, language, voice_for(p.name), style)
        )
        assert isinstance(result, Audio)
        return result


def gates_passed(path: Path = GATES) -> dict[str, bool]:
    """Reads `bodhan_tts:` and `bodhan_stt:` from the front matter of docs/evidence/speech_gates.md
    (written in Prompt 4). A missing file or value counts as not passed."""
    out = {"bodhan_tts": False, "bodhan_stt": False}
    if not path.exists():
        return out
    text = path.read_text(encoding="utf-8")
    front = text.split("---")[1] if text.startswith("---") and text.count("---") >= 2 else ""
    for key in out:
        m = re.search(rf"^{key}:\s*(\w+)", front, re.M)
        out[key] = bool(m and m.group(1).lower() == "pass")
    return out


def startup_warning(path: Path = GATES) -> str | None:
    """A log-only warning when Bodhan is first for a function whose gate has not passed. It never
    blocks the app."""
    passed = gates_passed(path)
    late = [
        f for f, gate in (("tts", "bodhan_tts"), ("stt", "bodhan_stt"))
        if order_from_env(f)[:1] == ["bodhan"] and not passed[gate]
    ]  # fmt: skip
    if not late:
        return None
    msg = (
        f"speech: Bodhan is the first provider for {' and '.join(late)} but "
        f"docs/evidence/speech_gates.md does not say its gate passed; evaluate it (Prompt 4)"
    )
    log.warning(msg)
    return msg
