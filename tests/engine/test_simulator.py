from __future__ import annotations

import pytest

from engine.bugs import correct_answer
from engine.model import ErrorCode, Item, ItemType
from engine.simulator import (
    Child,
    MoveEffect,
    Problem,
    ScenarioConfig,
    Seat,
    SessionState,
    correct_steps,
    doubt_steps,
    fill_seats,
    is_finished,
    new_session,
    plan_turn,
    reasoning_steps,
    wrong_answers,
)

SFL = ErrorCode.SUB_SFL
P1 = Problem("sub", 52, 29)  # SFL -> 37, NODEC -> 33, correct 23

MOVES = {
    "pose_problem": MoveEffect("answer", 0.0, 0.0, False),
    "ask_explain": MoveEffect("explain", -0.2, 0.05, False),
    "show_bundles": MoveEffect("work_aloud", -0.3, 0.1, False),
    "check_back": MoveEffect("doubt", -0.2, 0.05, False),
    "tell_rule": MoveEffect("agree", -0.05, 0.0, False),
    "praise": MoveEffect("thanks", 0.0, 0.15, False),
    "scold": MoveEffect("quiet", 0.0, -0.3, True),
}


def config(**kw: object) -> ScenarioConfig:
    base: dict[str, object] = {
        "error": SFL,
        "start_strength": 0.9,
        "start_engagement": 0.6,
        "max_turns": 40,
        "finish_streak": 2,
        "quiet_turns": 2,
        "problems": (Problem("sub", 52, 29), Problem("sub", 74, 46), Problem("sub", 81, 57)),
        "moves": MOVES,
        "material_moves": {"bundles": "show_bundles"},
    }
    base.update(kw)
    return ScenarioConfig(**base)  # type: ignore[arg-type]


SEATS = (
    Seat("Asha", None, False),
    Seat("Meena", SFL, False),
    Seat("Ravi", SFL, False),
    Seat("Mani", SFL, True),  # shy
    Seat("Anu", ErrorCode.SUB_NODEC, False),
)


def start(seed: int = 7, cfg: ScenarioConfig | None = None) -> tuple[ScenarioConfig, SessionState]:
    cfg = cfg or config()
    return cfg, new_session(cfg, SEATS, seed)


def child(state: SessionState, name: str) -> Child:
    return next(c for c in state.children if c.name == name)


# bug functions ------------------------------------------------------------------------------


def test_wrong_answers_come_from_the_bug_functions() -> None:
    assert wrong_answers(SFL, P1) == {37}
    assert wrong_answers(ErrorCode.SUB_NODEC, P1) == {33}
    assert wrong_answers(ErrorCode.ADD_NOCARRY, Problem("add", 47, 25)) == {62}
    assert wrong_answers(ErrorCode.PV_HEARD, Problem("dictation", 43)) == {403}
    assert wrong_answers(ErrorCode.PV_REVERSE, Problem("dictation", 43)) == {34}


def test_an_error_that_does_not_apply_to_the_problem_gives_no_wrong_answer() -> None:
    assert wrong_answers(SFL, Problem("add", 47, 25)) == frozenset()
    assert (
        wrong_answers(SFL, Problem("sub", 48, 23)) == frozenset()
    )  # no borrowing: same as correct


def test_problem_correct_answers_match_the_engine() -> None:
    assert Problem("sub", 52, 29).correct == correct_answer(Item(7, ItemType.SUB_BORROW, 52, 29))
    assert Problem("add", 47, 25).correct == 72
    assert Problem("dictation", 43).correct == 43


# session setup ------------------------------------------------------------------------------


def test_new_session_starts_every_error_child_at_the_start_strength() -> None:
    _, state = start()
    assert child(state, "Asha").strength == 0.0 and child(state, "Asha").error is None
    assert all(c.strength == 0.9 for c in state.children if c.error)
    assert all(c.engagement == 0.6 for c in state.children)
    assert state.turn == 0 and state.problem is None and not state.finished


# determinism --------------------------------------------------------------------------------


def play(seed: int) -> list[tuple[object, ...]]:
    cfg, state = start(seed)
    out: list[tuple[object, ...]] = []
    script = [("pose_problem", "Meena"), ("ask_explain", "Meena"), ("show_bundles", "Meena"),
              ("pose_problem", "Ravi"), ("check_back", "Ravi"), ("pose_problem", None)]  # fmt: skip
    for move, who in script:
        plan, state = plan_turn(state, cfg, move, addressed=who, posed=None)
        out.append((plan.speaker, plan.intent, plan.answer, plan.steps, plan.mood))
    return out


def test_same_seed_same_session_different_seed_may_differ() -> None:
    assert play(11) == play(11)
    assert any(play(s) != play(11) for s in range(12, 40))


