"""Legacy simulator golden runs for the 32-state Bayesian build
(docs/build/BAYESIAN-32-STATE-BUILD-PROMPT-v2.md step 1): every scenario, seeds 1 to 20, two
scripts.

Per turn it records the speaker, intent, answer, written answer, correctness, error code and
problem, the chorus, and every child's strength, engagement, streak, quiet turns, stage and mood.
Saved once to tests/fixtures/legacy_sim_golden.json with the SHA-256 of engine/simulator.py beside
it (tests/fixtures/legacy_sim.sha256):

    python -m tests.engine.legacy_golden --write

`capture(start, step)` takes how to start a session and play a turn, so the same grid checks the
simulator called directly and the factory in engine/sim_switch.py.
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from engine.simulator import TurnPlan, _mood, fill_seats, new_session, plan_turn
from services.practice.content import load_scenario

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "legacy_sim_golden.json"
HASH_FILE = ROOT / "tests" / "fixtures" / "legacy_sim.sha256"
SIMULATOR = ROOT / "engine" / "simulator.py"

SCENARIOS = ("SUB-SFL", "SUB-NODEC", "ADD-NOCARRY", "PV-HEARD")
SEEDS = range(1, 21)
# The 12-move script of docs/build/reports/BAYESIAN-CHECK.md section 2.9, by seat. "MATERIAL" is
# the scenario's second materials move (the addition and place-value lists have no exchange_ten).
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
MATERIAL = {
    "SUB-SFL": "exchange_ten",
    "SUB-NODEC": "exchange_ten",
    "ADD-NOCARRY": "regroup_ten",
    "PV-HEARD": "show_chart",
}
ROTATION: tuple[int | None, ...] = (1, 2, 3, 4, None)

Start = Callable[[str, int], Any]  # (error, seed) -> state
Step = Callable[[Any, str, str, str | None], tuple[TurnPlan, Any]]  # (state, error, move, to)


def simulator_hash() -> str:
    return hashlib.sha256(SIMULATOR.read_bytes()).hexdigest()


def check_script(error: str) -> list[tuple[str, int | None]]:
    return [(MATERIAL[error] if m == "MATERIAL" else m, s) for m, s in SCRIPT_CHECK]


def every_move_script(error: str) -> list[tuple[str, int | None]]:
    """Every move in the scenario's list, then `other`, twice over, aimed round the seats."""
    ids = [*load_scenario(error).config.moves, "other"]
    return [(m, ROTATION[i % len(ROTATION)]) for i, m in enumerate(ids * 2)]


def seats_for(error: str) -> Any:
    loaded = load_scenario(error)
    return fill_seats(
        {}, 0, loaded.config.error, loaded.scenario.seat_mix, stage_mix=loaded.scenario.stage_mix
    )


def direct_start(error: str, seed: int) -> Any:
    from engine.child_model import LEGACY

    return new_session(load_scenario(error).config, seats_for(error), seed, LEGACY)


def direct_step(state: Any, error: str, move: str, to: str | None) -> tuple[TurnPlan, Any]:
    return plan_turn(state, load_scenario(error).config, move, addressed=to, posed=None)


def _plan(p: TurnPlan) -> dict[str, Any]:
    return {
        "speaker": p.speaker,
        "intent": p.intent,
        "answer": p.answer,
        "written": p.written,
        "correct": p.correct,
        "code": p.error_code.value if p.error_code else None,
        "problem": [p.problem.kind, p.problem.a, p.problem.b] if p.problem else None,
    }


def play(
    error: str, script: list[tuple[str, int | None]], seed: int, start: Start, step: Step
) -> dict[str, Any]:
    state = start(error, seed)
    turns: list[dict[str, Any]] = []
    for move, seat in script:
        if state.finished:
            break
        to = state.children[seat].name if seat is not None else None
        plan, state = step(state, error, move, to)
        turns.append(
            {
                "move": move,
                "to": to,
                **_plan(plan),
                "chorus": [_plan(c) for c in plan.chorus],
                "children": [
                    [
                        c.name,
                        c.strength,
                        c.engagement,
                        c.streak,
                        c.quiet_turns,
                        c.stage,
                        _mood(c),
                    ]
                    for c in state.children
                ],
            }
        )
    return {"error": error, "seed": seed, "turns": turns, "finished": state.finished_reason}


def capture(
    start: Start = direct_start, step: Step = direct_step
) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {"check_script": [], "every_move": []}
    for error in SCENARIOS:
        for seed in SEEDS:
            out["check_script"].append(play(error, check_script(error), seed, start, step))
            out["every_move"].append(play(error, every_move_script(error), seed, start, step))
    return out


def main(argv: list[str]) -> int:
    if "--write" not in argv:
        print("Run with --write to save the legacy golden runs and the simulator hash.")
        return 1
    runs = capture()
    blocks = [
        json.dumps(kind) + ":[\n" + ",\n".join(json.dumps(r, separators=(",", ":")) for r in rows)
        for kind, rows in runs.items()
    ]
    FIXTURE.write_text("{" + "\n],\n".join(blocks) + "\n]}\n", encoding="utf-8")
    HASH_FILE.write_text(simulator_hash() + "  engine/simulator.py\n", encoding="utf-8")
    print(f"wrote {FIXTURE.relative_to(ROOT)} and {HASH_FILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
