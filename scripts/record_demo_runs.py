"""Record Watch runs of the live system: one per style and language, for the judge-mode fallback.

    AI_MODE=live python scripts/record_demo_runs.py [--lang en hi ta] [--seed 5]

Each file in content/demo_runs/ keeps the date, model and prompt versions, seed and scenario
version, and the demo shows it labelled "recorded run". Prints a cost estimate first (about USD
0.03 a run) and stops if the live call fails. Records synthetic lines only.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai.client import CallContext  # noqa: E402
from ai.config import ai_mode, load_env  # noqa: E402
from services.practice.watch import STYLES, WatchFallback, run_watch, save_recorded  # noqa: E402

PER_RUN_USD = 0.03


def main() -> int:
    load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", nargs="+", default=["en", "hi", "ta"])
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--scenario", default="SUB-SFL")
    args = ap.parse_args()
    if ai_mode() != "live":
        print("Set AI_MODE=live: a recorded run must come from the live system.")
        return 2
    n = len(args.lang) * len(STYLES)
    print(f"{n} runs, estimated cost about USD {n * PER_RUN_USD:.2f}")
    for lang in args.lang:
        for style in STYLES:
            try:
                run = run_watch(
                    scenario=args.scenario, style=style, language=lang, seed=args.seed,
                    context=CallContext(), slow_s=None,
                )  # fmt: skip
            except WatchFallback as exc:
                print(f"{style}/{lang}: stopped ({exc})")
                return 1
            path = save_recorded(run)
            print(
                f"{style}/{lang}: {len(run['turns'])} turns, rubric points touched "
                f"{run['summary']['rubric_points_touched']}/{run['summary']['rubric_points']}, "
                f"USD {run['provenance']['cost_usd']} -> {path.name}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
