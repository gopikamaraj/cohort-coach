"""A stand-in for Bodhan's speech API (httpx.MockTransport), built from the documented rules in
docs/vendors/bodhan/api-reference.md: WAV, FLAC, OGG and MP3 accepted for speech to text and M4A,
AAC, WebM and AMR refused with 415; at most 30 s of audio; `instructions` a JSON string with `lang`;
voice and style from the lists, else 422; WAV out (PCM16, 24 kHz, mono). Failures can be switched
on: 401, 429 (with headers), 500, and slow replies. No real voice is used: the audio is
generated."""

from __future__ import annotations

import io
import json
import wave
from dataclasses import dataclass, field
from typing import Any

import httpx

from services.speech.bodhan import STT_MODEL, STYLES, TTS_MODEL, VOICES

SPEAK_KEY = "test-speak-key-0001"
TRANSCRIBE_KEY = "test-transcribe-key-0002"
LANGS = {"en", "hi", "ta"}


def wav24k(seconds: float) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"\x00\x01" * int(24000 * seconds))
    return buf.getvalue()


def _sniff(data: bytes) -> str:
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return "wav"
    if data[:4] == b"OggS":
        return "ogg"
    if data[:4] == b"fLaC":
        return "flac"
    if data[:3] == b"ID3" or data[:2] in (b"\xff\xfb", b"\xff\xf3"):
        return "mp3"
    if data[:4] == b"\x1a\x45\xdf\xa3":
        return "webm"
    if data[4:8] == b"ftyp":
        return "m4a"
    if data[:6] == b"#!AMR\n":
        return "amr"
    return "aac"


def _wav_seconds(data: bytes) -> float:
    with wave.open(io.BytesIO(data)) as w:
        return w.getnframes() / w.getframerate()


def _multipart(request: httpx.Request) -> dict[str, bytes]:
    """Field name -> value (the file's bytes for `file`)."""
    boundary = request.headers["content-type"].split("boundary=")[1].encode()
    out: dict[str, bytes] = {}
    for part in request.content.split(b"--" + boundary):
        if b"\r\n\r\n" not in part:
            continue
        head, body = part.split(b"\r\n\r\n", 1)
        name = head.split(b'name="')[1].split(b'"')[0].decode()
        out[name] = body[:-2] if body.endswith(b"\r\n") else body
    return out


def _error(status: int, message: str, rid: str) -> httpx.Response:
    return httpx.Response(status, json={"detail": message}, headers={"x-request-id": rid})


@dataclass
class BodhanMock:
    """`fail` is a list of statuses (or "slow") returned before normal service, one per request."""

    fail: list[Any] = field(default_factory=list)
    retry_after: str | None = None
    requests: list[httpx.Request] = field(default_factory=list)
    count: int = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        self.count += 1
        rid = f"req-{self.count:04d}"
        if self.fail:
            what = self.fail.pop(0)
            if what == "slow":
                raise httpx.ReadTimeout("slow", request=request)
            headers = {"x-request-id": rid, "x-ratelimit-limit-requests": "60"}
            if what == 429 and self.retry_after is not None:
                headers["retry-after"] = self.retry_after
            return httpx.Response(int(what), json={"detail": "forced"}, headers=headers)
        auth = request.headers.get("authorization", "")
        path = request.url.path
        if path == "/v1/audio/transcriptions":
            if auth != f"Bearer {TRANSCRIBE_KEY}":
                return _error(401, "bad key", rid)
            fields = _multipart(request)
            if fields.get("model", b"").decode() != STT_MODEL:
                return _error(422, "model must be indic-transcribe", rid)
            kind = _sniff(fields["file"])
            if kind in {"webm", "m4a", "aac", "amr"}:
                return _error(415, f"{kind} cannot be measured", rid)
            if kind == "wav" and _wav_seconds(fields["file"]) > 30.0:
                return _error(400, "longer than 30 seconds", rid)
            lang = fields.get("language", b"").decode()
            return httpx.Response(
                200, json={"text": f"heard in {lang or 'auto'}"}, headers={"x-request-id": rid}
            )
        if path == "/v1/audio/speech":
            if auth != f"Bearer {SPEAK_KEY}":
                return _error(401, "bad key", rid)
            body = json.loads(request.content)
            if body.get("model") != TTS_MODEL:
                return _error(422, "model must be indic-speak", rid)
            instructions = body.get("instructions")
            if not isinstance(instructions, str):
                return _error(422, "instructions must be a JSON string", rid)
            ins = json.loads(instructions)
            if ins.get("lang") not in LANGS:
                return _error(422, f"unknown lang {ins.get('lang')!r}", rid)
            if "style" in ins and ins["style"] not in STYLES:
                return _error(422, f"unknown style {ins['style']!r}", rid)
            if body.get("voice") not in VOICES:
                return _error(422, f"unknown voice {body.get('voice')!r}", rid)
            if not body.get("input"):
                return _error(422, "input is empty", rid)
            seconds = min(30.0, 0.06 * len(body["input"]))
            return httpx.Response(
                200,
                content=wav24k(seconds),
                headers={"content-type": "audio/wav", "x-request-id": rid},
            )
        return _error(404, "not found", rid)

    def client(self) -> httpx.Client:
        return httpx.Client(transport=httpx.MockTransport(self))
