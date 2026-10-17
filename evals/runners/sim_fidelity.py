"""Eval 2: simulator fidelity. Every number a simulated child says is the engine's.

200 scripted teacher turns (4 tracked errors x 5 seeds x 10 turns, evals/sets/sim_fidelity/*.yaml)
drive the real simulator. For each turn where a child speaks:

  (a) the planned answer is the correct answer, or a wrong answer an independent oracle gives
      for that child's error (digit and string procedures, not the engine's closed forms);
  (b) every number in the child's line is in the plan's allowed set, and an `answer` line
      contains the planned answer.

A turn matches when both hold. Bar: 100%. Modes: default `engine_templates` uses the template
line (free, deterministic, runs in CI); `--live` uses call 1 with the real model and the gates
(prints a cost estimate first and asks), so it also shows how often the model's line was kept
or replaced by the template. Writes evals/results/sim_fidelity.json, or sim_fidelity_live.json for
`--live`.

Usage: python -m evals.runners.sim_fidelity [--live] [--limit N] [--yes] [--no-write]
"""

from __future__ import annotations

import argparse
import datetime
import json
import statistics
import sys
from pathlib import Path
from typing import Any

import yaml

from ai.calls.c01_child_voice import child_line
from ai.client import CallContext
from ai.config import load_env
from ai.pricing import Usage, cost_usd
from ai.registry import get_call
from ai.validators.numbers import extract_numbers
from engine.model import ErrorCode
from engine.simulator import Problem, TurnPlan, fill_seats, new_session, plan_turn
from services.practice.content import load_personas, load_scenario
from services.practice.templates import render_line

SET_DIR = Path(__file__).resolve().parents[1] / "sets" / "sim_fidelity"
RESULTS = Path(__file__).resolve().parents[1] / "results"
BAR = {"numeric_match": 1.0}
ERRORS = ("PV-HEARD", "ADD-NOCARRY", "SUB-SFL", "SUB-NODEC")


def oracle(code: ErrorCode, p: Problem) -> set[int]:
    """Wrong answers for this error on this problem, by digit and string procedures."""
    if code in (ErrorCode.PV_HEARD, ErrorCode.PV_REVERSE):
        if p.kind != "dictation":
            return set()
        s = str(p.a)
        if code is ErrorCode.PV_REVERSE:
            return {int(s[:-2] + s[-1] + s[-2])}
        if len(s) == 2:
            return {int(s[0] + "0" + s[1])}
        return {
            int(s[0] + "00" + s[1:]),
            int(s[0] + "0" + s[1:]),
            int(s[0] + "00" + s[1] + "0" + s[2]),
        }
    if code is ErrorCode.ADD_NOCARRY:
        if p.kind != "add":
            return set()
        a, b = f"{p.a:02d}", f"{p.b:02d}"
        return {int(str(int(a[0]) + int(b[0])) + str((int(a[1]) + int(b[1])) % 10))}
    if p.kind != "sub":
        return set()
    top, bottom = f"{p.a:02d}", f"{p.b:02d}"
    tt, to, bt, bo = int(top[0]), int(top[1]), int(bottom[0]), int(bottom[1])
    if code is ErrorCode.SUB_SFL:
        return {int(str(abs(tt - bt)) + str(abs(to - bo)))}
    if to < bo:  # SUB-NODEC: borrow ten for the ones, forget to cross out the tens
        return {int(str(tt - bt) + str(to + 10 - bo))}
    return {p.a - p.b}


def answer_ok(plan: TurnPlan, error: ErrorCode | None) -> bool:
    if plan.answer is None or plan.problem is None:
        return True  # nothing numeric to check this turn
    legit = {plan.problem.correct}
    if error is not None:
        legit |= oracle(error, plan.problem) - {plan.problem.correct}
    if plan.answer not in legit:
        return False
    # An answer the child got right must equal the correct answer; wrong must be that error's.
    return plan.correct == (plan.answer == plan.problem.correct)


def line_ok(plan: TurnPlan, text: str) -> bool:
    said = set(extract_numbers(text))
    if not said <= set(plan.allowed_numbers):
        return False
    return not (plan.intent == "answer" and plan.answer is not None and plan.answer not in said)


def load_scripts(errors: tuple[str, ...] = ERRORS) -> list[dict[str, Any]]:
    return [
        yaml.safe_load((SET_DIR / f"{e.lower()}.yaml").read_text(encoding="utf-8")) for e in errors
    ]


