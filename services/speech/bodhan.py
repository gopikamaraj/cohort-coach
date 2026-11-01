"""Bodhan AI speech: speech to text (`indic-transcribe`) and text to speech (`indic-speak`).

Read from https://console.bodhan.ai/api-docs/ on 2026-11-01; notes in
docs/vendors/bodhan/api-reference.md. Auth is `Authorization: Bearer <key>`. Speech to text takes
WAV, FLAC, OGG or MP3 of at most 30 s (we send 16 kHz mono WAV of at most 28 s); text to speech
returns WAV (PCM16, 24 kHz, mono) and takes `instructions` as a JSON *string*.

Status mapping: 401/403 auth (no retry); 415 our conversion is wrong (no retry, logged loudly); 422
a bad voice, language or style (no retry, the unknown value is logged); 400 and other 4xx bad
request (no retry); 429 and 5xx retried once with backoff and jitter, honouring Retry-After;
timeouts retried once. Logged: provider, model, characters or seconds, latency, status and
x-request-id. Never the key, the audio or the text.
"""

from __future__ import annotations

import json
import logging
import os
import random
import time
from collections.abc import Callable
from typing import Any

import httpx

from services.speech import audio
from services.speech.provider import Audio, Capabilities, Transcript
from services.speech.sarvam import SpeechError

log = logging.getLogger(__name__)

BASE_URL = "https://api.bodhan.ai"
STT_MODEL = "indic-transcribe"
TTS_MODEL = "indic-speak"
# App language -> Bodhan's code (the same short codes for the three we use).
LANGUAGE_CODES = {"en": "en", "hi": "hi", "ta": "ta"}
STYLES = frozenset(
    {
        "AIR style news", "Customer Care", "TV style news", "advertisements", "anger",
        "children's stories", "disgust", "educational lecture", "fear", "happy", "news", "sad",
        "single person narration audiobook", "surprise",
    }
)  # fmt: skip
# The 45 voices by the language each was recorded in (female first). Any voice reads any language.
VOICES_BY_LANGUAGE: dict[str, tuple[str, ...]] = {
    "as": ("Prastuti", "Ankur"), "bn": ("Ishita", "Sourav"), "brx": ("Gwrbw", "Sansuma"),
    "doi": ("Preeti", "Sham"), "gu": ("Dhara", "Parth"), "hi": ("Kavya", "Suhani", "Amit"),
    "kn": ("Deepika", "Adarsh"), "kok": ("Anjali", "Sandeep"), "ks": ("Zoon", "Ishfaq"),
    "mai": ("Vaidehi", "Madhukar"), "ml": ("Lakshmi", "Kiran"), "mni": ("Thoibi", "Chaoba"),
    "mr": ("Anagha", "Chinmay"), "ne": ("Srijana", "Sagar"), "or": ("Itishree", "Akash"),
    "pa": ("Kaur", "Manpreet"), "sa": ("Bharati", "Aryaman"), "sat": ("Phulmani", "Sibu"),
    "sd": ("Moomal", "Rano"), "ta": ("Anitha", "Arun"), "te": ("Sravani", "Vamsi"),
    "ur": ("Saba", "Zaid"),
}  # fmt: skip
VOICES = frozenset(v for vs in VOICES_BY_LANGUAGE.values() for v in vs)
# A default voice per app language until content/voices.yaml (Prompt 2) sets the cast.
# TODO-HUMAN(Seema): confirm by listening.
DEFAULT_VOICE = {"hi": "Kavya", "ta": "Anitha", "en": "Kavya"}
MAX_INPUT_CHARS = int(os.environ.get("BODHAN_TTS_MAX_CHARS", "300"))  # about 30 s of speech


def _key(var: str) -> str:
    return os.environ.get(var) or os.environ.get("BODHAN_API_KEY", "")


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "") or default)
    except ValueError:
        return default


def _kind_for(status: int) -> str:
    if status in (401, 403):
        return "auth"
    if status == 429:
        return "rate"
    if status >= 500:
        return "unavailable"
    return "bad_request"


