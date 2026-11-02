# ruff: noqa: E501
"""The spoken script of a module, made for listening.

Code builds the script from the approved text: the module line, then each part with its heading
("What this does", "What you need", "Steps", ...) spoken by code, then the part. Call 18 may reword the
parts so a listener can follow them by ear. The headings never come from the model, and its output is
used only if every part is there in order, every number and {slot} of the approved text is kept (none
added), the length is close, and the gates (pre-filter and call 7) pass. Otherwise the code-built script
is used. It runs once, when a module is made, and the result is stored with the module.
"""

from __future__ import annotations

import re
from typing import Any

from ai import config as ai_config
from ai.calls.c18_module_narration import narrate
from ai.client import CallContext
from ai.guard.gates import ContentType, GateInput, run_gates
from ai.schemas import ModuleNarration
from services.api import strings
from services.modules import library

_TOKENS = re.compile(r"\{pv:\d+\}|\d+")
_SLOT = re.compile(r"\{pv:\d+\}")
_BAD = re.compile(r"[\[\]*#`<>{}]")


def heading(part_id: str, lang: str) -> str:
    return strings.text(lang, f"module.part.{part_id}")


def body(part: dict[str, Any]) -> str:
    """The approved text of one part as plain text; steps and examples are joined into sentences."""
    if part.get("text"):
        return str(part["text"])
    return " ".join(x if x.rstrip()[-1:] in ".?!।" else x + "." for x in map(str, part.get("list") or []))


def speakable(mt: dict[str, Any]) -> list[dict[str, Any]]:
    """The parts that are voiced: worked examples are numbers in sums, so they are read in English only."""
    lang = mt.get("language", "en")
    return [p for p in mt.get("parts", []) if p["id"] != "example" or lang == "en"]


def script(mt: dict[str, Any], intro: str, narrated: dict[str, str] | None = None) -> str:
    """Intro (already ends with a pause after "Module n of N."), then heading, pause, body for each part."""
    lang = mt.get("language", "en")
    lines = [intro]
    for p in speakable(mt):
        text = (narrated or {}).get(p["id"]) or body(p)
        if text:
            lines.append(f"{heading(p['id'], lang)}.")
            lines.append(text)
    return " [pause] ".join(lines)


def _tokens(text: str) -> list[str]:
    return sorted(_TOKENS.findall(text))


def validate(out: ModuleNarration, mt: dict[str, Any]) -> dict[str, str] | None:
    """Every part present in order; numbers and slots kept and none added; length close; no markup."""
    parts = speakable(mt)
    if [s.id for s in out.sections] != [p["id"] for p in parts]:
        return None
    got: dict[str, str] = {}
    for s, p in zip(out.sections, parts, strict=True):
        text = " ".join(s.text.split())
        src = body(p)
        if not text or _BAD.search(_SLOT.sub("", text)) or _tokens(text) != _tokens(src):
            return None
        words, src_words = len(text.split()), max(1, len(src.split()))
        if words > src_words * 1.8 + 15 or words < src_words * 0.4:
            return None
        got[p["id"]] = text
    return got


def run(mt: dict[str, Any], *, context: CallContext | None = None) -> dict[str, Any] | None:
    """{language, sections: {id: text}} or None (AI off, offline, anything invalid, or a gate held it)."""
    if ai_config.ai_mode() == "off":
        return None
    lang = mt.get("language", "en")
    try:
        parts = [{"id": p["id"], "heading": heading(p["id"], lang), "text": body(p)} for p in speakable(mt)]
        got = narrate(language=lang, title=mt.get("title", ""), parts=parts, context=context)
        checked = None if got.fell_back else validate(got.output, mt)
        if checked is None:
            return None
        heard = " ".join(library.display(t) for t in checked.values())
        gate = run_gates(GateInput(text=heard, content_type=ContentType.FEEDBACK_CARD, language=lang), context=context)
        return {"language": lang, "sections": checked} if gate.passed_automatic else None
    except Exception:  # noqa: BLE001 - narration is a nicety: it must never block making a module
        return None


def stored_for(stored: dict[str, Any], mt: dict[str, Any]) -> dict[str, str] | None:
    """The narration saved with the module, if it is in the language being voiced and covers these parts."""
    n = stored.get("narration")
    if not n or n.get("language") != mt.get("language"):
        return None
    secs = n.get("sections", {})
    return secs if all(p["id"] in secs for p in speakable(mt)) else None
