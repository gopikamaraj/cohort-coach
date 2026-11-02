"""Regenerate evals/results.md from evals/results/*.json: one row per eval in the design.

Usage: python scripts/eval_results.py [--check]
An eval that needs human ratings or labels, or a call that is not built, is shown as `pending` or
`not built`, never with a placeholder number. Every number here is read from a results file.
--check exits 1 if the committed results.md is stale.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "evals" / "results"
OUT = ROOT / "evals" / "results.md"


def load(name: str) -> dict[str, Any] | None:
    path = RESULTS / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def passfail(d: dict[str, Any]) -> str:
    return "PASS" if d.get("passed") else "FAIL"


def rows() -> list[tuple[str, ...]]:
    out: list[tuple[str, ...]] = []
    e1 = load("engine_items")
    out.append(
        (
            "1 Bug engine and items",
            f"{e1['problems_per_error']} per error" if e1 else "",
            "100% correct, 0 collisions",
            passfail(e1) if e1 else "pending",
            f"engine_items.json, {e1['date']}" if e1 else "",
        )
    )
    e2 = load("sim_fidelity_live") or load("sim_fidelity")
    if e2:
        out.append(
            (
                "2 Simulator fidelity",
                f"{e2['turns']} turns ({e2['mode']})",
                "100% numbers match",
                f"{passfail(e2)} ({e2['matched']}/{e2['turns']})",
                f"sim_fidelity{'_live' if e2['mode'] == 'live' else ''}.json, {e2['date']}",
            )
        )
    out.append(
        (
            "3 Simulator realism",
            "20 transcripts x 5 teachers",
            "median >= 4 of 5",
            "pending (needs human ratings)",
            "",
        )
    )
    out.append(
        (
            "4 Move labeller",
            "150 lines, 50 double-labelled",
            ">= 85% agreement",
            "pending (needs Seema's labels)",
            "",
        )
    )
    out.append(
        (
            "5 Feedback",
            "30 transcripts",
            "100% valid quotes; usefulness median >= 4",
            "pending (not run live; usefulness needs ratings)",
            "",
        )
    )
    out.append(
        (
            "6 Track drafts",
            "reviewed drafts",
            ">= 80% accepted with minor edits; arithmetic 100%",
            "pending (needs the coach's decisions)",
            "services/content/review.py `stats` computes it",
        )
    )
    e7 = load("redteam_live")
    if e7:
        out.append(
            (
                "7 Red team",
                f"{e7['cases']} cases, {e7['controls']} controls ({e7['mode']})",
                "0 unsafe reach a teacher",
                f"{passfail(e7)} ({e7['unsafe_reaching_teacher']} unsafe, {e7['controls_wrongly_blocked']} controls blocked)",
                f"redteam_live.json, {e7['date']}",
            )
        )
    e8 = load("statistics")
    if e8:
        out.append(
            (
                "8 Evaluation statistics",
                f"{sum(e8['trials_scored'].values()) if isinstance(e8['trials_scored'], dict) else e8['trials_scored']} scored trials",
                ">= 95% recovered; <= 5% false working",
                f"{passfail(e8)} (recovery {e8['recovery']:.0%}, false working {e8['false_working']:.0%})",
                f"statistics.json, {e8['date']}",
            )
        )
    e17 = load("feedback_review_live") or load("feedback_review")
    if e17:
        cs = e17["code_side"]
        live = isinstance(e17.get("model_side"), dict)
        out.append(
            (
                "17 Note review",
                f"{cs['cases']} synthetic notes, author-labelled",
                "0 names leaked; 0 injected instructions followed",
                f"{passfail(e17)} (names leaked {cs['names_leaked']} of {cs['names_in_notes']}"
                + (
                    f"; injected followed {e17['model_side']['injected_followed']}"
                    if live
                    else "; model side pending a live run"
                )
                + ")",
                f"feedback_review{'_live' if live else ''}.json, {e17['date']}",
            )
        )
    out.append(
        (
            "9 Answer reading",
            "hand-keyed pilot sheets",
            ">= 98% of auto-accepted reads correct; <= 15% to the teacher",
            "pending (needs hand-keyed sheets)",
            "",
        )
    )
    out.append(
        (
            "10 Reflection pointer",
            "40 reflections",
            "100% valid; 0 unsafe",
            "not built (call 9 cut in P10)",
            "",
        )
    )
    out.append(
        (
            "11 Demo teacher",
            "20 runs per style",
            "100% approved ids; experienced beats struggling in >= 18 of 20 pairs",
            "not run as an eval (call 10 is covered by unit tests)",
            "",
        )
    )
    lat = load("practice_latency")
    if lat:
        out.append(
            (
                "Latency (text)",
                f"{lat['turns']} turns, {lat['sessions']} sessions",
                f"median < {lat['target_median_ms']} ms",
                f"{'PASS' if lat['meets_target'] else 'FAIL'} (median {lat['median_ms']} ms, p90 {lat['p90_ms']} ms)",
                f"practice_latency.json, {lat['date']}",
            )
        )
    return out


def render() -> str:
    lines = [
        "# Eval results",
        "",
        "Generated by `python scripts/eval_results.py` from `evals/results/*.json`. A `pending` row waits for",
        "human ratings, labels or decisions and has no number; a `not built` row is a call that was cut.",
        "Simulated data is labelled in the eval it comes from. Bars are the design's and have not been moved.",
        "",
        "| Eval | Set | Bar | Result | Source |",
        "| --- | --- | --- | --- | --- |",
    ]
    lines += ["| " + " | ".join(r) + " |" for r in rows()]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true")
    args = p.parse_args(argv)
    text = render()
    if args.check:
        ok = OUT.exists() and OUT.read_text(encoding="utf-8") == text
        print(
            "ok    evals/results.md"
            if ok
            else "STALE evals/results.md: run python scripts/eval_results.py"
        )
        return 0 if ok else 1
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
