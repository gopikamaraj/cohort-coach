"""Speech-to-text evaluation on team members' recordings: Bodhan against Sarvam.

    python tasks.py speech-eval-stt                       # checks the recordings, prints the cost
    python tasks.py speech-eval-stt --yes                 # live: transcribes with both (paid)
    python tasks.py speech-eval-stt --yes --record "Gopi" # and records the gate

Reads data/speech-eval/references.csv (git-ignored; columns: id, language, file, reference, phone,
noise) and the audio files it names (protocol: docs/evidence/speech-eval/PROTOCOL.md). Each file is
converted to 16 kHz mono WAV and transcribed by Bodhan and by Sarvam. Per item: character and word
error rates after normalising numbers (digits and words), whether every number was heard, and the key
maths terms heard. Per provider, language and tag (phone, noise): the means, and the gate against its
threshold. The raw transcripts stay in data/speech-eval/results.json (git-ignored); only the numbers
go to evals/results/speech_eval_stt.json. The gate is written only with --record NAME.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai.config import load_env  # noqa: E402
from services.speech import audio, costs, evaluation  # noqa: E402
from services.speech.sarvam import SpeechError  # noqa: E402

DATA = ROOT / "data" / "speech-eval"
RESULTS = ROOT / "evals" / "results" / "speech_eval_stt.json"


def load(folder: Path) -> list[dict[str, str]]:
    path = folder / "references.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]


def run(
    items: list[dict[str, str]], providers: dict[str, Any], folder: Path
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for it in items:
        wav = audio.to_wav_16k_mono((folder / it["file"]).read_bytes())
        parts = audio.split_for_stt(audio.trim_silence(wav))
        tags = ";".join(t for t in (it.get("phone", ""), it.get("noise", "")) if t)
        for name, p in providers.items():
            try:
                heard = " ".join(p.transcribe(x, it["language"]).text for x in parts)
                failed = ""
            except SpeechError as exc:
                heard, failed = "", f"{exc.kind}:{exc.code}"
            rows.append(
                {
                    "id": it["id"],
                    "language": it["language"],
                    "provider": name,
                    "tags": tags,
                    "reference": it["reference"],
                    "heard": heard,
                    "failed": failed,
                    **evaluation.stt_item(it["reference"], heard, it["language"]),
                }
            )
    return rows


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--record", default="")
    args = ap.parse_args(argv)
    load_env()
    items = load(DATA)
    if not items:
        print(
            f"No recordings yet: put references.csv and the audio in {DATA}/ (docs/evidence/speech-eval/PROTOCOL.md)."
        )
        return 1
    missing = [i["file"] for i in items if not (DATA / i["file"]).exists()]
    if missing:
        print(f"{len(missing)} files listed but missing, e.g. {missing[:3]}")
        return 1
    seconds = sum(
        audio.wav_seconds(audio.to_wav_16k_mono((DATA / i["file"]).read_bytes())) for i in items
    )
    cost = costs.cost_inr("bodhan", "stt", seconds=seconds) + costs.cost_inr(
        "sarvam", "stt", seconds=seconds
    )
    print(
        f"{len(items)} recordings, {seconds:.0f} s of audio, estimated INR {cost:.2f} for both providers (unverified prices); about {len(items) / 8:.0f} minutes at Bodhan's rate limit"
    )
    if not args.yes:
        print("Nothing spent. Run again with --yes.")
        return 0
    from services.speech.bodhan import BodhanClient, BodhanProvider
    from services.speech.provider import SarvamProvider

    rows = run(items, {"bodhan": BodhanProvider(BodhanClient()), "sarvam": SarvamProvider()}, DATA)
    summary = evaluation.stt_summary(rows)
    gate = evaluation.stt_gate(summary)
    for group in ("provider", "provider_language", "provider_tag"):
        print(f"\n{group}:")
        for name, s in summary[group].items():
            print(
                f"  {name:<28} n={s['items']:<4} CER {s['cer']:.3f}  WER {s['wer']:.3f}  numbers {s['number_accuracy']}  key terms {s['key_term_accuracy']}"
            )
    print(f"\nspeech-to-text gate: {gate['result'].upper()}")
    for name, c in gate.get("checks", {}).items():
        print(f"  {name}: {c['value']} against {c['limit']} -> {'ok' if c['ok'] else 'NOT MET'}")
    print("\nworst items (by CER):")
    for r in evaluation.worst(rows):
        print(f"  {r['id']} {r['provider']} {r['language']} CER {r['cer']:.2f} {r['failed']}")
    (DATA / "results.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(
        json.dumps(
            {
                "source": "scripts/speech_eval_stt.py",
                "date": date.today().isoformat(),
                "items": len(items),
                "summary": summary,
                "gate": gate,
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    if args.record:
        if gate["result"] == "pending":
            print("Not recorded: the gate is pending.")
            return 1
        detail = "\n".join(
            f"- {n}: {c['value']} against {c['limit']} ({'met' if c['ok'] else 'not met'})"
            for n, c in gate["checks"].items()
        )
        evaluation.record("bodhan_stt", gate["result"], args.record, details=detail)
        print(f"recorded bodhan_stt: {gate['result']} by {args.record}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
