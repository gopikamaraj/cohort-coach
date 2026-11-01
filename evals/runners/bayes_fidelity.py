"""Simulator fidelity for the 32-state model: the sim_fidelity protocol
(evals/runners/sim_fidelity.py, 4 errors x 5 seeds x 10 scripted turns = 200 turns) on the bayesian
planner.

For each turn where a child speaks: the planned answer is the correct answer, or a wrong answer the
independent digit oracle of sim_fidelity.py gives for the child's current error code (the code of
her habit at that moment; a child with no habit who slips errs by the target code, section 5.2),
or the legacy stage form (output: says it right, writes it reversed; input-test: the other
operation or a digit swap); and every number in the child's template line is in the plan's
allowed set. Bar: 100%.

The protocol seats every child as core, as sim_fidelity does. A second pass with the scenarios'
stage mix (core, input-test, output) is reported beside it, outside the bar.

    python -m evals.runners.bayes_fidelity            # writes evals/out/bayes/fidelity.json
    python -m evals.runners.bayes_fidelity --no-write
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from engine.bayes import response as resp
from engine.bayes.planner import new_session, plan_turn_traced
from engine.model import ErrorCode
from engine.simulator import TurnPlan, fill_seats
from evals.runners.bayes_protocols import default_params
from evals.runners.sim_fidelity import line_ok, load_scripts, oracle
from services.practice.content import load_personas, load_scenario
from services.practice.templates import render_line

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "evals" / "out" / "bayes"


def answer_ok(plan: TurnPlan, stage: str, habit_code: ErrorCode | None, target: ErrorCode) -> bool:
    if plan.answer is None or plan.problem is None:
        return True
    p = plan.problem
    if plan.correct:
        return plan.answer == p.correct and plan.written == p.correct
    if stage == "output":
        return plan.answer == p.correct and plan.written == resp.rev(p.correct)
    if stage == "input-test":
        return plan.answer in resp.misheard_options(p) and plan.written == plan.answer
    code = habit_code if habit_code is not None else target  # none: a slip takes the target form
    return plan.error_code == code and plan.answer in (oracle(code, p) - {p.correct})


def run(stages: bool) -> dict[str, Any]:
    params = default_params()
    per_error: dict[str, dict[str, Any]] = {}
    total = matched = 0
    failures: list[dict[str, Any]] = []
    for script in load_scripts():
        error = script["error"]
        loaded = load_scenario(error)
        kids = load_personas().children
        n = m = 0
        for seed in script["seeds"]:
            names = [k.names["en"] for k in kids[:5]]
            seats = fill_seats(
                {}, 0, loaded.scenario.error, loaded.scenario.seat_mix, names=names,
                stage_mix=loaded.scenario.stage_mix if stages else (),
            )  # fmt: skip
            state = new_session(loaded.config, seats, seed, params)
            for step in script["script"]:
                if state.finished:
                    break
                seat = step["seat"]
                to = state.children[seat].name if seat is not None else None
                plan, state, trace = plan_turn_traced(
                    state, loaded.config, step["move"], addressed=to, posed=None
                )
                if plan.speaker is None:
                    continue
                child = next(c for c in state.children if c.name == plan.speaker)
                row = next((r for r in trace["children"] if r["name"] == plan.speaker), None)
                hc = row["true"]["habit_code"] if row else None
                habit_code = ErrorCode(hc) if hc else None
                text = render_line(plan, "en")
                ok = answer_ok(plan, child.stage, habit_code, state.roles.target) and line_ok(
                    plan, text
                )
                n += 1
                m += ok
                if not ok:
                    failures.append({"error": error, "seed": seed, "turn": plan.turn,
                                     "answer": plan.answer, "text": text})  # fmt: skip
        per_error[error] = {"turns": n, "matched": m, "share": m / n if n else 0.0}
        total += n
        matched += m
    return {"turns": total, "matched": matched, "share": matched / total if total else 0.0,
            "per_error": per_error, "failures": failures[:20],
            "passed": total > 0 and matched == total}  # fmt: skip


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args(argv)
    proto = run(stages=False)
    staged = run(stages=True)
    for label, r in (("protocol (all core)", proto), ("with the stage mix", staged)):
        print(f"{label}: {r['matched']}/{r['turns']} match ({r['share']:.0%})")
        for e, s in r["per_error"].items():
            print(f"  {e:<12} turns={s['turns']} matched={s['matched']}")
    print("bar 100% on the protocol:", "PASS" if proto["passed"] else "FAIL")
    if not args.no_write:
        OUT.mkdir(parents=True, exist_ok=True)
        out = {"eval": "bayes_fidelity", "source": "evals/runners/bayes_fidelity.py",
               "set": "evals/sets/sim_fidelity/*.yaml", "bar": 1.0, "protocol": proto,
               "with_stage_mix": staged, "passed": proto["passed"]}  # fmt: skip
        (OUT / "fidelity.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {(OUT / 'fidelity.json').relative_to(ROOT)}")
    return 0 if proto["passed"] and staged["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
