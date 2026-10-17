"""Rehearse in the terminal: five simulated children, your own lines.

Usage: python scripts/practice_cli.py --scenario sub-sfl --lang en [--stub | --live] [--seed 5]
                                      [--script lines.txt] [--verbose]
  --stub   rule-based stand-in for the model: no API key, no cost (default without a key)
  --live   Claude API (needs ANTHROPIC_API_KEY in .env); prints the cost of each turn
  --record live, and save each answer under ai/fixtures/recorded/ (use only synthetic lines)
  --recorded replay saved answers, no network
  commands: /tap bundles|sticks|chart   /end (feedback)   /quit
Nothing is saved: the transcript stays in this terminal.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ai.client import CallContext  # noqa: E402
from ai.config import load_env  # noqa: E402
from services.practice.session import (  # noqa: E402
    PracticeSession,
    SessionFinished,
    end_session,
    start_session,
    take_turn,
)
from services.practice.stub_client import StubClient  # noqa: E402


def show_card(session: PracticeSession, ctx: CallContext) -> None:
    card, layers = end_session(session, context=ctx)
    print("\n--- Feedback (private) ---")
    for s in card.strengths:
        print(f'+ {s.comment}\n    you said: "{s.quote}" (turn {s.turn_id})')
    t = card.try_next
    print(f"> Try next: {t.suggestion}")
    if t.quote:
        print(f'    you said: "{t.quote}" (turn {t.turn_id})')
    if card.note:
        print(f"* {card.note}")
    print(f"[{card.badge.value} · source {card.source} · {layers['evaluation']['latency_ms']} ms]")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="sub-sfl")
    ap.add_argument("--lang", default="en", choices=["en", "hi", "ta"])
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--stub", action="store_true")
    ap.add_argument("--recorded", action="store_true", help="replay ai/fixtures/recorded/")
    ap.add_argument("--record", action="store_true", help="live, and save answers as fixtures")
    ap.add_argument("--script", help="a text file with one teacher line per row")
    ap.add_argument("--verbose", action="store_true", help="show the AI layers of each turn")
    args = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):  # Hindi, Tamil and the middle dot on Windows consoles
        stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    load_env()
    live = (
        args.live
        or args.record
        or (not (args.stub or args.recorded) and bool(os.environ.get("ANTHROPIC_API_KEY")))
    )
    if args.record:
        ctx = CallContext(mode="record")
    elif args.recorded:
        ctx = CallContext(mode="recorded")
    elif live:
        ctx = CallContext(mode="live")
    else:
        ctx = CallContext(mode="stub", client=StubClient())
    session = start_session(args.scenario.upper(), args.lang, seed=args.seed)
    kids = ", ".join(f"{c.name}{' (shy)' if c.shy else ''}" for c in session.state.children)
    print(f"Practice Class: {args.scenario.upper()} · {args.lang} · {ctx.mode}")
    print(f"Children: {kids}\nType what you would say. /tap bundles · /end · /quit\n")
    lines = Path(args.script).read_text(encoding="utf-8").splitlines() if args.script else None
    total_cost = 0.0
    try:
        while True:
            raw = lines.pop(0) if lines else (input("Teacher> ") if lines is None else "/end")
            raw = raw.strip()
            if not raw:
                continue
            if lines is not None:
                print(f"Teacher> {raw}")
            if raw == "/quit":
                return 0
            if raw == "/end":
                show_card(session, ctx)
                print(f"turns: {session.state.turn} · cost USD {total_cost:.4f}")
                return 0
            try:
                if raw.startswith("/tap "):
                    result = take_turn(session, material=raw[5:].strip(), context=ctx)
                else:
                    result = take_turn(session, text=raw, context=ctx)
            except SessionFinished:
                print("The rehearsal has finished. Type /end for feedback.")
                continue
            total_cost += result.cost_usd
            who = result.speaker or "(nobody speaks)"
            print(f"{who}: {result.child_text}")
            print(f"   [{result.label.get('move_id') if result.label else ''} · {result.intent}"
                  f" · {result.latency_ms} ms · {result.badge}]")  # fmt: skip
            if args.verbose:
                print(f"   layers: {result.layers}")
            if result.finished:
                print(f"\n({result.finished_reason}: the rehearsal is over.)")
                show_card(session, ctx)
                return 0
    except (EOFError, KeyboardInterrupt):
        print()
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
