"""Persona to stock speaker and pitch ratio, from content/voices/children.v1.yaml."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

_FILE = Path(__file__).resolve().parents[2] / "content" / "voices" / "children.v1.yaml"
DEFAULT_TEACHER_SPEAKER = "ritu"


@dataclass(frozen=True)
class Voice:
    speaker: str
    pitch: float
    pace: float


@lru_cache(maxsize=1)
def _load() -> dict[str, Voice]:
    raw = yaml.safe_load(_FILE.read_text(encoding="utf-8"))["voices"]
    return {
        k: Voice(str(v["speaker"]), float(v["pitch"]), float(v["pace"])) for k, v in raw.items()
    }


def voice_for(child_id: str) -> Voice:
    """The child's voice; an unknown id gets the first listed voice rather than failing."""
    voices = _load()
    return voices.get(child_id) or next(iter(voices.values()))


def all_voices() -> dict[str, Voice]:
    return dict(_load())


def clones_enabled() -> bool:
    return os.environ.get("SARVAM_CLONES", "") == "1"
