"""A listening page for choosing the Practice Class voices: sample child lines in each mood, per
voice.

    python scripts/voice_audition.py --lang hi                    # the plan and estimated cost
    python scripts/voice_audition.py --lang hi --yes              # live: makes the clips (paid)
    python scripts/voice_audition.py --lang ta --voices Arun,Lakshmi --yes

For each chosen Bodhan voice (default: every child voice for the language in content/voices.yaml)
it makes three sample child lines in each distinct style the moods map to (happy for bright, sad
for small, the neutral reading for calm, flat and doubtful), raised in pitch as a child's line is,
into audition/<lang>/ (git-ignored), with a simple index.html to listen and compare. The lines are
made-up children's answers; no real child's voice or name. Prints the estimated cost first.
"""

from __future__ import annotations

import argparse
import html
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai.config import load_env  # noqa: E402
from services.speech import audio, cast, costs  # noqa: E402
from services.speech.bodhan import BodhanProvider  # noqa: E402
from services.speech.sarvam import SpeechError  # noqa: E402

OUT = ROOT / "audition"
LINES = {
    "en": [
        "I think it is 37, Miss!",
        "Oh. I took 2 from 9. Is that wrong?",
        "Wait, I opened a bundle. So it is 23!",
    ],
    "hi": [
        "मुझे लगता है 37 है, दीदी!",
        "अरे, मैंने 9 में से 2 घटाया। क्या यह गलत है?",
        "रुकिए, मैंने एक गट्ठर खोला। तो 23 हुआ!",
    ],
    "ta": [
        "எனக்கு 37 என்று தோன்றுகிறது, டீச்சர்!",
        "ஓ, நான் 9-இலிருந்து 2 கழித்தேன். அது தவறா?",
        "இருங்கள், நான் ஒரு கட்டைப் பிரித்தேன். அப்போ 23!",
    ],
}
PITCH = 1.25  # a child's line is raised in pitch, as in the Practice Class


def styles() -> list[tuple[str, str | None]]:
    """(label, style) for each distinct style the moods map to."""
    out: dict[str | None, list[str]] = {}
    for mood in ("bright", "small", "calm", "flat", "doubtful"):
        out.setdefault(cast.mood_style(mood), []).append(mood)
    return [(" / ".join(m), s) for s, m in out.items()]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=sorted(LINES), required=True)
    ap.add_argument("--voices", default="", help="comma-separated Bodhan voices")
    ap.add_argument("--yes", action="store_true")
    args = ap.parse_args(argv)
    load_env()
    data = cast._data()["children"][args.lang]
    voices = [v for v in args.voices.split(",") if v] or [*data["f"], *data["m"]]
    st = styles()
    n = len(voices) * len(st) * len(LINES[args.lang])
    chars = len(voices) * len(st) * sum(len(x) for x in LINES[args.lang])
    print(
        f"{n} clips ({len(voices)} voices x {len(st)} styles x 3 lines), {chars} characters, "
        f"estimated INR {costs.cost_inr('bodhan', 'tts', chars=chars):.2f} (unverified prices); "
        f"about {n / 8:.0f} minutes at Bodhan's 8 requests a minute"
    )
    if not args.yes:
        print("Nothing spent. Run again with --yes.")
        return 0
    p = BodhanProvider()
    folder = OUT / args.lang
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for voice in voices:
        for label, style in st:
            for i, line in enumerate(LINES[args.lang]):
                name = f"{voice}-{(style or 'neutral').replace(' ', '_')}-{i + 1}.ogg"
                t0 = time.monotonic()
                try:
                    got = p.synthesize(line, args.lang, voice, style)
                    (folder / name).write_bytes(audio.to_ogg_opus(got.data, pitch_ratio=PITCH))
                    rows.append(
                        (voice, label, style, line, name, int((time.monotonic() - t0) * 1000))
                    )
                    print(f"{voice} {style or 'neutral'} {i + 1}: ok")
                except SpeechError as exc:
                    rows.append((voice, label, style, line, "", 0))
                    print(f"{voice} {style or 'neutral'} {i + 1}: failed ({exc.kind} {exc.code})")
    cells = "\n".join(
        f"<tr><td>{html.escape(v)}</td><td>{html.escape(lab)}</td><td>{html.escape(line)}</td>"
        f"<td>{
            f'<audio controls preload=none src={html.escape(f)!r}></audio>' if f else 'failed'
        }</td></tr>"
        for v, lab, _s, line, f, _ms in rows
    )
    (folder / "index.html").write_text(
        f"""<!doctype html><meta charset="utf-8"><title>Voice audition {args.lang}</title>
<style>body{{font-family:system-ui,sans-serif;margin:16px}}td{{padding:4px 8px;border-bottom:1px
solid #ccc}}</style> <h1>Practice Class voices: {args.lang}</h1> <p>Each child keeps one voice for a
session. Listen and note which voices sound like a Grade 3 child and fit each mood. Made-up lines;
AI-generated voices (Bodhan AI / AI4Bharat).</p>
<table><tr><th>Voice</th><th>Mood</th><th>Line</th><th>Listen</th></tr> {cells}
</table>""",
        encoding="utf-8",
    )
    print(f"wrote {folder.relative_to(ROOT)}/index.html ({sum(1 for r in rows if r[4])} clips)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
