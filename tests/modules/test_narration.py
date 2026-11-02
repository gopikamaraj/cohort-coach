# ruff: noqa: E501
"""The spoken script of a module: headings spoken by code, call 18 only rewords and is checked by code."""

from __future__ import annotations

import re

from ai.schemas import ModuleNarration, NarrationSection
from services.modules import library, narration, speech_input

INTRO = "Module 1 of 2. [pause] Ask the child to explain her steps."


def _mt() -> dict:
    return library.module_text("PV-HEARD", "ask_explain", False, "en").to_dict()


def _spoken(mt: dict, text: str) -> str:
    """The approved text with its numbers in words, as prompt v2 asks: digit by digit for the sidecar's."""
    by_digit = speech_input.readings_for(mt)
    return re.sub(
        r"\d+",
        lambda m: speech_input.digit_words(m[0]) if m[0] in by_digit else speech_input.number_words(int(m[0])),
        text,
    )


def _out(mt: dict, edit: dict[str, str] | None = None) -> ModuleNarration:
    return ModuleNarration(
        sections=[
            NarrationSection(id=p["id"], text=(edit or {}).get(p["id"], _spoken(mt, narration.body(p))))
            for p in narration.speakable(mt)
        ]
    )


def test_the_code_built_script_speaks_every_heading_before_its_part() -> None:
    s = narration.script(_mt(), INTRO)
    for h in ("What this does", "What you need", "Steps", "An example", "How to know it worked"):
        assert f"{h}. [pause] " in s
    assert s.startswith("Module 1 of 2. [pause] ")
    assert "None" not in s and "?." not in s


def test_the_headings_are_spoken_in_the_listeners_language() -> None:
    mt = library.module_text("PV-HEARD", "ask_explain", False, "hi").to_dict()
    assert narration.heading("steps", "hi") in narration.script(mt, "x")


def test_reworded_parts_keep_the_code_headings() -> None:
    mt = _mt()
    said = narration.validate(_out(mt, {"steps": "First, ask how she got it. Then listen to the end."}), mt)
    assert said is not None
    s = narration.script(mt, INTRO, said)
    assert "Steps. [pause] First, ask how she got it." in s


def test_output_that_adds_or_drops_a_number_or_a_part_is_refused() -> None:
    mt = _mt()
    assert narration.validate(_out(mt), mt) is not None
    assert narration.validate(_out(mt, {"example": "A child wrote six zero three for sixty-two. Ask: how did you get six zero three? The child says: I wrote sixty, then two."}), mt) is None
    assert narration.validate(_out(mt, {"example": "A child wrote six hundred two for sixty-two. Ask: how did you get six hundred two? The child says: I wrote sixty, then two."}), mt) is None
    assert narration.validate(_out(mt, {"example": narration.body(mt["parts"][3])}), mt) is None  # digits left in
    assert narration.validate(_out(mt, {"example": "Ask how she got it. The child says: I wrote sixty."}), mt) is None
    short = _out(mt)
    assert narration.validate(ModuleNarration(sections=short.sections[:-1]), mt) is None
    assert narration.validate(_out(mt, {"purpose": "**The teacher asks** how she got it."}), mt) is None
    long = " ".join(["Listen carefully to the child."] * 10)
    assert narration.validate(_out(mt, {"purpose": long}), mt) is None


def test_a_stored_narration_is_used_only_for_the_same_language_and_parts() -> None:
    mt = _mt()
    said = narration.validate(_out(mt), mt)
    stored = {"narration": {"language": "en", "sections": said}}
    assert narration.stored_for(stored, mt) == said
    assert narration.stored_for({"narration": {"language": "hi", "sections": said}}, mt) is None
    assert narration.stored_for({}, mt) is None


def test_any_failure_keeps_the_code_script(monkeypatch) -> None:
    mt = _mt()
    monkeypatch.setattr(narration, "narrate", lambda **kw: (_ for _ in ()).throw(RuntimeError("down")))
    monkeypatch.setattr(narration.ai_config, "ai_mode", lambda: "live")
    assert narration.run(mt) is None
    monkeypatch.setattr(narration.ai_config, "ai_mode", lambda: "off")
    assert narration.run(mt) is None


def test_ordinary_numbers_are_said_in_words_and_602_digit_by_digit() -> None:
    assert speech_input.number_words(52) == "fifty-two" and speech_input.number_words(105) == "one hundred five"
    assert speech_input.digit_words("602") == "six zero two"
    mt = library.module_text("ADD-NOCARRY", "show_bundles", False, "en").to_dict()
    assert narration.validate(_out(mt), mt) is not None


def test_a_bad_first_answer_is_retried_once_then_the_code_script_is_kept(monkeypatch) -> None:
    from ai.calls.c18_module_narration import NarrationRun

    mt = _mt()
    calls = []
    good, bad = _out(mt), ModuleNarration(sections=[])

    def fake(**kw):
        calls.append(kw["module"])
        return NarrationRun(bad if len(calls) == 1 else good, False, None)  # type: ignore[arg-type]

    monkeypatch.setattr(narration, "narrate", fake)
    monkeypatch.setattr(narration.ai_config, "ai_mode", lambda: "live")
    monkeypatch.setattr(narration, "run_gates", lambda *a, **k: type("G", (), {"passed_automatic": True})())
    assert narration.run(mt, number=1, count=2) is not None and len(calls) == 2
    calls.clear()
    monkeypatch.setattr(narration, "narrate", lambda **kw: calls.append(1) or NarrationRun(bad, False, None))  # type: ignore[arg-type]
    assert narration.run(mt, number=1, count=2) is None and len(calls) == 2
