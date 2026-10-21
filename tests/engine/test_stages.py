"""Stage of breakdown (addendum v3.1 F): signatures from the forms, stage rules, counts."""

from __future__ import annotations

from itertools import combinations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from engine.bugs import correct_answer
from engine.forms import FORM_A, FORM_B
from engine.model import Form, Item, ItemType, Reading
from engine.stages import (
    Stage,
    StageResult,
    class_counts,
    classify_child,
    signature_answers,
    signature_overlaps,
)


def row(values: str) -> list[Reading]:
    out: list[Reading] = []
    for v in values.split(","):
        out.append("blank" if v == "" else int(v))
    return out


def run(values: str, form: Form = FORM_A, **tags: int | bool) -> StageResult:
    return classify_child(form, row(values), **tags)  # type: ignore[arg-type]


def stages(r: StageResult) -> set[str]:
    return {s.value for s in r.stages}


# signatures ---------------------------------------------------------------------------------


def test_signatures_are_disjoint_on_both_forms_except_the_designed_overlap() -> None:
    for form in (FORM_A, FORM_B):
        for item in form.items:
            if item.n == 6:
                continue
            sigs = signature_answers(item)
            for a, b in combinations(sigs, 2):
                shared = sigs[a] & sigs[b]
                assert not shared or {a, b} == {"PV-HEARD", "PV-REVERSE"} and item.n in (1, 2)
            for name, answers in sigs.items():
                assert correct_answer(item) not in answers, (item.n, name)


def test_nothing_is_dropped_on_the_real_forms() -> None:
    assert signature_overlaps(FORM_A) == {} and signature_overlaps(FORM_B) == {}


def test_signature_answers_are_generated_for_a_new_item() -> None:
    sigs = signature_answers(Item(7, ItemType.SUB_BORROW, 63, 28))
    assert sigs["CORE-OFF1"] == {34, 36}
    assert sigs["IN-OP"] == {91}
    assert sigs["OUT-REV"] == {53}


@given(st.integers(min_value=20, max_value=99), st.integers(min_value=10, max_value=19))
def test_signature_answers_never_contain_the_correct_answer(a: int, b: int) -> None:
    for kind in (ItemType.ADD_CARRY, ItemType.SUB_BORROW):
        item = Item(7, kind, a, b)
        for answers in signature_answers(item).values():
            assert correct_answer(item) not in answers


# the rows of addendum §G ---------------------------------------------------------------------

S_ROWS = [
    ("S01", "346,728,85,74,82,35,110,26,121,54", {"Input (test)"}, {"IN-OP"}),
    ("S02", "346,728,9,18,36,35,38,26,43,54", {"Input (test)"}, {"IN-OP"}),
    ("S03", "346,728,130,92,118,35,38,26,43,54", {"Input (test)"}, {"IN-OPND"}),
    ("S04", "346,728,58,47,28,35,83,62,43,54", {"Output"}, {"OUT-REV"}),
    ("S05", "347,738,85,74,82,35,38,26,43,54", {"Input (test)"}, {"IN-NEAR"}),
    ("S06", "346,728,84,73,83,35,39,26,43,54", {"Core"}, {"CORE-OFF1"}),
    ("S07", "364,782,58,47,28,35,42,34,57,66", {"Output", "Core"}, {"OUT-REV", "SUB-SFL"}),
]


@pytest.mark.parametrize(("name", "answers", "expected", "codes"), S_ROWS)
def test_the_synthetic_stage_sheets(
    name: str, answers: str, expected: set[str], codes: set[str]
) -> None:
    r = run(answers)
    assert stages(r) == expected, name
    assert codes <= r.signatures, name


HEROES = [
    ("H02", "300406,700208,85,74,82,35,38,26,43,54", {"Core"}),
    ("H03", "364,782,85,74,82,35,38,26,43,54", {"Input (test)"}),
    ("H04", "300604,700802,85,74,82,35,38,26,43,54", {"Core", "Input (test)"}),
    ("H05", "346,728,75,64,72,35,38,26,43,54", {"Core"}),
    ("H06", "346,728,85,74,82,35,42,34,57,66", {"Core"}),
    ("H07", "346,728,85,74,82,35,48,36,53,64", {"Core"}),
    ("H08", "346,728,85,74,82,35,42,34,43,54", {"Core"}),
    ("H09", "346,728,85,74,82,35,42,26,43,54", set()),
    ("H10", "346,728,75,64,72,25,42,34,57,66", {"Core"}),
    ("H11", "346,728,715,614,712,35,38,26,43,54", {"Core"}),
    ("H12", "346,728,95,70,82,35,39,26,41,54", set()),
    ("H14", "346,728,85,74,82,35,38,26,57,54", set()),
    ("H20", "346,728,85,74,82,35,42,34,57,66", {"Core"}),
    ("H26", "346,728,85,74,82,35,48,36,53,64", {"Core"}),
]


