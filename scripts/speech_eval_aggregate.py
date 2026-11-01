"""Aggregate the listening test: raters' CSVs plus the pack's key -> means per provider, voice and
language, the "numbers wrong" share, and the text-to-speech gate against its threshold.

    python scripts/speech_eval_aggregate.py evals/speech-eval/pack-2026-11-01
    python scripts/speech_eval_aggregate.py evals/speech-eval/pack-2026-11-01 --record "Seema"

Reads every ratings-*.csv in the folder and key.json. Prints each gate check against its threshold
always; writes the result to docs/evidence/speech_gates.md only with --record NAME (and never a
pending result). Writes evals/speech-eval/<pack>/summary.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.speech import evaluation  # noqa: E402


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--record", default="", help="your name: record the gate's result")
    args = ap.parse_args(argv)
    key = json.loads((args.folder / "key.json").read_text(encoding="utf-8"))["clips"]
    files = sorted(args.folder.glob("ratings-*.csv"))
    if not files:
        print(f"No ratings-*.csv in {args.folder}.")
        return 1
    agg = evaluation.aggregate(evaluation.read_ratings(files), key)
    gate = evaluation.tts_gate(agg)
    print(f"{len(files)} rating files, {agg['rejected']} ratings left out")
    for group in ("provider", "provider_language", "provider_voice"):
        print(f"\n{group}:")
        for name, s in agg[group].items():
            print(
                f"  {name:<24} n={s['ratings']:<4} naturalness {s['naturalness']:.2f}  clarity {s['clarity']:.2f}  numbers {s['numbers']:.2f}  suitability {s['suitability']:.2f}  numbers wrong {s['numbers_wrong_share']:.1%}"
            )
    print(f"\ntext-to-speech gate: {gate['result'].upper()}")
    for name, c in gate.get("checks", {}).items():
        print(f"  {name}: {c['value']} against {c['limit']} -> {'ok' if c['ok'] else 'NOT MET'}")
    if gate["result"] == "pending":
        print(f"  {gate['why']}")
    (args.folder / "summary.json").write_text(
        json.dumps({"aggregate": agg, "gate": gate}, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    if args.record:
        if gate["result"] == "pending":
            print("Not recorded: the gate is pending.")
            return 1
        detail = "\n".join(
            f"- {n}: {c['value']} against {c['limit']} ({'met' if c['ok'] else 'not met'})"
            for n, c in gate["checks"].items()
        )
        evaluation.record("bodhan_tts", gate["result"], args.record, details=detail)
        print(
            f"recorded bodhan_tts: {gate['result']} by {args.record} in docs/evidence/speech_gates.md"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
