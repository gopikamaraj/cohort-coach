# ruff: noqa: E501
"""The spoken script of a module: headings spoken by code, call 18 only rewords and is checked by code."""

from __future__ import annotations

from ai.schemas import ModuleNarration, NarrationSection
from services.modules import library, narration

INTRO = "Module 1 of 2. [pause] Ask the child to explain her steps."


def _mt() -> dict:
    return library.module_text("PV-HEARD", "ask_explain", False, "en").to_dict()


def _out(mt: dict, edit: dict[str, str] | None = None) -> ModuleNarration:
    return ModuleNarration(
        sections=[
            NarrationSection(id=p["id"], text=(edit or {}).get(p["id"], narration.body(p)))
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
    assert narration.validate(_out(mt, {"example": "Ask how she got 603 for sixty-two."}), mt) is None
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
