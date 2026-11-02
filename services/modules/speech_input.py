# ruff: noqa: E501
"""The input of the call that writes the text sent to TTS (call 18), built by code from the module
the screen shows.

    <facts>
    {"language": "en", "title": "...", "module_number": 1, "module_count": 2, "step_count": 3}
    </facts>
    <module>
    [purpose] What this does
    ...
    </module>

Pure code: no AI call, no network. It reads the same text dict the screen renders (library.module_text
and the order her note gave it) and never changes it. A partly built input is never returned: any
problem raises SpeechInputError and the caller uses its fallback. Spec: docs/SPEECH-INPUT.md.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from services.api import strings

LANGUAGES = ("en", "hi", "ta")
# The sections the screen can show (services/modules/library.py), in the order the builder writes them
# when the caller gives no order. A "smaller_step" note leads a shorter version of a module.
TAGS = ("smaller_step", "purpose", "materials", "steps", "example", "check")
# The longest current module is about 1,300 characters in English and 2,300 in Tamil
# (scripts/speech_inputs_report.py); the limit leaves room for a longer one and stops a runaway.
MAX_INPUT_CHARS = 4000
SPEECH_CONTENT = Path(__file__).resolve().parents[2] / "content" / "speech"


class SpeechInputError(ValueError):
    """The input could not be built. Nothing partial is returned."""


@dataclass(frozen=True)
class Section:
    tag: str
    heading: str
    body: str = ""  # purpose, materials, example, check, smaller_step
    steps: tuple[str, ...] = ()  # one step per entry

    def lines(self) -> str:
        return "\n".join(self.steps) if self.tag == "steps" else self.body


@dataclass(frozen=True)
class SpeechInput:
    text: str  # exactly what the model is sent: the facts block and the module block
    facts: dict[str, Any]
    sections: tuple[Section, ...]
    input_hash: str

    @property
    def module_block(self) -> str:
        """The text inside <module>...</module>."""
        return self.text.split("<module>" + chr(10), 1)[1].rsplit(chr(10) + "</module>", 1)[0]


# ---- cleaning ---------------------------------------------------------------------------------------

_DELIMS = re.compile(r"<\s*/?\s*(?:module|facts)\s*>", re.I)
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_HTML = re.compile(r"</?[A-Za-z][^>]*>")
_LIST_MARK = re.compile(r"^\s*(?:[-*+•]|\d+[.)])\s+")
_HEAD_MARK = re.compile(r"^\s*#{1,6}\s+")
_PICTO = {"So", "Cs", "Co", "Cn"}  # symbols (emoji, pictographs) and unassigned or private characters


def clean(text: str) -> str:
    """One field as plain speech text. Keeps quotation marks, colons, plus, minus, equals, less-than,
    greater-than and digits; removes markup, pictographs, invisible characters and the delimiters."""
    text = _DELIMS.sub("", text)
    text = _LINK.sub(r"\1", text)
    text = _HTML.sub("", text)
    out: list[str] = []
    for line in text.splitlines():
        line = _HEAD_MARK.sub("", _LIST_MARK.sub("", line))
        out.append(line)
    text = " ".join(out)
    text = re.sub(r"\*+|__+|`+", "", text)
    kept = []
    for ch in text:
        cat = unicodedata.category(ch)
        if ch in ("\n", "\t", " "):
            kept.append(" ")
        elif cat in ("Cc", "Cf") or cat in _PICTO or ch in "️︎":
            continue  # control, zero-width, emoji and other pictographs
        else:
            kept.append(ch)
    return " ".join("".join(kept).split())


def wrap_digits(text: str, readings: tuple[str, ...]) -> str:
    """Wrap each listed digit string, where it is a whole number token, as {digits:N}."""
    for d in readings:
        text = re.sub(rf"(?<![0-9A-Za-z{{:]){re.escape(d)}(?![0-9A-Za-z}}])", f"{{digits:{d}}}", text)
    return text


# ---- the builder ------------------------------------------------------------------------------------


def heading_for(tag: str, language: str) -> str:
    """The heading the screen shows for this section, in the module's language."""
    return strings.text(language, f"module.part.{tag}")


