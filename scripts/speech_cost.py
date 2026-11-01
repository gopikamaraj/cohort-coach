"""Speech cost per lesson and per Practice Class session, for each provider (Prompt 4).

    python scripts/speech_cost.py          # writes docs/evidence/speech_cost.md and .json

Computed by code from measured inputs, never estimated by an AI:
- lesson characters: the lesson drafts in the local database, filled with a large cohort's numbers as
  publishing does (falls back to the two live smoke-run lessons' sizes if the database has none);
- speaking rate: evals/results/chunk_calibration.json (characters per second per narrator voice), used
  for the round-trip check's seconds of speech to text;
- a Practice Class session: lines and characters per session from engine-simulated sessions (the
  engine's template lines), and the teacher's speech per turn (an ASSUMPTION, shown as such: 6 s);
- prices: content/speech_prices.yaml. Every paid price is `verified: false` until a person confirms it
  on the provider's page; the file says so beside every figure.
"""

from __future__ import annotations

import json
import random
import statistics
import sys
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.speech import costs  # noqa: E402

OUT_MD = ROOT / "docs" / "evidence" / "speech_cost.md"
OUT_JSON = ROOT / "docs" / "evidence" / "speech_cost.json"
TEACHER_SECONDS_PER_TURN = 6.0  # ASSUMPTION: what she says in one turn (the recorder allows 25 s)
SMOKE_LESSON_CHARS = {"en": 3174, "hi": 2773}  # the live smoke run of 1 Nov (SPEECH-LESSONS.md)


def lesson_chars() -> tuple[dict[str, list[int]], str]:
    try:
        from sqlalchemy.orm import sessionmaker

        from ai.config import load_env
        from ai.guard.explain import error_name
        from services.api.db import ReviewItem, make_engine
        from services.content import publish
        from services.speech import lessons

        load_env()
        db = sessionmaker(make_engine())()
        values = {
            **publish.cohort_values("SUB-SFL-g3-hindi-X-1", "SUB-SFL", example=(52, 29)),
            "track.total_days": "6",
        }
        out: dict[str, list[int]] = {}
        for r in db.query(ReviewItem).filter(ReviewItem.content_type == "track_draft").all():
            if r.content.get("kind") != "lesson":
                continue
            vals = {
                **values,
                "track.error_name": error_name("SUB-SFL", r.language),
                "track.day": str(r.content["day"]),
            }
            try:
                text = publish.checked_text(str(r.content["script"]), vals, "cost")
            except publish.PublishBlocked:
                continue
            out.setdefault(r.language, []).append(
                int(sum(len(s.text) for s in lessons.split_sentences(text)))
            )
        if out:
            return (
                out,
                "the lesson drafts in the local database, filled with a 9-class cohort's numbers",
            )
    except Exception:  # noqa: BLE001 - no database here: use the smoke-run sizes
        pass
    return {
        k: [v] for k, v in SMOKE_LESSON_CHARS.items()
    }, "the live smoke run of 1 Nov (two lessons)"


def chars_per_second() -> dict[str, float]:
    path = ROOT / "evals" / "results" / "chunk_calibration.json"
    rows = json.loads(path.read_text(encoding="utf-8"))["rows"]
    narrators = {"en": "Kavya", "hi": "Kavya", "ta": "Anitha"}
    return {
        r["language"]: r["chars_per_second"]
        for r in rows
        if narrators.get(r["language"]) == r["voice"]
    }


def practice_session() -> dict[str, float]:
    """Average child lines and characters per simulated session (random moves), and turns."""
    from engine.simulator import plan_turn
    from services.practice.session import start_session
    from services.practice.templates import render_line

    lines, chars, turns = [], [], []
    for error in ("SUB-SFL", "SUB-NODEC", "ADD-NOCARRY", "PV-HEARD"):
        for lang in ("en", "hi", "ta"):
            for seed in range(1, 4):
                s = start_session(error, lang, seed=seed)
                rng = random.Random(f"cost:{error}:{lang}:{seed}")
                st, n_lines, n_chars = s.state, 0, 0
                while not st.finished:
                    to = rng.choice([None, *[c.name for c in st.children]])
                    move = rng.choice(list(s.loaded.config.moves))
                    plan, st = plan_turn(st, s.loaded.config, move, addressed=to, posed=None)
                    for q in (plan, *plan.chorus):
                        if q.speaker:
                            n_lines += 1
                            n_chars += len(render_line(q, lang))
                lines.append(n_lines)
                chars.append(n_chars)
                turns.append(st.turn)
    return {
        "sessions": len(turns),
        "turns": statistics.fmean(turns),
        "lines": statistics.fmean(lines),
        "chars": statistics.fmean(chars),
    }


