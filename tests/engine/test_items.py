import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from engine.bugs import (
    add_nocarry,
    add_whole_ones,
    correct_answer,
    heard_and_reversed,
    pv_heard,
    pv_reverse,
    sub_nodec,
    sub_sfl,
)
from engine.items import collision_problems, constraint_problems, is_valid, validate_item
from engine.model import Item, ItemType

D = ItemType.DICTATION
A = ItemType.ADD_CARRY
S = ItemType.SUB_ANCHOR
B = ItemType.SUB_BORROW


def test_52_minus_27_is_rejected_for_the_shared_wrong_answer() -> None:
    item = Item(7, B, 52, 27)
    reasons = validate_item(item)
    assert not is_valid(item)
    assert any("SUB-SFL" in r and "SUB-NODEC" in r and "35" in r for r in reasons)
    assert collision_problems(item)  # not only a constraint failure


def test_52_minus_29_is_valid() -> None:
    assert validate_item(Item(7, B, 52, 29)) == []


@pytest.mark.parametrize(
    "item",
    [
        Item(1, D, 306),  # zero digit
        Item(1, D, 344),  # tens == ones
        Item(1, D, 46),  # not 3-digit
        Item(3, A, 31, 42),  # no carry
        Item(3, A, 58, 47),  # sum > 99
        Item(3, A, 8, 47),  # not 2-digit
        Item(6, S, 82, 39),  # borrows
        Item(6, S, 52, 52),  # tens not larger
        Item(7, B, 87, 52),  # no borrow
        Item(7, B, 31, 29),  # tens not larger after borrow
        Item(7, B, 52, 27),  # gap 5
        Item(7, B, 21, 19),  # result 2 is below 10
    ],
)
def test_constraint_violations_are_reported(item: Item) -> None:
    assert constraint_problems(item)
    assert not is_valid(item)


def test_pilot_style_items_are_valid() -> None:
    for item in [
        Item(1, D, 346),
        Item(3, A, 38, 47),
        Item(6, S, 87, 52),
        Item(7, B, 74, 36),
        Item(10, B, 81, 27),
        Item(8, B, 32, 19),  # result 13 is legal
    ]:
        assert validate_item(item) == []


@settings(max_examples=500)
@given(
    at=st.integers(2, 9),
    bt=st.integers(1, 7),
    ao=st.integers(0, 8),
    gap=st.integers(1, 9),
)
def test_valid_borrow_items_have_three_different_answers(
    at: int, bt: int, ao: int, gap: int
) -> None:
    bo = ao + gap
    if bo > 9:
        return
    item = Item(7, B, 10 * at + ao, 10 * bt + bo)
    if not is_valid(item):
        return
    (sfl,) = sub_sfl(item.a, item.b)
    (nodec,) = sub_nodec(item.a, item.b)
    assert len({sfl, nodec, correct_answer(item)}) == 3


@settings(max_examples=500)
@given(
    at=st.integers(1, 9),
    bt=st.integers(1, 9),
    ao=st.integers(1, 9),
    bo=st.integers(1, 9),
)
def test_valid_add_carry_items_have_distinct_error_and_correct_answers(
    at: int, bt: int, ao: int, bo: int
) -> None:
    item = Item(3, A, 10 * at + ao, 10 * bt + bo)
    if not is_valid(item):
        return
    (nocarry,) = add_nocarry(item.a, item.b)
    (whole,) = add_whole_ones(item.a, item.b)
    assert len({nocarry, whole, correct_answer(item)}) == 3


@settings(max_examples=500)
@given(h=st.integers(1, 9), t=st.integers(1, 9), o=st.integers(1, 9))
def test_valid_dictation_items_have_disjoint_answer_sets(h: int, t: int, o: int) -> None:
    item = Item(1, D, 100 * h + 10 * t + o)
    if not is_valid(item):
        return
    heard, rev, both = pv_heard(item.a), pv_reverse(item.a), heard_and_reversed(item.a)
    assert not (heard & rev) and not (both & heard) and not (both & rev)
    assert item.a not in heard | rev | both
