"""Spend by call, model and day, from the audit trail (table ai_calls).

Usage: python scripts/budget.py
Every figure is a sum of the cost column that run_call wrote from usage x ai/pricing.yaml.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ai import config  # noqa: E402

config.load_env()
from ai.audit import default_sink  # noqa: E402
from ai.pricing import load_pricing  # noqa: E402


def summarise(rows: list) -> dict[str, dict[str, float]]:  # type: ignore[type-arg]
    out: dict[str, dict[str, float]] = {"call": defaultdict(float), "model": defaultdict(float)}
    out["day"] = defaultdict(float)
    for r in rows:
        out["call"][r.call_key] += r.cost_usd
        out["model"][r.model] += r.cost_usd
        out["day"][r.created_at.date().isoformat()] += r.cost_usd
    return out


def main() -> int:
    sink = default_sink()
    rows = sink.recent(1_000_000)
    sums = summarise(rows)
    total = sink.spend_total()
    judge = sink.spend_total(judge=True)
    pricing = load_pricing()
    print(f"AI spend from the audit trail ({len(rows)} calls). Prices: {pricing['as_of']}")
    for title in ("call", "model", "day"):
        print(f"\nby {title}")
        for key in sorted(sums[title]):
            print(f"  {key:<24} USD {sums[title][key]:.4f}")
    live = [r for r in rows if r.mode != "recorded"]
    cached = sum(r.tokens_cache_read for r in live)
    print(f"\ncache read tokens across live calls: {cached}")
    print(f"total USD {total:.4f} of {config.budget_total_usd():.2f} (non-judge cap)")
    print(f"judge-mode USD {judge:.4f}; hard ceiling USD {config.budget_hard_usd():.2f}")
    print(f"today USD {sink.spend_day(__import__('datetime').date.today()):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
