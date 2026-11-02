"""The error functions on the pilot paper's extra items (11 to 15) and its dictation with a zero.

The real pilot pre-test (15 items) adds a three-digit sum with two carries (246 + 178), two
three-digit takeaways without borrowing, a takeaway that borrows across a zero (703 - 468) and one
that borrows twice (542 - 179), and dictates 305 to one class. The same five error functions give
the wrong answer for each, column by column; two-digit answers are unchanged (test_bugs.py).
"""

from __future__ import annotations

from engine.bugs import (
    add_nocarry,
    correct_answer,
    error_answers,
    pv_heard,
    pv_reverse,
    sub_nodec,
    sub_sfl,
)
from engine.diagnosis import diagnose_child, single_probe_items, skill_family
from engine.model import ErrorCode, Item, ItemType

D, A, S, B = ItemType.DICTATION, ItemType.ADD_CARRY, ItemType.SUB_ANCHOR, ItemType.SUB_BORROW


def test_three_digit_sum_with_two_carries_drops_both_carries() -> None:
    assert add_nocarry(246, 178) == {314}  # 2+1 | 4+7=11 -> 1 | 6+8=14 -> 4
    assert correct_answer(Item(11, A, 246, 178)) == 424


def test_two_digit_answers_are_unchanged() -> None:
    assert add_nocarry(47, 25) == {62}
    assert add_nocarry(59, 73) == {122}  # the leftmost column is written whole
    assert sub_sfl(52, 29) == {37}
    assert sub_nodec(52, 29) == {33}
    assert sub_nodec(87, 52) == {35}


def test_borrowing_across_a_zero() -> None:
    assert sub_sfl(703, 468) == {365}  # 7-4 | 6-0 | 8-3, the smaller from the larger
    # the zero becomes ten (one from the hundreds) but is not reduced for the ones
    assert sub_nodec(703, 468) == {245}
    item = Item(14, B, 703, 468)
    assert correct_answer(item) == 235
    assert error_answers(item) == {ErrorCode.SUB_SFL: {365}, ErrorCode.SUB_NODEC: {245}}


def test_three_digit_borrow_twice() -> None:
    assert sub_sfl(542, 179) == {437}
    assert sub_nodec(542, 179) == {373}  # only the tens is left unreduced
    assert correct_answer(Item(15, B, 542, 179)) == 363


def test_three_digit_takeaway_without_borrowing_is_an_anchor_with_no_probes() -> None:
    assert error_answers(Item(12, S, 786, 452)) == {}


def test_a_dictated_number_with_a_zero_in_the_tens() -> None:
    assert pv_heard(305) == {3005}  # three hundred, five
    assert pv_reverse(305) == {350}
    assert pv_heard(340) == frozenset()  # a zero in the ones still has no heard answer
    item = Item(1, D, 305)
    assert error_answers(item) == {ErrorCode.PV_HEARD: {3005}, ErrorCode.PV_REVERSE: {350}}


PILOT_LIKE = (
    Item(1, D, 305),
    Item(2, D, 496),
    Item(3, A, 38, 47),
    Item(4, A, 46, 28),
    Item(5, A, 59, 23),
    Item(6, S, 87, 52),
    Item(7, B, 74, 36),
    Item(8, B, 45, 19),
    Item(9, B, 82, 39),
    Item(10, B, 81, 27),
    Item(11, A, 246, 178),
    Item(12, S, 786, 452),
    Item(13, S, 895, 324),
    Item(14, B, 703, 468),
    Item(15, B, 542, 179),
)


def test_skill_families_are_worked_out_from_the_numbers() -> None:
    fam = {it.n: skill_family(it) for it in PILOT_LIKE}
    assert fam[1] == "dictate-zero" and fam[2] == "dictate-3d"
    assert fam[3] == fam[4] == fam[5] == "add-2d-1c"
    assert fam[11] == "add-3d-2c"
    assert fam[7] == fam[10] == "sub-2d-1b"
    assert fam[14] == "sub-across-zero" and fam[15] == "sub-3d-2b"


def test_single_probe_items_on_the_pilot_like_paper() -> None:
    from engine.model import Form

    single = single_probe_items(Form("pilot-like", PILOT_LIKE))
    assert single[ErrorCode.SUB_SFL] == {14, 15}
    assert single[ErrorCode.ADD_NOCARRY] == {11}
    assert single[ErrorCode.PV_HEARD] == {1, 2}  # 305 and 496 are different skills


def _answers(**wrong: int) -> list[int | str]:
    out: list[int | str] = [correct_answer(it) for it in PILOT_LIKE]
    for key, value in wrong.items():
        out[int(key[1:]) - 1] = value
    return out


def test_one_question_flags_only_as_possible_and_the_two_item_rule_holds() -> None:
    from engine.model import Form

    form = Form("pilot-like", PILOT_LIKE)
    child = diagnose_child(form, _answers(q14=365))
    assert child.shows == frozenset()
    assert child.possible == {ErrorCode.SUB_SFL}
    sfl7 = next(iter(sub_sfl(74, 36)))
    two = diagnose_child(form, _answers(q7=sfl7, q14=365))  # two items: the normal rule
    assert two.shows == {ErrorCode.SUB_SFL} and two.possible == frozenset()


def test_a_wrong_answer_on_two_items_of_one_skill_is_not_single() -> None:
    from engine.model import Form

    form = Form("pilot-like", PILOT_LIKE)
    sfl7 = next(iter(sub_sfl(74, 36)))
    sfl8 = next(iter(sub_sfl(45, 19)))
    child = diagnose_child(form, _answers(q7=sfl7, q8=sfl8))
    assert child.shows == {ErrorCode.SUB_SFL} and child.possible == frozenset()
    lone = diagnose_child(form, _answers(q7=sfl7))
    assert lone.shows == frozenset() and lone.possible == frozenset()  # item 7 is not single
