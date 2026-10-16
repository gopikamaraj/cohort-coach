"""Regenerate docs/evidence/: every number the README, docs and deck cite, with its source.

Usage: python scripts/evidence.py [--check]
  default  write the files under docs/evidence/
  --check  write nothing; exit 1 if a committed file differs from what would be written now

Inputs are generated files only: data/synthetic/block_T1T2.json (run `python tasks.py seed`) and
evals/results/*.json (run `python tasks.py eval all`). Nothing here is typed by hand. Dates come
from the eval results themselves, so regenerating without new inputs gives identical files.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.synthetic.block import VERDICT_SEED, track_verdicts  # noqa: E402
from engine.evaluation import BlockEffect  # noqa: E402

EVIDENCE = ROOT / "docs" / "evidence"
BLOCK_PATH = ROOT / "data" / "synthetic" / "block_T1T2.json"
RESULTS = ROOT / "evals" / "results"
HIDDEN = "hidden (fewer than 5 classes)"


def _load(path: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def _verdict_record(e: BlockEffect) -> dict[str, Any]:
    if e.hidden:
        return {
            "verdict": e.verdict.value,
            "hidden": True,
            "estimate_points": None,
            "ci_low": None,
            "ci_high": None,
            "n_track": None,
            "n_comparison": None,
            "confidence_note": e.confidence_note,
        }
    return {
        "verdict": e.verdict.value,
        "hidden": False,
        "reason": e.reason,
        "estimate_points": e.estimate_points,
        "ci_low": e.ci_low,
        "ci_high": e.ci_high,
        "n_track": e.n_track,
        "n_comparison": e.n_comparison,
        "confidence_note": e.confidence_note,
    }


def _demo_verdicts(block: dict[str, Any]) -> tuple[str, str]:
    verdicts = track_verdicts(block)
    records = {k: _verdict_record(v) for k, v in verdicts.items()}
    lines = [
        "# Demo verdicts (SIMULATED)",
        "",
        f"> {block['label']}",
        "",
        f"Source: `data/synthetic/block_T1T2.json` (data hash `{block['data_hash']}`, seed "
        f"{block['seed']}), evaluated by `engine.evaluation.block_effect` (95% percentile "
        f"bootstrap over classes, 2000 resamples, seed {VERDICT_SEED}) through "
        "`scripts/evidence.py`. Effect = change in prevalence of the track's error for track "
        "classes minus the same for waitlist (comparison) classes, in percentage points; "
        "negative means the track classes fell more. Verdicts are per track version, never per "
        "teacher. A figure covering fewer than 5 classes is hidden.",
        "",
        "| Track version | Classes (track / comparison) | Effect (points) | 95% CI "
        "| Verdict | Note |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for version, r in records.items():
        if r["hidden"]:
            row = [version, HIDDEN, HIDDEN, HIDDEN, r["verdict"], r["confidence_note"] or ""]
        else:
            row = [
                version,
                f"{r['n_track']} / {r['n_comparison']}",
                f"{r['estimate_points']:.1f}",
                f"{r['ci_low']:.1f} to {r['ci_high']:.1f}",
                r["verdict"],
                r["confidence_note"] or "",
            ]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n", json.dumps(records, indent=2, sort_keys=True) + "\n"


def _eval_summary() -> str:
    items = _load(RESULTS / "engine_items.json")
    stats = _load(RESULTS / "statistics.json")
    lines = [
        "# Eval summary",
        "",
        "Generated from `evals/results/*.json` by `scripts/evidence.py`. Run the evals with "
        "`python tasks.py eval all`. Simulated data is labelled where it is used.",
        "",
        f"## Eval 1: error answers and item collisions (`evals/results/engine_items.json`, "
        f"{items['date']})",
        "",
        f"{items['problems_per_error']} generated problems per error, compared with an independent "
        f"column-procedure oracle (seed {items['seed']}). Bar: 100% correct, 0 collisions. "
        f"Result: {'pass' if items['passed'] else 'FAIL'}.",
        "",
        "| Error | Item type | Problems | Matching oracle | Share | Collisions |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for code, s in items["per_error"].items():
        lines.append(
            f"| {code} | {s['item_type']} | {s['n']} | {s['correct_wrong_answers']} | "
            f"{s['share_correct']:.0%} | {s['collisions']} |"
        )
    lines += [
        "",
        f"## Eval 8: statistics (`evals/results/statistics.json`, {stats['date']})",
        "",
        f"Simulated terms (SIMULATED data): {stats['arm_size']} classes per arm, "
        f"{stats['bootstrap_resamples']} bootstrap resamples, seed {stats['seed']}, class-to-class "
        f"effect spread {stats['effect_sd_points']} points. Planted working effects "
        f"{stats['planted_effects_points']} points; no-effect trials planted 0.",
        "",
        f"- Recovery of planted working effects: {stats['recovery']:.0%} of "
        f"{stats['trials_scored']['planted_working']} trials (bar at least 95%).",
        f'- False "working" with no effect: {stats["false_working"]:.0%} of '
        f"{stats['trials_scored']['no_effect']} trials (bar at most 5%).",
        f"- Result: {'pass' if stats['passed'] else 'FAIL'}.",
        "",
        "| Planted effect (points) | Trials | Working | Not working | Inconclusive | Scored |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    scored = {0, *stats["planted_effects_points"]}
    for effect, t in stats["per_effect"].items():
        lines.append(
            f"| {effect} | {t['trials']} | {t['working']} | {t['not_working']} | "
            f"{t['inconclusive']} | {'yes' if int(effect) in scored else 'no (information)'} |"
        )
    return "\n".join(lines) + "\n"


def _registry(block: dict[str, Any]) -> str:
    items = _load(RESULTS / "engine_items.json")
    stats = _load(RESULTS / "statistics.json")
    n_classes = len(block["classes"])
    scored = stats["trials_scored"]
    lines = [
        "# Numbers registry",
        "",
        "Every number in the README, docs, reports and deck comes from one of these generated "
        "files. Regenerate with `python tasks.py evidence`.",
        "",
        "| File | Source (script and input) | Date | Sample | Confidence note |",
        "| --- | --- | --- | --- | --- |",
        f"| `docs/evidence/demo_verdicts.md` (+ `.json`) | `scripts/evidence.py` on "
        f"`data/synthetic/block_T1T2.json` (hash `{block['data_hash'][:12]}`) | n/a: seeded, "
        f"simulated | {n_classes} simulated classes, 2 terms | Simulated; small tracks carry "
        "their own note in the table |",
        f"| `docs/evidence/eval_summary.md` (eval 1) | `evals/runners/engine_items.py` | "
        f"{items['date']} | {items['problems_per_error']} problems per error | Exact "
        "check, not a sample estimate |",
        f"| `docs/evidence/eval_summary.md` (eval 8) | `evals/runners/statistics.py` | "
        f"{stats['date']} | {scored['planted_working']} planted and {scored['no_effect']} "
        "no-effect simulated terms | Simulated terms; effect sizes and arm size are stated |",
    ]
    return "\n".join(lines) + "\n"


def build_all() -> dict[str, str]:
    block = _load(BLOCK_PATH)
    md, js = _demo_verdicts(block)
    return {
        "demo_verdicts.md": md,
        "demo_verdicts.json": js,
        "eval_summary.md": _eval_summary(),
        "numbers.md": _registry(block),
    }


def main(argv: list[str]) -> int:
    check = "--check" in argv
    stale = 0
    for name, text in build_all().items():
        path = EVIDENCE / name
        rel = path.relative_to(ROOT)
        if check:
            same = path.exists() and path.read_text(encoding="utf-8") == text
            print(f"{'ok   ' if same else 'STALE'} {rel}")
            stale += not same
        else:
            path.write_text(text, encoding="utf-8", newline="\n")
            print(f"wrote {rel}")
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
