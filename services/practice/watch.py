"""Watch mode (judge mode only): an AI teacher runs a rehearsal in one of two styles.

A run is a plain dict a client can replay with pause, step, 2x and skip. It is either live (the
system just ran it) or a recorded run (the same thing, run once and stored with its provenance,
and always labelled "recorded run"). A live run that fails a call or takes over 8 seconds on a turn
is abandoned, and the recorded run is shown instead, with the reason.
"""

from __future__ import annotations

import json
import time
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai.calls.c10_demo_teacher import LABEL, demo_teacher_turn
from ai.client import CallContext
from ai.prompt_loader import load_prompt
from ai.registry import get_call
from engine.simulator import Problem
from services.practice.content import CONTENT, LoadedScenario
from services.practice.session import (
    PracticeSession,
    ScriptedMove,
    end_session,
    start_session,
    take_turn,
)

RUNS_DIR = CONTENT / "demo_runs"
SLOW_TURN_S = 8.0  # a live turn slower than this switches the run to the recorded one
MAX_WATCH_TURNS = 9
DEFAULT_SEED = 5
STYLES = ("experienced", "struggling")


_CALL_FAILED = ("api_error", "no_output", "schema", "no_recording")


def call_failed(fallback_used: str | None) -> bool:
    """A fallback because the call itself failed (not because a guardrail caught a line)."""
    return bool(fallback_used) and str(fallback_used).rsplit(":", 1)[-1] in _CALL_FAILED


class WatchFallback(RuntimeError):
    """A live run was abandoned: why (a failed call, or a slow turn). The recorded run is used."""


def run_path(scenario: str, style: str, language: str, root: Path = RUNS_DIR) -> Path:
    return root / f"{scenario.lower()}.{style}.{language}.json"


def rubric_coverage(moves: Sequence[str], loaded: LoadedScenario) -> int:
    """How many rubric points the labelled moves touch. Internal to eval 11 and the run's own
    summary line; it is a count of moves the AI teacher chose, never a score for a real teacher."""
    used = set(moves)
    return sum(1 for p in loaded.rubric.points if used & set(p.move_ids))


def _next_problem(session: PracticeSession) -> Problem:
    cfg = session.loaded.config
    return session.state.problem or cfg.problems[session.state.next_problem % len(cfg.problems)]


def _provenance(session: PracticeSession, style: str, cost: float) -> dict[str, Any]:
    return {
        "scenario": session.error,
        "scenario_version": session.loaded.scenario.version,
        "style": style,
        "language": session.language,
        "seed": session.seed,
        "models": {str(i): get_call(i).model for i in (1, 3, 7, 10)},
        "prompt_versions": {
            k: load_prompt(k).version
            for k in ("c01_child_voice", "c03_feedback", "c07_checker", "c10_demo_teacher")
        },
        "cost_usd": round(cost, 5),
        "label": LABEL,
    }


def run_watch(
    *,
    scenario: str = "SUB-SFL",
    style: str,
    language: str,
    seed: int = DEFAULT_SEED,
    context: CallContext | None = None,
    max_turns: int = MAX_WATCH_TURNS,
    clock: Callable[[], float] = time.monotonic,
    slow_s: float | None = SLOW_TURN_S,
) -> dict[str, Any]:
    """Run the AI teacher against the five simulated children. Raises WatchFallback if a call
    fails or a turn is slower than `slow_s` (so the caller can show the recorded run)."""
    base = replace(context or CallContext(), judge=True)
    session = start_session(scenario, language, seed=seed, judge=True)
    movelist = session.loaded.movelist
    kids = [c.name for c in session.state.children]
    transcript: list[str] = []
    child_lines: list[str] = []
    turns: list[dict[str, Any]] = []
    cost = 0.0
    for n in range(1, max_turns + 1):
        if session.state.finished:
            break
        started = clock()
        try:
            problem = _next_problem(session)
            dt = demo_teacher_turn(
                style=style, movelist=movelist, language=language, children=kids,
                transcript=transcript, child_lines=child_lines, turn=n, problem=problem,
                context=base,
            )  # fmt: skip
            posed = problem if dt.move_id == "pose_problem" else None
            r = take_turn(
                session, text=dt.line, scripted=ScriptedMove(dt.move_id, dt.addressed, posed),
                context=base,
            )  # fmt: skip
        except PermissionError:
            raise
        except Exception as exc:  # a budget stop or anything else
            raise WatchFallback(f"a call failed: {type(exc).__name__}") from exc
        elapsed = clock() - started
        if slow_s is not None and elapsed > slow_s:
            raise WatchFallback(f"a turn took {elapsed:.0f} s")
        if call_failed(dt.run.fallback_used if dt.run else None) or call_failed(
            r.layers["guardrails"]["fallback_used"]
        ):
            raise WatchFallback("a call failed")
        teacher_cost = dt.run.cost_usd if dt.run else 0.0
        cost += r.cost_usd + teacher_cost
        transcript += [f"Teacher: {dt.line}", f"{r.speaker or 'Children'}: {r.child_text}"]
        if r.child_text:
            child_lines.append(r.child_text)
        turns.append(
            {
                "turn": r.turn,
                "teacher": {
                    "line": dt.line, "move": r.move, "addressed": dt.addressed,
                    "source": dt.source, "label": LABEL,
                },
                "child": {
                    "speaker": r.speaker, "text": r.child_text, "text_en": r.child_text_en,
                    "intent": r.intent, "badge": r.badge,
                },
                "children": r.children,
                "machinery": _machinery(r.layers, dt),
                "latency_ms": r.latency_ms,
            }
        )  # fmt: skip
    card, _layers = end_session(session, context=base)
    cost += _layers.get("evaluation", {}).get("cost_usd", 0.0)
    moves = [t["teacher"]["move"]["id"] for t in turns]
    return {
        "provenance": _provenance(session, style, cost),
        "turns": turns,
        "feedback": {
            "strengths": [
                {
                    "point": s.point,
                    "text": s.text,
                    "quote": s.quote,
                    "turn": s.turn_id,
                    "comment": s.comment,
                }
                for s in card.strengths
            ],
            "try_next": {
                "point": card.try_next.point,
                "text": card.try_next.text,
                "suggestion": card.try_next.suggestion,
                "quote": card.try_next.quote,
                "turn": card.try_next.turn_id,
            },
            "note": card.note,
            "badge": card.badge.value,
            "source": card.source,
        },
        "summary": {
            "turns": len(turns),
            "moves_used": len(set(moves)),
            "rubric_points_touched": rubric_coverage(moves, session.loaded),
            "rubric_points": len(session.loaded.rubric.points),
        },
    }