def _sections(mt: dict[str, Any], language: str, readings: tuple[str, ...]) -> list[Section]:
    out: list[Section] = []
    for p in mt.get("parts", []):
        tag = p["id"]
        if tag not in TAGS:
            raise SpeechInputError(f"unknown section tag {tag!r}")
        if tag == "example" and language != "en":
            continue  # worked examples are numbers in sums, shown in English only; they are not spoken
        if tag == "steps":
            steps = tuple(wrap_digits(clean(str(x)), readings) for x in (p.get("list") or []))
            steps = tuple(s for s in steps if s)
            if steps:
                out.append(Section(tag, heading_for(tag, language), steps=steps))
            continue
        raw = p.get("text") or " ".join(str(x) for x in p.get("list") or [])  # an example is a list on screen
        body = wrap_digits(clean(str(raw)), readings)
        if body:
            out.append(Section(tag, heading_for(tag, language), body=body))
    return out


def build_speech_input(
    mt: dict[str, Any],
    *,
    language: str,
    number: int | None = None,
    count: int | None = None,
    digit_readings: tuple[str, ...] = (),
    prompt_version: int | str = 0,
    model: str = "",
) -> SpeechInput:
    """`mt`: the module's text as the screen gets it (title, language, parts in screen order).
    `number` and `count`: the "Module n of N" label's own numbers; leave both out when unknown or when
    the module stands alone. `digit_readings`: digit strings to read digit by digit (the sidecar)."""
    if language not in LANGUAGES:
        raise SpeechInputError(f"unsupported language {language!r}")
    title = clean(str(mt.get("title") or ""))
    if not title:
        raise SpeechInputError("the module has no title")
    sections = _sections(mt, language, digit_readings)
    stale = unmatched(sections, digit_readings) if language == "en" else []
    if stale:  # English shows every section, so a listed number that wraps nothing is a stale entry
        raise SpeechInputError(f"digit reading {stale} matches nothing in this module")
    tags = {s.tag for s in sections}
    if "purpose" not in tags and "steps" not in tags:
        raise SpeechInputError("the module has neither a purpose nor steps")
    facts: dict[str, Any] = {"language": language, "title": title}
    if number is not None and count is not None:
        if number < 1 or count < number:
            raise SpeechInputError("the module number and count do not agree")
        facts["module_number"], facts["module_count"] = number, count
    for s in sections:
        if s.tag == "steps":
            facts["step_count"] = len(s.steps)
    blocks = [f"[{s.tag}] {s.heading}\n{s.lines()}" for s in sections]
    text = f"<facts>\n{json.dumps(facts, ensure_ascii=False)}\n</facts>\n<module>\n" + "\n\n".join(blocks) + "\n</module>"
    if len(text) > MAX_INPUT_CHARS:
        raise SpeechInputError(f"the input is {len(text)} characters; the limit is {MAX_INPUT_CHARS}")
    digest = hashlib.sha256(f"{text}\0{prompt_version}\0{model}".encode()).hexdigest()
    return SpeechInput(text, facts, tuple(sections), digest)


@cache
def _sidecar() -> dict[str, tuple[str, ...]]:
    raw = yaml.safe_load((SPEECH_CONTENT / "digit_readings.v1.yaml").read_text(encoding="utf-8"))
    return {k: tuple(str(x) for x in v) for k, v in (raw.get("modules") or {}).items()}


def readings_for(mt: dict[str, Any]) -> tuple[str, ...]:
    """The digit strings the sidecar lists for this module (none for a module it does not list)."""
    return _sidecar().get(f"{mt.get('error')}:{mt.get('approach')}", ())


def unmatched(sections: list[Section], readings: tuple[str, ...]) -> list[str]:
    """Entries that wrapped nothing: stale (the module text changed or the number is not there)."""
    said = " ".join(s.lines() for s in sections)
    return [d for d in readings if f"{{digits:{d}}}" not in said]


_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def number_words(n: int) -> str:
    """An ordinary number in English words, 0 to 999: 52 -> fifty-two."""
    if n < 20:
        return _ONES[n]
    if n < 100:
        return _TENS[n // 10] + ("-" + _ONES[n % 10] if n % 10 else "")
    if n < 1000:
        return _ONES[n // 100] + " hundred" + (" " + number_words(n % 100) if n % 100 else "")
    raise ValueError(n)


def digit_words(digits: str) -> str:
    """A number read digit by digit: 602 -> six zero two."""
    return " ".join(_ONES[int(c)] for c in digits)