class BodhanClient:
    def __init__(
        self,
        *,
        speak_key: str | None = None,
        transcribe_key: str | None = None,
        base_url: str | None = None,
        client: httpx.Client | None = None,
        connect_s: float | None = None,
        stt_read_s: float | None = None,
        tts_read_s: float | None = None,
        sleep: Callable[[float], None] = time.sleep,
        jitter: Callable[[], float] = random.random,
    ) -> None:
        self._speak_key = speak_key if speak_key is not None else _key("BODHAN_SPEAK_API_KEY")
        self._transcribe_key = (
            transcribe_key if transcribe_key is not None else _key("BODHAN_TRANSCRIBE_API_KEY")
        )
        self._base = (base_url or os.environ.get("BODHAN_BASE_URL") or BASE_URL).rstrip("/")
        connect = connect_s if connect_s is not None else _float_env("BODHAN_CONNECT_TIMEOUT_S", 5)
        self._stt_timeout = httpx.Timeout(
            stt_read_s if stt_read_s is not None else _float_env("BODHAN_STT_TIMEOUT_S", 20),
            connect=connect,
        )
        self._tts_timeout = httpx.Timeout(
            tts_read_s if tts_read_s is not None else _float_env("BODHAN_TTS_TIMEOUT_S", 30),
            connect=connect,
        )
        self._http = client or httpx.Client()
        self._sleep = sleep
        self._jitter = jitter
        self.last_rate_limits: dict[str, str] = {}

    @property
    def speak_configured(self) -> bool:
        return bool(self._speak_key)

    @property
    def transcribe_configured(self) -> bool:
        return bool(self._transcribe_key)

    def _post(
        self, path: str, key: str, model: str, timeout: httpx.Timeout, **kw: Any
    ) -> httpx.Response:
        if not key:
            raise SpeechError("auth", 0, "no_key")
        headers = {"Authorization": f"Bearer {key}"}
        last: SpeechError | None = None
        for attempt in range(2):  # one retry, for 429, 5xx and timeouts only
            t0 = time.monotonic()
            wait = 0.0
            try:
                res = self._http.post(f"{self._base}{path}", headers=headers, timeout=timeout, **kw)
            except httpx.TimeoutException:
                last = SpeechError("timeout", 0, "timeout")
                self._log(model, 0, t0, None, "timeout")
            except httpx.HTTPError:
                last = SpeechError("unavailable", 0, "network")
                self._log(model, 0, t0, None, "network")
            else:
                rid = res.headers.get("x-request-id")
                self.last_rate_limits = {
                    k: v for k, v in res.headers.items() if k.lower().startswith("x-ratelimit")
                }
                if res.is_success:
                    self._log(model, res.status_code, t0, rid, None)
                    return res
                kind = _kind_for(res.status_code)
                last = SpeechError(kind, res.status_code, _code(res))  # type: ignore[arg-type]
                if res.status_code == 415:
                    log.error(
                        "bodhan refused the audio format (415): our conversion to WAV is wrong; "
                        "model=%s request_id=%s",
                        model,
                        rid,
                    )
                elif res.status_code == 422:
                    log.warning(
                        "bodhan refused a value (422): %s; model=%s request_id=%s",
                        _unknown_value(res),
                        model,
                        rid,
                    )
                else:
                    self._log(model, res.status_code, t0, rid, kind)
                if res.status_code != 429 and res.status_code < 500:
                    raise last
                wait = _retry_after(res)
            if attempt == 0:
                self._sleep(max(wait, 0.5 * (1 + self._jitter())))
        assert last is not None
        raise last

    def _log(self, model: str, status: int, t0: float, rid: str | None, err: str | None) -> None:
        log.info(
            "bodhan model=%s status=%s latency_ms=%d request_id=%s error=%s",
            model,
            status,
            int((time.monotonic() - t0) * 1000),
            rid,
            err,
        )

    def transcribe(self, wav: bytes, language: str) -> tuple[str, str | None]:
        """(text, request id) for one WAV clip of at most 28 s. The language is always sent."""
        res = self._post(
            "/v1/audio/transcriptions",
            self._transcribe_key,
            STT_MODEL,
            self._stt_timeout,
            files={"file": ("clip.wav", wav, "audio/wav")},
            data={"model": STT_MODEL, "language": language},
        )
        try:
            text = str(res.json().get("text", "")).strip()
        except ValueError as exc:
            raise SpeechError("other", res.status_code, "bad_json") from exc
        return text, res.headers.get("x-request-id")

    def synthesize(
        self, text: str, language: str, voice: str, style: str | None
    ) -> tuple[bytes, str | None]:
        """(WAV bytes, request id) for a sentence or two."""
        res = self._post(
            "/v1/audio/speech",
            self._speak_key,
            TTS_MODEL,
            self._tts_timeout,
            json=speech_body(text, language, voice, style),
        )
        if not res.content:
            raise SpeechError("other", res.status_code, "no_audio")
        return res.content, res.headers.get("x-request-id")


