"""Measure how fast each lesson voice speaks, so the chunk target can be set from evidence.

    python scripts/calibrate_chunks.py          # prints the plan and estimated cost
    python scripts/calibrate_chunks.py --yes    # live: synthesizes the sample sentences (paid)

For each language and each candidate Bodhan voice it synthesizes three sample lesson sentences
(with numbers and sums), measures the real audio length, and reports characters per second and the
longest chunk that stays under 28 seconds. Writes evals/results/chunk_calibration.json. Prices are
unverified (content/speech_prices.yaml).
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai.config import load_env  # noqa: E402
from services.speech import audio, costs  # noqa: E402
from services.speech.bodhan import BodhanProvider  # noqa: E402
from services.speech.sarvam import SpeechError  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "evals" / "results" / "chunk_calibration.json"
SAMPLES = {
    "en": [
        "Today we look at a mistake many children make with 52 minus 29.",
        "Show the number with bundles of ten and loose sticks, then take away 9 sticks.",
        "If a child writes 37, ask her to check by adding back: 37 plus 29 is not 52.",
    ],
    "hi": [
        "आज हम 52 में से 29 घटाने की एक आम गलती देखेंगे।",
        "संख्या को दस-दस के गट्ठर और खुली तीलियों से दिखाइए, फिर 9 तीलियाँ हटाइए।",
        "अगर बच्चा 37 लिखे, तो उससे जोड़कर जाँचने को कहिए: 37 और 29 मिलकर 52 नहीं होते।",
    ],
    "ta": [
        "இன்று 52 இலிருந்து 29 கழிப்பதில் குழந்தைகள் செய்யும் ஒரு பொதுவான தவறைப் பார்ப்போம்.",
        "எண்ணைப் பத்துக் கட்டுகளாலும் தனிக் குச்சிகளாலும் காட்டி, பிறகு 9 குச்சிகளை எடுங்கள்.",
        "குழந்தை 37 என்று எழுதினால், திரும்பக் கூட்டிச் சரிபார்க்கச் சொல்லுங்கள்: 37 உடன் 29 சேர்த்தால் 52 வராது.",
    ],
}
VOICES = {"en": ["Kavya", "Amit"], "hi": ["Kavya", "Suhani", "Amit"], "ta": ["Anitha", "Arun"]}
STYLE = "educational lecture"


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args(argv)
    load_env()
    chars = sum(len(s) * len(VOICES[lang]) for lang, ss in SAMPLES.items() for s in ss)
    print(
        f"{sum(len(v) for v in VOICES.values()) * 3} requests, {chars} characters, estimated INR "
        f"{costs.cost_inr('bodhan', 'tts', chars=chars):.3f} (unverified prices)"
    )
    if not args.yes:
        print("Nothing spent. Run again with --yes.")
        return 0
    p = BodhanProvider()
    if not p.configured_for("tts"):
        print("BODHAN_SPEAK_API_KEY is not set.")
        return 1
    rows = []
    for lang, sentences in SAMPLES.items():
        for voice in VOICES[lang]:
            rates = []
            for s in sentences:
                t0 = time.monotonic()
                try:
                    got = p.synthesize(s, lang, voice, STYLE)
                except SpeechError as exc:
                    print(f"{lang} {voice}: failed ({exc.kind} {exc.status})")
                    continue
                secs = audio.duration_seconds(got.data)
                rates.append(len(s) / secs if secs else 0.0)
                print(
                    f"{lang} {voice}: {len(s)} chars -> {secs:.2f} s "
                    f"({int((time.monotonic() - t0) * 1000)} ms)"
                )
            if rates:
                cps = statistics.fmean(rates)
                rows.append(
                    {
                        "language": lang,
                        "voice": voice,
                        "chars_per_second": round(cps, 2),
                        "max_chars_under_28s": int(cps * 28),
                        "samples": len(rates),
                    }
                )
    for r in rows:
        print(
            f"{r['language']} {r['voice']}: {r['chars_per_second']} chars/s; "
            f"28 s is about {r['max_chars_under_28s']} characters"
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "source": "scripts/calibrate_chunks.py",
                "date": time.strftime("%Y-%m-%d"),
                "style": STYLE,
                "rows": rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT.relative_to(OUT.parents[2])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
