# ruff: noqa: E501
"""The module library: the plan for each error and the text of one module, put together in code from
the strategy library, the intervention text and content/modules/modules.v1.yaml. No AI is called and
nothing is invented: a part with no text is left out and named in `omitted`.

A module's text is cached by (error, approach, smaller, language), not by teacher, so teachers on the
same branch get the same text and, through the audio cache (keyed by the text), the same audio file.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from services.content import error_content
from services.modules.branch import Plan, Template

PLANS = Path(__file__).resolve().parents[2] / "content" / "modules" / "modules.v1.yaml"
LANGS = ("en", "hi", "ta")
PV = re.compile(r"\{pv:(\d+)\}")

SRC_LIB = "Strategy library (strategies.v1)"
SRC_PACK = "Intervention text (content/errors/intervention.v1)"
SRC_MOD = "Module plan (content/modules/modules.v1)"


@cache
def config() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(PLANS.read_text(encoding="utf-8"))
    return data


@cache
def content() -> dict[str, Any]:
    return error_content.build()


def reset() -> None:
    config.cache_clear()
    content.cache_clear()
    module_text.cache_clear()


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    return int(raw) if raw.isdigit() and int(raw) > 0 else default


def cap() -> int:
    return _env_int("MODULE_CAP", int(config()["cap"]))


def gap_days() -> int:
    return _env_int("MODULE_GAP_DAYS", int(config()["gap_days"]))


def no_download_days() -> int:
    return _env_int("MODULE_NO_DOWNLOAD_DAYS", 5)


def has_plan(error: str) -> bool:
    return error in config()["errors"]


def _approaches_for(error: str) -> list[str]:
    c = content()
    ids = [sid for sid, s in c["strategies"].items() if error in s["fits"]]
    ids += [x["id"] for x in c["pack"]["extra_strategies"].get(error, [])]
    return ids


def plan_for(error: str) -> Plan:
    """The plan for an error. With none in the file, the single-module fallback: the library's first
    approach for it (the caller logs that)."""
    entry = config()["errors"].get(error)
    if entry is None:
        approaches = _approaches_for(error)
        return Plan(error, tuple(Template(a) for a in approaches[:1]), tuple(approaches[1:]))
    return Plan(
        error,
        tuple(Template(t["approach"], tuple(t.get("alternatives", ()))) for t in entry["plan"]),
        tuple(entry.get("extra", ())),
    )


def planned_length(error: str) -> int:
    return max(1, min(len(plan_for(error).templates), cap()))


def _pick(field_: dict[str, Any] | None, lang: str) -> tuple[Any, bool] | None:
    """(value, fell_back_to_english) or None when there is no text at all."""
    if not field_:
        return None
    if field_.get(lang):
        return field_[lang], False
    if field_.get("en"):
        return field_["en"], lang != "en"
    return None


def _strategy(error: str, approach: str) -> dict[str, Any] | None:
    """label, description, materials, steps, worked examples and draft flag for one approach."""
    c = content()
    for x in c["pack"]["extra_strategies"].get(error, []):
        if x["id"] == approach:
            return {
                "label": x["label"],
                "description": x["description"],
                "materials": x.get("materials"),
                "steps": x.get("steps"),
                "worked": [],
                "draft": True,
            }
    s = c["strategies"].get(approach)
    if s is None:
        return None
    details = c["pack"]["strategy_details"].get(approach, {})
    return {
        "label": s["label"],
        "description": s["description"],
        "materials": details.get("materials"),
        "steps": details.get("steps"),
        "worked": s.get("worked_examples", []),
        "draft": s.get("status") != "approved",
    }


def title(error: str, approach: str, lang: str) -> str:
    s = _strategy(error, approach)
    got = _pick(s["label"], lang) if s else None
    return str(got[0]) if got else approach


@dataclass
class Part:
    id: str
    text: str | None = None
    items: list[str] | None = None
    fallback: bool = False  # the language asked for had no text: English is shown
    draft: bool = True
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id": self.id,
            "fallback": self.fallback,
            "draft": self.draft,
            "source": self.source,
        }
        if self.text is not None:
            out["text"] = display(self.text)
        if self.items is not None:
            out["list"] = [display(x) for x in self.items]
        return out


@dataclass
class ModuleText:
    error: str
    approach: str
    language: str
    title: str
    parts: list[Part] = field(default_factory=list)
    omitted: list[str] = field(default_factory=list)
    smaller: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "error": self.error,
            "approach": self.approach,
            "language": self.language,
            "title": self.title,
            "smaller": self.smaller,
            "parts": [p.to_dict() for p in self.parts],
            "omitted": self.omitted,
        }


@cache
def module_text(error: str, approach: str, smaller: bool, language: str) -> ModuleText:
    s = _strategy(error, approach)
    lang = language if language in LANGS else "en"
    out = ModuleText(error, approach, lang, title(error, approach, lang), smaller=smaller)
    if s is None:
        out.omitted.append("all")
        return out
    pack = content()["pack"]["errors"].get(error, {})

    def text_part(pid: str, field_: dict[str, Any] | None, source: str, draft: bool) -> None:
        got = _pick(field_, lang)
        if got is None:
            out.omitted.append(pid)
            return
        out.parts.append(Part(pid, text=str(got[0]), fallback=got[1], draft=draft, source=source))

    if smaller:
        text_part("smaller_step", config()["smaller_step"]["intro"], SRC_MOD, True)
    text_part("purpose", s["description"], SRC_LIB, s["draft"])
    text_part("materials", s["materials"], SRC_PACK, True)
    steps = _pick(s["steps"], lang)
    if steps is None:
        out.omitted.append("steps")
    else:
        value = list(steps[0])[:1] if smaller else list(steps[0])
        out.parts.append(Part("steps", items=value, fallback=steps[1], source=SRC_PACK))
    if s["worked"] and not smaller:
        # worked examples are numbers in sums; they are not translated, so they show in English only
        out.parts.append(
            Part(
                "example",
                items=[str(w) for w in s["worked"]],
                draft=s["draft"],
                source=SRC_LIB,
                fallback=lang != "en",
            )
        )
    text_part("check", pack.get("two_minute_check"), SRC_PACK, True)
    return out


def display(text: str) -> str:
    """The reading text: a {pv:602} slot shows as 602."""
    return PV.sub(lambda m: m.group(1), text)


def spoken(mt: ModuleText, intro: str) -> str:
    """The text sent to the voice: the intro line, then each part with a pause. The shared spoken
    layer (the normaliser) turns numbers and slots into words. Worked examples are numbers in sums,
    so they are read only in English."""
    lines = [intro]
    for p in mt.parts:
        if p.id == "example":
            if mt.language == "en":
                lines += p.items or []
            continue
        if p.text:
            lines.append(p.text)
        elif p.items:
            lines += [f"{i}. {x}" for i, x in enumerate(p.items, 1)]
    return " [pause] ".join(lines)
