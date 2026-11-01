"""One interface for every speech provider: Bodhan (first), Sarvam (fallback), and a mock for tests.

A provider turns one short clip into text (`transcribe`) or one short text into audio
(`synthesize`). It does not convert, split or trim: callers hand it 16 kHz mono WAV of at most
`capabilities.max_audio_seconds`, and text of at most `capabilities.max_input_chars`
(services.speech.audio and services.speech.chain do that work). Providers never log the audio, the
text, or a key."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from services.speech import audio
from services.speech.sarvam import LANGUAGE_CODES, SarvamClient, SpeechError


@dataclass(frozen=True)
class Transcript:
    text: str
    seconds_billed: float
    provider: str
    request_id: str | None = None


@dataclass(frozen=True)
class Audio:
    data: bytes
    format: str  # "wav" | "mp3"
    sample_rate: int
    seconds: float
    chars_billed: int
    provider: str
    request_id: str | None = None


@dataclass(frozen=True)
class Capabilities:
    max_audio_seconds: float  # per speech-to-text request
    accepted_formats: frozenset[str]  # what the provider takes for speech to text
    max_input_chars: int  # per text-to-speech request (a sentence or two)
    voices: frozenset[str] = field(default_factory=frozenset)
    styles: frozenset[str] = field(default_factory=frozenset)


class SpeechProvider(Protocol):
    name: str

    def configured_for(self, function: str) -> bool:
        """False when the provider has no key for "stt" or "tts": the chain skips it there."""
        ...

    @property
    def capabilities(self) -> Capabilities: ...

    def transcribe(self, wav: bytes, language: str) -> Transcript: ...

    def synthesize(self, text: str, language: str, voice: str, style: str | None) -> Audio: ...


class SarvamProvider:
    """The existing Sarvam client behind the interface. Its requests are unchanged: same models,
    same language codes, same retries."""

    name = "sarvam"

    def __init__(self, client: SarvamClient | None = None) -> None:
        self.client = client or SarvamClient()

    def configured_for(self, function: str) -> bool:
        return self.client.configured

    @property
    def capabilities(self) -> Capabilities:
        return Capabilities(30.0, frozenset({"wav"}), 2500)

    def transcribe(self, wav: bytes, language: str) -> Transcript:
        got = self.client.transcribe(wav, LANGUAGE_CODES.get(language, "unknown"))
        return Transcript(got.transcript, audio.wav_seconds(wav), self.name)

    def synthesize(self, text: str, language: str, voice: str, style: str | None) -> Audio:
        # Sarvam has no styles; `style` is ignored. `voice` is a Sarvam speaker name.
        mp3 = self.client.synthesize(text, LANGUAGE_CODES.get(language, "en-IN"), voice)
        return Audio(mp3, "mp3", 24000, 0.0, len(text), self.name)


class MockProvider:
    """For tests: scripted answers and failures, no network."""

    def __init__(
        self,
        name: str = "mock",
        *,
        text: str = "mock transcript",
        fail: SpeechError | None = None,
        configured: bool = True,
        max_audio_seconds: float = 30.0,
        max_input_chars: int = 300,
    ) -> None:
        self.name = name
        self.text = text
        self.fail = fail
        self._configured = configured
        self._caps = Capabilities(max_audio_seconds, frozenset({"wav"}), max_input_chars)
        self.calls: list[tuple[str, str]] = []  # (function, language)

    def configured_for(self, function: str) -> bool:
        return self._configured

    @property
    def capabilities(self) -> Capabilities:
        return self._caps

    def transcribe(self, wav: bytes, language: str) -> Transcript:
        self.calls.append(("stt", language))
        if self.fail:
            raise self.fail
        return Transcript(self.text, audio.wav_seconds(wav), self.name, "mock-req")

    def synthesize(self, text: str, language: str, voice: str, style: str | None) -> Audio:
        self.calls.append(("tts", language))
        if self.fail:
            raise self.fail
        wav = audio.tone(0.5, 440)
        return Audio(wav, "wav", 24000, 0.5, len(text), self.name, "mock-req")
