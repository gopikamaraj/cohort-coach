# ruff: noqa: E501
"""The spoken script of a module: call 18 writes it whole, code checks it, the fallback is code-built."""

from __future__ import annotations

import pytest

from ai.calls.c18_module_narration import NarrationRun
from ai.schemas import ModuleNarration
from services.modules import library, narration, speech_check, speech_input

INTRO = "Module 1 of 2. [pause] Ask the child to explain her steps."

SUPPLIED = """This is the first of two modules. In this one, you will practise asking the child to explain her steps.
[pause]
Here is what this does. The teacher asks, how did you get that? Then the teacher listens before saying whether it is right.
[pause]
What do you need? You do not need any materials.
[pause]
Now the steps. There are three. First, ask, how did you get that? Second, listen all the way through before you say whether it is right. Third, ask her to show the same step with sticks.
[pause]
Here is an example. A child wrote six zero two for sixty-two. That is the mistake. You ask, how did you get six zero two? The child says, I wrote sixty, then two.
[pause]
How will you know it worked? Say sixty-two to three children, one at a time, and ask each one to write it. Then ask each one to build it with bundles, and say how many bundles and how many loose sticks. Notice who writes six zero two.
[pause]"""


def _mt(lang: str = "en") -> dict:
    return library.module_text("PV-HEARD", "ask_explain", False, lang).to_dict()


def test_the_supplied_example_output_passes_the_checks_with_the_real_input() -> None:
    mt = _mt()
    si = narration._input(mt, 1, 2)
    assert speech_check.check_speech_output(SUPPLIED, si, speech_input.readings_for(mt)) == []


def test_the_code_built_script_speaks_every_heading_before_its_part() -> None:
    s = narration.script(_mt(), INTRO)
    for h in ("What this does", "What you need", "Steps", "An example", "How to know it worked"):
        assert f"{h}. [pause] " in s
    assert s.startswith("Module 1 of 2. [pause] ") and "None" not in s


def test_the_headings_are_spoken_in_the_listeners_language() -> None:
    assert narration.heading("steps", "hi") in narration.script(_mt("hi"), "x")


def _fake(monkeypatch, outputs: list[str]) -> list[str]:
    calls: list[str] = []

    def fake(**kw):
        calls.append(kw["module"])
        return NarrationRun(ModuleNarration(script=outputs[min(len(calls), len(outputs)) - 1]), False, None)  # type: ignore[arg-type]

    monkeypatch.setattr(narration, "narrate", fake)
    monkeypatch.setattr(narration.ai_config, "ai_mode", lambda: "live")
    monkeypatch.setattr(narration, "run_gates", lambda *a, **k: type("G", (), {"passed_automatic": True})())
    return calls


def test_a_good_script_is_stored_and_used_as_the_spoken_text(monkeypatch) -> None:
    _fake(monkeypatch, [SUPPLIED])
    mt = _mt()
    said = narration.run(mt, number=1, count=2)
    assert said == {"language": "en", "script": SUPPLIED}
    assert narration.spoken_for(mt, {"narration": said}, INTRO, 1, 2) == SUPPLIED


def test_a_bad_answer_is_retried_once_then_the_english_template_is_used(monkeypatch) -> None:
    calls = _fake(monkeypatch, ["Too short. [pause]", SUPPLIED])
    assert narration.run(_mt(), number=1, count=2) is not None and len(calls) == 2
    calls = _fake(monkeypatch, ["Too short. [pause]"])
    mt = _mt()
    assert narration.run(mt, number=1, count=2) is None and len(calls) == 2
    spoken = narration.spoken_for(mt, {}, INTRO, 1, 2)
    assert spoken.startswith("This is the first of two modules. [pause] ")
    assert speech_check.check_speech_output(spoken, narration._input(mt, 1, 2), speech_input.readings_for(mt)) == []


def test_without_a_stored_script_another_language_keeps_the_code_script() -> None:
    mt = _mt("hi")
    assert narration.spoken_for(mt, {}, INTRO, 1, 2) == narration.script(mt, INTRO)


def test_a_stored_script_in_another_language_is_not_used() -> None:
    mt = _mt()
    stored = {"narration": {"language": "hi", "script": "x [pause]"}}
    assert narration.spoken_for(mt, stored, INTRO, 1, 2) != "x [pause]"


def test_any_failure_or_ai_off_keeps_the_fallback(monkeypatch) -> None:
    mt = _mt()
    monkeypatch.setattr(narration, "narrate", lambda **kw: (_ for _ in ()).throw(RuntimeError("down")))
    monkeypatch.setattr(narration.ai_config, "ai_mode", lambda: "live")
    assert narration.run(mt) is None
    monkeypatch.setattr(narration.ai_config, "ai_mode", lambda: "off")
    assert narration.run(mt) is None


def test_a_gate_that_holds_the_script_keeps_the_fallback(monkeypatch) -> None:
    _fake(monkeypatch, [SUPPLIED])
    monkeypatch.setattr(narration, "run_gates", lambda *a, **k: type("G", (), {"passed_automatic": False})())
    assert narration.run(_mt(), number=1, count=2) is None


def test_the_input_sent_is_the_built_input(monkeypatch) -> None:
    calls = _fake(monkeypatch, [SUPPLIED])
    mt = _mt()
    narration.run(mt, number=1, count=2)
    assert calls[0] == narration._input(mt, 1, 2).module_block


@pytest.mark.parametrize("lang", ["hi", "ta"])
def test_other_languages_build_an_input_too(lang) -> None:
    assert "[purpose]" in narration._input(_mt(lang), 1, 2).text
