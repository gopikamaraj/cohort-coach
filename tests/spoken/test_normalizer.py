# ruff: noqa: E501
"""The normaliser: screen text in, spoken text out; deterministic, idempotent, no digits or symbols."""

from __future__ import annotations

import pytest

from services.spoken import PAUSE_LONG, PAUSE_SHORT, normalize, pieces, to_plain, to_ssml, validate
from services.spoken.adapters.intervention import build_script
from services.spoken.adapters.practice import prepare_utterance

SCREEN = (
    "Source: Strategy library (strategies.v1) · Draft\n"
    "- Materials: bundles of ten, 3 sticks\n"
    "83 - 47 = 36: 8 bundles; 1 of 16 children write {pv:403} [pause] ok **bold**"
)


def test_screen_only_text_is_removed_and_numbers_become_words():
    out = normalize(SCREEN, "en")
    assert "Source" not in out and "Draft" not in out and "Materials:" not in out
    assert out.startswith("You will need bundles of ten, three sticks.")
    assert "eighty-three minus forty-seven equals thirty-six" in out
    assert "one child out of sixteen" in out
    assert "four, zero, three" in out  # a marked place-value number is said digit by digit
    assert validate(out, "en") == []


@pytest.mark.parametrize(
    ("text", "lang"),
    [(SCREEN, "en"), ("16 में से 3 बच्चे। 346 + 25 = 371", "hi"), ("346 மற்றும் 52 - 29 = 23", "ta")],
)
def test_idempotent(text, lang):  # type: ignore[no-untyped-def]
    once = normalize(text, lang)
    assert normalize(once, lang) == once


def test_unmarked_numbers_are_ordinary_numbers():
    assert (
        normalize("Write 403 on the board.", "en") == "Write four hundred and three on the board."
    )


def test_a_quoted_line_is_set_off_by_commas_not_lost():
    assert normalize('The teacher asks "How did you get that?" and listens.', "en") == (
        "The teacher asks, How did you get that? and listens."
    )


def test_pauses_survive_and_never_double():
    out = normalize(
        f"Do it {PAUSE_SHORT} {PAUSE_SHORT} then stop {PAUSE_LONG} {PAUSE_SHORT} done", "en"
    )
    assert out.count(PAUSE_SHORT) == 1 and out.count(PAUSE_LONG) == 1


def test_pieces_and_targets():
    spoken = f"First part. {PAUSE_SHORT} Second part. {PAUSE_LONG} Third."
    assert [(p.text, p.pause_after_ms) for p in pieces(spoken)] == [
        ("First part.", 350),
        ("Second part.", 900),
        ("Third.", 0),
    ]
    assert "[pause" not in to_plain(spoken)
    assert to_ssml(spoken).startswith("<speak>") and '<break time="350ms"/>' in to_ssml(spoken)


def test_validator_names_what_is_wrong():
    codes = {i.code for i in validate("Source: x. It is 5 + 3 {pv:4}", "en")}
    assert {"screen_only", "symbol_or_digit"} <= codes


def test_practice_line_is_spoken_ready_and_the_screen_line_is_untouched():
    line = "I did 52 minus 29, that is 37"
    assert (
        prepare_utterance(line, "en") == "I did fifty-two minus twenty-nine, that is thirty-seven."
    )
    assert line == "I did 52 minus 29, that is 37"


def test_intervention_script_is_clean_and_uses_the_callers_counts():
    s = build_script(
        "PV-HEARD",
        "en",
        3,
        16,
        {"confirmed": [3, 7], "possible": []},
        {"question": "43", "wrote": "403", "correct": "43"},
    )
    assert s.surface == "intervention" and s.language == "en" and not s.fallback
    assert "three children out of sixteen" in s.text
    assert "Roll numbers three, seven." in s.text
    assert "four, zero, three" in s.text
    assert s.issues == () and s.total_words > 100 and s.est_seconds > 0
    assert "Source" not in s.text and "Draft" not in s.text and "1 of 16" not in s.text


def test_missing_language_falls_back_to_english_for_the_whole_script():
    s = build_script("SUB-SFL", "hi", 3, 16)
    assert s.language == "en" and s.fallback
