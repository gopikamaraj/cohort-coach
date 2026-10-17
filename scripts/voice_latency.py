"""Measure Practice Class voice-turn latency (speech in, speech out) with live Sarvam and Claude.

Usage: python scripts/voice_latency.py --live [--sessions 2] [--yes] [--no-write]
  --live   needed: real Sarvam and Claude calls. Prints a cost estimate first and asks.
           Needs SARVAM_API_KEY (a working one) and ANTHROPIC_API_KEY.
Each teacher line is first synthesised with a stock voice (so the speech-to-text has real
speech to hear), then sent through POST /voice-turn in-process. Per turn it records the whole
round trip, the speech-to-text time, the wait for the child's audio, and the size of the reply
audio. Reports the median per language and overall against the target (median under 5 s), and
writes evals/results/voice_latency.json. Without --live it only checks the harness with the
stub speech service and writes nothing.
"""

from __future__ import annotations

import argparse
import base64
import datetime
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from ai.client import CallContext  # noqa: E402
from ai.config import load_env, model_for  # noqa: E402
from services.api import practice as api  # noqa: E402
from services.api.main import app  # noqa: E402
from services.practice.stub_client import StubClient  # noqa: E402
from services.speech import audio  # noqa: E402
from services.speech.service import STUB_LINES, SpeechService  # noqa: E402
from services.speech.voices import Voice  # noqa: E402

TARGET_MS = 5000
LANGS = ("en", "hi", "ta")
EST_USD_PER_TURN = 0.003  # Claude, from the first live text session
EST_INR_PER_TURN = 0.2  # a short synthesis each way and about 4 s of audio


def run(sessions: int, live: bool) -> dict[str, Any]:
    speech = SpeechService("live" if live else "stub", log=lambda **kw: None)
    app.dependency_overrides[api.get_speech] = lambda: speech
    app.dependency_overrides[api.get_ai_context] = lambda: (
        CallContext(mode="live") if live else CallContext(mode="stub", client=StubClient())
    )
    http = TestClient(app)
    teacher = Voice("ritu", 1.0, 1.0)
    rows: list[dict[str, Any]] = []
    try:
        for lang in LANGS:
            for i in range(sessions):
                sid = http.post(
                    "/api/practice/sessions",
                    json={"scenario": "SUB-SFL", "language": lang, "seed": 5 + i},
                ).json()["session_id"]
                for line in STUB_LINES[lang]:
                    clip = speech.synthesize(line, lang, teacher)
                    t0 = time.monotonic()
                    res = http.post(
                        f"/api/practice/sessions/{sid}/voice-turn",
                        files={"audio": ("clip.ogg", clip, "audio/ogg")},
                    )
                    wall = int((time.monotonic() - t0) * 1000)
                    if res.status_code != 200:
                        rows.append({"lang": lang, "ok": False, "status": res.status_code})
                        continue
                    body = res.json()
                    st = body["layers"]["evaluation"]["stages"]
                    rows.append(
                        {
                            "lang": lang,
                            "ok": True,
                            "total_ms": wall,
                            "stt_ms": st["stt_ms"],
                            "tts_wait_ms": st["tts_wait_ms"],
                            "text_ms": body["latency_ms"],
                            "reply_bytes": len(base64.b64decode(body["audio"] or "")),
                            "has_audio": bool(body["audio"]),
                        }
                    )
    finally:
        app.dependency_overrides.clear()
    ok = [r for r in rows if r["ok"]]
    totals = sorted(r["total_ms"] for r in ok)
    median = int(statistics.median(totals)) if totals else 0
    per_lang = {
        lang: int(statistics.median([r["total_ms"] for r in ok if r["lang"] == lang]))
        for lang in LANGS
        if any(r["lang"] == lang for r in ok)
    }
    avg_reply = int(statistics.mean(r["reply_bytes"] for r in ok)) if ok else 0
    return {
        "measure": "practice_voice_turn_latency",
        "source": "scripts/voice_latency.py",
        "date": datetime.date.today().isoformat(),
        "mode": "live" if live else "stub",
        "models": {k: model_for(k) for k in ("MODEL_CHILD", "MODEL_LABEL", "MODEL_CHECK")},
        "turns": len(rows),
        "failed": len(rows) - len(ok),
        "without_audio": sum(1 for r in ok if not r["has_audio"]),
        "median_ms": median,
        "p90_ms": totals[min(len(totals) - 1, int(0.9 * len(totals)))] if totals else 0,
        "max_ms": totals[-1] if totals else 0,
        "median_by_language_ms": per_lang,
        "median_stt_ms": int(statistics.median(r["stt_ms"] for r in ok)) if ok else 0,
        "median_tts_wait_ms": int(statistics.median(r["tts_wait_ms"] for r in ok)) if ok else 0,
        "mean_reply_audio_bytes": avg_reply,
        "target_median_ms": TARGET_MS,
        "meets_target": bool(ok) and median < TARGET_MS,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--sessions", type=int, default=2)
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args(argv)
    if args.live:
        load_env()
        n = args.sessions * len(LANGS) * 4
        print(
            f"live voice run: {n} turns, estimated Claude USD {n * EST_USD_PER_TURN:.3f} "
            f"and Sarvam INR {n * EST_INR_PER_TURN:.0f} (the 100 INR sign-up credit covers it)"
        )
        if not args.yes and input("Run live? [y/N] ").strip().lower() != "y":
            return 0
    elif audio.shutil.which("ffmpeg") is None:
        print("ffmpeg is not installed: the stub check needs it.")
        return 1
    result = run(args.sessions, args.live)
    print(
        f"{result['mode']}: {result['turns']} turns ({result['failed']} failed), median "
        f"{result['median_ms']} ms, p90 {result['p90_ms']} ms (target median < {TARGET_MS} ms); "
        f"by language {result['median_by_language_ms']}"
    )
    if not args.live:
        print("STUB RUN: checks the harness only; these timings are not a measurement.")
    else:
        print("MEETS TARGET" if result["meets_target"] else "OVER TARGET OR NO DATA")
    if args.live and not args.no_write and result["failed"] == 0:
        path = ROOT / "evals" / "results" / "voice_latency.json"
        path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
        print("wrote evals/results/voice_latency.json")
    elif args.live and result["failed"]:
        print("Some turns failed, so nothing was written. Check the key with check_voices.py.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
