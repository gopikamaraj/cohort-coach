"""Shared protocols for the 32-state model's behaviour tests and evals (docs/BAYESIAN-MODEL.md 7.4).

Protocol "2.10" (docs/build/reports/BAYESIAN-CHECK.md section 2.10): SUB-SFL, no class counts; each
round is pose_problem to child X then the chosen move to child X, going round the erring children,
until the session ends or 40 turns. `drill` runs it under either model; `schedule` replaces the
round (a list of move ids, each aimed at child X).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from engine import sim_switch
from engine.bayes.content import Params, load_params
from engine.bayes.planner import BayesState, plan_turn_traced
from engine.bayes.planner import new_session as bayes_new_session
from engine.simulator import Seat, TurnPlan, fill_seats
from services.practice.content import LoadedScenario, load_scenario

MOVES_210 = (
    "decomposition",
    "exchange_ten",
    "show_bundles",
    "compensation",
    "ask_explain",
    "check_back",
    "order_probe",
    "tell_rule",
    "repeat_rule_louder",
)
LEGACY_BASELINE = {  # BAYESIAN-CHECK.md 2.10, printed there (200 seeds)
    "decomposition": 13.6,
    "exchange_ten": 13.6,
    "show_bundles": 13.6,
    "compensation": 14.6,
    "ask_explain": 22.2,
    "check_back": 22.2,
    "order_probe": 22.2,
    "tell_rule": 39.8,
    "repeat_rule_louder": 40.0,
}
SCRIPT_12: tuple[tuple[str, int | None], ...] = (
    ("pose_problem", 1),
    ("ask_explain", 1),
    ("show_bundles", None),
    ("exchange_ten", 1),
    ("pose_problem", 2),
    ("check_back", 2),
    ("scold", 3),
    ("praise", None),
    ("pose_problem", 3),
    ("show_bundles", 3),
    ("pose_problem", None),
    ("other", None),
)


def scenario(error: str = "SUB-SFL") -> tuple[LoadedScenario, tuple[Seat, ...]]:
    loaded = load_scenario(error)
    seats = fill_seats(
        {}, 0, loaded.config.error, loaded.scenario.seat_mix, stage_mix=loaded.scenario.stage_mix
    )
    return loaded, seats


def default_params() -> Params:
    return load_params().defaults


@dataclass
class Run:
    turns: int
    finished_reason: str | None
    plans: list[TurnPlan]
    traces: list[dict[str, Any]] = field(default_factory=list)
    state: Any = None
    attention: list[float] = field(default_factory=list)  # mean erring-child attention per turn


def start(model: str, seed: int, error: str = "SUB-SFL", params: Params | None = None) -> Any:
    loaded, seats = scenario(error)
    if model == "legacy":
        return sim_switch.new_session(loaded.config, seats, seed, model="legacy")
    return bayes_new_session(loaded.config, seats, seed, params or default_params())


def step(state: Any, error: str, move: str, to: str | None) -> tuple[TurnPlan, Any, Any]:
    cfg = load_scenario(error).config
    if isinstance(state, BayesState):
        return plan_turn_traced(state, cfg, move, addressed=to, posed=None)
    plan, nxt, _ = sim_switch.plan_turn(state, cfg, move, addressed=to, posed=None)
    return plan, nxt, None


def drill(
    model: str,
    move: str,
    seed: int,
    *,
    error: str = "SUB-SFL",
    params: Params | None = None,
    schedule: Sequence[str] | None = None,
) -> Run:
    state = start(model, seed, error, params)
    erring = [i for i, c in enumerate(state.children) if c.error]
    rounds = list(schedule) if schedule is not None else ["pose_problem", move]
    run = Run(0, None, [])
    k = 0
    while not state.finished:
        x = state.children[erring[k % len(erring)]].name
        for mv in rounds:
            if state.finished:
                break
            plan, state, trace = step(state, error, mv, x)
            run.plans.append(plan)
            if trace is not None:
                run.traces.append(trace)
            run.attention.append(
                sum(c.engagement for c in state.children if c.error)
                / max(1, sum(1 for c in state.children if c.error))
            )
        k += 1
    run.turns = state.turn
    run.finished_reason = state.finished_reason
    run.state = state
    return run


def play_script(
    model: str,
    seed: int,
    script: Sequence[tuple[str, int | None]] = SCRIPT_12,
    error: str = "SUB-SFL",
    params: Params | None = None,
) -> Run:
    state = start(model, seed, error, params)
    run = Run(0, None, [])
    for move, seat in script:
        if state.finished:
            break
        to = state.children[seat].name if seat is not None else None
        plan, state, trace = step(state, error, move, to)
        run.plans.append(plan)
        if trace is not None:
            run.traces.append(trace)
    run.turns, run.finished_reason, run.state = state.turn, state.finished_reason, state
    return run
