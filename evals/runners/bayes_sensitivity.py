"""Parameter uncertainty bands for the 32-state model (docs/BAYESIAN-MODEL.md section 8).

Runs protocol 2.10 for the nine moves under: the defaults; every parameter at its low and at its
high, one at a time (content/bayes/params.v1.yaml bands); and 50 seeded Latin-hypercube draws
across all bands at once. The same seeds are used for every configuration (common random numbers).

Reports per move the median and the 5-95% band of mean turns to finish across the Latin-hypercube
draws (and across the one-at-a-time runs), how often the top tier (the three fastest moves) keeps
the same members, and the parameters whose low or high changes the move ranking or the top tier.

    python -m evals.runners.bayes_sensitivity [--seeds 100] [--draws 50] [--workers N]
"""

from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from engine.bayes.content import RANGES, load_params, params_from_dict
from evals.runners.bayes_protocols import MOVES_210, drill

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "evals" / "out" / "bayes"


def configs(draws: int, seed: int = 20261101) -> dict[str, dict[str, float]]:
    ps = load_params()
    base = ps.defaults.as_dict()
    out: dict[str, dict[str, float]] = {"defaults": dict(base)}
    for name, (lo, hi) in ps.bands.items():
        for label, v in (("low", lo), ("high", hi)):
            if v != base[name]:
                out[f"{name}={label}"] = {**base, name: v}
    rng = random.Random(seed)
    strata = {n: rng.sample(range(draws), draws) for n in ps.bands}
    for d in range(draws):
        values = dict(base)
        for name, (lo, hi) in ps.bands.items():
            v = lo + (strata[name][d] + rng.random()) / draws * (hi - lo)
            values[name] = round(v) if RANGES[name][2] else v
        out[f"lhs{d:02d}"] = values
    return out


def _cell(args: tuple[str, dict[str, float], str, int]) -> tuple[str, str, float]:
    label, values, move, n = args
    params = params_from_dict(values)
    turns = [drill("bayesian", move, s, params=params).turns for s in range(1, n + 1)]
    return label, move, statistics.fmean(turns)


def _pct(xs: list[float], q: float) -> float:
    s = sorted(xs)
    k = (len(s) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def summarise(table: dict[str, dict[str, float]]) -> dict[str, Any]:
    base = table["defaults"]
    order = sorted(MOVES_210, key=lambda m: (base[m], m))
    top = set(order[:3])
    lhs = [k for k in table if k.startswith("lhs")]
    oat = [k for k in table if "=" in k]
    bands = {
        m: {
            "defaults": base[m],
            "lhs_median": statistics.median(table[k][m] for k in lhs),
            "lhs_p5": _pct([table[k][m] for k in lhs], 0.05),
            "lhs_p95": _pct([table[k][m] for k in lhs], 0.95),
            "oat_min": min(table[k][m] for k in oat),
            "oat_max": max(table[k][m] for k in oat),
        }
        for m in MOVES_210
    }

    def ranking(k: str) -> list[str]:
        return sorted(MOVES_210, key=lambda m: (table[k][m], m))

    changes_order = sorted({k.split("=")[0] for k in oat if ranking(k) != order})
    changes_top = sorted({k.split("=")[0] for k in oat if set(ranking(k)[:3]) != top})
    rule_moves = {"tell_rule", "repeat_rule_louder"}
    rule_last = {
        "lhs": sum(set(ranking(k)[-2:]) == rule_moves for k in lhs) / len(lhs),
        "oat": sum(set(ranking(k)[-2:]) == rule_moves for k in oat) / len(oat),
    }
    return {
        "default_ranking": order,
        "default_top_tier": sorted(top),
        "bands": bands,
        "top_tier_same_share": {
            "lhs": sum(set(ranking(k)[:3]) == top for k in lhs) / len(lhs),
            "oat": sum(set(ranking(k)[:3]) == top for k in oat) / len(oat),
        },
        "rule_moves_last_share": rule_last,
        "params_changing_full_ranking": changes_order,
        "params_changing_top_tier": changes_top,
        "top_tier_by_oat": {k: ranking(k)[:3] for k in oat if set(ranking(k)[:3]) != top},
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=100)
    ap.add_argument("--draws", type=int, default=50)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args(argv)
    cfgs = configs(args.draws)
    jobs = [(label, v, m, args.seeds) for label, v in cfgs.items() for m in MOVES_210]
    print(f"{len(cfgs)} configurations x {len(MOVES_210)} moves x {args.seeds} seeds "
          f"({len(jobs)} cells) on {args.workers} workers")  # fmt: skip
    table: dict[str, dict[str, float]] = {k: {} for k in cfgs}
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for label, move, mean in pool.map(_cell, jobs, chunksize=4):
            table[label][move] = mean
    summary = summarise(table)
    print("default ranking:", summary["default_ranking"])
    for m, b in summary["bands"].items():
        print(f"  {m:<20} defaults {b['defaults']:5.1f}  LHS median {b['lhs_median']:5.1f} "
              f"[{b['lhs_p5']:5.1f}, {b['lhs_p95']:5.1f}]  one-at-a-time "
              f"[{b['oat_min']:5.1f}, {b['oat_max']:5.1f}]")  # fmt: skip
    print("top tier same:", summary["top_tier_same_share"])
    print("rule moves last:", summary["rule_moves_last_share"])
    print("params changing the full ranking:", summary["params_changing_full_ranking"])
    print("params changing the top tier:", summary["params_changing_top_tier"])
    if not args.no_write:
        OUT.mkdir(parents=True, exist_ok=True)
        out = {"source": "evals/runners/bayes_sensitivity.py", "protocol": "BAYESIAN-CHECK 2.10",
               "seeds_per_cell": args.seeds, "lhs_draws": args.draws,
               "configurations": len(cfgs), "summary": summary, "table": table,
               "configs": cfgs}  # fmt: skip
        (OUT / "sensitivity.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {(OUT / 'sensitivity.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