# move effects -------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("move", "delta"),
    [("show_bundles", -0.3), ("ask_explain", -0.2), ("check_back", -0.2), ("tell_rule", -0.05)],
)
def test_each_move_changes_the_addressed_childs_strength_exactly_as_configured(
    move: str, delta: float
) -> None:
    cfg, state = start()
    _, state = plan_turn(state, cfg, "pose_problem", addressed="Meena", posed=None)
    before = child(state, "Meena").strength
    plan, state = plan_turn(state, cfg, move, addressed="Meena", posed=None)
    assert child(state, "Meena").strength == pytest.approx(before + delta)
    assert plan.strength_after["Meena"] == pytest.approx(before + delta)
    assert child(state, "Ravi").strength == 0.9  # not addressed: unchanged


def test_a_class_level_move_reaches_every_child_with_the_error() -> None:
    cfg, state = start()
    _, state = plan_turn(state, cfg, "show_bundles", addressed=None, posed=None)
    for c in state.children:
        assert c.strength == (pytest.approx(0.6) if c.error else 0.0)


def test_strength_never_leaves_zero_to_one() -> None:
    cfg, state = start()
    for _ in range(6):
        _, state = plan_turn(state, cfg, "show_bundles", addressed="Meena", posed=None)
    assert child(state, "Meena").strength == 0.0


def test_praise_raises_engagement_and_scold_lowers_it_and_silences_the_child() -> None:
    cfg, state = start()
    _, state = plan_turn(state, cfg, "praise", addressed="Meena", posed=None)
    assert child(state, "Meena").engagement == pytest.approx(0.75)
    _, state = plan_turn(state, cfg, "scold", addressed="Ravi", posed=None)
    assert child(state, "Ravi").engagement == pytest.approx(0.3)
    assert child(state, "Ravi").strength == 0.9  # scolding teaches nothing
    plan, state = plan_turn(state, cfg, "pose_problem", addressed="Ravi", posed=None)
    assert plan.intent == "quiet" and plan.answer is None and plan.speaker == "Ravi"


def test_a_scolded_child_is_quiet_for_exactly_the_configured_turns() -> None:
    cfg, state = start()
    _, state = plan_turn(state, cfg, "scold", addressed="Ravi", posed=None)
    intents = []
    for _ in range(3):
        plan, state = plan_turn(state, cfg, "pose_problem", addressed="Ravi", posed=None)
        intents.append(plan.intent)
    assert intents == ["quiet", "quiet", "answer"]


# the shy child ------------------------------------------------------------------------------


def test_the_shy_child_speaks_only_when_named() -> None:
    cfg, state = start()
    speakers = set()
    for _ in range(30):
        plan, state = plan_turn(state, cfg, "pose_problem", addressed=None, posed=None)
        speakers.add(plan.speaker)
    assert "Mani" not in speakers
    cfg, state = start()
    plan, _ = plan_turn(state, cfg, "pose_problem", addressed="Mani", posed=None)
    assert plan.speaker == "Mani"


# answers ------------------------------------------------------------------------------------


def test_an_error_child_at_strength_one_always_gives_the_bug_answer() -> None:
    cfg = config(start_strength=1.0)
    for seed in range(20):
        state = new_session(cfg, SEATS, seed)
        plan, _ = plan_turn(state, cfg, "pose_problem", addressed="Meena", posed=P1)
        assert plan.answer == 37 and plan.correct is False and plan.error_code == SFL


def test_an_error_child_at_strength_zero_and_the_correct_child_answer_correctly() -> None:
    cfg = config(start_strength=0.0)
    for seed in range(20):
        state = new_session(cfg, SEATS, seed)
        plan, _ = plan_turn(state, cfg, "pose_problem", addressed="Meena", posed=P1)
        assert plan.answer == 23 and plan.correct is True
        plan, _ = plan_turn(state, cfg, "pose_problem", addressed="Asha", posed=P1)
        assert plan.answer == 23 and plan.correct is True and plan.error_code is None


def test_wrong_rate_tracks_strength() -> None:
    cfg = config(start_strength=0.5)
    wrong = 0
    for seed in range(400):
        state = new_session(cfg, SEATS, seed)
        plan, _ = plan_turn(state, cfg, "pose_problem", addressed="Meena", posed=P1)
        wrong += plan.correct is False
    assert 150 < wrong < 250


def test_the_nodec_child_gives_the_nodec_answer() -> None:
    cfg = config(start_strength=1.0)
    plan, _ = plan_turn(new_session(cfg, SEATS, 1), cfg, "pose_problem", addressed="Anu", posed=P1)
    assert plan.answer == 33 and plan.error_code == ErrorCode.SUB_NODEC


