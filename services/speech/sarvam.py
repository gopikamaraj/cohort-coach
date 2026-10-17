"""A thin client for Sarvam's speech APIs (read from their docs on 2026-10-17; see DECISIONS.md).

Auth is the `api-subscription-key` header. Failures become a `SpeechError` with a kind the rest
of the app understands; 429 and 503 and timeouts are retried a bounded number of times. The
audio and the text passing through are never logged.
"""

from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass
from typing import Literal

import httpx

BASE_URL = "https://api.sarvam.ai"
STT_MODEL = "saaras:v4"
TTS_MODEL = "bulbul:v3"
LANGUAGE_CODES = {"en": "en-IN", "hi": "hi-IN", "ta": "ta-IN"}
Kind = Literal["auth", "rate", "timeout", "unavailable", "bad_request", "other"]


class SpeechError(Exception):
    def __init__(self, kind: Kind, status: int = 0, code: str = "") -> None:
        super().__init__(f"{kind} ({status} {code})".strip())
        self.kind: Kind = kind
        self.status = status
        self.code = code


@dataclass(frozen=True)
class SttResult:
    transcript: str
    language_code: str | None
    language_probability: float | None


def _kind(status: int) -> Kind:
    if status in (401, 403):
        return "auth"
    if status == 429:
        return "rate"
    if status in (400, 413, 422):
        return "bad_request"
    if status >= 500:
        return "unavailable"
    return "other"


class SarvamClient:
    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = BASE_URL,
        client: httpx.Client | None = None,
        timeout: float = 15.0,
        retries: int = 1,
        sleep: object = time.sleep,
    ) -> None:
        self._key = api_key if api_key is not None else os.environ.get("SARVAM_API_KEY", "")
        self._base = base_url.rstrip("/")
        self._http = client or httpx.Client(timeout=timeout)
        self._retries = retries
        self._sleep = sleep

    @property
    def configured(self) -> bool:
        return bool(self._key)

    def _post(self, path: str, **kwargs: object) -> httpx.Response:
        if not self._key:
            raise SpeechError("auth", 0, "no_key")
        headers = {"api-subscription-key": self._key}
        last: SpeechError | None = None
        for attempt in range(self._retries + 1):
            try:
                res = self._http.post(f"{self._base}{path}", headers=headers, **kwargs)  # type: ignore[arg-type]
            except httpx.TimeoutException:
                last = SpeechError("timeout")
            except httpx.HTTPError:
                last = SpeechError("unavailable")
            else:
                if res.is_success:
                    return res
                code = ""
                try:
                    code = str(res.json().get("error", {}).get("code", ""))
                except ValueError:
                    pass
                last = SpeechError(_kind(res.status_code), res.status_code, code)
                if res.status_code not in (429, 503):
                    raise last
            if attempt < self._retries and callable(self._sleep):
                self._sleep(0.25 * (2**attempt))
        assert last is not None
        raise last

    def transcribe(self, wav: bytes, language_code: str, model: str = STT_MODEL) -> SttResult:
        """Speech to text for one clip of at most 30 seconds."""
        res = self._post(
            "/speech-to-text",
            files={"file": ("clip.wav", wav, "audio/wav")},
            data={"model": model, "language_code": language_code},
        )
        body = res.json()
        return SttResult(
            transcript=str(body.get("transcript", "")).strip(),
            language_code=body.get("language_code"),
            language_probability=body.get("language_probability"),
        )

    def synthesize(
        self,
        text: str,
        language_code: str,
        speaker: str,
        *,
        model: str = TTS_MODEL,
        pace: float = 1.0,
        sample_rate: int = 24000,
        dict_id: str | None = None,
    ) -> bytes:
        """Text to speech as MP3 bytes. Opus is refused by v3, so we encode it ourselves."""
        body: dict[str, object] = {
            "text": text,
            "language_code": language_code,
            "speaker": speaker,
            "model": model,
            "pace": pace,
            "speech_sample_rate": sample_rate,
            "output_audio_codec": "mp3",
        }
        if dict_id:
            body["dict_id"] = dict_id
        res = self._post("/text-to-speech", json=body)
        audios = res.json().get("audios") or []
        if not audios:
            raise SpeechError("other", res.status_code, "no_audio")
        return base64.b64decode(audios[0])

    # Voice cloning is beta, off by default, and not verified against the live service: the
    # documentation does not list the /voices/clone request fields.
    def create_voice(self, clip: bytes, name: str, language_code: str) -> str:
        res = self._post(
            "/voices/create",
            files={"file": ("voice.wav", clip, "audio/wav")},
            data={"name": name, "language": language_code},
        )
        return str(res.json()["data"]["voice_id"])

    def clone_speech(self, text: str, voice_id: str, language_code: str) -> bytes:
        res = self._post(
            "/voices/clone",
            json={"text": text, "voice_id": voice_id, "language_code": language_code},
        )
        audios = res.json().get("audios") or []
        if not audios:
            raise SpeechError("other", res.status_code, "no_audio")
        return base64.b64decode(audios[0])
