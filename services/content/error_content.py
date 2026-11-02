"""The text behind "What each error means" and the cohort's intervention pack.

Loads content/errors/*.yaml, the strategy library and the plain error names, checks them, and
builds the one JSON file the phone reads (apps/pwa/src/generated/error_content.json, written by
scripts/export_keys.py). No AI call and no number is made here: the app fills the worked example
from the answer key of the class's own question. A section with no text is left out of the pack.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
ERRORS = ROOT / "content" / "errors"
STRATEGIES = ROOT / "content" / "strategies" / "strategies.v1.yaml"
NAMES = ROOT / "content" / "lang" / "error_names.yaml"

# The words the explanation panel needs for every error the engine can show a teacher.
EXPLANATION_FIELDS = ("what", "why", "spot", "first")
# The sections of an intervention pack that come from content/errors/intervention.v1.yaml.
PACK_FIELDS = (
    "two_minute_check",
    "ten_minute_activity",
    "teaching_mistakes",
    "at_home",
    "if_not_improving",
)
UNTRACKED = "ADD-WHOLE-ONES"


def _load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


# Tamil and Hindi text live in their own draft files (written by Claude, not reviewed by a person).
# Each line is added as that language's version of the English field of the same name; the English
# files do not change.
OVERLAYS = {"ta": ERRORS / "tamil.draft.v1.yaml", "hi": ERRORS / "hindi.draft.v1.yaml"}


def _overlays() -> list[tuple[str, dict[str, Any]]]:
    return [(lang, _load(path)) for lang, path in OVERLAYS.items() if path.exists()]


def explanations() -> dict[str, Any]:
    data = _load(ERRORS / "explanations.v1.yaml")
    for lang, ov in _overlays():
        for code, fields in ov["explanations"].items():
            for field, text in fields.items():
                data["errors"][code][field][lang] = text
    return data


def intervention() -> dict[str, Any]:
    data = _load(ERRORS / "intervention.v1.yaml")
    for lang, ov in _overlays():
        for code, fields in ov["intervention"].items():
            for field, text in fields.items():
                data["errors"][code][field][lang] = text
        for sid, fields in ov["strategy_details"].items():
            for field, text in fields.items():
                data["strategy_details"][sid][field][lang] = text
        for code, by_id in ov["extra_strategies"].items():
            for item in data["extra_strategies"][code]:
                for field, text in by_id.get(item["id"], {}).items():
                    item[field][lang] = text
    return data


def strategies() -> dict[str, Any]:
    data = _load(STRATEGIES)
    for lang, ov in _overlays():
        for sid, text in ov["strategy_descriptions"].items():
            data["strategies"][sid]["description"][lang] = text
    return data


def names() -> dict[str, Any]:
    return _load(NAMES)


def build() -> dict[str, Any]:
    """The JSON the phone reads. Every text field keeps its languages as written (en always; hi
    and ta only where they exist)."""
    ex, iv, st = explanations(), intervention(), strategies()
    return {
        "status": ex["status"],
        "explanations": ex["errors"],
        "names": names(),
        "pack": {
            "status": iv["status"],
            "source": iv["source"],
            "errors": iv["errors"],
            "strategy_details": iv["strategy_details"],
            "extra_strategies": iv["extra_strategies"],
        },
        "strategies": {
            sid: {
                "status": s["status"],
                "fits": s["fits"],
                "label": s["label"],
                "description": s["description"],
                "worked_examples": s.get("worked_examples", []),
                "worked_by_error": s.get("worked_by_error", {}),
            }
            for sid, s in st["strategies"].items()
        },
    }
