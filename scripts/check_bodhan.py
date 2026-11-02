"""Check the Bodhan keys: synthesize one short Hindi sentence, then transcribe that audio back.

    python scripts/check_bodhan.py            # live: two small paid calls (estimate printed first)
    python scripts/check_bodhan.py --no-live  # configuration only, no call

Reads .env. A key is never printed beyond its first 4 characters. Each key is checked on its own:
the speak key with text to speech, the transcribe key with speech to text.

Exit codes: 0 both work; 1 configuration problem (a key missing, ffmpeg missing for the round trip);
2 the speak key (text to speech) failed; 3 the transcribe key (speech to text) failed.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai.config import load_env  # noqa: E402
from services.speech import audio, costs  # noqa: E402
from services.speech.bodhan import BASE_URL, BodhanClient, BodhanProvider  # noqa: E402
from services.speech.sarvam import SpeechError  # noqa: E402

SENTENCE = "बावन में से उनतीस घटाओ तो तेईस बचते हैं।"  # "52 minus 29 leaves 23": no name, no child
VOICE = "Kavya"


def masked(var: str) -> str:
    value = os.environ.get(var, "")
    return f"{value[:4]}... ({len(value)} characters)" if value else "not set"


def key_status() -> tuple[bool, bool]:
    speak = bool(os.environ.get("BODHAN_SPEAK_API_KEY") or os.environ.get("BODHAN_API_KEY"))
    transcribe = bool(
        os.environ.get("BODHAN_TRANSCRIBE_API_KEY") or os.environ.get("BODHAN_API_KEY")
    )
    print(f"base URL                  {os.environ.get('BODHAN_BASE_URL') or BASE_URL}")
    for var in ("BODHAN_SPEAK_API_KEY", "BODHAN_TRANSCRIBE_API_KEY", "BODHAN_API_KEY"):
        print(f"{var:<26}{masked(var)}")
    print(f"speak key in use          {'yes' if speak else 'NO'}")
    print(f"transcribe key in use     {'yes' if transcribe else 'NO'}")
    return speak, transcribe


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-live", action="store_true", help="check the configuration only")
    args = ap.parse_args(argv)
    load_env()
    speak, transcribe = key_status()
    have_ffmpeg = True
    try:
        audio.ffmpeg()
    except SpeechError:
        have_ffmpeg = False
    print(
        "ffmpeg                    "
        + ("found" if have_ffmpeg else "NOT FOUND (needed to convert phone audio)")
    )
    if not (speak and transcribe):
        print("A key is missing: put BODHAN_SPEAK_API_KEY and BODHAN_TRANSCRIBE_API_KEY in .env.")
        return 1
    tts_cost = costs.cost_inr("bodhan", "tts", chars=len(SENTENCE))
    print(
        f"estimated cost            text to speech INR {tts_cost:.4f} "
        f"({len(SENTENCE)} characters), "
        f"plus speech to text of about 3 s (INR {costs.cost_inr('bodhan', 'stt', seconds=3):.4f}); "
        f"prices are unverified (content/speech_prices.yaml)"
    )
    if args.no_live:
        print("configuration OK (no call made)")
        return 0

    p = BodhanProvider(BodhanClient())
    t0 = time.monotonic()
    try:
        spoken = p.synthesize(SENTENCE, "hi", VOICE, "educational lecture")
    except SpeechError as exc:
        print(f"TEXT TO SPEECH FAILED: {exc.kind} (status {exc.status} {exc.code})")
        return 2
    print(
        f"text to speech            {len(spoken.data)} bytes, {spoken.seconds:.2f} s, "
        f"{spoken.sample_rate} Hz {spoken.format}, {int((time.monotonic() - t0) * 1000)} ms, "
        f"request id {spoken.request_id}"
    )
    wav = audio.to_wav_16k_mono(spoken.data) if have_ffmpeg else spoken.data
    t1 = time.monotonic()
    try:
        heard = p.transcribe(wav, "hi")
    except SpeechError as exc:
        print(f"SPEECH TO TEXT FAILED: {exc.kind} (status {exc.status} {exc.code})")
        return 3
    print(
        f"speech to text            {heard.seconds_billed:.2f} s billed, "
        f"{int((time.monotonic() - t1) * 1000)} ms, request id {heard.request_id}"
    )
    print(f"sent                      {SENTENCE}")
    print(f"heard back                {heard.text}")
    total = tts_cost + costs.cost_inr("bodhan", "stt", seconds=heard.seconds_billed)
    print(f"estimated cost            INR {total:.4f} (unverified prices)")
    print("both keys work")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
