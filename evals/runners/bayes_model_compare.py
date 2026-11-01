"""Legacy versus the 32-state model under protocol 2.10 (docs/build/reports/BAYESIAN-CHECK.md
section 2.10), 200 seeds per move.

Per move: mean turns to finish (with its standard error) and the share of sessions that end by
two-in-a-row versus the 40-turn cap; for the bayesian model also the mean concepts learned per
erring child (place value, exchange, written step that went 0 -> 1), the mean final entropy of the
observer's belief, and the recovery rate (the observer's most likely written step equals the true
one). The legacy baseline printed in BAYESIAN-CHECK is shown beside the legacy run.

Whether the legacy ties (three moves at -0.30, three at -0.20) separate: for each pair in a tier,
the paired difference in turns over the same seeds with a 95% interval (difference +- 1.96 SE);
separated when the interval excludes 0. Which coverage values cause it: an ablation that sets one
field (cov_P, cov_E, cov_W, scaf, conf) of a tied move to the value of the tier's first move and
re-runs it (100 seeds).

A new file; evals/runners/sim_model_compare.py (the one-variable model's comparison) is unchanged.

    python -m evals.runners.bayes_model_compare     # writes evals/out/bayes/model_compare.json
    python -m evals.runners.bayes_model_compare --no-write
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

import engine.bayes.planner as planner
from engine.bayes.content import MoveSpec, load_moves
from engine.bayes.state import mask
from evals.runners.bayes_protocols import LEGACY_BASELINE, MOVES_210, drill, start

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "evals" / "out" / "bayes"
TIERS = {
    "-0.30": ("decomposition", "exchange_ten", "show_bundles"),
    "-0.20": ("ask_explain", "check_back", "order_probe"),
}
FIELDS = ("cov_P", "cov_E", "cov_W", "scaf", "conf")


@contextmanager
def moves_override(table: Mapping[str, MoveSpec]) -> Iterator[None]:
    """Run the planner with a different move table (this eval only)."""
    original = planner.load_moves
    planner.load_moves = lambda: table  # type: ignore[assignment]
    try:
        yield
    finally:
        planner.load_moves = original  # type: ignore[assignment]


def _concepts(state: Any) -> list[int]:
    return [
        int(s.true["place_value"]) + int(s.true["exchange"]) + int(s.true["written_step"])
        for s in state.seats
        if s.true is not None
    ]


def run_move(model: str, move: str, seeds: range) -> dict[str, Any]:
    turns: list[int] = []
    capped = 0
    learned: list[float] = []
    entropy: list[float] = []
    hits: list[bool] = []
    for s in seeds:
        r = drill(model, move, s)
        turns.append(r.turns)
        capped += r.finished_reason == "turn_cap"
        if model == "bayesian":
            before = _concepts(start("bayesian", s))
            after = _concepts(r.state)
            learned += [a - b for a, b in zip(after, before, strict=True)]
            for seat in r.state.seats:
                if seat.true is None:
                    continue
                b = np.asarray(seat.belief)
                q = b[b > 0]
                entropy.append(float(-(q * np.log2(q)).sum()))
                hits.append(int(b[mask(written_step=1)].sum() > 0.5) == seat.true["written_step"])
    n = len(turns)
    out: dict[str, Any] = {
        "seeds": n,
        "mean_turns": statistics.fmean(turns),
        "se_turns": statistics.stdev(turns) / math.sqrt(n),
        "share_two_in_a_row": (n - capped) / n,
        "share_turn_cap": capped / n,
        "turns": turns,
    }
    if model == "bayesian":
        out |= {
            "mean_concepts_learned": statistics.fmean(learned),
            "mean_final_entropy_bits": statistics.fmean(entropy),
            "recovery_written_step": sum(hits) / len(hits),
        }
    return out


def paired(a: list[int], b: list[int]) -> dict[str, float | bool]:
    d = [x - y for x, y in zip(a, b, strict=True)]
    mean = statistics.fmean(d)
    se = statistics.stdev(d) / math.sqrt(len(d)) if len(d) > 1 else 0.0
    return {
        "mean_diff": mean,
        "low": mean - 1.96 * se,
        "high": mean + 1.96 * se,
        "separated": (mean - 1.96 * se) > 0 or (mean + 1.96 * se) < 0,
    }


def ablation(seeds: range) -> dict[str, Any]:
    base = dict(load_moves())
    out: dict[str, Any] = {}
    for tier, members in TIERS.items():
        ref = base[members[0]]
        for m in members[1:]:
            row: dict[str, Any] = {
                "as_is": statistics.fmean(drill("bayesian", m, s).turns for s in seeds)
            }
            for f in FIELDS:
                if getattr(base[m], f) == getattr(ref, f):
                    continue
                table = {**base, m: replace(base[m], **{f: getattr(ref, f)})}
                with moves_override(table):
                    row[f"{f}={getattr(ref, f)}"] = statistics.fmean(
                        drill("bayesian", m, s).turns for s in seeds
                    )
            out[f"{tier}: {m} (reference {members[0]})"] = row
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=200)
    ap.add_argument("--ablation-seeds", type=int, default=100)
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args(argv)
    seeds = range(1, args.seeds + 1)
    res: dict[str, dict[str, Any]] = {"legacy": {}, "bayesian": {}}
    for model in ("legacy", "bayesian"):
        for move in MOVES_210:
            res[model][move] = run_move(model, move, seeds)
    print(
        f"{'move':<20} {'legacy':>8} {'(printed)':>9} {'cap':>5} {'bayesian':>9} {'cap':>5} "
        f"{'learned':>8} {'entropy':>8} {'recov':>6}"
    )
    for move in MOVES_210:
        lg, by = res["legacy"][move], res["bayesian"][move]
        print(
            f"{move:<20} {lg['mean_turns']:8.1f} {LEGACY_BASELINE[move]:9.1f} "
            f"{lg['share_turn_cap']:5.0%} {by['mean_turns']:9.1f} {by['share_turn_cap']:5.0%} "
            f"{by['mean_concepts_learned']:8.2f} {by['mean_final_entropy_bits']:8.2f} "
            f"{by['recovery_written_step']:6.0%}"
        )
    ties: dict[str, Any] = {}
    for tier, members in TIERS.items():
        for i, a in enumerate(members):
            for b in members[i + 1 :]:
                ties[f"{tier}: {a} - {b}"] = {
                    m: paired(res[m][a]["turns"], res[m][b]["turns"]) for m in res
                }
    for k, v in ties.items():
        by = v["bayesian"]
        verdict = "separated" if by["separated"] else "tied"
        print(
            f"{k:<40} legacy {v['legacy']['mean_diff']:+5.1f}  bayesian "
            f"{by['mean_diff']:+5.1f} [{by['low']:+.1f}, {by['high']:+.1f}] {verdict}"
        )
    abl = ablation(range(1, args.ablation_seeds + 1))
    for k, v in abl.items():
        print(k, {kk: round(vv, 1) for kk, vv in v.items()})
    if not args.no_write:
        OUT.mkdir(parents=True, exist_ok=True)
        coverage = {m: load_moves()[m].__dict__ for t in TIERS.values() for m in t}
        for model in res:
            for move in res[model]:
                res[model][move].pop("turns")
        out = {
            "source": "evals/runners/bayes_model_compare.py",
            "protocol": "BAYESIAN-CHECK 2.10",
            "seeds_per_move": args.seeds,
            "legacy_baseline_printed": LEGACY_BASELINE,
            "results": res,
            "ties": ties,
            "tie_coverage": coverage,
            "ablation_seeds": args.ablation_seeds,
            "ablation": abl,
        }
        (OUT / "model_compare.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {(OUT / 'model_compare.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
