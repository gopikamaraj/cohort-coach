"""Make the blinded listening pack: every script voiced by Bodhan (two candidate voices) and Sarvam
(two matching voices), random file names, a separate key, and an offline rating page.

    python tasks.py speech-eval-pack                 # the plan and the estimated cost
    python tasks.py speech-eval-pack --yes           # live: makes the clips (paid)

Writes evals/speech-eval/pack-<date>/ (git-ignored): `rate.html` (self-contained: the clips are
embedded, it works offline; a rater scores each clip 1 to 5 for naturalness, clarity, correct
numbers and suitability, adds a comment, and saves a CSV), and `key.json` (which clip is which
provider and voice; keep it away from raters). Then `python scripts/speech_eval_aggregate.py`.
"""

from __future__ import annotations

import argparse
import base64
import html
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

OUT = ROOT / "evals" / "speech-eval"
LANGS = ("en", "hi", "ta")
# Two candidate voices per provider and language. Bodhan from its page; Sarvam from voices.v1.
BODHAN = {"en": ["Kavya", "Amit"], "hi": ["Kavya", "Amit"], "ta": ["Anitha", "Arun"]}
SARVAM = {"en": ["ritu", "rahul"], "hi": ["ritu", "rahul"], "ta": ["ritu", "rahul"]}


def _style(mood: str | None) -> str | None:
    from services.speech import cast

    return cast.mood_style(mood)


def clips() -> list[evaluation.Clip]:
    s = evaluation.scripts()
    out: list[evaluation.Clip] = []
    for lang in LANGS:
        items = [("lesson", i, t, None) for i, t in enumerate(s["lesson"][lang])]
        items += [("child", i, c["text"], c["mood"]) for i, c in enumerate(s["child"][lang])]
        for kind, i, text, mood in items:
            style = "educational lecture" if kind == "lesson" else _style(mood)
            for v in BODHAN[lang]:
                out.append(evaluation.Clip(lang, kind, i, text, "bodhan", v, style))
            for v in SARVAM[lang]:
                out.append(evaluation.Clip(lang, kind, i, text, "sarvam", v, None))
    return out


def plan(cs: list[evaluation.Clip]) -> dict[str, Any]:
    b = [c for c in cs if c.provider == "bodhan"]
    s = [c for c in cs if c.provider == "sarvam"]
    cost = costs.cost_inr("bodhan", "tts", chars=sum(len(c.text) for c in b)) + costs.cost_inr(
        "sarvam", "tts", chars=sum(len(c.text) for c in s)
    )
    return {
        "clips": len(cs),
        "bodhan": len(b),
        "sarvam": len(s),
        "cost_inr": round(cost, 2),
        "bodhan_minutes": round(len(b) / 8, 1),
    }


def page(named: list[tuple[str, bytes, str]], lang_of: dict[str, str]) -> str:
    """A self-contained rating page: embedded clips, four 1-5 scores and a comment per clip, and a
    button that saves the ratings as CSV. No network, no tracking."""
    rows = []
    for name, ogg, text in named:
        src = "data:audio/ogg;base64," + base64.b64encode(ogg).decode()
        selects = "".join(
            f'<label>{s}<select name="{s}" aria-label="{s} for {name}"><option value=""></option>'
            + "".join(f"<option>{n}</option>" for n in range(1, 6))
            + "</select></label>"
            for s in evaluation.SCORES
        )
        rows.append(
            f'<section class="clip" data-clip="{name}"><h2>{name}</h2>'
            f'<p lang="{lang_of[name]}">{html.escape(text)}</p>'
            f'<audio controls preload="none" src="{src}"></audio>'
            f'<div class="scores">{selects}</div>'
            f'<label class="c">Comment<input name="comment" aria-label="comment for {name}"></label></section>'
        )
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Speech listening test</title>
<style>body{{font-family:system-ui,sans-serif;margin:16px;max-width:760px}}.clip{{border-bottom:1px solid #999;padding:8px 0}}
.scores{{display:flex;flex-wrap:wrap;gap:8px}}label{{display:inline-flex;gap:4px;align-items:center;min-height:44px}}
select,input,button{{min-height:44px;font-size:16px}}audio{{width:100%}}</style>
<main>
<h1>Speech listening test</h1>
<p>Listen to each clip and score it from 1 (poor) to 5 (excellent): <b>naturalness</b> (sounds like a person),
<b>clarity</b> (easy to follow), <b>numbers</b> (every number said correctly) and <b>suitability</b> (right for a
teacher or a Grade 3 child). The clip names say nothing about who made them. Then save your ratings and send the file.</p>
<label>Your name or initials<input id="rater" aria-label="your name or initials"></label>
{"".join(rows)}
<p><button id="save" type="button">Save my ratings (CSV)</button></p>
</main>
<script>
document.getElementById("save").onclick = () => {{
  const rater = document.getElementById("rater").value.replace(/[",\\n]/g, " ");
  const lines = ["rater,clip,{",".join(evaluation.SCORES)},comment"];
  for (const s of document.querySelectorAll(".clip")) {{
    const v = (n) => s.querySelector(`[name=${{n}}]`).value;
    const c = v("comment").replace(/"/g, "'");
    lines.push([rater, s.dataset.clip, {", ".join(f'v("{x}")' for x in evaluation.SCORES)}, `"${{c}}"`].join(","));
  }}
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([lines.join("\\n") + "\\n"], {{ type: "text/csv" }}));
  a.download = `ratings-${{rater || "rater"}}.csv`;
  a.click();
}};
</script></html>"""


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--seed", type=int, default=20261101)
    args = ap.parse_args(argv)
    load_env()
    cs = clips()
    p = plan(cs)
    print(
        f"{p['clips']} clips ({p['bodhan']} Bodhan, {p['sarvam']} Sarvam), estimated INR {p['cost_inr']} (unverified prices); Bodhan's rate limit makes it about {p['bodhan_minutes']} minutes"
    )
    if not args.yes:
        print("Nothing spent. Run again with --yes.")
        return 0
    from services.speech.bodhan import BodhanClient, BodhanProvider
    from services.speech.provider import SarvamProvider

    providers = {"bodhan": BodhanProvider(BodhanClient()), "sarvam": SarvamProvider()}
    named, key = evaluation.blind(cs, args.seed)
    folder = OUT / f"pack-{date.today().isoformat()}"
    folder.mkdir(parents=True, exist_ok=True)
    made: list[tuple[str, bytes, str]] = []
    failed = 0
    for name, c in named:
        try:
            got = providers[c.provider].synthesize(c.text, c.language, c.voice, c.style)
            ogg = audio.to_ogg_opus(got.data, pitch_ratio=1.0, input_rate=got.sample_rate, kbps=32)
        except SpeechError as exc:
            failed += 1
            print(f"{name}: failed ({c.provider} {exc.kind} {exc.code})")
            continue
        made.append((name, ogg, c.text))
    made_names = {n for n, _, _ in made}
    key = [k for k in key if k["clip"] in made_names]
    (folder / "key.json").write_text(
        json.dumps({"seed": args.seed, "clips": key}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    lang_of = {k["clip"]: k["language"] for k in key}
    (folder / "rate.html").write_text(page(made, lang_of), encoding="utf-8")
    print(
        f"wrote {folder.relative_to(ROOT)}/rate.html ({len(made)} clips, {failed} failed) and key.json"
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
