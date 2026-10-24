"""The lesson chain's pieces: counts, diagnosis, approach, script; every number from code."""

from __future__ import annotations

import re

import pytest

from ai.guard.gates import ContentType, GateInput, gate1
from ai.validators.check_items import check_items
from ai.validators.numbers import extract_numbers
from engine.bugs import sub_nodec, sub_sfl
from engine.model import ErrorCode
from services.pilot import lessons
from services.pilot.lessons import NoTrack, Pooled, TemplateDrafter, choose_error, plan_slots

TRACKED = [ErrorCode.PV_HEARD, ErrorCode.ADD_NOCARRY, ErrorCode.SUB_SFL, ErrorCode.SUB_NODEC]


def test_choose_error_follows_the_engine_rules() -> None:
    assert choose_error(Pooled(40, 2, {"SUB-SFL": 14, "ADD-NOCARRY": 20}, 0)) == (
        ErrorCode.ADD_NOCARRY,
        20,
    )
    # PV-HEARD comes first whenever it is eligible
    assert choose_error(Pooled(40, 2, {"SUB-SFL": 30, "PV-HEARD": 10}, 0)) == (
        ErrorCode.PV_HEARD,
        10,
    )


def test_no_lesson_without_enough_children_or_a_common_error() -> None:
    with pytest.raises(NoTrack) as no_sheets:
        choose_error(Pooled(0, 0, {}, 0))
    assert no_sheets.value.reason == "no_sheets"
    with pytest.raises(NoTrack) as few:
        choose_error(Pooled(9, 1, {"SUB-SFL": 9}, 0))
    assert few.value.reason == "not_enough"
    with pytest.raises(NoTrack) as rare:
        choose_error(Pooled(40, 2, {"SUB-SFL": 9}, 0))  # 9 of 40 is under 1 in 4
    assert rare.value.reason == "no_error"


def test_slots_are_one_look_for_lesson_then_one_move_each() -> None:
    plans = plan_slots(ErrorCode.SUB_SFL, 12, 20, 4)
    assert [p.kind for p in plans] == ["spot", "move", "move", "move"]
    assert len({p.move_id for p in plans[1:]}) == 3
    # more lessons than moves: the moves come round again with a different worked example
    many = plan_slots(ErrorCode.SUB_SFL, 12, 20, 10)
    assert len(many) == 10 and many[1].move_id == many[6].move_id and many[6].round == 1


@pytest.mark.parametrize("lang", ["en", "hi", "ta"])
@pytest.mark.parametrize("error", TRACKED)
def test_every_script_passes_the_code_gates_with_numbers_from_code(
    error: ErrorCode, lang: str
) -> None:
    for total in (1, 3, 10):
        for plan in plan_slots(error, 11, 28, total):
            draft = TemplateDrafter().draft(plan, lang)
            assert draft.title and len(draft.title) <= 120
            result = gate1(
                GateInput(
                    text=draft.script,
                    content_type=ContentType.TRACK_DRAFT,
                    language=lang,
                    target_error=error.value,
                    allowed_numbers=draft.allowed_numbers,
                )
            )
            assert all(r.ok for r in result), (
                error,
                lang,
                plan.slot,
                [(r.name, r.violations) for r in result if not r.ok],
            )
            assert not check_items(draft.script)  # never a Form A or Form B item
            assert "%" not in draft.script  # teacher-facing numbers are counts
            assert "{" not in draft.script  # every slot was filled


def test_the_class_numbers_in_the_script_are_the_counts_the_code_passed_in() -> None:
    plan = plan_slots(ErrorCode.SUB_SFL, 11, 28, 3)[0]
    en = TemplateDrafter().draft(plan, "en").script
    assert "11 of 28 children" in en
    assert 11 in extract_numbers(en) and 28 in extract_numbers(en)


def test_wrong_answers_in_the_script_come_from_the_engine() -> None:
    plan = plan_slots(ErrorCode.SUB_SFL, 11, 28, 3)[0]
    en = TemplateDrafter().draft(plan, "en").script
    assert (
        "writes 37" in en and "right answer is 23" in en
    )  # 52 - 29: the smaller digit from the larger
    nodec = TemplateDrafter().draft(plan_slots(ErrorCode.SUB_NODEC, 11, 28, 3)[0], "en").script
    assert "writes 33" in nodec
    assert min(sub_sfl(52, 29)) == 37 and min(sub_nodec(52, 29)) == 33


def test_worked_examples_keep_the_two_subtraction_errors_apart() -> None:
    for a, b in lessons.lesson_content()["examples"]["SUB-SFL"]:
        assert not (sub_sfl(a, b) & sub_nodec(a, b)), (a, b)  # the item generator's own rule
        assert a - b not in sub_sfl(a, b) | sub_nodec(a, b)


def test_a_script_has_no_html_or_markup_and_reads_in_sentences() -> None:
    for lang in ("en", "hi", "ta"):
        for plan in plan_slots(ErrorCode.SUB_SFL, 11, 28, 3):
            script = TemplateDrafter().draft(plan, lang).script
            assert not re.search(r"[<>*_#`]", script)
            assert script.count("\n") >= 3
