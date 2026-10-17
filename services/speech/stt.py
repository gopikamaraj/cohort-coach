"""Speech to text: whatever the phone recorded -> 16 kHz mono WAV -> chunks of at most 28 s cut at
silences -> Sarvam -> one transcript. The audio is never stored."""

from __future__ import annotations

from dataclasses import dataclass

from services.speech import audio
from services.speech.sarvam import LANGUAGE_CODES, SarvamClient, SpeechError


@dataclass(frozen=True)
class Transcript:
    text: str
    seconds: float
    chunks: int


MAX_SECONDS = 30.0  # one real-time request; the phone stops at 25 s, so more is not from us


def transcribe(client: SarvamClient, recording: bytes, lang: str) -> Transcript:
    wav = audio.to_wav16k(recording)
    if audio.wav_seconds(wav) > MAX_SECONDS:
        raise SpeechError("bad_request", 0, "too_long")
    code = LANGUAGE_CODES.get(lang, "unknown")
    parts = audio.split_at_silences(wav)
    texts = [client.transcribe(p, code).transcript for p in parts]
    return Transcript(" ".join(t for t in texts if t), audio.wav_seconds(wav), len(parts))