def speech_body(text: str, language: str, voice: str, style: str | None) -> dict[str, str]:
    """The text-to-speech request. `instructions` is a JSON string, not an object; `style` is left
    out when there is none (the voice's neutral reading)."""
    instructions: dict[str, str] = {"lang": language}
    if style:
        instructions["style"] = style
    return {
        "model": TTS_MODEL,
        "input": text,
        "voice": voice,
        "instructions": json.dumps(instructions),
    }


def _code(res: httpx.Response) -> str:
    try:
        body = res.json()
    except ValueError:
        return ""
    err = body.get("error") if isinstance(body, dict) else None
    if isinstance(err, dict):
        return str(err.get("code", ""))[:40]
    return ""


def _unknown_value(res: httpx.Response) -> str:
    """The 422 message names the unknown value. It is about our request (a voice, language or
    style), never about the audio or the text, so it can be logged, cut short."""
    try:
        body = res.json()
    except ValueError:
        return ""
    msg = body.get("error", {}).get("message") if isinstance(body, dict) else None
    if msg is None and isinstance(body, dict):
        msg = body.get("detail") or body.get("message")
    return str(msg or "")[:200]


def _retry_after(res: httpx.Response) -> float:
    try:
        return min(float(res.headers.get("retry-after", "0")), 10.0)
    except ValueError:
        return 0.0


class BodhanProvider:
    name = "bodhan"

    def __init__(self, client: BodhanClient | None = None) -> None:
        self.client = client or BodhanClient()

    def configured_for(self, function: str) -> bool:
        """Two keys: speech to text needs the transcribe key, text to speech the speak key."""
        if function == "stt":
            return self.client.transcribe_configured
        return self.client.speak_configured

    @property
    def capabilities(self) -> Capabilities:
        return Capabilities(
            30.0, frozenset({"wav", "flac", "ogg", "mp3"}), MAX_INPUT_CHARS, VOICES, STYLES
        )

    def transcribe(self, wav: bytes, language: str) -> Transcript:
        seconds = audio.wav_seconds(wav)
        if seconds > audio.MAX_CHUNK_SECONDS:
            raise SpeechError("bad_request", 0, "too_long")  # split first (audio.split_for_stt)
        text, rid = self.client.transcribe(wav, LANGUAGE_CODES.get(language, language))
        return Transcript(text, seconds, self.name, rid)

    def synthesize(self, text: str, language: str, voice: str, style: str | None) -> Audio:
        if not text.strip():
            raise SpeechError("bad_request", 0, "empty_input")
        if len(text) > MAX_INPUT_CHARS:
            raise SpeechError("bad_request", 0, "input_too_long")  # callers split into sentences
        if voice not in VOICES:
            voice = DEFAULT_VOICE.get(language, "Kavya")
        if style is not None and style not in STYLES:
            raise SpeechError("bad_request", 0, "unknown_style")
        wav, rid = self.client.synthesize(
            text, LANGUAGE_CODES.get(language, language), voice, style
        )
        return Audio(wav, "wav", 24000, audio.duration_seconds(wav), len(text), self.name, rid)
