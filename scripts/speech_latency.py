"""Speech latency per function and provider, by input size (Prompt 4). Live, capped, opt-in.

    python tasks.py speech-latency                # the plan and the estimated cost
    python tasks.py speech-latency --yes          # live: 30 calls per function and provider (paid)

Text to speech: short, medium and long lines (about 20, 80 and 200 characters) in turn. Speech to
text: clips of about 2, 6 and 15 seconds, made once with Sarvam and sent to both providers. Each call
is timed on its own; Bodhan's rate allowance (about 8 a minute) is respected by waiting between its
calls, and the wait is not counted. Reports the median and 95th percentile per function, provider
and size, and writes evals/results/speech_latency.json. `--calls N` lowers the count (at most 30).
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai.config import load_env  # noqa: E402
from services.speech import audio, costs  # noqa: E402
from services.speech.sarvam import SpeechError  # noqa: E402

OUT = ROOT / "evals" / "results" / "speech_latency.json"
LINES = {
    "short": "52 minus 29 is 23.",
    "medium": "Show 52 as 5 bundles of ten and 2 loose sticks, then take away 9 sticks.",
    "long": "Today we look at a mistake many children make with 52 minus 29. Show the number with bundles of ten and loose sticks, then open one bundle so there are enough loose sticks.",
}
CAP = 30
BODHAN_GAP_S = 60 / 8 + 0.3


def pct(values: list[float], q: float) -> float:
    s = sorted(values)
    return s[min(len(s) - 1, max(0, math.ceil(q * len(s)) - 1))]


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for fn in ("tts", "stt"):
        for prov in ("bodhan", "sarvam"):
            for size in ("short", "medium", "long"):
                mine = [r for r in rows if (r["fn"], r["provider"], r["size"]) == (fn, prov, size)]
                ms = [r["ms"] for r in mine if r["ok"]]
                fails = sum(1 for r in mine if not r["ok"])
                if ms or fails:
                    out[f"{fn} / {prov} / {size}"] = {
                        "calls": len(ms) + fails,
                        "failed": fails,
                        "median_ms": round(statistics.median(ms)) if ms else None,
                        "p95_ms": round(pct(ms, 0.95)) if ms else None,
                    }
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--calls", type=int, default=CAP)
    args = ap.parse_args(argv)
    n = max(1, min(args.calls, CAP))
    load_env()
    chars = sum(len(LINES[s]) for s in ("short", "medium", "long")) * n / 3
    secs = (2 + 6 + 15) * n / 3
    cost = sum(
        costs.cost_inr(p, "tts", chars=int(chars)) + costs.cost_inr(p, "stt", seconds=secs)
        for p in ("bodhan", "sarvam")
    )
    print(
        f"{n} calls per function and provider ({4 * n} in all), estimated INR {cost:.2f} (unverified prices); about {2 * n * BODHAN_GAP_S / 60:.0f} minutes for Bodhan's rate limit"
    )
    if not args.yes:
        print("Nothing spent. Run again with --yes.")
        return 0
    from services.speech.bodhan import BodhanClient, BodhanProvider
    from services.speech.provider import SarvamProvider

    providers = {
        "bodhan": BodhanProvider(
            BodhanClient(requests_per_minute=0)
        ),  # paced here, outside the timing
        "sarvam": SarvamProvider(),
    }
    clips: dict[str, bytes] = {}
    for size in ("short", "medium", "long"):
        made = providers["sarvam"].synthesize(LINES[size], "en", "ritu", None)
        clips[size] = audio.to_wav_16k_mono(made.data)
    rows: list[dict[str, Any]] = []
    sizes = ("short", "medium", "long")
    last_bodhan = 0.0
    for fn in ("tts", "stt"):
        for prov, p in providers.items():
            for i in range(n):
                size = sizes[i % 3]
                if prov == "bodhan":
                    wait = BODHAN_GAP_S - (time.monotonic() - last_bodhan)
                    if wait > 0:
                        time.sleep(wait)
                    last_bodhan = time.monotonic()
                t0 = time.monotonic()
                try:
                    if fn == "tts":
                        p.synthesize(
                            LINES[size], "en", "Kavya" if prov == "bodhan" else "ritu", None
                        )
                    else:
                        p.transcribe(clips[size], "en")
                    ok, why = True, ""
                except SpeechError as exc:
                    ok, why = False, f"{exc.kind}:{exc.code}"
                rows.append(
                    {
                        "fn": fn,
                        "provider": prov,
                        "size": size,
                        "ms": int((time.monotonic() - t0) * 1000),
                        "ok": ok,
                        "why": why,
                    }
                )
            done = sum(r["ok"] for r in rows if r["fn"] == fn and r["provider"] == prov)
            print(f"{fn} {prov}: {done} of {n} ok")
    summary = summarise(rows)
    for k, s in summary.items():
        print(
            f"  {k:<24} median {s['median_ms']} ms  p95 {s['p95_ms']} ms  ({s['calls']} calls, {s['failed']} failed)"
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "source": "scripts/speech_latency.py",
                "date": date.today().isoformat(),
                "calls_per_function_and_provider": n,
                "language": "en",
                "summary": summary,
                "rows": rows,
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
