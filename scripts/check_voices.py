"""Check the Sarvam key and the twelve child voices, live. Run this first when you have a key.

Usage: python scripts/check_voices.py [--out DIR] [--dict]
  1. Sends one short synthesis. A 403 invalid_api_key_error means the key is wrong, revoked or
     not activated: fix it on the Sarvam dashboard and run again.
  2. For each of the twelve children (content/voices/children.v1.yaml) synthesises a line in each
     of en, hi and ta and saves OGG/Opus files in DIR (default: a temp folder, not the repo), so
     a person can LISTEN: are the five seats audibly distinct, and do they sound like children?
     Speaker names come from Sarvam's docs and were not verified live: a 400 here names the
     speaker to change.
  --dict  lists which pronunciation dictionaries have filled-in words ready to upload (none yet).
Audio is for listening only and is never committed. Costs a few rupees of Sarvam credit.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ai.config import load_env  # noqa: E402
from services.speech import audio, pronunciation  # noqa: E402
from services.speech.sarvam import LANGUAGE_CODES, SarvamClient, SpeechError  # noqa: E402
from services.speech.tts import SpeechCache, synthesize  # noqa: E402
from services.speech.voices import all_voices  # noqa: E402

LINES = {
    "en": "I think the answer is thirty-seven.",
    "hi": "मुझे लगता है जवाब सैंतीस है।",
    "ta": "விடை முப்பத்தேழு என்று நினைக்கிறேன்.",
}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    ap.add_argument("--dict", action="store_true")
    args = ap.parse_args(argv)
    load_env()
    client = SarvamClient()
    if not client.configured:
        print("SARVAM_API_KEY is not set in .env")
        return 1
    try:
        client.synthesize("hello", "en-IN", "shubh")
    except SpeechError as exc:
        print(f"The key does not work: {exc}. Check it on the Sarvam dashboard.")
        return 1
    print("The key works.")
    if audio.shutil.which("ffmpeg") is None:
        print("ffmpeg is not installed, so voices cannot be pitch-shifted or encoded.")
        return 1
    out = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="cc-voices-"))
    out.mkdir(parents=True, exist_ok=True)
    cache, bad, made = SpeechCache(), 0, 0
    for child, voice in all_voices().items():
        for lang, line in LINES.items():
            try:
                ogg, _ = synthesize(client, line, lang, voice, cache=cache)
            except SpeechError as exc:
                bad += 1
                print(f"  FAIL {child:<8} {lang} speaker={voice.speaker}: {exc}")
                continue
            (out / f"{child}-{lang}.ogg").write_bytes(ogg)
            made += 1
    print(f"Wrote clips to {out}. Listen to them; {bad} failed.")
    result = {
        "measure": "child_voice_synthesis_check",
        "source": "scripts/check_voices.py",
        "date": datetime.date.today().isoformat(),
        "children": len(all_voices()),
        "languages": sorted(LINES),
        "clips_made": made,
        "clips_failed": bad,
        "note": "synthesis only: whether the voices sound distinct needs a person to listen",
    }
    path = ROOT / "evals" / "results" / "voice_check.json"
    body = json.dumps(result, indent=2, sort_keys=True) + "\n"
    path.write_text(body, encoding="utf-8", newline="\n")
    print("wrote evals/results/voice_check.json")
    if args.dict:
        for lang in ("hi", "ta"):
            body = pronunciation.dictionary_json(lang)
            if body is None:
                print(f"  {lang}: no words filled in yet, nothing to upload")
                continue
            env = f"SARVAM_DICT_{lang.upper()}"
            print(f"  {lang}: ready; upload it through the dictionary API and set {env}")
    print("Languages:", ", ".join(LANGUAGE_CODES.values()))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
