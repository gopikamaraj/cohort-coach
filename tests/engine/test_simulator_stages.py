"""Simulator stages (addendum v3.1 F6): spoken and written answers, mishearing, no method."""

from __future__ import annotations

import pytest

from engine.model import ErrorCode
from engine.simulator import (
    MoveEffect,
    Problem,
    ScenarioConfig,
    Seat,
    fill_seats,
    new_session,
    plan_turn,
)

SFL = ErrorCode.SUB_SFL
P1 = Problem("sub", 52, 29)  # correct 23, reversed 32, other operation 81

MOVES = {
    "pose_problem": MoveEffect("answer", 0.0, 0.0, False),
    "ask_explain": MoveEffect("explain", -0.2, 0.05, False),
    "show_bundles": MoveEffect("work_aloud", -0.3, 0.1, False),
    "check_back": MoveEffect("doubt", -0.2, 0.05, False),
}


def config(strength: float = 1.0, streak: int = 2) -> ScenarioConfig:
    return ScenarioConfig(
        error=SFL, start_strength=strength, start_engagement=0.6, max_turns=40,
        finish_streak=streak, quiet_turns=2, problems=(P1, Problem("sub", 74, 46)),
        moves=MOVES, material_moves={},
    )  # fmt: skip


def one(stage: str, strength: float = 1.0, seed: int = 1, problem: Problem = P1):  # type: ignore[no-untyped-def]
    seats = (Seat("Asha", None, False), Seat("Meena", SFL, False, stage=stage))
    cfg = config(strength)
    state = new_session(cfg, seats, seed)
    return plan_turn(state, cfg, "pose_problem", addressed="Meena", posed=problem), cfg


def test_a_core_child_is_unchanged_and_writes_what_she_says() -> None:
    (plan, _), _ = one("core")
    assert plan.answer == 37 and plan.written == 37 and plan.correct is False
    assert plan.stage == "core" and plan.spoken_correct is False


def test_an_output_child_says_the_right_number_and_writes_it_reversed() -> None:
    (plan, _), _ = one("output")
    assert plan.answer == 23 and plan.spoken_correct is True
    assert plan.written == 32 and plan.correct is False  # the slate is wrong, so she is not done
    assert plan.error_code is not None


def test_an_output_child_who_has_got_it_writes_it_right() -> None:
    (plan, _), _ = one("output", strength=0.0)
    assert plan.answer == 23 and plan.written == 23 and plan.correct is True


def test_an_input_test_child_hears_the_other_operation_or_swaps_the_numbers() -> None:
    seen = set()
    for seed in range(40):
        (plan, _), _ = one("input-test", seed=seed, problem=Problem("sub", 74, 46))  # 28
        assert plan.answer is not None and plan.answer != 28 and plan.written == plan.answer
        seen.add(plan.answer)
    assert 120 in seen  # reads the minus as plus
    assert 1 in seen  # or swaps the digits of 74 before working (47 - 46)
    (plan, _), _ = one("input-test", problem=P1)  # swapping 52 gives a negative: only plus is left
    assert plan.answer == 81


def test_an_input_test_child_misreads_a_dictation_by_one_digit() -> None:
    cfg = ScenarioConfig(
        error=ErrorCode.PV_HEARD, start_strength=1.0, start_engagement=0.6, max_turns=40,
        finish_streak=2, quiet_turns=2, problems=(Problem("dictation", 346),),
        moves=MOVES, material_moves={},
    )  # fmt: skip
    seats = (
        Seat("Asha", None, False),
        Seat("Meena", ErrorCode.PV_HEARD, False, stage="input-test"),
    )
    plan, _ = plan_turn(
        new_session(cfg, seats, 3), cfg, "pose_problem", addressed="Meena", posed=None
    )
    assert plan.answer in {246, 336, 345, 347, 356, 446}


def test_an_input_teaching_child_has_no_method_and_says_so_without_a_number() -> None:
    (plan, _), _ = one("input-teaching")
    assert plan.answer is None and plan.written is None and plan.intent == "confused"
    assert plan.correct is False and plan.error_code is not None


def test_materials_lower_the_strength_of_every_stage_so_each_child_gets_there() -> None:
    for stage in ("core", "input-test", "output", "input-teaching"):
        seats = (Seat("Asha", None, False), Seat("Meena", SFL, False, stage=stage))
        cfg = config(0.9, streak=99)
        state = new_session(cfg, seats, 2)
        plan, state = plan_turn(state, cfg, "pose_problem", addressed="Meena", posed=P1)
        for _ in range(4):
            plan, state = plan_turn(state, cfg, "show_bundles", addressed="Meena", posed=None)
        assert plan.correct is True, stage
        assert plan.answer == 23 and plan.written == 23


def test_every_number_the_child_says_is_in_the_plans_allowed_set() -> None:
    for stage in ("core", "input-test", "output", "input-teaching"):
        for seed in range(30):
            (plan, _), _ = one(stage, seed=seed)
            if plan.answer is not None:
                assert plan.answer in plan.allowed_numbers


def test_default_seating_for_a_stage_mix_is_three_core_one_input_test_one_output() -> None:
    seats = fill_seats(
        {}, 0, SFL, {SFL: 3, ErrorCode.SUB_NODEC: 1},
        stage_mix=("core", "input-test", "output", "core"),
    )  # fmt: skip
    assert [s.stage for s in seats] == ["core", "core", "input-test", "output", "core"]
    assert seats[0].error is None  # the always-correct child stays correct


def test_an_unknown_stage_is_refused() -> None:
    with pytest.raises(ValueError):
        fill_seats({}, 0, SFL, {SFL: 3}, stage_mix=("core", "bored"))


def test_the_seating_without_a_stage_mix_is_all_core() -> None:
    seats = fill_seats({}, 0, SFL, {SFL: 3, ErrorCode.SUB_NODEC: 1})
    assert {s.stage for s in seats} == {"core"}


def test_the_stage_never_changes_who_is_in_the_class_only_how_they_err() -> None:
    plain = fill_seats({}, 0, SFL, {SFL: 3, ErrorCode.SUB_NODEC: 1})
    staged = fill_seats(
        {},
        0,
        SFL,
        {SFL: 3, ErrorCode.SUB_NODEC: 1},
        stage_mix=("core", "input-test", "output", "core"),
    )
    assert [(s.name, s.error, s.shy) for s in plain] == [(s.name, s.error, s.shy) for s in staged]
