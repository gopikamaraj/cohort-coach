# ruff: noqa: E501
"""The spoken script of a module, made for listening.

Call 18 writes the whole script from the input built in speech_input.py. Its output is used only if
speech_check.check_speech_output finds nothing wrong and the gates (pre-filter and call 7) pass; it is asked
twice, then the fallback is used: the English template (speech_check.template_script) or, for another
language, the script code builds from the approved text. It runs once, when a module is made (and on
Refresh in testing), and the result is stored with the module.
"""

from __future__ import annotations

from typing import Any

from ai import config as ai_config
from ai.calls.c18_module_narration import narrate
from ai.client import CallContext
from ai.guard.gates import ContentType, GateInput, run_gates
from ai.prompt_loader import load_prompt
from services.api import strings
from services.modules import speech_check, speech_input


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


def script(mt: dict[str, Any], intro: str) -> str:
    """The code-built script: the intro, then each part under its spoken heading (Hindi and Tamil fallback)."""
    lang = mt.get("language", "en")
    lines = [intro]
    for p in speakable(mt):
        text = body(p)
        if text:
            lines.append(f"{heading(p['id'], lang)}.")
            lines.append(text)
    return " [pause] ".join(lines)


def _input(mt: dict[str, Any], number: int | None, count: int | None) -> speech_input.SpeechInput:
    return speech_input.build_speech_input(
        mt,
        language=mt.get("language", "en"),
        number=number,
        count=count,
        prompt_version=load_prompt("c18_module_narration").version,
        model=ai_config.model_for("MODEL_NARRATION"),
    )


def run(
    mt: dict[str, Any],
    *,
    number: int | None = None,
    count: int | None = None,
    context: CallContext | None = None,
) -> dict[str, Any] | None:
    """{language, script} or None (AI off, offline, two bad answers, or a gate held it)."""
    if ai_config.ai_mode() == "off":
        return None
    lang = mt.get("language", "en")
    try:
        si = _input(mt, number, count)
        readings = speech_input.readings_for(mt)
        for _attempt in range(2):  # one retry, then the fallback
            got = narrate(facts=si.facts, module=si.module_block, context=context)
            text = got.output.script.strip()
            if got.fell_back or speech_check.check_speech_output(text, si, readings):
                continue
            heard = text.replace(speech_check.PAUSE, " ")
            gate = run_gates(GateInput(text=heard, content_type=ContentType.FEEDBACK_CARD, language=lang), context=context)
            return {"language": lang, "script": text} if gate.passed_automatic else None
    except Exception:  # noqa: BLE001 - narration is a nicety: it must never block making a module
        return None
    return None


def spoken_for(mt: dict[str, Any], stored: dict[str, Any], intro: str, number: int | None, count: int | None) -> str:
    """What the voice is sent: the stored AI script if there is one in this language, else the fallback."""
    n = stored.get("narration")
    if n and n.get("language") == mt.get("language") and n.get("script"):
        return str(n["script"])
    try:
        fallback = speech_check.template_script(_input(mt, number, count), speech_input.readings_for(mt))
    except speech_input.SpeechInputError:
        fallback = None
    return fallback or script(mt, intro)
