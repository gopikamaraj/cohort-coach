"""Exemplar replay: every recorded Watch run in content/demo_runs/ replayed on its class and seed
through both models (docs/BAYESIAN-MODEL.md section 8). The recorded runs are read, never edited.

The class is rebuilt as start_session builds it (the same fictional names for the run's language
and seed, the scenario's seat and stage mix). Each recorded teacher move is replayed with the
addressee the session used (the machinery record) and, for pose_problem, the problem the Watch run
posed (the one on the board, else the scenario's next). Per run and model: turns, finish reason,
wrong-answer rate by turn (speaker and chorus), and for the bayesian model the final belief
marginals; for legacy, how many turns repeat the recorded engine answer.

    python -m evals.runners.bayes_replay            # writes evals/out/bayes/replay.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from engine import sim_switch
from engine.bayes import belief as bel
from engine.bayes.planner import new_session as bayes_new_session
from engine.bayes.planner import plan_turn_traced
from engine.simulator import TurnPlan, fill_seats
from evals.runners.bayes_protocols import default_params
from services.practice.content import load_scenario
from services.practice.session import _pick_names

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "content" / "demo_runs"
OUT = ROOT / "evals" / "out" / "bayes"


def _wrong_rate(plan: TurnPlan) -> float | None:
    said = [p for p in (plan, *plan.chorus) if p.answer is not None and p.correct is not None]
    if not said:
        return None
    return sum(not p.correct for p in said) / len(said)


def replay(path: Path, model: str) -> dict[str, Any]:
    run = json.loads(path.read_text(encoding="utf-8"))
    prov = run["provenance"]
    loaded = load_scenario(prov["scenario"])
    cfg = loaded.config
    seed, lang = prov["seed"], prov["language"]
    names = [k.names[lang] for k in _pick_names(lang, seed)]
    seats = fill_seats(
        {},
        0,
        loaded.scenario.error,
        loaded.scenario.seat_mix,
        names=names,
        stage_mix=loaded.scenario.stage_mix,
    )
    if model == "legacy":
        state: Any = sim_switch.new_session(cfg, seats, seed, model="legacy")
    else:
        state = bayes_new_session(cfg, seats, seed, default_params())
    rates: list[float | None] = []
    same_as_recorded = compared = 0
    for t in run["turns"]:
        if state.finished:
            break
        move = t["teacher"]["move"]["id"]
        to = t["machinery"]["code"]["move"].get("addressed")
        posed = None
        if move == "pose_problem":
            posed = state.problem or cfg.problems[state.next_problem % len(cfg.problems)]
        if model == "legacy":
            plan, state, _ = sim_switch.plan_turn(state, cfg, move, addressed=to, posed=posed)
        else:
            plan, state, _ = plan_turn_traced(state, cfg, move, addressed=to, posed=posed)
        rates.append(_wrong_rate(plan))
        rec = t["machinery"]["code"]["engine"]
        if model == "legacy":
            compared += 1
            same_as_recorded += (rec["speaker"], rec["answer"]) == (plan.speaker, plan.answer)
    out: dict[str, Any] = {
        "turns": state.turn,
        "finished": state.finished_reason,
        "wrong_rate_by_turn": rates,
    }
    if model == "legacy":
        out["turns_matching_recorded_engine"] = f"{same_as_recorded} of {compared}"
    else:
        out["final_marginals"] = {
            c.name: bel.marginals(np.asarray(s.belief))
            for c, s in zip(state.children, state.seats, strict=True)
            if s.belief is not None
        }
        out["final_true_states"] = {
            c.name: s.true for c, s in zip(state.children, state.seats, strict=True) if s.true
        }
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args(argv)
    result: dict[str, Any] = {}
    for path in sorted(RUNS.glob("*.json")):
        recorded = json.loads(path.read_text(encoding="utf-8"))
        result[path.name] = {
            "recorded_turns": len(recorded["turns"]),
            "legacy": replay(path, "legacy"),
            "bayesian": replay(path, "bayesian"),
        }
        r = result[path.name]
        lg, by = r["legacy"], r["bayesian"]
        print(f"{path.name:<32} recorded {r['recorded_turns']:>2} turns")
        print(
            f"  legacy   {lg['turns']:>2} turns, finished {lg['finished']}, "
            f"{lg['turns_matching_recorded_engine']} turns as recorded"
        )
        print(f"  bayesian {by['turns']:>2} turns, finished {by['finished']}")
    styles: dict[str, dict[str, list[float]]] = {}
    for name, r in result.items():
        style = name.split(".")[1]
        for model in ("legacy", "bayesian"):
            rates = [x for x in r[model]["wrong_rate_by_turn"] if x is not None]
            styles.setdefault(style, {}).setdefault(model, []).append(
                sum(rates[-3:]) / len(rates[-3:]) if rates else 0.0
            )
    summary = {
        style: {m: sum(v) / len(v) for m, v in by_model.items()}
        for style, by_model in styles.items()
    }
    print("mean wrong-answer rate over the last three answering turns, by style:", summary)
    if not args.no_write:
        OUT.mkdir(parents=True, exist_ok=True)
        out = {
            "source": "evals/runners/bayes_replay.py",
            "runs": result,
            "last_three_wrong_rate_by_style": summary,
        }
        (OUT / "replay.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {(OUT / 'replay.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
