"""Legacy simulator golden runs: a fixed grid of classes, seeds and teacher scripts.

`capture()` plays the grid and records, per turn, who spoke, what she said and whether it was right,
the chorus, and every child's strength, engagement, streak, quiet turns and last answer. The output
was saved to tests/fixtures/sim_legacy_golden.json before the Bayesian model was added
(scripts/capture_sim_golden.py); test_simulator_golden.py checks that legacy still plays the same.
"""

from __future__ import annotations

from typing import Any

from engine.simulator import TurnPlan, fill_seats, new_session, plan_turn
from services.practice.content import load_scenario

SCENARIOS = ("SUB-SFL", "ADD-NOCARRY")
SEEDS = range(1, 21)
# The 12-move script of docs/build/reports/BAYESIAN-CHECK.md section 2.9, by seat (seat 1 = Ravi,
# 2 = Meena, 3 = Arun in that report). "MATERIAL" is the scenario's second materials move:
# exchange_ten for SUB-SFL, regroup_ten for ADD-NOCARRY.
SCRIPT_CHECK: tuple[tuple[str, int | None], ...] = (
    ("pose_problem", 1),
    ("ask_explain", 1),
    ("show_bundles", None),
    ("MATERIAL", 1),
    ("pose_problem", 2),
    ("check_back", 2),
    ("scold", 3),
    ("praise", None),
    ("pose_problem", 3),
    ("show_bundles", 3),
    ("pose_problem", None),
    ("other", None),
)
MATERIAL = {"SUB-SFL": "exchange_ten", "ADD-NOCARRY": "regroup_ten"}
ROTATION: tuple[int | None, ...] = (1, 2, 3, 4, None)


def every_move_script(error: str) -> list[tuple[str, int | None]]:
    """Every move in the scenario's list, then `other`, twice over, aimed round the seats."""
    ids = [*load_scenario(error).config.moves, "other"]
    return [(m, ROTATION[i % len(ROTATION)]) for i, m in enumerate(ids * 2)]


def _plan(p: TurnPlan) -> dict[str, Any]:
    return {
        "speaker": p.speaker,
        "intent": p.intent,
        "answer": p.answer,
        "written": p.written,
        "correct": p.correct,
        "code": p.error_code.value if p.error_code else None,
    }


def play(error: str, script: list[tuple[str, int | None]], seed: int) -> dict[str, Any]:
    loaded = load_scenario(error)
    cfg = loaded.config
    seats = fill_seats(
        {}, 0, cfg.error, loaded.scenario.seat_mix, stage_mix=loaded.scenario.stage_mix
    )
    state = new_session(cfg, seats, seed)
    turns: list[dict[str, Any]] = []
    for move, seat in script:
        if state.finished:
            break
        addressed = state.children[seat].name if seat is not None else None
        plan, state = plan_turn(state, cfg, move, addressed=addressed, posed=None)
        turns.append(
            {
                "move": move,
                "to": addressed,
                **_plan(plan),
                "chorus": [_plan(c) for c in plan.chorus],
                "children": [
                    [c.name, c.strength, c.engagement, c.streak, c.quiet_turns, c.last_answer]
                    for c in state.children
                ],
            }
        )
    return {"error": error, "seed": seed, "turns": turns, "finished": state.finished_reason}


def capture() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {"check_script": [], "every_move": []}
    for error in SCENARIOS:
        check = [(MATERIAL[error] if m == "MATERIAL" else m, s) for m, s in SCRIPT_CHECK]
        every = every_move_script(error)
        for seed in SEEDS:
            out["check_script"].append(play(error, check, seed))
            out["every_move"].append(play(error, every, seed))
    return out