def test_a_posed_problem_goes_through_the_bug_function() -> None:
    cfg = config(start_strength=1.0)
    plan, state = plan_turn(
        new_session(cfg, SEATS, 1),
        cfg,
        "pose_problem",
        addressed="Meena",
        posed=Problem("sub", 74, 46),
    )
    assert plan.answer == 32 and plan.problem == Problem("sub", 74, 46)  # 10*|7-4| + |4-6|
    assert state.problem == Problem("sub", 74, 46)


def test_without_a_posed_problem_the_next_scenario_problem_is_used_in_order() -> None:
    cfg, state = start()
    seen = []
    for _ in range(4):
        plan, state = plan_turn(state, cfg, "pose_problem", addressed="Meena", posed=None)
        seen.append(plan.problem)
    assert seen == [Problem("sub", 52, 29), Problem("sub", 74, 46), Problem("sub", 81, 57),
                    Problem("sub", 52, 29)]  # fmt: skip


def test_an_invalid_posed_problem_falls_back_to_the_scenario() -> None:
    cfg, state = start()
    for bad in (Problem("sub", 5, 29), Problem("sub", 52, 129), Problem("sub", 20, 30)):
        plan, _ = plan_turn(state, cfg, "pose_problem", addressed="Meena", posed=bad)
        assert plan.problem == Problem("sub", 52, 29)


# numbers always from the engine -------------------------------------------------------------


def test_every_number_in_a_plan_is_allowed_and_comes_from_the_problem_or_the_bug_functions() -> (
    None
):
    cfg = config(start_strength=1.0)
    for seed in range(15):
        state = new_session(cfg, SEATS, seed)
        for move in ("pose_problem", "ask_explain", "check_back", "show_bundles", "tell_rule"):
            for who in ("Meena", "Anu", "Asha"):
                plan, state = plan_turn(state, cfg, move, addressed=who, posed=None)
                p = plan.problem
                if p is None:
                    continue
                legit = {p.a, p.b, p.correct} | set(wrong_answers(SFL, p))
                legit |= set(wrong_answers(ErrorCode.SUB_NODEC, p))
                for step in plan.steps:
                    assert plan.allowed_numbers >= set(step.numbers)
                if plan.answer is not None:
                    assert plan.answer in legit and plan.answer in plan.allowed_numbers


def test_explaining_a_wrong_answer_reveals_the_faulty_steps_as_data() -> None:
    cfg = config(start_strength=1.0)
    state = new_session(cfg, SEATS, 3)
    _, state = plan_turn(state, cfg, "pose_problem", addressed="Meena", posed=P1)
    plan, _ = plan_turn(state, cfg, "ask_explain", addressed="Meena", posed=None)
    assert plan.intent == "explain" and plan.answer == 37
    assert [(s.op, s.numbers) for s in plan.steps] == [
        ("cant", (2, 9)), ("minus", (9, 2, 7)), ("minus", (5, 2, 3)),
    ]  # fmt: skip


def test_checking_by_adding_back_makes_the_child_doubt_with_code_made_numbers() -> None:
    cfg = config(start_strength=1.0)
    state = new_session(cfg, SEATS, 3)
    _, state = plan_turn(state, cfg, "pose_problem", addressed="Meena", posed=P1)
    plan, _ = plan_turn(state, cfg, "check_back", addressed="Meena", posed=None)
    assert plan.intent == "doubt" and plan.mood == "doubtful"
    assert [(s.op, s.numbers) for s in plan.steps] == [("addback", (37, 29, 66, 52))]


def test_showing_bundles_makes_a_child_with_low_strength_work_it_out_correctly() -> None:
    cfg = config(start_strength=0.0)
    state = new_session(cfg, SEATS, 3)
    _, state = plan_turn(state, cfg, "pose_problem", addressed="Meena", posed=P1)
    plan, _ = plan_turn(state, cfg, "show_bundles", addressed="Meena", posed=None)
    assert plan.intent == "work_aloud" and plan.correct is True and plan.answer == 23
    assert plan.steps[-1].numbers[-1] == 2  # 4 bundles minus 2 bundles: 2 bundles left


def test_step_builders_for_every_tracked_error() -> None:
    assert [s.op for s in reasoning_steps(ErrorCode.SUB_NODEC, P1, 33)] == [
        "cant", "borrow", "minus", "minus",
    ]  # fmt: skip
    add = Problem("add", 47, 25)
    assert [(s.op, s.numbers) for s in reasoning_steps(ErrorCode.ADD_NOCARRY, add, 62)] == [
        ("plus", (7, 5, 12)), ("write", (2,)), ("plus", (4, 2, 6)),
    ]  # fmt: skip
    assert reasoning_steps(ErrorCode.PV_HEARD, Problem("dictation", 43), 403)[0].numbers == (
        40,
        3,
        403,
    )
    assert reasoning_steps(ErrorCode.PV_REVERSE, Problem("dictation", 43), 34)[0].numbers == (
        4,
        3,
        34,
    )
    assert doubt_steps(add, 62)[0].numbers == (62, 25, 37, 47)
    assert doubt_steps(Problem("dictation", 43), 403)[0].numbers == (403, 43)
    assert correct_steps(P1)[0].op == "open"


