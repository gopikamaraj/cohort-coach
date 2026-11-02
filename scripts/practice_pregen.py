"""Pre-generate and cache the Practice Class template lines, so they cost nothing when a child says
them.

    python tasks.py practice-pregen                          # counts, characters, cost and time
    python tasks.py practice-pregen --yes --limit 40          # live: voice and cache (paid)

The engine's template lines (services/practice/templates.py) are a finite set, but a large one:
every answer a child can give to every problem, in every language, in each child's voice and mood.
This script finds them the way a session meets them: it plays seeded sessions of every scenario and
language with random moves (`--sessions` per scenario and language) and collects each line a child
says, with the voice and the style she would say it in. It prints how many lines, voices, styles and
languages, the characters, the estimated cost and how long Bodhan's rate limit would take; nothing
is spent without --yes. `--limit` voices only the first N (the rest stay live). Lines go into the
private audio store (`line-cache/`), the cache the speech service reads first."""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ai.config import load_env  # noqa: E402
from engine.simulator import plan_turn  # noqa: E402
from services.practice.session import start_session  # noqa: E402
from services.practice.templates import render_line  # noqa: E402
from services.speech import cast, costs  # noqa: E402
from services.speech.voices import voice_for  # noqa: E402

SCENARIOS = ("SUB-SFL", "SUB-NODEC", "ADD-NOCARRY", "PV-HEARD")
LANGS = ("en", "hi", "ta")


def template_lines(sessions: int = 3) -> list[dict[str, Any]]:
    """Distinct (line, language, child voice, Bodhan voice, style) the engine's templates
    produce."""
    seen: dict[tuple[str, str, str, float, str, str], dict[str, Any]] = {}
    for error in SCENARIOS:
        for lang in LANGS:
            for seed in range(1, sessions + 1):
                s = start_session(error, lang, seed=seed)
                rng = random.Random(f"pregen:{error}:{lang}:{seed}")
                kids = s.state.children
                genders = [s.personas[c.name].gender if c.name in s.personas else "f" for c in kids]
                seats = dict(
                    zip([c.name for c in kids], cast.seat_voices(lang, genders), strict=True)
                )
                moves = list(s.loaded.config.moves)
                st = s.state
                while not st.finished:
                    to = rng.choice([None, *[c.name for c in kids]])
                    plan, st = plan_turn(
                        st, s.loaded.config, rng.choice(moves), addressed=to, posed=None
                    )
                    for q in (plan, *plan.chorus):
                        if not q.speaker:
                            continue
                        persona = s.personas.get(q.speaker)
                        v = voice_for(persona.id if persona else "")
                        style = cast.mood_style(q.mood) or ""
                        text = render_line(q, lang)
                        key = (text, lang, v.speaker, v.pitch, seats[q.speaker], style)
                        seen.setdefault(
                            key,
                            {
                                "text": text,
                                "language": lang,
                                "voice": v,
                                "bodhan_voice": seats[q.speaker],
                                "style": style or None,
                            },
                        )
    return list(seen.values())


def plan(lines: list[dict[str, Any]], per_minute: int = 8) -> dict[str, Any]:
    chars = sum(len(x["text"]) for x in lines)
    return {
        "lines": len(lines),
        "languages": len({x["language"] for x in lines}),
        "voices": len({x["bodhan_voice"] for x in lines}),
        "styles": len({x["style"] for x in lines}),
        "chars": chars,
        "cost_inr": round(costs.cost_inr("bodhan", "tts", chars=chars), 2),
        "minutes_at_rate_limit": round(len(lines) / per_minute, 1),
    }


def run(speech: Any, lines: list[dict[str, Any]]) -> dict[str, int]:
    from services.speech.sarvam import SpeechError

    made = cached = failed = 0
    for x in lines:
        try:
            _, who = speech.synthesize_ex(
                x["text"],
                x["language"],
                x["voice"],
                style=x["style"],
                bodhan_voice=x["bodhan_voice"],
            )
        except SpeechError:
            failed += 1
            continue
        cached += who == "cache"
        made += who != "cache"
    return {"made": made, "cached": cached, "failed": failed}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--sessions", type=int, default=3, help="seeded sessions per scenario and language"
    )
    ap.add_argument("--limit", type=int, default=None, help="voice only the first N lines")
    ap.add_argument("--yes", action="store_true", help="spend: voice and cache the lines")
    args = ap.parse_args(argv)
    load_env()
    lines = template_lines(args.sessions)
    p = plan(lines)
    print(
        f"{p['lines']} template lines in {p['languages']} languages, {p['voices']} child voices, "
        f"{p['styles']} styles: {p['chars']} characters, estimated INR {p['cost_inr']} "
        f"(unverified prices); about {p['minutes_at_rate_limit']} minutes at Bodhan's "
        f"8 requests a minute"
    )
    todo = lines[: args.limit] if args.limit else lines
    if args.limit:
        q = plan(todo)
        print(
            f"--limit {args.limit}: {q['lines']} lines, INR {q['cost_inr']}, about "
            f"{q['minutes_at_rate_limit']} minutes"
        )
    if not args.yes:
        print("Nothing spent. Run again with --yes (and --limit N to voice only some).")
        return 0
    from services.media.storage import audio_store
    from services.speech.service import SpeechService, default_chain

    speech = SpeechService("live", providers=default_chain(live=False), cache_store=audio_store())
    out = run(speech, todo)
    print(f"done: {out['made']} voiced, {out['cached']} already cached, {out['failed']} failed")
    return 0 if out["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
