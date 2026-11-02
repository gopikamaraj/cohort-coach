# ruff: noqa: E501
"""The output checks and the English template for the text sent to TTS."""

from __future__ import annotations

import pytest

from services.modules import library, speech_input
from services.modules.speech_check import check_speech_output, opening_phrase, template_script
from services.modules.speech_input import build_speech_input

GOOD = (
    "This is the first of two modules. In this one, you will practise asking the child to explain her steps. [pause] "
    "Here is what this does. The teacher asks, how did you get that? Then the teacher listens before saying whether it is right. [pause] "
    "What do you need? You do not need any materials. [pause] "
    "Now the steps. There are three. First, ask, how did you get that? Second, listen all the way through before you say whether it is right. Third, ask her to show the same step with sticks. [pause] "
    "Here is an example. A child wrote six zero two for sixty-two. That is the mistake. You ask, how did you get six zero two? The child says, I wrote sixty, then two. [pause] "
    "How will you know it worked? Say sixty-two to three children, one at a time, and ask each one to write it. Then ask each one to build it with bundles, and say how many bundles and how many loose sticks. Notice who writes six zero two. [pause]"
)


def si_for(error="PV-HEARD", approach="ask_explain", lang="en", n=1, c=2):
    mt = library.module_text(error, approach, False, lang).to_dict()
    return build_speech_input(mt, language=lang, number=n, count=c, digit_readings=speech_input.readings_for(mt))


def test_the_example_output_passes() -> None:
    assert check_speech_output(GOOD, si_for(), ("602",)) == []


@pytest.mark.parametrize(
    ("edit", "code"),
    [
        (lambda t: t.replace("three children", "3 children"), "digits"),
        (lambda t: t.replace("how did you get that?", '"how did you get that?"', 1), "quotes"),
        (lambda t: t.replace("with sticks. [pause]", "with sticks (see below) [bad]. [pause]", 1), "brackets"),
        (lambda t: t.replace("What do you need?", "**What do you need?**"), "markup"),
        (lambda t: t.replace(" [pause] What do you need", " What do you need"), "pause_count"),
        (lambda t: t.replace("Second, listen", "[pause] Second, listen"), "pause_count"),
        (lambda t: t.replace("There are three.", "There are four."), "step_count"),
        (lambda t: t.replace("six zero two", "six hundred two"), "digits_reading"),
        (lambda t: t.replace(" [pause] ", " [pause] " + "Extra words here. " * 40, 1), "length"),
        (lambda t: "Short. [pause]", "length"),
        (lambda t: t.replace("first of two modules", "the module"), "opening"),
    ],
)
def test_each_failure_code_has_a_minimal_failing_text(edit, code) -> None:
    assert code in check_speech_output(edit(GOOD), si_for(), ("602",))


def test_the_opening_is_checked_only_when_number_and_count_are_known() -> None:
    standalone = si_for(n=None, c=None)
    assert "opening" not in check_speech_output(GOOD.replace("first of two modules", "the module"), standalone)
    assert opening_phrase(2, 2) == "last of two modules"
    assert opening_phrase(1, 2) == "first of two modules" and opening_phrase(2, 3) == "second of three modules"


def test_the_template_passes_its_own_checks_for_every_english_module() -> None:
    for error in ("PV-HEARD", "ADD-NOCARRY", "SUB-SFL", "SUB-NODEC"):
        for approach in library.plan_for(error).approaches():
            mt = library.module_text(error, approach, False, "en")
            if mt.omitted:
                continue
            si = si_for(error, approach)
            assert check_speech_output(template_script(si) or "", si) == [], (error, approach)


def test_the_template_keeps_the_content_and_says_modules_never_lessons() -> None:
    script = template_script(si_for()) or ""
    assert script.startswith("This is the first of two modules. [pause] ")
    assert "six zero two" in script and '"' not in script and "lesson" not in script.lower()
    assert "listen all the way through before saying whether it is right." in script


def test_there_is_no_template_for_another_language() -> None:
    assert template_script(si_for(lang="hi")) is None
