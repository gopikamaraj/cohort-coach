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


REASON_TEXT = {
    "too_few_classes": "under 15 classes in an arm, so inconclusive whatever the estimate",
    "ci_below_zero_and_fall_at_least_10": "interval below 0 and a fall of at least 10 points",
    "fall_below_5_or_rise": "a fall of under 5 points, or a rise",
    "between_the_bars": "between the working and not-working bars",
}


def _note(r: dict[str, Any]) -> str:
    parts = [r["confidence_note"]] if r["confidence_note"] else []
    parts.append(REASON_TEXT.get(r["reason"], r["reason"]))
    return "; ".join(parts)


def _verdict_record(e: BlockEffect) -> dict[str, Any]:
    if e.hidden:
        return {
            "verdict": e.verdict.value,
            "hidden": True,
            "reason": e.reason,
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
            row = [version, HIDDEN, HIDDEN, HIDDEN, r["verdict"], _note(r)]
        else:
            row = [
                version,
                f"{r['n_track']} / {r['n_comparison']}",
                f"{r['estimate_points']:.1f}",
                f"{r['ci_low']:.1f} to {r['ci_high']:.1f}",
                r["verdict"],
                _note(r),
            ]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n", json.dumps(records, indent=2, sort_keys=True) + "\n"


def _power_note(stats: dict[str, Any]) -> str:
    """Power just above and below the 10-point working bar, from the characterisation rows."""
    parts = []
    for effect in ("5", "10"):
        t = stats["per_effect"].get(effect)
        if t:
            parts.append(
                f"a planted {effect}-point effect was called working in "
                f"{t['working']} of {t['trials']} trials"
            )
    return ("Near the working bar, " + "; ".join(parts) + " (not scored).") if parts else ""


def _optional(name: str) -> dict[str, Any] | None:
    path = RESULTS / name
    return _load(path) if path.exists() else None


def _practice_sections() -> list[str]:
    """Evals and measurements from P04: simulator fidelity, red team, Practice Class latency."""
    lines: list[str] = []
    fid, fid_live = _optional("sim_fidelity.json"), _optional("sim_fidelity_live.json")
    if fid:
        lines += [
            "",
            f"## Eval 2: simulator fidelity (`evals/results/sim_fidelity.json`, {fid['date']})",
            "",
            "Scripted teacher turns drive the real simulator; every child number must be the "
            "engine's (the answer is the correct answer or one an independent oracle gives for "
            "the child's error, and every number in the line is in the plan's allowed set). "
            f"Bar: 100%. Engine and template lines: {fid['matched']} of {fid['turns']} turns "
            f"match ({fid['numeric_match']:.0%}). Result: {'pass' if fid['passed'] else 'FAIL'}.",
            "",
            "| Error | Turns | Matched |",
            "| --- | --- | --- |",
        ]
        lines += [f"| {e} | {s['turns']} | {s['matched']} |" for e, s in fid["per_error"].items()]
    if fid_live:
        lines += [
            "",
            "Live run with the real model (`evals/results/sim_fidelity_live.json`, "
            f"{fid_live['date']}): {fid_live['matched']} of {fid_live['turns']} turns match "
            f"({fid_live['numeric_match']:.0%}); the model's line was kept in "
            f"{fid_live['line_sources']['ai']} turns and replaced by the template in "
            f"{fid_live['line_sources']['template']}; cost USD {fid_live['cost_usd']}. This is a "
            "short live run (the full 200 turns are scheduled for P13).",
        ]
    rt, rt_live = _optional("redteam.json"), _optional("redteam_live.json")
    if rt:
        blocked = sum(c["blocked"] for c in rt["per_category"].values())
        needs_model = len(rt["pending_checker_ids"]) + len(rt["pending_labeller_ids"])
        lines += [
            "",
            f"## Red team (`evals/results/redteam.json`, `redteam_live.json`, {rt['date']})",
            "",
            f"Seed set `evals/sets/redteam.yaml`: {rt['cases']} attacks and {rt['controls']} "
            "benign controls (seeds written by the build; the full 50 are still to be written). "
            f"Code gates alone: {blocked} of {rt['cases']} attacks blocked, {needs_model} need a "
            "model.",
        ]
    if rt_live:
        lines += [
            "",
            f"Live run (call 7 and the call 2 labeller on the rest, {rt_live['date']}): "
            f"{rt_live['unsafe_reaching_teacher']} of {rt_live['cases']} attacks reached a "
            f"teacher (bar 0); {rt_live['controls_wrongly_blocked']} of {rt_live['controls']} "
            f"benign controls blocked. Result: {'pass' if rt_live['passed'] else 'FAIL'}. Small "
            "seed set: read as directional.",
        ]
    lat = _optional("practice_latency.json")
    if lat:
        ab = _optional("practice_latency_haiku_child.json")
        lines += [
            "",
            "## Practice Class text-turn latency (`evals/results/practice_latency.json`, "
            f"{lat['date']})",
            "",
            f"{lat['turns']} scripted live turns over {lat['sessions']} sessions (label, engine, "
            f"child line, gates): median {lat['median_ms']} ms, 90th percentile "
            f"{lat['p90_ms']} ms, maximum {lat['max_ms']} ms, against a target median under "
            f"{lat['target_median_ms']} ms: "
            f"{'meets' if lat['meets_target'] else 'does not meet'} the target. Cost USD "
            f"{lat['cost_per_turn_usd']} per turn. From one network and one machine, so read as "
            "directional.",
        ]
        if ab:
            lines.append(
                "A/B with Haiku 5.5 for call 1 (`practice_latency_haiku_child.json`): median "
                f"{ab['median_ms']} ms, {ab['line_sources']['template']} of {ab['turns']} lines "
                "replaced by the template; not adopted."
            )
    vlat = _optional("voice_latency.json")
    if vlat and vlat.get("mode") == "live":
        lines += [
            "",
            "## Practice Class voice-turn latency (`evals/results/voice_latency.json`, "
            f"{vlat['date']})",
            "",
            f"{vlat['turns']} live voice turns ({vlat['failed']} failed, "
            f"{vlat['without_audio']} answered in text only): median "
            f"{vlat['median_ms']} ms, 90th percentile {vlat['p90_ms']} ms, maximum "
            f"{vlat['max_ms']} ms, against a target median under {vlat['target_median_ms']} ms: "
            f"{'meets' if vlat['meets_target'] else 'does not meet'} the target. Median by "
            f"language: {vlat['median_by_language_ms']}. Median speech-to-text "
            f"{vlat['median_stt_ms']} ms; median wait for the child's audio "
            f"{vlat['median_tts_wait_ms']} ms; mean reply audio {vlat['mean_reply_audio_bytes']} "
            "bytes. From one network and one machine, so read as directional.",
        ]
    return lines


def _practice_registry() -> list[str]:
    rows: list[str] = []
    entries = (
        (
            "sim_fidelity.json",
            "evals/runners/sim_fidelity.py",
            "scripted simulator turns",
            "Exact check",
        ),
        (
            "sim_fidelity_live.json",
            "evals/runners/sim_fidelity.py --live",
            "live child-voice turns",
            "Short live run: directional",
        ),
        (
            "redteam.json",
            "evals/runners/redteam.py",
            "red-team seeds, code gates",
            "Seed set: directional",
        ),
        (
            "redteam_live.json",
            "evals/runners/redteam.py --live",
            "red-team seeds, with models",
            "Seed set: directional",
        ),
        (
            "practice_latency.json",
            "scripts/practice_latency.py --live",
            "live Practice Class turns",
            "One network and machine: directional",
        ),
        (
            "voice_latency.json",
            "scripts/voice_latency.py --live",
            "live Practice Class voice turns",
            "One network and machine: directional",
        ),
    )
    for name, script, what, note in entries:
        data = _optional(name)
        if data:
            n = data.get("turns") or data.get("cases")
            rows.append(
                f"| `docs/evidence/eval_summary.md` (`evals/results/{name}`) | `{script}` | "
                f"{data['date']} | {n} {what} | {note} |"
            )
    for fname, script, what, note in (
        (
            "bundle_size.json",
            "scripts/bundle_size.py --write",
            "initial JS of the built PWA",
            "Exact measurement",
        ),
        (
            "lighthouse_mobile.json",
            "scripts/lighthouse_summary.py",
            "one Lighthouse mobile run",
            "One run: directional",
        ),
    ):
        path = EVIDENCE / fname
        if path.exists():
            date = _load(path)["date"]
            rows.append(f"| `docs/evidence/{fname}` | `{script}` | {date} | {what} | {note} |")
    session = EVIDENCE / "practice_session_live.json"
    if session.exists():
        s = _load(session)
        rows.append(
            "| `docs/evidence/practice_session_live.json` | `scripts/practice_cli.py --json` | "
            f"{s['date']} | {s['totals']['turns']} turns of one scripted live session | "
            "One session: illustrative |"
        )
    return rows


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
        f"- Scope of the recovery bar: it applies to planted effects of "
        f"{min(stats['planted_effects_points'])} points or more. {_power_note(stats)}",
        "- Eval 8 uses a simplified class-level simulator (binomial child counts, with natural "
        "drift and onset set to the same values as the simulated block). It tests the verdict "
        "code, not the answer-sheet model.",
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
    lines += _practice_sections()
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
    lines += _practice_registry()
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
