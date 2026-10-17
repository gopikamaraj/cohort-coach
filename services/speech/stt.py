"""Speech to text: whatever the phone recorded -> 16 kHz mono WAV -> chunks of at most 28 s cut at
silences -> Sarvam -> one transcript. The audio is never stored."""

from __future__ import annotations

from dataclasses import dataclass

from services.speech import audio
from services.speech.sarvam import LANGUAGE_CODES, SarvamClient


@dataclass(frozen=True)
class Transcript:
    text: str
    seconds: float
    chunks: int


def transcribe(client: SarvamClient, recording: bytes, lang: str) -> Transcript:
    wav = audio.to_wav16k(recording)
    code = LANGUAGE_CODES.get(lang, "unknown")
    parts = audio.split_at_silences(wav)
    texts = [client.transcribe(p, code).transcript for p in parts]
    return Transcript(" ".join(t for t in texts if t), audio.wav_seconds(wav), len(parts))