def _machinery(layers: dict[str, Any], dt: Any) -> dict[str, Any]:
    """What code decided, which AI call ran, which validators passed: for the panel."""
    eng = layers["processing"]["engine"]
    return {
        "code": {
            "move": layers["processing"]["label"],
            "engine": {k: eng.get(k) for k in ("speaker", "intent", "answer", "correct")},
        },
        "ai_calls": [
            {"call": 10, "name": "Demo teacher", "source": dt.source,
             "latency_ms": dt.run.latency_ms if dt.run else None},
            {"call": 1, "name": "Child voices", "source": layers["output"]["source"],
             "latency_ms": layers["evaluation"]["call_ms"].get("child")},
            {"call": 7, "name": "Output checker", "source": "ai",
             "latency_ms": layers["evaluation"]["call_ms"].get("check")},
        ],
        "validators": [
            {"name": v["name"], "ok": v["ok"]} for v in layers["guardrails"]["validators"]
        ]
        + [
            {"name": r.name, "ok": r.ok}
            for r in (dt.run.results if dt.run else [])
        ],
        "checker": layers["guardrails"]["checker"],
        "fallback": layers["guardrails"]["fallback_used"]
        or (dt.run.fallback_used if dt.run else None),
    }  # fmt: skip


# recorded runs ------------------------------------------------------------------------------


def save_recorded(run: dict[str, Any], root: Path = RUNS_DIR) -> Path:
    p = run_path(
        run["provenance"]["scenario"],
        run["provenance"]["style"],
        run["provenance"]["language"],
        root,
    )
    p.parent.mkdir(parents=True, exist_ok=True)
    stamped = {
        **run,
        "provenance": {**run["provenance"], "recorded_at": datetime.now(UTC).strftime("%Y-%m-%d")},
    }
    p.write_text(json.dumps(stamped, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return p


def load_recorded(
    scenario: str, style: str, language: str, root: Path = RUNS_DIR
) -> dict[str, Any] | None:
    p = run_path(scenario, style, language, root)
    if not p.exists():
        return None
    data: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
    return data


def tag(run: dict[str, Any], *, kind: str, reason: str | None = None) -> dict[str, Any]:
    """Label a run for the client: "live run" or "recorded run", and why a recorded one shows."""
    return {**run, "kind": kind, "label": f"{kind}", "reason": reason}


# the live cap and the cost meter (in memory, per deployment) ----------------------------------


@dataclass
class LiveMeter:
    cap_per_hour: int
    runs: deque[tuple[float, float]]  # (timestamp, cost) of live runs

    def _fresh(self, now: float) -> list[tuple[float, float]]:
        return [(t, c) for t, c in self.runs if now - t < 3600]

    def allowed(self, now: float | None = None) -> bool:
        return len(self._fresh(now or time.time())) < self.cap_per_hour

    def record(self, cost: float, now: float | None = None) -> None:
        self.runs.append((now or time.time(), cost))

    def snapshot(self, now: float | None = None) -> dict[str, Any]:
        fresh = self._fresh(now or time.time())
        return {
            "live_runs_this_hour": len(fresh),
            "cap_per_hour": self.cap_per_hour,
            "cost_usd_this_hour": round(sum(c for _, c in fresh), 5),
        }
