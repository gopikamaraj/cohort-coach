"""The class answers together: one to three children speak each turn, and every child in the room
hears what the teacher says to one of them (third person), with a smaller effect than the child
she is talking to."""

from __future__ import annotations

from dataclasses import replace

import pytest

from engine.model import ErrorCode
from engine.simulator import (
    MoveEffect,
    Problem,
    ScenarioConfig,
    Seat,
    SessionState,
    new_session,
    plan_turn,
    wrong_answers,
)

SFL = ErrorCode.SUB_SFL
MOVES = {
    "pose_problem": MoveEffect("answer", 0.0, 0.0, False),
    "ask_explain": MoveEffect("explain", -0.2, 0.05, False),
    "show_bundles": MoveEffect("work_aloud", -0.3, 0.1, False),
    "tell_rule": MoveEffect("agree", -0.05, 0.0, False),
    "praise": MoveEffect("thanks", 0.0, 0.15, False),
    "scold": MoveEffect("quiet", 0.0, -0.3, True),
}
SEATS = (
    Seat("Asha", None, False),
    Seat("Meena", SFL, False),
    Seat("Ravi", SFL, False),
    Seat("Mani", SFL, True),  # shy: speaks only when named
    Seat("Anu", ErrorCode.SUB_NODEC, False),
)


def cfg(**kw: object) -> ScenarioConfig:
    base: dict[str, object] = {
        "error": SFL,
        "start_strength": 0.9,
        "start_engagement": 0.6,
        "max_turns": 40,
        "finish_streak": 2,
        "quiet_turns": 2,
        "problems": (Problem("sub", 52, 29), Problem("sub", 74, 46), Problem("sub", 81, 57)),
        "moves": MOVES,
        "material_moves": {},
        "overhear": 0.5,
        "chorus_max": 3,
    }
    base.update(kw)
    return ScenarioConfig(**base)  # type: ignore[arg-type]


def start(seed: int = 7, c: ScenarioConfig | None = None) -> tuple[ScenarioConfig, SessionState]:
    c = c or cfg()
    return c, new_session(c, SEATS, seed)


def kid(state: SessionState, name: str):  # type: ignore[no-untyped-def]
    return next(k for k in state.children if k.name == name)


def speakers(plan) -> list[str]:  # type: ignore[no-untyped-def]
    return [plan.speaker, *[p.speaker for p in plan.chorus]]


def test_one_to_three_children_speak_and_all_three_counts_happen() -> None:
    counts = set()
    for seed in range(1, 200):
        c, s = start(seed)
        plan, _ = plan_turn(s, c, "pose_problem", addressed=None, posed=None)
        n = len(speakers(plan))
        assert 1 <= n <= 3
        counts.add(n)
    assert counts == {1, 2, 3}


def test_speakers_are_distinct_named_children_in_the_class() -> None:
    for seed in range(1, 120):
        c, s = start(seed)
        plan, _ = plan_turn(s, c, "pose_problem", addressed=None, posed=None)
        names = speakers(plan)
        assert len(set(names)) == len(names)
        assert set(names) <= {k.name for k in s.children}


def test_the_child_she_names_speaks_first() -> None:
    for seed in range(1, 60):
        c, s = start(seed)
        plan, _ = plan_turn(s, c, "ask_explain", addressed="Meena", posed=None)
        assert plan.speaker == "Meena"
        assert "Meena" not in [p.speaker for p in plan.chorus]


def test_the_shy_child_speaks_only_when_named() -> None:
    for seed in range(1, 150):
        c, s = start(seed)
        plan, _ = plan_turn(s, c, "pose_problem", addressed=None, posed=None)
        assert "Mani" not in speakers(plan)
        plan, _ = plan_turn(s, c, "ask_explain", addressed="Ravi", posed=None)
        assert "Mani" not in speakers(plan)
    c, s = start(3)
    plan, _ = plan_turn(s, c, "ask_explain", addressed="Mani", posed=None)
    assert plan.speaker == "Mani"


def test_a_child_who_went_quiet_stays_out_of_the_chorus() -> None:
    c, s = start(5)
    _, s = plan_turn(s, c, "scold", addressed="Ravi", posed=None)
    assert kid(s, "Ravi").quiet_turns > 0
    for seed in range(1, 80):
        s2 = replace(s, seed=seed)
        plan, _ = plan_turn(s2, c, "pose_problem", addressed=None, posed=None)
        assert "Ravi" not in speakers(plan)


