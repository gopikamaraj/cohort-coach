"""Measure Practice Class turn latency and cost over scripted sessions.

Usage: python scripts/practice_latency.py [--live] [--sessions 3] [--tag NAME] [--yes] [--no-write]
  default  the rule-based stub (checks the harness only; its latencies mean nothing)
  --live   real Claude calls; prints a cost estimate first and asks. Needs ANTHROPIC_API_KEY.
Runs the scripted SUB-SFL session in evals/sets/practice_scripts/ once per session (different
seeds), and reports the median, 90th percentile and maximum of the full text-turn latency
(label, engine, child line, gates) and the cost per turn, against the target of a median under
3 s. Writes evals/results/practice_latency[_TAG].json.
"""

from __future__ import annotations

import argparse
import datetime
import json
import statistics
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ai.client import CallContext  # noqa: E402
from ai.config import load_env, model_for  # noqa: E402
from services.practice.session import start_session, take_turn  # noqa: E402
from services.practice.stub_client import StubClient  # noqa: E402

SCRIPT = ROOT / "evals" / "sets" / "practice_scripts" / "sub-sfl-en.txt"
TARGET_MS = 3000
EST_USD_PER_TURN = 0.003  # from the first live session: USD 0.0101 for 7 turns plus feedback


def run(sessions: int, live: bool, context: CallContext | None = None) -> dict[str, Any]:
    lines = SCRIPT.read_text(encoding="utf-8").splitlines()
    ctx = context or (
        CallContext(mode="live") if live else CallContext(mode="stub", client=StubClient())
    )
    latencies: list[int] = []
    cost = 0.0
    sources = {"ai": 0, "template": 0, "silent": 0}
    for i in range(sessions):
        s = start_session("SUB-SFL", "en", seed=5 + i)
        name = s.state.children[1].name
        for line in lines:
            if s.state.finished:
                break
            if line.startswith("/tap"):
                r = take_turn(s, material=line[5:].strip(), context=ctx)
            else:
                r = take_turn(s, text=line.replace("Priya", name), context=ctx)
            latencies.append(r.latency_ms)
            cost += r.cost_usd
            sources[r.layers["output"]["source"]] += 1
    latencies.sort()
    p90 = latencies[min(len(latencies) - 1, int(0.9 * len(latencies)))]
    median = int(statistics.median(latencies))
    return {
        "measure": "practice_turn_latency",
        "source": "scripts/practice_latency.py",
        "date": datetime.date.today().isoformat(),
        "mode": "live" if live else "stub",
        "models": {k: model_for(k) for k in ("MODEL_CHILD", "MODEL_LABEL", "MODEL_CHECK")},
        "sessions": sessions,
        "turns": len(latencies),
        "median_ms": median,
        "p90_ms": p90,
        "max_ms": latencies[-1],
        "target_median_ms": TARGET_MS,
        "meets_target": median < TARGET_MS,
        "cost_usd": round(cost, 6),
        "cost_per_turn_usd": round(cost / len(latencies), 6),
        "line_sources": sources,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--sessions", type=int, default=3)
    ap.add_argument("--tag", default="")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args(argv)
    if args.live:
        load_env()
        n = args.sessions * len(SCRIPT.read_text(encoding="utf-8").splitlines())
        print(f"live latency run: {n} turns, estimated cost USD {n * EST_USD_PER_TURN:.3f}")
        if not args.yes and input("Run live? [y/N] ").strip().lower() != "y":
            return 0
    result = run(args.sessions, args.live)
    print(
        f"{result['mode']}: {result['turns']} turns, median {result['median_ms']} ms, "
        f"p90 {result['p90_ms']} ms, max {result['max_ms']} ms (target median < {TARGET_MS} ms), "
        f"cost USD {result['cost_usd']}, line sources {result['line_sources']}"
    )
    print("MEETS TARGET" if result["meets_target"] else "OVER TARGET")
    if args.live and not args.no_write:
        name = f"practice_latency{'_' + args.tag if args.tag else ''}.json"
        path = ROOT / "evals" / "results" / name
        path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
        print(f"wrote {name} in evals/results/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