def main() -> int:
    per_lang, source = lesson_chars()
    cps = chars_per_second()
    sess = practice_session()
    prices = costs.prices()["providers"]
    rows: list[dict[str, Any]] = []
    for prov in ("bodhan", "sarvam"):
        for lang, sizes in sorted(per_lang.items()):
            c = statistics.fmean(sizes)
            secs = c / cps.get(lang, 11.0)
            tts = costs.cost_inr(prov, "tts", chars=int(c))
            stt = costs.cost_inr(prov, "stt", seconds=secs)
            rows.append(
                {
                    "what": "lesson",
                    "provider": prov,
                    "language": lang,
                    "lessons_measured": len(sizes),
                    "chars": round(c),
                    "speech_seconds": round(secs, 1),
                    "tts_inr": round(tts, 3),
                    "round_trip_stt_inr": round(stt, 3),
                    "total_inr": round(tts + stt, 3),
                }
            )
        stt_s = sess["turns"] * TEACHER_SECONDS_PER_TURN
        tts = costs.cost_inr(prov, "tts", chars=int(sess["chars"]))
        stt = costs.cost_inr(prov, "stt", seconds=stt_s)
        rows.append(
            {
                "what": "practice session (voice)",
                "provider": prov,
                "language": "all",
                "turns": round(sess["turns"], 1),
                "child_lines": round(sess["lines"], 1),
                "chars": round(sess["chars"]),
                "teacher_speech_seconds": round(stt_s),
                "tts_inr": round(tts, 3),
                "stt_inr": round(stt, 3),
                "total_inr": round(tts + stt, 3),
            }
        )
    verified = {
        p: {f: prices[p][f]["verified"] for f in ("tts", "stt")} for p in ("bodhan", "sarvam")
    }
    data = {
        "source": "scripts/speech_cost.py",
        "date": date.today().isoformat(),
        "lesson_source": source,
        "teacher_seconds_per_turn_assumed": TEACHER_SECONDS_PER_TURN,
        "simulated_sessions": sess["sessions"],
        "prices_verified": verified,
        "rows": rows,
    }
    OUT_JSON.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    lines = [
        "# Speech cost per lesson and per Practice Class session",
        "",
        f"Generated by `scripts/speech_cost.py` on {data['date']} (data: `docs/evidence/speech_cost.json`). **Every paid price is unverified** (`content/speech_prices.yaml`: Bodhan's from an article, the API page shows none; Sarvam's copied on 17 Oct). Confirm the prices on each provider's console, then mark them `verified: true` and run this again.",
        "",
        f"Lesson characters: {source}. Seconds of speech for the round-trip check: characters divided by the narrator's speaking rate from `evals/results/chunk_calibration.json`. Practice Class session: {sess['sessions']} engine-simulated sessions with random moves (template lines only; AI-written lines are similar in length); the teacher's speech is an **assumption** of {TEACHER_SECONDS_PER_TURN:g} s a turn.",
        "",
        "| What | Provider | Language | Characters | Seconds of speech to text | Text to speech (INR) | Speech to text (INR) | Total (INR) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        secs = r.get("speech_seconds", r.get("teacher_speech_seconds"))
        stt = r.get("round_trip_stt_inr", r.get("stt_inr"))
        what = r["what"] + (
            f" ({r['lessons_measured']} measured)"
            if r["what"] == "lesson"
            else f" ({r['turns']} turns, {r['child_lines']} child lines)"
        )
        lines.append(
            f"| {what} | {r['provider']} | {r['language']} | {r['chars']} | {secs} | {r['tts_inr']} | {stt} | {r['total_inr']} |"
        )
    lines += [
        "",
        "A 3-week track has 6 lessons per language; the cost per teacher is shared by every teacher in the cohort, since a lesson is voiced once per cohort and cached.",
        "",
    ]
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
