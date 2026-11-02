"""Pairing a pre-test with its post-test: counts only, absent and unentered children left out."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine.bugs import correct_answer, error_answers
from engine.checkpair import COMPETENCIES, Pairing, pair_checks
from engine.forms import FORM_A, FORM_B, twin_of
from engine.items import parallel_signature
from engine.model import ErrorCode, Form, ItemType

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "check_pairing_cases.json"


def clean(form: Form) -> list[str]:
    return [str(correct_answer(i)) for i in form.items]


def showing(form: Form, code: ErrorCode) -> list[str]:
    """A child with two wrong answers that carry this error (the 2-item rule), the rest correct."""
    row = clean(form)
    made = 0
    for k, item in enumerate(form.items):
        wrong = sorted(error_answers(item).get(code, frozenset()))
        # an answer that belongs to this error only
        only = [
            w for w in wrong if all(w not in v for c, v in error_answers(item).items() if c != code)
        ]
        if made < 2 and only:
            row[k] = str(only[0])
            made += 1
    assert made == 2, (code, form.label)
    return row


def blank_row(form: Form) -> list[str]:
    return [""] * len(form.items)


def test_a_child_flagged_before_and_clear_after_is_counted_as_fixed() -> None:
    pre = [showing(FORM_A, ErrorCode.SUB_SFL), clean(FORM_A)]
    post = [clean(FORM_B), clean(FORM_B)]
    p = pair_checks(FORM_A, pre, FORM_B, post)
    c3 = p.by_competency["C3"]
    assert (c3.flagged_before, c3.fixed, c3.still_flagged, c3.newly_flagged) == (1, 1, 0, 0)
    assert p.paired == 2


def test_still_flagged_and_newly_flagged_are_counted() -> None:
    pre = [showing(FORM_A, ErrorCode.SUB_SFL), clean(FORM_A), clean(FORM_A)]
    post = [
        showing(FORM_B, ErrorCode.SUB_SFL),
        showing(FORM_B, ErrorCode.ADD_NOCARRY),
        clean(FORM_B),
    ]
    p = pair_checks(FORM_A, pre, FORM_B, post)
    assert (p.by_competency["C3"].still_flagged, p.by_competency["C3"].fixed) == (1, 0)
    assert (p.by_competency["C2"].newly_flagged, p.by_competency["C2"].flagged_before) == (1, 0)


def test_children_absent_in_either_check_are_excluded_and_counted_separately() -> None:
    pre = [showing(FORM_A, ErrorCode.SUB_SFL), clean(FORM_A), clean(FORM_A), clean(FORM_A)]
    post = [clean(FORM_B), clean(FORM_B), clean(FORM_B), clean(FORM_B)]
    p = pair_checks(FORM_A, pre, FORM_B, post, pre_absent={1}, post_absent={0})
    assert p.paired == 2 and p.excluded_absent == 2
    assert p.by_competency["C3"].flagged_before == 0  # child 0 was excluded because absent after


def test_a_child_with_no_entry_in_either_check_is_excluded_and_counted() -> None:
    pre = [clean(FORM_A), blank_row(FORM_A), clean(FORM_A)]
    post = [clean(FORM_B), clean(FORM_B), blank_row(FORM_B)]
    p = pair_checks(FORM_A, pre, FORM_B, post)
    assert p.paired == 1 and p.excluded_not_entered == 2


def test_a_check_with_more_children_than_the_other_leaves_the_extra_ones_out() -> None:
    pre = [clean(FORM_A)] * 4
    post = [clean(FORM_B)] * 3
    p = pair_checks(FORM_A, pre, FORM_B, post)
    assert p.paired == 3 and p.excluded_unmatched == 1


def test_fewer_than_ten_paired_children_is_a_small_sample() -> None:
    assert pair_checks(FORM_A, [clean(FORM_A)] * 9, FORM_B, [clean(FORM_B)] * 9).small_sample
    assert not pair_checks(FORM_A, [clean(FORM_A)] * 10, FORM_B, [clean(FORM_B)] * 10).small_sample


def test_the_result_holds_counts_and_labels_only_never_an_identifier() -> None:
    pre = [showing(FORM_A, ErrorCode.PV_HEARD), clean(FORM_A)]
    post = [clean(FORM_B), clean(FORM_B)]
    flat = json.dumps(pair_checks(FORM_A, pre, FORM_B, post).to_dict())
    for forbidden in ("row", "child", "roll", "index", "name", "id"):
        assert forbidden not in json.loads(flat)  # no such key at the top level
    values = json.loads(flat)["by_competency"]["C1"].values()
    assert all(isinstance(v, int) for v in values)


def test_the_competencies_cover_every_tracked_error_once() -> None:
    codes = [c for group in COMPETENCIES.values() for c in group]
    assert sorted(codes) == sorted(ErrorCode)


def test_golden_cases_are_current_and_the_phone_port_checks_the_same_file() -> None:
    cases = [
        {
            "name": name,
            "pre_form": "A",
            "post_form": "B",
            "pre": pre,
            "post": post,
            "pre_absent": pre_abs,
            "post_absent": post_abs,
            "expected": pair_checks(
                FORM_A, pre, FORM_B, post, set(pre_abs), set(post_abs)
            ).to_dict(),
        }
        for name, pre, post, pre_abs, post_abs in _cases()
    ]
    if not GOLDEN.exists():  # first run writes it; later runs must match it byte for byte
        GOLDEN.write_text(json.dumps(cases, indent=2) + "\n", encoding="utf-8")
    assert json.loads(GOLDEN.read_text(encoding="utf-8")) == cases


def _cases() -> list[tuple[str, list[list[str]], list[list[str]], list[int], list[int]]]:
    a_sfl, a_add, a_pv = (
        showing(FORM_A, c) for c in (ErrorCode.SUB_SFL, ErrorCode.ADD_NOCARRY, ErrorCode.PV_HEARD)
    )
    b_sfl, b_add = showing(FORM_B, ErrorCode.SUB_SFL), showing(FORM_B, ErrorCode.ADD_NOCARRY)
    return [
        (
            "fixed and still",
            [a_sfl, a_sfl, a_add, clean(FORM_A)],
            [clean(FORM_B), b_sfl, b_add, b_add],
            [],
            [],
        ),
        (
            "absent and blank",
            [a_pv, blank_row(FORM_A), a_sfl, clean(FORM_A)],
            [clean(FORM_B), clean(FORM_B), blank_row(FORM_B), b_sfl],
            [3],
            [0],
        ),
        ("unequal sizes", [a_sfl] * 5, [b_sfl] * 3, [], []),
    ]


@pytest.mark.parametrize("n", range(1, 11))
def test_every_form_b_item_is_the_twin_of_the_form_a_item_with_the_same_number(n: int) -> None:
    a, b = FORM_A.items[n - 1], FORM_B.items[n - 1]
    assert twin_of(n) == n and a.type == b.type
    if a.type is ItemType.ADD_CARRY:
        assert a.a % 10 + a.b % 10 == b.a % 10 + b.b % 10 and (a.a % 10 + a.b % 10) >= 10
    if a.type is ItemType.SUB_BORROW:
        assert a.b % 10 - a.a % 10 == b.b % 10 - b.a % 10 and a.a % 10 < a.b % 10
    if a.type is ItemType.DICTATION:
        assert len(str(a.a)) == len(str(b.a)) and a.a != b.a


def test_the_twins_share_the_forms_parallel_signature() -> None:
    assert parallel_signature(FORM_A) == parallel_signature(FORM_B)


def test_pairing_is_a_type_of_result() -> None:
    assert isinstance(pair_checks(FORM_A, [clean(FORM_A)], FORM_B, [clean(FORM_B)]), Pairing)
