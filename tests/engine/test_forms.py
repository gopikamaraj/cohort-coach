import json
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from engine.bugs import both_heard_and_reversed, correct_answer, error_answers
from engine.forms import FORM_A, FORM_B
from engine.items import generate_form, is_valid, parallel_signature
from engine.model import ErrorCode, Form, ItemType

GOLDEN = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "pilot_forms.golden.json").read_text(
        encoding="utf-8"
    )
)

TYPE_ORDER = [
    ItemType.DICTATION,
    ItemType.DICTATION,
    ItemType.ADD_CARRY,
    ItemType.ADD_CARRY,
    ItemType.ADD_CARRY,
    ItemType.SUB_ANCHOR,
    ItemType.SUB_BORROW,
    ItemType.SUB_BORROW,
    ItemType.SUB_BORROW,
    ItemType.SUB_BORROW,
]


@pytest.mark.parametrize(("key", "form"), [("A", FORM_A), ("B", FORM_B)])
def test_pilot_forms_reproduce_the_printed_key(key: str, form: Form) -> None:
    raw_items = GOLDEN["forms"][key]["items"]
    assert form.label == GOLDEN["forms"][key]["label"]
    assert len(form.items) == len(raw_items) == 10
    for item, raw in zip(form.items, raw_items, strict=True):
        assert item.n == raw["n"]
        assert item.type == ItemType(raw["type"])
        assert correct_answer(item) == raw["correct"]
        assert error_answers(item) == {
            ErrorCode(k): frozenset(v) for k, v in raw["error_answers"].items()
        }
        assert both_heard_and_reversed(item) == frozenset(raw.get("both_heard_and_reversed", []))
        assert is_valid(item)


def test_pilot_form_b_is_parallel_to_form_a() -> None:
    assert parallel_signature(FORM_A) == parallel_signature(FORM_B)
    assert parallel_signature(FORM_A) == ((15, 14, 12), (2, 4, 7, 6))


def check_form(form: Form) -> None:
    assert [i.type for i in form.items] == TYPE_ORDER
    assert [i.n for i in form.items] == list(range(1, 11))
    assert all(is_valid(i) for i in form.items)


@settings(max_examples=500)
@given(seed=st.integers(0, 10**9))
def test_generator_never_emits_an_invalid_item(seed: int) -> None:
    form = generate_form(seed)
    check_form(form)
    totals, gaps = parallel_signature(form)
    assert len(set(totals)) == 3 and len(set(gaps)) == 4 and 5 not in gaps


def test_generator_is_deterministic() -> None:
    assert generate_form(2026) == generate_form(2026)
    assert generate_form(1) != generate_form(2)


@settings(max_examples=500)
@given(seed=st.integers(0, 10**9), like_seed=st.integers(0, 10**9))
def test_parallel_forms_keep_ones_totals_and_gaps_with_new_numbers(
    seed: int, like_seed: int
) -> None:
    like = generate_form(like_seed)
    form = generate_form(seed, like=like)
    check_form(form)
    assert parallel_signature(form) == parallel_signature(like)
    for new, old in zip(form.items, like.items, strict=True):
        assert new.a != old.a
        assert new.type is ItemType.DICTATION or new.b != old.b


def test_parallel_form_of_the_pilot_form_a() -> None:
    form = generate_form(7, like=FORM_A)
    check_form(form)
    assert parallel_signature(form) == parallel_signature(FORM_A)