# end conditions -----------------------------------------------------------------------------


def test_session_finishes_when_every_error_child_is_correct_twice_in_a_row() -> None:
    cfg = config(start_strength=0.0)
    state = new_session(cfg, SEATS, 1)
    assert not is_finished(state, cfg)
    for who in ("Meena", "Ravi", "Mani", "Anu"):
        for _ in range(2):
            plan, state = plan_turn(state, cfg, "pose_problem", addressed=who, posed=None)
            assert plan.correct is True
    assert state.finished and state.finished_reason == "all_correct" and is_finished(state, cfg)


def test_one_wrong_answer_resets_the_streak() -> None:
    cfg = config(start_strength=0.0)
    state = new_session(cfg, SEATS, 1)
    _, state = plan_turn(state, cfg, "pose_problem", addressed="Meena", posed=None)
    assert child(state, "Meena").streak == 1
    cfg2 = config(start_strength=1.0)
    state2 = new_session(cfg2, SEATS, 1)
    _, state2 = plan_turn(state2, cfg2, "pose_problem", addressed="Meena", posed=None)
    assert child(state2, "Meena").streak == 0


def test_session_ends_at_the_turn_cap() -> None:
    cfg = config(max_turns=5)
    state = new_session(cfg, SEATS, 1)
    for _ in range(5):
        _, state = plan_turn(state, cfg, "praise", addressed="Asha", posed=None)
    assert state.finished and state.finished_reason == "turn_cap" and state.turn == 5


def test_a_finished_session_takes_no_more_turns() -> None:
    cfg = config(max_turns=1)
    state = new_session(cfg, SEATS, 1)
    _, state = plan_turn(state, cfg, "praise", addressed="Asha", posed=None)
    with pytest.raises(ValueError):
        plan_turn(state, cfg, "praise", addressed="Asha", posed=None)


# other, off-task, unknown --------------------------------------------------------------------


@pytest.mark.parametrize("move", ["other", "off_task"])
def test_other_and_off_task_change_nothing_but_the_turn_counter(move: str) -> None:
    cfg, state = start()
    plan, after = plan_turn(state, cfg, move, addressed="Meena", posed=None)
    assert plan.intent == "confused" and plan.answer is None and plan.steps == ()
    assert after.children == state.children and after.turn == state.turn + 1


def test_an_unknown_move_is_an_error_not_a_silent_no_op() -> None:
    cfg, state = start()
    with pytest.raises(ValueError):
        plan_turn(state, cfg, "teleport", addressed=None, posed=None)


def test_an_unknown_child_name_is_treated_as_the_whole_class() -> None:
    cfg, state = start()
    plan, _ = plan_turn(state, cfg, "show_bundles", addressed="Nobody", posed=None)
    assert set(plan.strength_after) == {"Meena", "Ravi", "Mani", "Anu"}


# seat filling -------------------------------------------------------------------------------


def test_seats_follow_the_class_error_mix() -> None:
    # 40% of the class shows SUB-SFL: 2 of the 5 children do.
    seats = fill_seats({SFL: 10, ErrorCode.SUB_NODEC: 0}, 25, SFL, {SFL: 3, ErrorCode.SUB_NODEC: 1})
    assert len(seats) == 5
    assert sum(s.error == SFL for s in seats) == 2
    assert sum(s.error is None for s in seats) >= 1  # always-correct
    assert sum(s.shy for s in seats) == 1


def test_seats_always_include_the_target_error_and_a_correct_child() -> None:
    seats = fill_seats({SFL: 1}, 40, SFL, {SFL: 3, ErrorCode.SUB_NODEC: 1})
    assert sum(s.error == SFL for s in seats) >= 1 and seats[0].error is None


def test_seats_fall_back_to_the_demo_mix_without_class_counts() -> None:
    seats = fill_seats({}, 0, SFL, {SFL: 3, ErrorCode.SUB_NODEC: 1})
    assert sorted(s.error.value for s in seats if s.error) == [
        "SUB-NODEC",
        "SUB-SFL",
        "SUB-SFL",
        "SUB-SFL",
    ]


def test_seats_never_hold_more_than_four_error_children() -> None:
    seats = fill_seats(
        {SFL: 30, ErrorCode.SUB_NODEC: 30}, 40, SFL, {SFL: 3, ErrorCode.SUB_NODEC: 1}
    )
    assert sum(s.error is not None for s in seats) == 4
    assert seats[0].error is None
