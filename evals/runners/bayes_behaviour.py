"""Behaviour tests B1 to B8 for the 32-state model (docs/BAYESIAN-MODEL.md 7.4), as measurements.

Each function runs at least 200 seeds and returns the measured values with the fixed threshold and
a pass flag. tests/engine/bayes/test_bayes_behaviour.py asserts the flags; this runner writes them
all to evals/out/bayes/behaviour.json for the report. A failure is reported with its measured
value; thresholds, parameters and the model are not changed to pass.

    python -m evals.runners.bayes_behaviour            # writes evals/out/bayes/behaviour.json
    python -m evals.runners.bayes_behaviour --no-write
"""

from __future__ import annotations

import argparse
import inspect
import json
import random
import statistics
import sys
from collections.abc import Callable
from dataclasses import fields
from pathlib import Path
from typing import Any

import numpy as np

from engine.bayes import dynamics as dyn
from engine.bayes import response as resp
from engine.bayes.content import NEUTRAL_MOVE, load_moves
from engine.bayes.planner import BayesState, first_step_item
from engine.bayes.state import index, mask
from evals.runners.bayes_protocols import (
    MOVES_210,
    default_params,
    drill,
    play_script,
    scenario,
    start,
    step,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "evals" / "out" / "bayes"
SEEDS = range(1, 201)


def _fingerprint(run: Any) -> list[Any]:
    out: list[Any] = []
    for plan, trace in zip(run.plans, run.traces, strict=True):
        out.append(
            [
                plan.speaker,
                plan.answer,
                plan.written,
                [(c.speaker, c.answer) for c in plan.chorus],
                [(c["true"], c["marginals"]) for c in trace["children"]],
            ]
        )
    return out


def b1_determinism() -> dict[str, Any]:
    same = all(
        _fingerprint(play_script("bayesian", s)) == _fingerprint(play_script("bayesian", s))
        for s in SEEDS
    )
    differ = _fingerprint(play_script("bayesian", 5)) != _fingerprint(play_script("bayesian", 6))
    return {
        "seeds": len(SEEDS),
        "identical_every_seed": same,
        "seed5_differs_from_seed6": differ,
        "threshold": "identical for every seed; 5 != 6",
        "pass": same and differ,
    }


def b2_teaching_quality() -> dict[str, Any]:
    moves = ("show_bundles", "exchange_ten", "decomposition", "tell_rule", "repeat_rule_louder")
    mean = {m: statistics.fmean(drill("bayesian", m, s).turns for s in SEEDS) for m in moves}
    good, weak = moves[:3], moves[3:]
    ok = all(mean[g] < mean[w] for g in good for w in weak)
    return {
        "seeds": len(SEEDS),
        "mean_turns": mean,
        "threshold": "each of show_bundles, exchange_ten, decomposition below both rule moves",
        "pass": ok,
    }


def b3_prerequisites() -> dict[str, Any]:
    p = default_params()
    spec = load_moves()["show_bundles"]
    learned: dict[int, list[bool]] = {0: [], 1: []}
    for s in SEEDS:
        st = start("bayesian", s)
        roles = st.roles
        for i, seat in enumerate(st.seats):
            if seat.true is None or seat.true["exchange"] != 0:
                continue
            ctx = dyn.TurnContext(spec, 1.0, 0.6, 0.0, 0)
            u = [random.Random(f"bayes:trans:{s}:1:{i}").random() for _ in range(4)]
            nxt, _ = dyn.sample_next(seat.true, ctx, roles, p, u)
            learned[int(seat.true["place_value"])].append(nxt["exchange"] == 1)
    rate = {k: sum(v) / len(v) for k, v in learned.items()}
    diff = rate[1] - rate[0]
    return {
        "seeds": len(SEEDS),
        "children": {k: len(v) for k, v in learned.items()},
        "rate_P1": rate[1],
        "rate_P0": rate[0],
        "difference": diff,
        "threshold": ">= 0.10",
        "pass": diff >= 0.10,
    }


def b4_attention() -> dict[str, Any]:
    out: dict[str, dict[str, float]] = {}
    for first in ("scold", "praise"):
        runs = [
            drill("bayesian", "show_bundles", s, schedule=["pose_problem", first, "show_bundles"])
            for s in SEEDS
        ]
        out[first] = {
            "mean_turns": statistics.fmean(r.turns for r in runs),
            "mean_attention": statistics.fmean(statistics.fmean(r.attention) for r in runs),
        }
    ok = (
        out["scold"]["mean_turns"] > out["praise"]["mean_turns"]
        and out["scold"]["mean_attention"] < out["praise"]["mean_attention"]
    )
    return {
        "seeds": len(SEEDS),
        **out,
        "threshold": "scold finishes later and has lower mean attention",
        "pass": ok,
    }


def _plearn_on_teaching_turns(schedule: list[str], seed: int) -> list[float]:
    p = default_params()
    spec = load_moves()["show_bundles"]
    st = start("bayesian", seed)
    x = st.children[1].name
    vals: list[float] = []
    for mv in schedule:
        _, st, trace = step(st, "SUB-SFL", mv, x)
        if mv == "show_bundles":
            row = next(c for c in trace["children"] if c["name"] == x)
            ctx = dyn.TurnContext(spec, 1.0, row["attention"], row["overload"], 0)
            vals.append(dyn.p_learn(spec.cov_E, 1.0, ctx, p))  # a child with P = 1, E = 0
    return vals


def b5_overload() -> dict[str, Any]:
    consecutive = ["show_bundles"] * 4
    spaced = ["show_bundles", "pose_problem"] * 3 + ["show_bundles"]
    c = statistics.fmean(v for s in SEEDS for v in _plearn_on_teaching_turns(consecutive, s))
    sp = statistics.fmean(v for s in SEEDS for v in _plearn_on_teaching_turns(spaced, s))
    return {
        "seeds": len(SEEDS),
        "mean_p_learn_consecutive": c,
        "mean_p_learn_spaced": sp,
        "threshold": "consecutive < spaced",
        "pass": c < sp,
    }


def b6_priming() -> dict[str, Any]:
    """show_bundles to the class (a demo, r = 1), then two neutral turns."""
    p = default_params()
    loaded, _ = scenario()
    rises: list[tuple[int, float, float]] = []  # (turn, primed, unprimed)
    states_same = True
    for s in SEEDS:
        st = start("bayesian", s)
        off = start("bayesian", s, params=p.with_values(delta0=0.0))
        item = first_step_item(loaded.config, st.roles)
        for turn, mv in enumerate(("show_bundles", "other", "other"), start=1):
            _, st, trace = step(st, "SUB-SFL", mv, None)
            _, off, _ = step(off, "SUB-SFL", mv, None)
            if turn == 1:  # the transition comes before any primed answer
                states_same &= [x.true for x in st.seats] == [x.true for x in off.seats]
            for row, seat, child in zip(
                trace["children"],
                [x for x in st.seats if x.true is not None],
                [c for c in st.children if c.error],
                strict=True,
            ):
                assert seat.true is not None
                if seat.true["written_step"] != 0:
                    continue
                i = index(seat.true)
                prim = resp.p_correct(i, item, st.roles, child.stage, p, row["priming"])
                base = resp.p_correct(i, item, st.roles, child.stage, p, 0.0)
                rises.append((turn, prim, base))
    by_turn = {
        t: {
            "n": sum(1 for r in rises if r[0] == t),
            "mean_primed": statistics.fmean(r[1] for r in rises if r[0] == t),
            "mean_unprimed": statistics.fmean(r[2] for r in rises if r[0] == t),
        }
        for t in (1, 2, 3)
    }
    higher = all(r[1] >= r[2] - 1e-12 for r in rises if r[0] in (1, 2)) and all(
        by_turn[t]["mean_primed"] > by_turn[t]["mean_unprimed"] for t in (1, 2)
    )
    back = all(abs(r[1] - r[2]) <= 1e-12 for r in rises if r[0] == 3)
    no_delta_in_transitions = all(
        "delta" not in inspect.signature(f).parameters
        for f in (dyn.sample_next, dyn.transition_matrix)
    ) and "delta" not in {f.name for f in fields(dyn.TurnContext)}
    ok = higher and back and states_same and no_delta_in_transitions
    return {
        "seeds": len(SEEDS),
        "by_turn": by_turn,
        "prime_window": p.prime_window,
        "higher_on_demo_turn_and_next": higher,
        "equal_after_window": back,
        "states_identical_with_and_without_priming": states_same,
        "transitions_take_no_priming_input": no_delta_in_transitions,
        "threshold": "higher on turns 1-2, equal on turn 3, state never changed",
        "pass": ok,
    }


def b7_forgetting(n: int = 20000) -> dict[str, Any]:
    p = default_params()
    st = start("bayesian", 1)
    rates: dict[int, float] = {}
    for c in (0, 4):
        reverted = 0
        for k in range(n):
            rng = random.Random(f"b7:{c}:{k}")
            true = {
                "place_value": rng.randrange(2),
                "exchange": rng.randrange(2),
                "written_step": 1,
                "habit": rng.choice(["none", "target", "sibling"]),
            }
            ctx = dyn.TurnContext(NEUTRAL_MOVE, 0.0, 0.6, 0.0, c)
            u = [rng.random() for _ in range(4)]
            nxt, _ = dyn.sample_next(true, ctx, st.roles, p, u)
            reverted += nxt["written_step"] == 0
        rates[c] = reverted / n
    ok = abs(rates[0] - p.h0_W) <= 0.01 and rates[4] < rates[0]
    return {
        "child_turns": n,
        "h0_W": p.h0_W,
        "rate_no_practice": rates[0],
        "rate_with_practice_c4": rates[4],
        "threshold": "|rate - h0_W| <= 0.01; with practice lower",
        "pass": ok,
    }


def b8_belief_recovery() -> dict[str, Any]:
    hits: list[bool] = []
    pairs: list[tuple[float, bool]] = []
    for s in SEEDS:
        move = MOVES_210[s % len(MOVES_210)]
        run = drill("bayesian", move, s)
        st: BayesState = run.state
        for seat in st.seats:
            if seat.true is None or seat.belief is None:
                continue
            p_w1 = float(np.asarray(seat.belief)[mask(written_step=1)].sum())
            hits.append(int(p_w1 > 0.5) == int(seat.true["written_step"]))
        for plan, trace in zip(run.plans, run.traces, strict=True):
            for row in trace["children"]:
                if row["predicted_correct"] is None or plan.problem is None:
                    continue
                out = row["outcome"]
                right = out == ["correct"] or out == ["n", plan.problem.correct]
                pairs.append((row["predicted_correct"], right))
    recovery = sum(hits) / len(hits)
    buckets = []
    for b in range(10):
        lo, hi = b / 10, (b + 1) / 10
        inside = [(q, r) for q, r in pairs if (lo <= q < hi) or (b == 9 and q == 1.0)]
        if not inside:
            continue
        mp = statistics.fmean(q for q, _ in inside)
        rate = sum(r for _, r in inside) / len(inside)
        buckets.append(
            {
                "bucket": f"{lo:.1f}-{hi:.1f}",
                "n": len(inside),
                "mean_predicted": mp,
                "observed": rate,
                "gap": abs(mp - rate),
                "counted": len(inside) >= 50,
            }
        )
    calibrated = all(b["gap"] <= 0.08 for b in buckets if b["counted"])
    return {
        "seeds": len(SEEDS),
        "children": len(hits),
        "recovery_written_step": recovery,
        "answers": len(pairs),
        "calibration": buckets,
        "threshold": "recovery >= 0.85; every bucket with >= 50 answers within 0.08",
        "pass": recovery >= 0.85 and calibrated,
    }


ALL: dict[str, Callable[[], dict[str, Any]]] = {
    "B1": b1_determinism,
    "B2": b2_teaching_quality,
    "B3": b3_prerequisites,
    "B4": b4_attention,
    "B5": b5_overload,
    "B6": b6_priming,
    "B7": b7_forgetting,
    "B8": b8_belief_recovery,
}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args(argv)
    results = {}
    for name, fn in ALL.items():
        results[name] = fn()
        print(f"{name}: {'PASS' if results[name]['pass'] else 'FAIL'}  {results[name]}")
    if not args.no_write:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "behaviour.json").write_text(json.dumps(results, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {(OUT / 'behaviour.json').relative_to(ROOT)}")
    return 0 if all(r["pass"] for r in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
