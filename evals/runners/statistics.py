"""Eval 8: does the block-scale test recover planted effects and avoid false "working"?

Each trial is one simulated term: two arms of classes (track and waitlist comparison), children
with and without the error, natural drift for everyone, and a planted extra fall of a known size
for the track arm. The real `engine.evaluation.block_effect` gives the verdict. Bars (from the
design): at least 95% of planted working effects are called "working", and at most 5% of
no-effect trials are.

Planted effect E means the track arm's prevalence falls E points more, in expectation. Each class's
own effect varies around E (sd below), as teachers' results do. Effects 15, 20 and 25 are the
planted "working" sizes (above the 10-point working bar). Effects 5 and 10 are reported for
information (how power drops near the bar) and do not count towards the bars.

Usage: python -m evals.runners.statistics [--quick] [--no-write]
Writes evals/results/statistics.json. Exit code 1 if a bar is missed.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from engine.evaluation import ClassChange, Group, Verdict, block_effect

BASE_SEED = 2026
BARS = {"recovery": 0.95, "false_working": 0.05}
RESULT_PATH = Path(__file__).resolve().parents[1] / "results" / "statistics.json"

ARM_SIZE = 20  # classes per arm: above the 15-class floor, as the demo block's tracks are
PLANTED_EFFECTS = [15, 20, 25]  # points of extra fall the track plants
CHARACTERISE_EFFECTS = [5, 10]  # reported, not scored
EFFECT_SD = 5.0  # class-to-class spread of the effect, in points
CLASS_SIZE = (20, 40)
BASELINE_P = {"mean": 0.45, "sd": 0.09, "min": 0.25, "max": 0.75}
NATURAL_FIX = 0.12  # as in data/synthetic/config.yaml
ONSET = 0.015


def _delta_points(rng: np.random.Generator, planted_points: float, trained: bool) -> float:
    """One class's change in prevalence, in points, from child-level binomial draws."""
    size = int(rng.integers(CLASS_SIZE[0], CLASS_SIZE[1] + 1))
    p0 = float(
        np.clip(
            rng.normal(BASELINE_P["mean"], BASELINE_P["sd"]), BASELINE_P["min"], BASELINE_P["max"]
        )
    )
    x1 = int(rng.binomial(size, p0))
    extra = 0.0
    if trained and planted_points > 0:
        effect = max(0.0, planted_points + float(rng.normal(0.0, EFFECT_SD)))
        extra = min(1.0, effect / (100.0 * p0))
    fixed = int(rng.binomial(x1, min(1.0, NATURAL_FIX + extra)))
    started = int(rng.binomial(size - x1, ONSET))
    x2 = x1 - fixed + started
    return (x2 - x1) / size * 100.0


def _trial(effect: int, index: int, effect_slot: int) -> Verdict:
    rng = np.random.default_rng([BASE_SEED, effect_slot, index])
    changes = [
        ClassChange(f"t{i}", Group.TRACK, _delta_points(rng, effect, True)) for i in range(ARM_SIZE)
    ] + [
        ClassChange(f"c{i}", Group.COMPARISON, _delta_points(rng, effect, False))
        for i in range(ARM_SIZE)
    ]
    return block_effect(f"eval8 effect {effect}", changes, B=2000, seed=index).verdict


def _tally(verdicts: list[Verdict]) -> dict[str, int]:
    return {
        "trials": len(verdicts),
        "working": sum(v is Verdict.WORKING for v in verdicts),
        "not_working": sum(v is Verdict.NOT_WORKING for v in verdicts),
        "inconclusive": sum(v is Verdict.INCONCLUSIVE for v in verdicts),
    }


def run(n_null: int = 100, n_planted: int = 100, n_characterise: int = 50) -> dict[str, Any]:
    per_effect: dict[str, list[Verdict]] = {}
    per_effect["0"] = [_trial(0, i, 0) for i in range(n_null)]
    for i in range(n_planted):
        effect = PLANTED_EFFECTS[i % len(PLANTED_EFFECTS)]
        per_effect.setdefault(str(effect), []).append(_trial(effect, i, effect))
    for effect in CHARACTERISE_EFFECTS:
        per_effect[str(effect)] = [_trial(effect, i, effect) for i in range(n_characterise)]

    planted = [v for e in PLANTED_EFFECTS for v in per_effect.get(str(e), [])]
    null = per_effect["0"]
    recovery = sum(v is Verdict.WORKING for v in planted) / len(planted) if planted else 0.0
    false_working = sum(v is Verdict.WORKING for v in null) / len(null) if null else 0.0
    return {
        "eval": "statistics",
        "source": "evals/runners/statistics.py",
        "date": datetime.date.today().isoformat(),
        "seed": BASE_SEED,
        "arm_size": ARM_SIZE,
        "bootstrap_resamples": 2000,
        "planted_effects_points": PLANTED_EFFECTS,
        "characterisation_effects_points": CHARACTERISE_EFFECTS,
        "effect_sd_points": EFFECT_SD,
        "bars": BARS,
        "trials_scored": {"no_effect": len(null), "planted_working": len(planted)},
        "recovery": recovery,
        "false_working": false_working,
        "per_effect": {
            k: _tally(v) for k, v in sorted(per_effect.items(), key=lambda kv: int(kv[0]))
        },
        "passed": bool(planted)
        and bool(null)
        and recovery >= BARS["recovery"]
        and false_working <= BARS["false_working"],
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="fewer trials, for the check smoke")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    result = run(40, 40, 0) if args.quick else run()
    print(
        f"statistics: recovery {result['recovery']:.0%} (bar >= 95%), "
        f"false working {result['false_working']:.0%} (bar <= 5%), arm size {result['arm_size']}"
    )
    for effect, tally in result["per_effect"].items():
        print(f"  effect {effect:>2} pts: {tally}")
    print("PASS" if result["passed"] else "FAIL")
    if not args.no_write and not args.quick:
        RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
        print(f"wrote {RESULT_PATH.name} in evals/results/")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
