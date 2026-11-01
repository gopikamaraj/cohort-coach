"""Speech cost per call (from content/speech_prices.yaml, all `verified: false` until a person
checks them) and the per-session caps: when a session has used its speech-to-text seconds or its
text-to-speech characters, speech stops for that session and the text carries on."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import yaml

PRICES = Path(__file__).resolve().parents[2] / "content" / "speech_prices.yaml"


@cache
def prices() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(PRICES.read_text(encoding="utf-8"))
    return data


def cost_inr(provider: str, function: str, *, seconds: float = 0.0, chars: int = 0) -> float:
    """Estimated cost of one call. An unknown provider costs 0 (and is logged as such)."""
    entry = prices()["providers"].get(provider, {}).get(function)
    if not entry:
        return 0.0
    if function == "stt":
        return round(seconds / 60 * float(entry["price"]), 6)
    return round(chars / 10000 * float(entry["price"]), 6)


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, "") or default)
    except ValueError:
        return default


@dataclass
class SessionSpeechBudget:
    """One session's speech allowance. `charge_*` records use; `allows_*` says whether more may be
    spent. The defaults come from SPEECH_SESSION_MAX_STT_SECONDS and
    SPEECH_SESSION_MAX_TTS_CHARS."""

    max_stt_seconds: float = field(
        default_factory=lambda: _env_float("SPEECH_SESSION_MAX_STT_SECONDS", 600.0)
    )
    max_tts_chars: int = field(
        default_factory=lambda: int(_env_float("SPEECH_SESSION_MAX_TTS_CHARS", 6000))
    )
    stt_seconds: float = 0.0
    tts_chars: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def allows_stt(self, seconds: float = 0.0) -> bool:
        return self.stt_seconds + seconds <= self.max_stt_seconds

    def allows_tts(self, chars: int = 0) -> bool:
        return self.tts_chars + chars <= self.max_tts_chars

    def charge_stt(self, seconds: float) -> None:
        with self._lock:
            self.stt_seconds += seconds

    def charge_tts(self, chars: int) -> None:
        with self._lock:
            self.tts_chars += chars
