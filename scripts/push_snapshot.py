# ruff: noqa: E501
"""Copy chosen tables from the local database over the same tables in another database (the cloud one).

    python scripts/push_snapshot.py --list
    python scripts/push_snapshot.py --tables paper,paper_item,paper_event --dry-run
    python scripts/push_snapshot.py --tables paper,paper_item,paper_event

The source is the local database (DATABASE_URL, else dev.sqlite). The target comes from the
TARGET_DATABASE_URL environment variable only, never from an argument or a file, so the password stays out of
shell history and git. For Cloud SQL start the Cloud SQL Auth Proxy first (docs/deploy.md, "Pushing a local
snapshot"). The replacement is one transaction: a failure leaves the target unchanged. Per-child sheet data is
never in these tables."""

from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.api.db import make_engine  # noqa: E402
from services.api.seed import SnapshotError, _all_tables, plan_replace, replace_tables  # noqa: E402


def _counts(db: Session, names: list[str]) -> dict[str, int | None]:
    have = set(inspect(db.get_bind()).get_table_names())
    tables = {t.name: t for t in _all_tables()}
    return {n: (db.scalar(select(func.count()).select_from(tables[n])) if n in have else None) for n in names}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tables", help="comma-separated table names to replace on the target")
    ap.add_argument("--list", action="store_true", help="list the tables and their local row counts")
    ap.add_argument("--dry-run", action="store_true", help="show what would be removed and copied, change nothing")
    ap.add_argument("--yes", action="store_true", help="skip the typed confirmation")
    args = ap.parse_args(argv)
    src_engine = make_engine()
    with Session(src_engine) as src:
        if args.list:
            for n, k in _counts(src, [t.name for t in _all_tables()]).items():
                print(f"{n:28} {'-' if k is None else k}")
            return 0
        if not args.tables:
            ap.error("give --tables, or --list")
        names = [n.strip() for n in args.tables.split(",") if n.strip()]
        target = os.environ.get("TARGET_DATABASE_URL")
        if not target:
            print("Set TARGET_DATABASE_URL to the cloud database URL first.", file=sys.stderr)
            return 2
        dst_engine = make_engine(target)
        if dst_engine.url == src_engine.url:
            print("The target is the same database as the source.", file=sys.stderr)
            return 2
        try:
            plan_replace(names)
        except SnapshotError as exc:
            print(f"Stopped: {exc}", file=sys.stderr)
            return 1
        with Session(dst_engine) as dst:
            if not set(names) <= set(inspect(dst_engine).get_table_names()):
                print("The target is missing some of these tables: start the app once on it so it makes them.", file=sys.stderr)
                return 1
            here, there = _counts(src, names), _counts(dst, names)
            print(f"{'table':28} {'local':>8} {'target now':>11}")
            for n in names:
                print(f"{n:28} {here[n]!s:>8} {there[n]!s:>11}")
            if args.dry_run:
                print("Dry run: nothing changed.")
                return 0
            if not args.yes and input("Type REPLACE to delete those target rows and copy the local ones: ").strip() != "REPLACE":
                print("Cancelled.")
                return 1
            try:
                done = replace_tables(src, dst, names)
            except SnapshotError as exc:
                print(f"Stopped: {exc}", file=sys.stderr)
                return 1
            for n, (gone, put) in done.items():
                print(f"{n}: removed {gone}, copied {put}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
