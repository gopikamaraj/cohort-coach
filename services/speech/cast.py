"""Which voice each Practice Class child speaks with, and which style her mood gives it.

Both come from content/voices.yaml (data, owned by Seema): a child keeps one voice for the whole
session, chosen in seat order from the list for the persona's gender; the engine's mood maps to a
Bodhan style by code (bright -> happy, small -> sad, others -> the voice's neutral reading). The AI
never chooses a voice or a style.
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import cache
from typing import Any

import yaml

from services.speech.lessons import VOICES


@cache
def _data() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(VOICES.read_text(encoding="utf-8"))
    return data


def mood_style(mood: str | None) -> str | None:
    style = _data().get("moods", {}).get(mood or "")
    return None if style in (None, "none") else str(style)


def seat_voices(language: str, genders: Sequence[str]) -> list[str]:
    """One Bodhan voice per child, in seat order, by gender ("f" or "m"); a list that runs out
    starts again from its first voice."""
    cast = _data()["children"].get(language) or _data()["children"]["en"]
    used = {"f": 0, "m": 0}
    out = []
    for g in genders:
        key = g if g in ("f", "m") else "f"
        pool = cast[key]
        out.append(str(pool[used[key] % len(pool)]))
        used[key] += 1
    return out
