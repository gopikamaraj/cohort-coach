"""What the bayesian planner promises the rest of the engine, over many seeds and every scenario
(docs/BAYESIAN-MODEL.md 7.1): numbers only from the allowed set, wrong numbers only from the bug
functions or the legacy stage forms, the correct child always right; and a full rehearsal through
take_turn with the stub AI client, with the debug trace kept out of the API response."""

from __future__ import annotations

import json
import random

import pytest

from ai.audit import SqlAuditSink
from ai.client import CallContext
from engine.bayes import response as resp
from engine.simulator import TurnPlan, wrong_answers
from evals.runners.bayes_protocols import start, step
from services.practice.content import load_scenario
from services.practice.stub_client import StubClient

SCENARIOS = ("SUB-SFL", "SUB-NODEC", "ADD-NOCARRY", "PV-HEARD")


def _plans(error: str, seed: int) -> list[tuple[TurnPlan, dict[str, TurnPlan]]]:
    moves = [*load_scenario(error).config.moves, "other", "off_task"]
    rng = random.Random(f"contract:{error}:{seed}")
    state = start("bayesian", seed, error)
    out = []
    while not state.finished:
        names = [c.name for c in state.children]
        to = rng.choice([None, *names])
        plan, state, _ = step(state, error, rng.choice(moves), to)
        out.append((plan, {c.name: c for c in state.children}))  # type: ignore[misc]
    return out


@pytest.mark.parametrize("error", SCENARIOS)
def test_numbers_answers_and_the_correct_child_over_many_seeds(error: str) -> None:
    for seed in range(1, 31):
        state0 = start("bayesian", seed, error)
        kids = {c.name: c for c in state0.children}
        codes = {state0.roles.target, state0.roles.sibling} - {None}
        for plan, _ in _plans(error, seed):
            for p in (plan, *plan.chorus):
                for n in (p.answer, p.written):
                    if n is not None:
                        assert n in p.allowed_numbers
                for s in p.steps:
                    assert set(s.numbers) <= p.allowed_numbers
                if p.speaker is None or p.answer is None or p.problem is None:
                    continue
                child = kids[p.speaker]
                if child.error is None:
                    assert p.correct and p.answer == p.written == p.problem.correct
                    continue
                if p.correct:
                    continue
                if child.stage == "output":
                    assert p.answer == p.problem.correct
                    assert p.written == resp.rev(p.problem.correct)
                elif child.stage == "input-test":
                    assert p.answer in resp.misheard_options(p.problem)
                else:
                    assert p.error_code is not None
                    assert p.answer in wrong_answers(p.error_code, p.problem)
                    assert p.error_code in codes  # the code of her habit now


@pytest.fixture
def ctx(sink: SqlAuditSink) -> CallContext:
    return CallContext(mode="stub", sink=sink, client=StubClient())


def test_a_full_rehearsal_runs_through_take_turn_and_the_trace_stays_out_of_the_response(
    ctx: CallContext, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import logging

    from services.practice.session import end_session, start_session, take_turn

    monkeypatch.setenv("SIMULATOR_MODEL", "bayesian")
    s = start_session("SUB-SFL", "en", seed=5)
    assert s.model == "bayesian"
    name = s.state.children[1].name
    lines = [
        f"{name}, what is 52 minus 29?",
        "Tell me how you got that.",
        "Here is 52: 5 bundles and 2 sticks. Take away 9 sticks.",
        "Let us check by adding back.",
    ]
    with caplog.at_level(logging.DEBUG, logger="services.practice.session"):
        results = [take_turn(s, text=line, context=ctx) for line in lines]
        results.append(take_turn(s, material="bundles", context=ctx))
    assert [r.turn for r in results] == [1, 2, 3, 4, 5]
    for r in results:
        said = {int(x) for x in "".join(c if c.isdigit() else " " for c in r.child_text).split()}
        assert said <= set(r.numbers), (r.child_text, r.numbers)
        body = json.dumps(r.__dict__, default=str)
        for word in ("belief", "marginals", "entropy", "habit", "eig", "place_value"):
            assert word not in body, word
        assert len(r.children) == 5 and all("level" in c for c in r.children)
    assert any("bayes trace" in rec.message for rec in caplog.records)
    card, _ = end_session(s, context=ctx)
    assert card.source in ("ai", "template")
