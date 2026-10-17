"""Text to speech for a child line or a lesson: Sarvam MP3 -> pitch shift -> OGG/Opus mono.
Results are cached by a hash of (text, language, voice) so a repeated line costs nothing."""

from __future__ import annotations

import hashlib
import os
from collections import OrderedDict

from services.speech import audio
from services.speech.sarvam import LANGUAGE_CODES, SarvamClient
from services.speech.voices import Voice

MAX_CHARS = 2500


class SpeechCache:
    def __init__(self, size: int = 256) -> None:
        self._size = size
        self._items: OrderedDict[str, bytes] = OrderedDict()

    def get(self, key: str) -> bytes | None:
        if key in self._items:
            self._items.move_to_end(key)
            return self._items[key]
        return None

    def put(self, key: str, value: bytes) -> None:
        self._items[key] = value
        self._items.move_to_end(key)
        while len(self._items) > self._size:
            self._items.popitem(last=False)


CACHE = SpeechCache()


def cache_key(text: str, lang: str, voice: Voice, dict_id: str | None) -> str:
    raw = "\x1f".join([text, lang, voice.speaker, f"{voice.pitch}", f"{voice.pace}", dict_id or ""])
    return hashlib.sha256(raw.encode()).hexdigest()


def synthesize(
    client: SarvamClient,
    text: str,
    lang: str,
    voice: Voice,
    *,
    cache: SpeechCache = CACHE,
) -> tuple[bytes, bool]:
    """Returns (OGG/Opus bytes, from_cache)."""
    text = text[:MAX_CHARS]
    dict_id = os.environ.get(f"SARVAM_DICT_{lang.upper()}") or None
    key = cache_key(text, lang, voice, dict_id)
    hit = cache.get(key)
    if hit is not None:
        return hit, True
    mp3 = client.synthesize(
        text, LANGUAGE_CODES.get(lang, "en-IN"), voice.speaker, pace=voice.pace, dict_id=dict_id
    )
    ogg = audio.to_ogg_opus(mp3, pitch_ratio=voice.pitch)
    cache.put(key, ogg)
    return ogg, False