def test_everyone_hears_it_the_named_child_fully_the_others_by_the_overhear_share() -> None:
    c, s = start(7)
    _, after = plan_turn(s, c, "ask_explain", addressed="Meena", posed=None)
    assert kid(after, "Meena").strength == pytest.approx(0.7)
    assert kid(after, "Meena").engagement == pytest.approx(0.65)
    assert kid(after, "Ravi").strength == pytest.approx(0.8)  # 0.9 - 0.2 * 0.5
    assert kid(after, "Ravi").engagement == pytest.approx(0.625)
    assert kid(after, "Asha").strength == 0.0  # no error, nothing to lower
    assert kid(after, "Asha").engagement == pytest.approx(0.625)


def test_with_no_overhear_only_the_named_child_changes_as_before() -> None:
    c, s = start(7, cfg(overhear=0.0, chorus_max=1))
    _, after = plan_turn(s, c, "ask_explain", addressed="Meena", posed=None)
    assert kid(after, "Ravi").strength == pytest.approx(0.9)
    assert kid(after, "Ravi").engagement == pytest.approx(0.6)


def test_scolding_one_child_quietens_only_her_but_the_room_notices() -> None:
    c, s = start(7)
    _, after = plan_turn(s, c, "scold", addressed="Ravi", posed=None)
    assert kid(after, "Ravi").quiet_turns > 0
    assert kid(after, "Ravi").engagement == pytest.approx(0.3)
    for name in ("Asha", "Meena", "Anu"):
        assert kid(after, name).quiet_turns == 0
        assert kid(after, name).engagement == pytest.approx(0.45)  # 0.6 - 0.3 * 0.5


def test_a_scolded_turn_has_no_chorus() -> None:
    for seed in range(1, 40):
        c, s = start(seed)
        plan, _ = plan_turn(s, c, "scold", addressed="Ravi", posed=None)
        assert plan.chorus == ()


def test_every_chorus_number_comes_from_the_engine() -> None:
    seen = 0
    for seed in range(1, 150):
        c, s = start(seed)
        plan, _ = plan_turn(s, c, "pose_problem", addressed=None, posed=None)
        for sub in plan.chorus:
            seen += 1
            who = kid(s, sub.speaker)
            assert sub.intent == "answer" and sub.problem == plan.problem
            ok = {plan.problem.correct}
            if who.error:
                ok |= wrong_answers(who.error, plan.problem)
            assert sub.answer in ok
            assert sub.answer in sub.allowed_numbers
            assert sub.correct == (sub.answer == plan.problem.correct)
    assert seen > 50


def test_the_first_speaker_is_the_same_with_or_without_the_chorus() -> None:
    for seed in range(1, 80):
        c1, s1 = start(seed, cfg(overhear=0.0, chorus_max=1))
        c3, s3 = start(seed, cfg(overhear=0.0, chorus_max=3))
        a, _ = plan_turn(s1, c1, "pose_problem", addressed=None, posed=None)
        b, _ = plan_turn(s3, c3, "pose_problem", addressed=None, posed=None)
        assert (a.speaker, a.intent, a.answer, a.written, a.allowed_numbers) == (
            b.speaker,
            b.intent,
            b.answer,
            b.written,
            b.allowed_numbers,
        )


def test_the_chorus_is_replayable_from_the_seed() -> None:
    c, s = start(11)
    a, _ = plan_turn(s, c, "pose_problem", addressed=None, posed=None)
    b, _ = plan_turn(s, c, "pose_problem", addressed=None, posed=None)
    assert a == b


def test_a_child_who_answers_in_the_chorus_has_her_answer_and_streak_updated() -> None:
    for seed in range(1, 100):
        c, s = start(seed)
        plan, after = plan_turn(s, c, "pose_problem", addressed=None, posed=None)
        for sub in plan.chorus:
            now = kid(after, sub.speaker)
            assert now.last_answer == sub.answer
            assert now.streak == (1 if sub.correct else 0)


def test_a_chorus_child_keeps_the_answer_she_already_gave_when_asked_to_explain() -> None:
    c, s = start(4)
    plan, s = plan_turn(s, c, "pose_problem", addressed=None, posed=None)
    given = {k.name: k.last_answer for k in s.children if k.last_answer is not None}
    plan2, _ = plan_turn(s, c, "ask_explain", addressed=None, posed=None)
    for sub in plan2.chorus:
        if sub.speaker in given:
            assert sub.answer == given[sub.speaker]
