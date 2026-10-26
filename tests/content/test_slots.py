"""P09 T02: class numbers appear only as slots filled by code; an intentional wrong child answer
is tagged so the arithmetic validator knows it is meant to be wrong."""

from __future__ import annotations

import pytest

from ai.validators.arithmetic import (
    check_arithmetic,
    check_child_tags,
    normalise_child_tags,
    strip_child_tags,
)
from services.content import slots


def values() -> dict[str, str]:
    return slots.example_values("SUB-SFL", 52, 29) | {
        "class.count_showing": "11",
        "class.children_checked": "28",
        "track.error_name": "taking the smaller digit from the larger",
        "track.day": "2",
        "track.total_days": "6",
    }


def test_the_engine_gives_the_example_values_never_the_model() -> None:
    v = slots.example_values("SUB-SFL", 52, 29)
    assert v["class.example_a"] == "52" and v["class.example_b"] == "29"
    assert v["class.example_correct_answer"] == "23"
    assert v["class.example_wrong_answer"] == "37"  # smaller digit from the larger in each column


def test_each_tracked_error_has_example_values() -> None:
    assert slots.example_values("SUB-NODEC", 52, 29)["class.example_wrong_answer"] == "33"
    assert slots.example_values("ADD-NOCARRY", 47, 25)["class.example_wrong_answer"] == "62"
    heard = slots.example_values("PV-HEARD", 43)
    assert heard["class.example_correct_answer"] == "43"
    assert heard["class.example_wrong_answer"] == "403"


def test_fill_replaces_every_slot_by_code() -> None:
    text = "{{class.count_showing}} of {{class.children_checked}} children. Day {{track.day}}."
    assert slots.fill(text, values()) == "11 of 28 children. Day 2."


def test_an_unknown_slot_is_refused() -> None:
    assert [v.code for v in slots.check_slots("Hello {{class.secret_number}}")] == ["slot_unknown"]
    with pytest.raises(slots.UnknownSlot):
        slots.fill("Hello {{class.secret_number}}", values())


def test_a_slot_with_no_value_is_refused_not_left_in_the_text() -> None:
    with pytest.raises(slots.UnfilledSlot):
        slots.fill("{{class.count_showing}} children", {})


def test_known_slots_pass_the_slot_check() -> None:
    assert slots.check_slots("{{ class.count_showing }} of {{class.children_checked}}") == []


@pytest.mark.parametrize(
    "text",
    [
        "11 of 28 children made this mistake.",
        "Out of 28 children, 11 showed it.",
        "About 40% of the class.",
        "40 percent of the children.",
        "11 बच्चों ने यह गलती की।",
        "11 குழந்தைகள் இந்தத் தவறைச் செய்தனர்.",
    ],
)
def test_a_literal_class_number_is_blocked(text: str) -> None:
    assert [v.code for v in slots.literal_class_counts(text)], text


@pytest.mark.parametrize(
    "text",
    [
        "Take 5 sticks and add 3 more.",
        "52 - 29: open one bundle, now 12 loose sticks.",
        "{{class.count_showing}} of {{class.children_checked}} children made this mistake.",
        "Try it with 3 children tomorrow.",
    ],
)
def test_worked_examples_and_slots_are_not_mistaken_for_class_counts(text: str) -> None:
    assert slots.literal_class_counts(text) == [], text


def test_the_filled_wrong_answer_carries_the_tag_and_passes_the_arithmetic_check() -> None:
    template = "{{class.example_a}} - {{class.example_b}} = {{class.example_wrong_answer}}"
    checked = slots.fill(template, values(), keep_tags=True)
    assert checked == "52 - 29 = 37 [child-wrong]"
    assert check_arithmetic(checked) == []
    assert strip_child_tags(checked) == "52 - 29 = 37"  # what is voiced


def test_an_untagged_wrong_statement_is_flagged_and_a_tagged_one_is_not() -> None:
    assert [v.code for v in check_arithmetic("52 - 29 = 37")] == ["arithmetic_wrong"]
    assert check_arithmetic(normalise_child_tags("52 - 29 = [child: 37]")) == []


def test_the_child_tag_forms_normalise_and_strip() -> None:
    assert normalise_child_tags("the child says [child: 37] here") == (
        "the child says 37 [child-wrong] here"
    )
    assert strip_child_tags("37 [child-wrong]") == "37"


def test_a_tag_on_a_correct_answer_is_flagged() -> None:
    text = normalise_child_tags("52 - 29 = [child: 23]")
    assert [v.code for v in check_child_tags(text)] == ["child_tag_is_correct"]


def test_a_tag_on_a_truly_wrong_answer_is_fine() -> None:
    assert check_child_tags(normalise_child_tags("52 - 29 = [child: 37]")) == []
