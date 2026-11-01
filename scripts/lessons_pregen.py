"""Pre-generate and cache the audio of every published demo lesson, in every language.

    python tasks.py lessons-pregen            # prints what it would do and the estimated cost
    python tasks.py lessons-pregen --yes      # live: voices and caches (paid)

Reads the newest published manifest of each track from the database (DATABASE_URL), and voices each
lesson through the speech layer (Bodhan first, Sarvam as the fallback) into the private audio store,
so a later publish, a regenerate of an unchanged sentence, and playback make no provider call, and
the demo lessons still play with every provider down. Prints characters and the estimated cost
first; nothing is spent without --yes. Prices are unverified (content/speech_prices.yaml)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from ai.config import load_env  # noqa: E402
from services.api.db import Base, TrackManifest, make_engine  # noqa: E402
from services.speech import lessons  # noqa: E402


def demo_lessons(db: Session) -> list[dict[str, Any]]:
    """The lesson parts of the newest manifest of each track (one cohort's filled text each)."""
    newest: dict[str, TrackManifest] = {}
    for m in db.execute(select(TrackManifest).order_by(TrackManifest.id.desc())).scalars():
        newest.setdefault(str(m.body.get("track_id")), m)
    out = []
    for m in newest.values():
        for p in m.body.get("parts", []):
            if p.get("kind") == "lesson" and p.get("script"):
                out.append(
                    {
                        "track": m.body.get("track_id"),
                        "language": p["language"],
                        "day": p["day"],
                        "script": p["script"],
                    }
                )
    return out


def plan(items: list[dict[str, Any]]) -> dict[str, float]:
    chars = sum(lessons.estimate(i["script"], i["language"])["chars"] for i in items)
    cost = sum(lessons.estimate(i["script"], i["language"])["cost_inr"] for i in items)
    return {"lessons": float(len(items)), "chars": chars, "cost_inr": round(cost, 2)}


def run(db: Session, store: Any, speech: Any, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    done = []
    for i in items:
        try:
            got = lessons.generate(i["script"], i["language"], speech, store)
        except lessons.LessonAudioUnavailable as exc:
            done.append({**i, "ok": False, "why": str(exc)})
            continue
        done.append(
            {
                **i,
                "ok": True,
                "provider": got.provider,
                "seconds": got.seconds,
                "cached": got.from_cache,
                "cost_inr": got.cost_inr,
                **got.summary,
            }
        )
    return done


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="spend: voice and cache the lessons")
    args = ap.parse_args(argv)
    load_env()
    from services.media.storage import audio_store
    from services.speech.service import default_service

    engine = make_engine()
    Base.metadata.create_all(engine)
    db = sessionmaker(engine, expire_on_commit=False)()
    items = demo_lessons(db)
    if not items:
        print(
            "No published lesson in the database: "
            "publish a track first (scripts/seed_demo_track.py)."
        )
        return 1
    p = plan(items)
    print(
        f"{int(p['lessons'])} lessons, {int(p['chars'])} characters, "
        f"estimated INR {p['cost_inr']} with the round-trip check (unverified prices)"
    )
    if not args.yes:
        print("Nothing spent. Run again with --yes to voice and cache them.")
        return 0
    rows = run(db, audio_store(), default_service(), items)
    for r in rows:
        if r["ok"]:
            print(
                f"{r['track']} {r['language']} day {r['day']}: {r['provider']}, "
                f"{r['seconds']:.1f} s, {r['passed']} of {r['checked']} sentences "
                f"passed the check"
                f"{' (from cache)' if r['cached'] else ''}, INR {r['cost_inr']}"
            )
        else:
            print(f"{r['track']} {r['language']} day {r['day']}: TEXT ONLY ({r['why']})")
    spent = sum(r.get("cost_inr", 0.0) for r in rows)
    print(f"done: {sum(r['ok'] for r in rows)} of {len(rows)} voiced, estimated INR {spent:.2f}")
    return 0 if all(r["ok"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
