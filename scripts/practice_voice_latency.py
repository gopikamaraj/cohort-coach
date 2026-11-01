"""Practice Class voice-turn latency, stage by stage and per provider (Prompt 3).

    python scripts/practice_voice_latency.py                   # mock: providers with fixed delays,
    no cost python scripts/practice_voice_latency.py --live --yes      # live: Bodhan/Sarvam and
    Claude (paid)

Each turn records: speech to text, call 2 (move label), the engine, call 1 (child line), call 7
(checker), text to speech and the time to the first audio (layers.evaluation.timing of POST
/voice-turn), with the provider that spoke. Reports the median and 95th percentile of each stage per
provider. No target is enforced. The mock run proves the measurement, not the services; its numbers
are the delays it was given. Writes evals/results/practice_voice_latency_mock.json or
practice_voice_latency_live.json. The live run prints its estimated cost first and needs --yes."""

from __future__ import annotations

import argparse
import datetime
import json
import math
import statistics
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from ai.client import CallContext  # noqa: E402
from ai.config import load_env  # noqa: E402
from services.api import practice as api  # noqa: E402
from services.api.main import app  # noqa: E402
from services.practice.stub_client import StubClient  # noqa: E402
from services.speech import audio, tts  # noqa: E402
from services.speech.chain import ProviderChain  # noqa: E402
from services.speech.provider import Audio, Capabilities, Transcript  # noqa: E402
from services.speech.service import STUB_LINES, SpeechService, default_chain  # noqa: E402
from services.speech.voices import Voice  # noqa: E402

OUT = ROOT / "evals" / "results"
STAGES = ("stt_ms", "label_ms", "engine_ms", "child_ms", "check_ms", "tts_ms", "first_audio_ms")
LANGS = ("en", "hi", "ta")


class Delayed:
    """A mock provider that takes a fixed time, so the report can be checked against it."""

    def __init__(self, name: str, stt_s: float, tts_s: float) -> None:
        self.name, self.stt_s, self.tts_s = name, stt_s, tts_s
        self.n = 0

    def configured_for(self, function: str) -> bool:
        return True

    @property
    def capabilities(self) -> Capabilities:
        return Capabilities(30.0, frozenset({"wav"}), 300)

    def transcribe(self, wav: bytes, language: str) -> Transcript:
        time.sleep(self.stt_s)
        self.n += 1
        return Transcript(STUB_LINES[language][self.n % 4], audio.wav_seconds(wav), self.name)

    def synthesize(self, text: str, language: str, voice: str, style: str | None) -> Audio:
        time.sleep(self.tts_s)
        return Audio(audio.tone(0.4, 440, rate=24000), "wav", 24000, 0.4, len(text), self.name)


def pct(values: list[float], q: float) -> float:
    s = sorted(values)
    return s[min(len(s) - 1, max(0, math.ceil(q * len(s)) - 1))]


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for provider in sorted({str(r.get("tts_provider")) for r in rows}):
        mine = [r for r in rows if str(r.get("tts_provider")) == provider]
        out[provider] = {"turns": len(mine)}
        for st in STAGES:
            vals = [float(r[st]) for r in mine if r.get(st) is not None]
            if vals:
                out[provider][st] = {
                    "median": round(statistics.median(vals)),
                    "p95": round(pct(vals, 0.95)),
                }
    return out


def teacher_audio(speech: SpeechService | None, line: str, lang: str) -> bytes:
    """What the teacher says, as audio: a tone in the mock (the mock does not listen), the line
    itself voiced in a live run so speech to text has real speech to hear."""
    if speech is None:
        return audio.tone(1.5, 300, rate=24000)
    data = speech.synthesize(line, lang, Voice("ritu", 1.0, 1.0))
    return audio.to_wav_16k_mono(data)


def run(live: bool, turns: int) -> dict[str, Any]:
    tts.CACHE._items.clear()
    if live:
        speech = SpeechService("live", log=lambda **kw: None, providers=default_chain())
        ctx = CallContext(mode="live")
    else:
        chain = ProviderChain(
            {"bodhan": Delayed("bodhan", 0.8, 1.2), "sarvam": Delayed("sarvam", 0.6, 0.9)},
            order=lambda f, lang: ["bodhan", "sarvam"],
        )
        speech = SpeechService("live", log=lambda **kw: None, providers=chain)
        ctx = CallContext(mode="stub", client=StubClient())
    app.dependency_overrides[api.get_speech] = lambda: speech
    app.dependency_overrides[api.get_ai_context] = lambda: ctx
    http = TestClient(app)
    rows: list[dict[str, Any]] = []
    try:
        for lang in LANGS:
            sid = http.post(
                "/api/practice/sessions", json={"scenario": "SUB-SFL", "language": lang, "seed": 5}
            ).json()["session_id"]
            for i in range(turns):
                line = STUB_LINES[lang][i % 4]
                clip = teacher_audio(speech if live else None, line, lang)
                t0 = time.monotonic()
                res = http.post(
                    f"/api/practice/sessions/{sid}/voice-turn",
                    files={"audio": ("t.wav", clip, "audio/wav")},
                )
                wall = int((time.monotonic() - t0) * 1000)
                if res.status_code != 200:
                    rows.append({"lang": lang, "status": res.status_code, "wall_ms": wall})
                    continue
                timing = res.json()["layers"]["evaluation"]["timing"]
                rows.append({"lang": lang, "status": 200, "wall_ms": wall, **timing})
    finally:
        app.dependency_overrides.clear()
    ok = [r for r in rows if r["status"] == 200]
    return {
        "source": "scripts/practice_voice_latency.py",
        "date": datetime.date.today().isoformat(),
        "mode": "live"
        if live
        else "mock (fixed delays: bodhan stt 0.8 s / tts 1.2 s; the AI is a stub)",
        "turns": len(rows),
        "ok_turns": len(ok),
        "failed_turns": [r for r in rows if r["status"] != 200],
        "by_provider": summarise(ok),
        "rows": rows,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--turns", type=int, default=4, help="turns per language")
    args = ap.parse_args(argv)
    if args.live:
        load_env()
        n = args.turns * len(LANGS)
        print(
            f"live run: {n} turns. Estimated cost: Claude about USD {0.003 * n:.3f}, speech about "
            f"INR {0.2 * n:.1f} (unverified prices)"
        )
        if not args.yes:
            print("Nothing spent. Run again with --yes.")
            return 0
    result = run(args.live, args.turns)
    for provider, stats in result["by_provider"].items():
        print(f"{provider}: {stats['turns']} turns")
        for st in STAGES:
            if st in stats:
                print(
                    f"  {st:<15} median {stats[st]['median']:>6} ms   p95 {stats[st]['p95']:>6} ms"
                )
    if result["failed_turns"]:
        print(f"failed turns: {[(r['lang'], r['status']) for r in result['failed_turns']]}")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / (
        "practice_voice_latency_live.json" if args.live else "practice_voice_latency_mock.json"
    )
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
