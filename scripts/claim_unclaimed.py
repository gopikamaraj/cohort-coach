# ruff: noqa: E501
"""Hand rows that the identity migration could not map (owner `unclaimed:<old id>`) to a real user.

    python scripts/claim_unclaimed.py --list
    python scripts/claim_unclaimed.py --from unclaimed:0524d3a1b2c3d4e5 --to "3A Math"      dry run
    python scripts/claim_unclaimed.py --from unclaimed:0524d3a1b2c3d4e5 --to "3A Math" --apply

The user must already exist (she registers a nickname in the app first). Nothing is deleted: rows only change
owner. If the user already has a document with the same id, the user's own copy is kept and the unclaimed
one stays under its owner and is reported."""

from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import text

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.migrate_identity import TEACHER_COLS, Plan, has, rekey  # noqa: E402
from services.api.db import make_engine  # noqa: E402
from services.api.identity import normalise  # noqa: E402

OWNER_COLS = [("profile_sync", "owner"), ("kept_sheet", "owner"), ("consents", "subject_id")]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--from", dest="old")
    ap.add_argument("--to")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    engine = make_engine()
    with engine.connect() as conn:
        if args.list or not (args.old and args.to):
            for t, c in [("user_docs", "owner"), ("teachers", "teacher_id"), ("consents", "subject_id"), ("profile_sync", "owner"), ("kept_sheet", "owner"), ("class_cohorts", "teacher_id")]:
                if has(conn, t):
                    for owner, k in conn.execute(text(f"SELECT {c}, count(*) FROM {t} WHERE {c} LIKE 'unclaimed:%' GROUP BY {c}")):
                        print(f"{t:14s} {owner:34s} {k}")
            return 0
        uid = normalise(args.to)
        if not conn.execute(text("SELECT 1 FROM users WHERE id=:u"), {"u": uid}).first():
            print(f"No user '{uid}'. She registers that nickname in the app first.")
            return 1
        trans = conn.begin()
        plan = Plan()
        # documents: a user's own copy wins
        clash = conn.execute(text("SELECT count(*) FROM user_docs a JOIN user_docs b ON a.collection=b.collection AND a.doc_id=b.doc_id WHERE a.owner=:o AND b.owner=:u"), {"o": args.old, "u": uid}).scalar_one()
        moved = conn.execute(text("UPDATE user_docs SET owner=:u WHERE owner=:o AND NOT EXISTS (SELECT 1 FROM user_docs b WHERE b.owner=:u AND b.collection=user_docs.collection AND b.doc_id=user_docs.doc_id)"), {"u": uid, "o": args.old}).rowcount
        print(f"user_docs: {moved} moved, {clash} left (the user already has a document with that id)")
        for t, c in OWNER_COLS + TEACHER_COLS:
            rekey(conn, plan, t, c, args.old, uid)
        for k, v in sorted(plan.counts.items()):
            print(f"{k}: {v}")
        if args.apply:
            trans.commit()
            print("Done.")
        else:
            trans.rollback()
            print("Dry run: nothing changed. Add --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
