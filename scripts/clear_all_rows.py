# ruff: noqa: E501
"""Delete every row from every table of the database DATABASE_URL points at. The tables stay.

    python scripts/clear_all_rows.py            (shows the counts, asks you to type the database name)
    python scripts/clear_all_rows.py --yes      (no question)

It is one transaction: if anything fails, nothing is deleted. Children first, so no foreign key is broken.
Postgres counters restart. The paper rules and other built-in rows are made again by the app the first time it
needs them. `.\\run-backend-cloud-db.ps1 -Clear` sets DATABASE_URL to the cloud database and runs this."""

from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import delete, func, inspect, select, text
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.api.db import make_engine  # noqa: E402
from services.api.seed import _all_tables  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--yes", action="store_true", help="skip the typed confirmation")
    args = ap.parse_args(argv)
    engine = make_engine()
    url = engine.url
    where = f"{url.host or 'local file'}:{url.port or ''}/{url.database}"  # never the password
    have = set(inspect(engine).get_table_names())
    tables = [t for t in _all_tables() if t.name in have]
    with Session(engine) as db:
        counts = {t.name: int(db.scalar(select(func.count()).select_from(t)) or 0) for t in tables}
        full = {k: v for k, v in counts.items() if v}
        print(f"Database: {where}")
        print(f"{len(full)} of {len(tables)} tables hold rows, {sum(full.values())} rows in all.")
        for name, n in sorted(full.items(), key=lambda kv: -kv[1])[:15]:
            print(f"  {name:28} {n}")
        if not full:
            print("Nothing to delete.")
            return 0
        if not args.yes:
            typed = input(f"Type the database name ({url.database}) to delete all {sum(full.values())} rows: ").strip()
            if typed != url.database:
                print("Cancelled: nothing was deleted.")
                return 1
        try:
            for table in reversed(tables):  # children first
                if counts[table.name]:
                    db.execute(delete(table))
            db.commit()
        except Exception as exc:
            db.rollback()
            print(f"Stopped, nothing was deleted: {exc}", file=sys.stderr)
            return 1
        if engine.dialect.name == "postgresql":
            for table in tables:
                pk = list(table.primary_key.columns)
                if len(pk) == 1 and str(pk[0].type).upper().startswith(("INT", "BIGINT", "SMALLINT")):
                    seq = db.execute(text("SELECT pg_get_serial_sequence(:t, :c)"), {"t": table.name, "c": pk[0].name}).scalar()
                    if seq:
                        db.execute(text("SELECT setval(:s, 1, false)"), {"s": seq})
            db.commit()
        left = sum(int(db.scalar(select(func.count()).select_from(t)) or 0) for t in tables)
        print(f"Deleted. Rows left: {left}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