@pytest.mark.parametrize(("name", "answers", "expected"), HEROES)
def test_the_hero_sheets(name: str, answers: str, expected: set[str]) -> None:
    assert stages(run(answers)) == expected, name


def test_a_clean_sheet_has_no_stage() -> None:
    r = run("346,728,85,74,82,35,38,26,43,54")
    assert r.stages == frozenset() and not r.not_attempted and not r.signatures


# rules ---------------------------------------------------------------------------------------


def test_one_item_is_never_enough() -> None:
    assert stages(run("346,728,84,74,82,35,38,26,43,54")) == set()  # one off-by-one
    assert stages(run("347,728,85,74,82,35,38,26,43,54")) == set()  # IN-NEAR needs both items


def test_the_anchor_item_is_excluded_from_stage_rules() -> None:
    assert stages(run("346,728,85,74,82,53,38,26,43,54")) == set()  # 53 is the anchor reversed
    assert run("346,728,85,74,82,53,38,26,43,54").anchor_wrong


def test_blank_on_three_of_items_7_to_10_is_not_attempted_and_has_no_stage() -> None:
    r = run("346,728,85,74,82,35,38,,,")
    assert r.not_attempted and r.stages == frozenset()


def test_no_method_needs_three_unmatched_wrong_of_7_to_10_and_stays_possible() -> None:
    r = run("346,728,85,74,82,35,5,6,7,54")
    assert "NO-METHOD" in r.signatures and stages(r) == {"Input (teaching)"}
    assert r.no_method_possible and not r.no_method_confirmed
    c = run("346,728,85,74,82,35,5,6,7,54", missed_teaching=True)
    assert c.no_method_confirmed and c.missed_teaching


def test_no_method_when_all_of_items_3_to_5_are_unmatched() -> None:
    assert "NO-METHOD" in run("346,728,1,2,3,35,38,26,43,54").signatures


def test_blanks_are_not_no_method() -> None:
    assert "NO-METHOD" not in run("346,728,,,,35,38,26,43,54").signatures


def test_out_rec_needs_two_tagged_boxes() -> None:
    assert "OUT-REC" not in run("346,728,85,74,82,35,38,26,43,54", unreadable=1).signatures
    r = run("346,728,85,74,82,35,38,26,43,54", unreadable=1, two_answers=1)
    assert "OUT-REC" in r.signatures and stages(r) == {"Output"}


def test_pv_reverse_is_output_when_computed_answers_are_reversed_too() -> None:
    assert stages(run("364,782,85,74,82,35,38,26,43,54")) == {"Input (test)"}
    assert "Output" in stages(run("364,782,58,47,28,35,38,26,43,54"))


def test_a_form_b_sheet_uses_form_b_items() -> None:
    r = run("264,853,17,14,72,45,48,36,53,64", FORM_B)  # the other operation on items 3 and 4
    assert "IN-OP" in r.signatures and stages(r) == {"Input (test)"}


# class counts --------------------------------------------------------------------------------


def test_class_counts_per_error_and_stage_exclude_missed_teaching_children() -> None:
    results = [
        run("346,728,85,74,82,35,42,34,57,66"),  # SUB-SFL, Core
        run("346,728,85,74,82,35,42,34,57,66"),  # same
        run("346,728,85,74,82,35,42,34,57,66", missed_teaching=True),
        run("346,728,58,47,28,35,83,62,43,54"),  # OUT-REV, Output
    ]
    c = class_counts(results)
    assert c.checked == 4 and c.missed_teaching == 1
    assert c.by_signature[("SUB-SFL", Stage.CORE)] == 2
    assert c.by_signature[("OUT-REV", Stage.OUTPUT)] == 1
    assert c.by_stage[Stage.CORE] == 2


def test_counts_hold_no_per_child_data() -> None:
    c = class_counts([run("346,728,85,74,82,35,42,34,57,66")])
    assert set(vars(c)) == {
        "checked",
        "missed_teaching",
        "not_attempted",
        "by_signature",
        "by_stage",
    }
