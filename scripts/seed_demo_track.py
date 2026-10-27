"""Switch a demo track on in the judge deployment, so a judge can walk T4 (track and lessons).

In the judge demo everything is simulated and a judge may press the coach's and officer's buttons
herself; this script presses them once so the lesson flow has something to show. It only approves
drafts that already passed every automatic gate (gate 1, the pre-filter and call 7): a draft the
checker held is never approved here. The audit rows say `demo-seed`.

It refuses to run outside a judge deployment (JUDGE_MODE=1): in a real deployment only people
approve content.

Usage:
  JUDGE_MODE=1 python scripts/seed_demo_track.py --languages hi,en
  JUDGE_MODE=1 python scripts/seed_demo_track.py --languages en --draft  # re-draft (spends)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402

from ai import config  # noqa: E402
from ai.calls.c05_track_draft import draft_part  # noqa: E402
from ai.client import CallContext  # noqa: E402
from services.api.db import ReviewItem, make_engine  # noqa: E402
from services.content import drafting, publish, review, versions  # noqa: E402
from services.content.track import load_track  # noqa: E402

COACH = ("demo-seed", "coach")
OFFICER = ("demo-seed", "officer")
ATTEMPTS = 3


class NotAJudgeDeployment(RuntimeError):
    pass


def parts_of(track) -> list[tuple[str, int]]:  # type: ignore[no-untyped-def]
    return [("lesson", d) for d in range(1, len(track.lessons) + 1)] + [("model_lesson", 0)]


def passing_item(db: Session, language: str, kind: str, day: int) -> ReviewItem | None:
    """The newest queued draft of this part that passed every automatic gate."""
    rows = db.execute(
        select(ReviewItem)
        .where(
            ReviewItem.content_type == "track_draft",
            ReviewItem.language == language,
            ReviewItem.status == "pending",
        )
        .order_by(ReviewItem.created_at.desc())
    ).scalars()
    for r in rows:
        c = r.content
        if (
            c.get("kind") == kind
            and int(c.get("day", -1)) == day
            and c.get("status") == "needs_review"
        ):
            return r
    return None


def seed(db: Session, languages: list[str], *, draft: bool, track_id: str = "sub-sfl.v1") -> dict:  # type: ignore[type-arg]
    if not config.judge_mode():
        raise NotAJudgeDeployment(
            "Seeding approvals is only for the judge deployment (JUDGE_MODE=1)."
        )
    track = load_track(track_id)
    ready: list[str] = []
    report: dict = {"languages": {}}  # type: ignore[type-arg]
    for lang in languages:
        missing: list[str] = []
        chosen: list[ReviewItem] = []
        for kind, day in parts_of(track):
            item = passing_item(db, lang, kind, day)
            tries = 0
            while item is None and draft and tries < ATTEMPTS:
                tries += 1
                d = draft_part(track, kind, day, lang, context=CallContext())
                drafting.store_draft(db, d, track)
                item = passing_item(db, lang, kind, day)
            if item is None:
                missing.append(f"{kind}:{day}")
            else:
                chosen.append(item)
        report["languages"][lang] = {"missing": missing}
        if not missing:
            for item in chosen:
                review.approve(db, item.item_id, *COACH)
            ready.append(lang)
    if not ready:
        report["published"] = False
        return report
    v = review.assemble_track_version(db, track, ready, *COACH)
    versions.coach_approve(db, v.id, *COACH)
    versions.officer_activate(db, v.id, *OFFICER)
    from services.pilot.storage import audio_store
    from services.speech.service import default_service

    cohort = publish.cohorts_for_error(track.error)[0]
    manifest = publish.publish_version(
        db, v.id, cohort, store=audio_store(), speech=default_service()
    )
    report.update(published=True, version=v.version, cohort=cohort, parts=len(manifest["parts"]))
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--languages", default="hi,en")
    p.add_argument(
        "--draft", action="store_true", help="re-draft parts that have no passing draft (spends)"
    )
    args = p.parse_args(argv)
    config.load_env()
    db = sessionmaker(make_engine(), expire_on_commit=False)()
    try:
        out = seed(
            db, [x.strip() for x in args.languages.split(",") if x.strip()], draft=args.draft
        )
    except NotAJudgeDeployment as exc:
        print(exc)
        return 2
    print(out)
    return 0 if out.get("published") else 1


if __name__ == "__main__":
    raise SystemExit(main())
