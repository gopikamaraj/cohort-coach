from __future__ import annotations

import pytest

from engine.forms import PILOT_FORMS
from engine.model import ItemType
from engine.practice_sets import check_pairs, practice_set


def test_the_check_pairs_are_every_computation_item_of_both_forms() -> None:
    assert len(check_pairs()) == 16
    assert frozenset((45, 19)) in check_pairs() and frozenset((19, 45)) in check_pairs()


@pytest.mark.parametrize("kind", ["sub", "add"])
@pytest.mark.parametrize("level", [1, 2])
def test_no_practice_set_contains_a_check_item(kind: str, level: int) -> None:
    banned = check_pairs()
    for seed in range(200):
        for a, b in practice_set(kind, level, seed):  # type: ignore[arg-type]
            assert frozenset((a, b)) not in banned


def test_level_one_subtraction_needs_no_regrouping_and_level_two_does() -> None:
    for seed in range(50):
        assert all(a % 10 >= b % 10 for a, b in practice_set("sub", 1, seed))
        assert all(a % 10 < b % 10 for a, b in practice_set("sub", 2, seed))


def test_level_two_addition_carries_and_level_one_does_not() -> None:
    for seed in range(50):
        assert all(a % 10 + b % 10 < 10 for a, b in practice_set("add", 1, seed))
        assert all(a % 10 + b % 10 >= 10 for a, b in practice_set("add", 2, seed))


def test_sets_are_deterministic_and_have_distinct_problems() -> None:
    assert practice_set("sub", 2, 7) == practice_set("sub", 2, 7)
    s = practice_set("sub", 2, 7)
    assert len(set(s)) == len(s) == 6


def test_the_pilot_forms_are_still_the_golden_ones() -> None:
    kinds = {i.type for f in PILOT_FORMS.values() for i in f.items}
    assert ItemType.SUB_BORROW in kinds
