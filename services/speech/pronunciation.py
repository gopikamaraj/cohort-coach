"""Pronunciation notes (content/pronunciation/*.yaml) -> the JSON Sarvam's dictionary upload takes.

Only words with a filled-in `say` are included; nothing is guessed. The dictionary id Sarvam
returns goes in SARVAM_DICT_HI / SARVAM_DICT_TA and is passed as `dict_id` on every synthesis.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

DIR = Path(__file__).resolve().parents[2] / "content" / "pronunciation"
MAX_WORDS = 100  # Sarvam's limit per dictionary


def load(lang: str) -> dict[str, str]:
    raw = yaml.safe_load((DIR / f"{lang}.yaml").read_text(encoding="utf-8"))
    return {w["word"]: w["say"] for w in raw["words"] if str(w.get("say", "")).strip()}


def dictionary_json(lang: str) -> str | None:
    """The file body to upload, or None when no word has been filled in yet."""
    words = load(lang)
    if not words:
        return None
    code = yaml.safe_load((DIR / f"{lang}.yaml").read_text(encoding="utf-8"))["language"]
    if len(words) > MAX_WORDS:
        raise ValueError(f"{lang}: {len(words)} words, the limit is {MAX_WORDS}")
    return json.dumps({"pronunciations": {code: words}}, ensure_ascii=False, indent=2)
