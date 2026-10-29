"""Loaders for track definitions, the strategy library and the templates (data in `content/`)."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import yaml

CONTENT = Path(__file__).resolve().parents[2] / "content"
STATUSES = ("draft", "in_review", "approved", "active", "retired")


@dataclass(frozen=True)
class Lesson:
    id: str
    day: int
    topic: dict[str, str]
    strategies: tuple[str, ...]
    practice_level: int


@dataclass(frozen=True)
class Track:
    id: str
    error: str
    version: int
    grade: int
    languages: tuple[str, ...]
    method_cards: tuple[str, ...]
    lessons: tuple[Lesson, ...]
    model_strategies: tuple[str, ...]
    model_minutes: int
    example: tuple[int, int] = (52, 29)


@dataclass(frozen=True)
class Strategy:
    id: str
    status: str
    fits: tuple[str, ...]
    label: dict[str, str]
    description: dict[str, str]
    worked_examples: tuple[str, ...]


def _yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


@cache
def load_track(track_id: str) -> Track:
    raw = _yaml(CONTENT / "tracks" / track_id / "track.yaml")
    lessons = tuple(
        Lesson(
            id=r["id"],
            day=int(r["day"]),
            topic=dict(r["topic"]),
            strategies=tuple(r["strategies"]),
            practice_level=int(r["practice_level"]),
        )
        for r in raw["lessons"]
    )
    model = raw.get("model_lesson", {})
    return Track(
        id=raw["id"],
        error=raw["error"],
        version=int(raw["version"]),
        grade=int(raw["grade"]),
        languages=tuple(raw["languages"]),
        method_cards=tuple(raw.get("method_cards") or ()),
        lessons=lessons,
        model_strategies=tuple(model.get("strategies", ())),
        model_minutes=int(model.get("minutes", 12)),
        example=(int(raw.get("example", [52, 29])[0]), int(raw.get("example", [52, 29])[1])),
    )


@cache
def load_strategies() -> dict[str, Strategy]:
    raw = _yaml(CONTENT / "strategies" / "strategies.v1.yaml")
    out: dict[str, Strategy] = {}
    for sid, r in raw["strategies"].items():
        if r["status"] not in STATUSES:
            raise ValueError(f"strategy {sid}: unknown status {r['status']}")
        out[sid] = Strategy(
            id=sid,
            status=r["status"],
            fits=tuple(r["fits"]),
            label=dict(r["label"]),
            description=dict(r["description"]),
            worked_examples=tuple(r.get("worked_examples") or ()),
        )
    return out


def load_template(name: str) -> str:
    return (CONTENT / "templates" / name).read_text(encoding="utf-8")
