"""The lesson voice: which voices exist, the audio format, and how a script is cut for speech.

The voices are data (`content/voices/lessons.v1.yaml`); the speech API is called elsewhere
(`services/speech/`). A script is cut on whole sentences so a pause never falls mid-sentence.
"""

from __future__ import annotations

import os
import re
from functools import cache
from pathlib import Path
from typing import Any

import yaml

VOICES = Path(__file__).resolve().parents[2] / "content" / "voices" / "lessons.v1.yaml"
CHUNK_CHARS = 1200  # well under the speech API's per-request limit
MIME = {"m4a": "audio/mp4", "mp3": "audio/mpeg"}


@cache
def voice_options() -> dict[str, Any]:
    data = yaml.safe_load(VOICES.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def voice_ids() -> list[str]:
    return [v["id"] for v in voice_options()["voices"]]


def audio_format() -> str:
    fmt = os.environ.get("AUDIO_FORMAT", "m4a")
    return fmt if fmt in MIME else "m4a"


def chunks(text: str, limit: int = CHUNK_CHARS) -> list[str]:
    """Whole sentences, joined up to the limit, so a pause never falls mid-sentence."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?।])\s+|\n+", text) if s.strip()]
    out: list[str] = []
    for s in sentences:
        if out and len(out[-1]) + 1 + len(s) <= limit:
            out[-1] += " " + s
        else:
            out.append(s[:limit] if len(s) > limit else s)
    return out
