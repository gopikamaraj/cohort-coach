from __future__ import annotations

import pytest

import engine.simulator as sim
from engine.model import ErrorCode
from engine.simulator import Problem, TurnPlan, wrong_answers
from evals.runners import sim_fidelity as ev


def plan(answer: int | None, correct: bool | None, p: Problem | None, intent: str = "answer",
         allowed: tuple[int, ...] = ()) -> TurnPlan:  # fmt: skip
    return TurnPlan(
        turn=1, move_id="pose_problem", behaviour="answer", speaker="A", intent=intent,
        problem=p, answer=answer, correct=correct, error_code=None, steps=(),
        allowed_numbers=frozenset(allowed), mood="calm",
    )  # fmt: skip


def test_the_oracle_agrees_with_the_engine_on_every_scenario_problem() -> None:
    from services.practice.content import load_scenario

    for error in ev.ERRORS:
        for p in load_scenario(error).config.problems:
            for code in ErrorCode:
                assert ev.oracle(code, p) - {p.correct} == set(wrong_answers(code, p)), (code, p)


def test_the_full_set_is_200_scripted_turns_and_all_match() -> None:
    result = ev.run()
    assert result["mode"] == "engine_templates" and result["bar"] == {"numeric_match": 1.0}
    assert result["turns"] >= 150  # turns where nobody speaks are not counted
    assert result["numeric_match"] == 1.0 and result["passed"] is True
    scripts = ev.load_scripts()
    assert sum(len(s["script"]) * len(s["seeds"]) for s in scripts) == 200
    assert set(result["per_error"]) == set(ev.ERRORS)


def test_answer_ok_rejects_numbers_the_error_cannot_give() -> None:
    p = Problem("sub", 52, 29)
    assert ev.answer_ok(plan(37, False, p), ErrorCode.SUB_SFL)
    assert ev.answer_ok(plan(23, True, p), ErrorCode.SUB_SFL)
    assert not ev.answer_ok(plan(38, False, p), ErrorCode.SUB_SFL)  # not an SFL answer
    assert not ev.answer_ok(plan(33, False, p), ErrorCode.SUB_SFL)  # NODEC's answer, wrong child
    assert not ev.answer_ok(plan(37, False, p), None)  # a child with no error is never wrong
    assert not ev.answer_ok(plan(37, True, p), ErrorCode.SUB_SFL)  # flag disagrees with the number


def test_line_ok_rejects_extra_numbers_and_a_missing_answer() -> None:
    p = Problem("sub", 52, 29)
    pl = plan(37, False, p, allowed=(52, 29, 37))
    assert ev.line_ok(pl, "37, Miss!")
    assert not ev.line_ok(pl, "36, Miss!")
    assert not ev.line_ok(pl, "Yes Miss.")  # an answer line must say the answer
    assert not ev.line_ok(pl, "37 and 99")


def test_a_broken_simulator_fails_the_eval(monkeypatch: pytest.MonkeyPatch) -> None:
    real = sim.wrong_answers
    monkeypatch.setattr(sim, "wrong_answers", lambda e, p: frozenset(x + 1 for x in real(e, p)))
    result = ev.run()
    assert result["passed"] is False and result["numeric_match"] < 1.0


def test_the_estimate_comes_from_prices() -> None:
    assert 0 < ev.estimate_cost(60) < 1.0


def test_a_limit_is_shared_evenly_by_the_four_errors() -> None:
    result = ev.run(limit=40)
    assert {s["turns"] for s in result["per_error"].values()} == {10}
    assert result["turns"] == 40
