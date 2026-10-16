import json
from pathlib import Path

import pytest

from engine.bugs import (
    add_nocarry,
    add_whole_ones,
    answer_codes,
    classify,
    correct_answer,
    error_answers,
    heard_and_reversed,
    probes,
    pv_heard,
    pv_reverse,
    sub_nodec,
    sub_sfl,
    untracked_signatures,
)
from engine.model import ErrorCode, Item, ItemType, Mark

GOLDEN = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "pilot_forms.golden.json").read_text(
        encoding="utf-8"
    )
)


def item_from_fixture(raw: dict) -> Item:  # type: ignore[type-arg]
    kind = ItemType(raw["type"])
    if kind is ItemType.DICTATION:
        return Item(raw["n"], kind, raw["value"])
    return Item(raw["n"], kind, raw["a"], raw["b"])


ALL_ITEMS = [(form, raw) for form, spec in GOLDEN["forms"].items() for raw in spec["items"]]


def test_design_examples() -> None:
    assert pv_heard(43) == {403}
    assert add_nocarry(47, 25) == {62}
    assert sub_sfl(52, 29) == {37}
    assert sub_nodec(52, 29) == {33}
    assert pv_reverse(43) == {34}
    assert pv_reverse(346) == {364}
    assert pv_heard(346) == {30046, 3046, 300406}
    assert heard_and_reversed(346) == {30064, 3064, 300604}
    assert add_whole_ones(38, 47) == {715}


def test_collision_example_52_minus_27() -> None:
    assert sub_sfl(52, 27) == sub_nodec(52, 27) == {35}


def test_numbers_with_a_zero_digit_have_no_heard_or_reverse_error() -> None:
    assert pv_heard(340) == frozenset()
    assert pv_reverse(340) == frozenset()


def test_nodec_without_borrowing_equals_correct() -> None:
    assert sub_nodec(87, 52) == {35}  # not a wrong answer: the error does not bite


@pytest.mark.parametrize(("form", "raw"), ALL_ITEMS)
def test_every_pilot_item_matches_the_fixture(form: str, raw: dict) -> None:  # type: ignore[type-arg]
    item = item_from_fixture(raw)
    assert correct_answer(item) == raw["correct"]
    assert probes(item) == tuple(ErrorCode(p) for p in raw["probes"])
    expected = {ErrorCode(k): frozenset(v) for k, v in raw["error_answers"].items()}
    assert error_answers(item) == expected
    assert untracked_signatures(item) == {
        k: frozenset(v) for k, v in raw.get("untracked_signatures", {}).items()
    }
    both = frozenset(raw.get("both_heard_and_reversed", []))
    codes = answer_codes(item)
    for answer in both:
        assert codes[answer] == {ErrorCode.PV_HEARD, ErrorCode.PV_REVERSE}


@pytest.mark.parametrize(("form", "raw"), ALL_ITEMS)
def test_every_printed_wrong_answer_classifies_to_its_code(form: str, raw: dict) -> None:  # type: ignore[type-arg]
    item = item_from_fixture(raw)
    assert classify(item, raw["correct"]).kind is Mark.CORRECT
    for code, answers in raw["error_answers"].items():
        for answer in answers:
            mark = classify(item, answer)
            assert mark.kind is Mark.ERROR
            assert mark.codes == {ErrorCode(code)}
    for answer in raw.get("both_heard_and_reversed", []):
        assert classify(item, answer).codes == {ErrorCode.PV_HEARD, ErrorCode.PV_REVERSE}


def test_715_on_item_3_is_other_with_an_add_whole_ones_tally() -> None:
    item = Item(3, ItemType.ADD_CARRY, 38, 47)
    mark = classify(item, 715)
    assert mark.kind is Mark.OTHER
    assert mark.untracked == "ADD-WHOLE-ONES"


def test_blank_unreadable_and_random_wrong_answers() -> None:
    item = Item(3, ItemType.ADD_CARRY, 38, 47)
    assert classify(item, "blank").kind is Mark.BLANK
    assert classify(item, "unreadable").kind is Mark.UNREADABLE
    other = classify(item, 99)
    assert other.kind is Mark.OTHER and other.untracked is None


def test_anchor_has_no_error_answers_so_wrong_is_other() -> None:
    item = Item(6, ItemType.SUB_ANCHOR, 87, 52)
    assert probes(item) == ()
    assert error_answers(item) == {}
    assert classify(item, 25).kind is Mark.OTHER
