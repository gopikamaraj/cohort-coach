"""Draft a track with call 5: the cost estimate prints first, then (only if you ask) the drafts.

Usage:
  python scripts/batch_draft.py --track sub-sfl.v1 --languages hi,en --dry-run
  python scripts/batch_draft.py --track sub-sfl.v1 --languages en --sync --only lesson:1 --yes
  python scripts/batch_draft.py --track sub-sfl.v1 --languages hi,en --submit --yes
  python scripts/batch_draft.py --track sub-sfl.v1 --collect <batch id>

--dry-run (the default) prints the estimate and calls nothing. --sync drafts one part after
another with the live model (standard price) and stores what passes the gates in the review queue
for the coach. --submit sends a Message Batch (half price) and --collect gates and stores its
results. The batch request shape follows the Message Batches documentation but has not been run
live yet: use --sync for urgent drafts. Nothing here approves or publishes: the coach and then
the programme officer do that.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ai import config  # noqa: E402
from ai.calls.c05_track_draft import draft_part  # noqa: E402
from ai.client import CallContext  # noqa: E402
from services.content import drafting  # noqa: E402
from services.content.track import load_track  # noqa: E402


def _parse(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--track", default="sub-sfl.v1")
    p.add_argument("--languages", default="hi,en", help="comma separated: hi,en,ta")
    p.add_argument("--only", default="", help="one part, for example lesson:1 or model_lesson:0")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--sync", action="store_true")
    mode.add_argument("--submit", action="store_true")
    mode.add_argument("--collect", metavar="BATCH_ID")
    p.add_argument("--yes", action="store_true", help="do not ask before spending")
    return p.parse_args(argv)


def _confirm(args: argparse.Namespace) -> bool:
    if args.yes:
        return True
    return input("Go ahead and spend this? [y/N] ").strip().lower() == "y"


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    track = load_track(args.track)
    languages = [x.strip() for x in args.languages.split(",") if x.strip()]
    for language in languages:
        if language not in track.languages:
            print(f"The track has no language {language!r}.")
            return 2
    requests = drafting.build_requests(track, languages)
    if args.only:
        kind, _, day = args.only.partition(":")
        requests = [r for r in requests if r.kind == kind and str(r.day) == day]
        if not requests:
            print(f"No part matches {args.only!r}.")
            return 2

    live = args.sync or args.submit or bool(args.collect)
    if not args.collect:
        print(drafting.estimate(requests, batch=bool(args.submit)).summary())
    if not live:
        print("Dry run: nothing was called.")
        return 0

    config.load_env()
    from ai.audit import default_sink
    from services.api.db import make_engine

    sink = default_sink()
    from sqlalchemy.orm import sessionmaker

    db = sessionmaker(make_engine(), expire_on_commit=False)()

    if args.collect:
        return _collect(args, track, db)
    if not _confirm(args):
        print("Stopped. Nothing was called.")
        return 1
    if args.submit:
        return _submit(requests)

    mode = config.ai_mode()
    print(f"Drafting {len(requests)} parts synchronously (AI_MODE={mode}).")
    ctx = CallContext(sink=sink)
    spent = 0.0
    for r in requests:
        draft = draft_part(track, r.kind, r.day, r.language, context=ctx)
        stored = drafting.store_draft(db, draft, track)
        cost = draft.run.cost_usd if draft.run else 0.0
        spent += cost
        print(
            f"  {r.custom_id}: {draft.status}"
            f"{' (queued for the coach)' if stored else ''}  USD {cost:.3f}"
        )
        if draft.status != "needs_review":
            print(f"    {draft.explanation}")
    print(f"Done. Measured spend this run: USD {spent:.2f}.")
    return 0


def _submit(requests: list[drafting.BatchRequest]) -> int:
    import anthropic

    client = anthropic.Anthropic()
    batch = client.messages.batches.create(
        requests=[{"custom_id": r.custom_id, "params": r.params} for r in requests]  # type: ignore[misc]
    )
    print(
        f"Batch {batch.id} submitted ({len(requests)} requests). "
        f"Collect it with --collect {batch.id}."
    )
    return 0


def _collect(args: argparse.Namespace, track, db) -> int:  # type: ignore[no-untyped-def]
    import anthropic

    client = anthropic.Anthropic()
    batch = client.messages.batches.retrieve(args.collect)
    if batch.processing_status != "ended":
        print(f"Batch {args.collect} is {batch.processing_status}; try again later.")
        return 1
    results = []
    for entry in client.messages.batches.results(args.collect):
        if entry.result.type == "succeeded":
            text = "".join(b.text for b in entry.result.message.content if b.type == "text")
            results.append({"custom_id": entry.custom_id, "text": text})
    outcomes = drafting.ingest_results(db, track, results, context=CallContext())
    for cid, status in sorted(outcomes.items()):
        print(f"  {cid}: {status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