def estimate_cost(n_turns: int) -> float:
    """Rough: one child call (about 1.4k tokens in, 60 out) and one checker call per turn."""
    child, check = get_call(1), get_call(7)
    return cost_usd(child.model, Usage(1400 * n_turns, 60 * n_turns)) + cost_usd(
        check.model, Usage(1500 * n_turns, 120 * n_turns)
    )


def run(
    *, live: bool = False, limit: int | None = None, context: CallContext | None = None
) -> dict[str, Any]:
    per_error: dict[str, dict[str, Any]] = {}
    latencies: list[int] = []
    cost = 0.0
    sources = {"ai": 0, "template": 0}
    # A limit is shared evenly by the four errors, so a short live run still covers all of them.
    per_error_cap = -(-limit // len(ERRORS)) if limit is not None else None
    total = matched = 0
    for script in load_scripts():
        error = script["error"]
        loaded = load_scenario(error)
        kids = load_personas().children
        n = m = 0
        for seed in script["seeds"]:
            names = [k.names["en"] for k in kids[:5]]
            seats = fill_seats({}, 0, loaded.scenario.error, loaded.scenario.seat_mix, names=names)
            state = new_session(loaded.config, seats, seed)
            history: list[str] = []
            for step in script["script"]:
                if state.finished or (per_error_cap is not None and n >= per_error_cap):
                    break
                seat = step["seat"]
                addressed = state.children[seat].name if seat is not None else None
                plan, state = plan_turn(
                    state, loaded.config, step["move"], addressed=addressed, posed=None
                )
                if plan.speaker is None:
                    continue
                speaker = next(c for c in state.children if c.name == plan.speaker)
                if live:
                    res = child_line(
                        plan, name=speaker.name, temperament="", language="en",
                        teacher_line=step["say"], history=history, context=context,
                    )  # fmt: skip
                    text = res.text
                    sources[res.source if res.source in sources else "template"] += 1
                    if res.run:
                        latencies.append(res.run.latency_ms)
                        cost += res.run.cost_usd
                    if res.gate and res.gate.checker:
                        cost += res.gate.checker.result.cost_usd
                else:
                    text = render_line(plan, "en")
                history += [f"teacher: {step['say']}", f"{speaker.name}: {text}"]
                ok = answer_ok(plan, speaker.error) and line_ok(plan, text)
                n += 1
                m += ok
                total += 1
                matched += ok
        per_error[error] = {"turns": n, "matched": m, "share": m / n if n else 0.0}
    result: dict[str, Any] = {
        "eval": "sim_fidelity",
        "source": "evals/runners/sim_fidelity.py",
        "set": "evals/sets/sim_fidelity/*.yaml",
        "date": datetime.date.today().isoformat(),
        "mode": "live" if live else "engine_templates",
        "turns": total,
        "matched": matched,
        "numeric_match": matched / total if total else 0.0,
        "bar": BAR,
        "per_error": per_error,
        "passed": total > 0 and matched == total,
    }
    if live:
        result["line_sources"] = sources
        result["median_call1_latency_ms"] = int(statistics.median(latencies)) if latencies else None
        result["cost_usd"] = round(cost, 6)
        result["limit"] = limit
    return result


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args(argv)
    ctx: CallContext | None = None
    if args.live:
        load_env()
        n = args.limit or 200
        print(f"live fidelity run: up to {n} turns, estimated cost USD {estimate_cost(n):.3f}")
        if not args.yes and input("Run live? [y/N] ").strip().lower() != "y":
            return 0
        ctx = CallContext(mode="live")
    result = run(live=args.live, limit=args.limit, context=ctx)
    for error, s in result["per_error"].items():
        print(f"{error:<12} turns={s['turns']} matched={s['matched']} ({s['share']:.0%})")
    print(
        f"{result['mode']}: {result['matched']}/{result['turns']} match "
        f"({result['numeric_match']:.0%}, bar 100%)"
    )
    if args.live:
        print(f"line sources {result['line_sources']}, cost USD {result['cost_usd']}, "
              f"median call-1 latency {result['median_call1_latency_ms']} ms")  # fmt: skip
    print("PASS" if result["passed"] else "FAIL")
    if not args.no_write:
        path = RESULTS / ("sim_fidelity_live.json" if args.live else "sim_fidelity.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
        print(f"wrote {path.name} in evals/results/")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
