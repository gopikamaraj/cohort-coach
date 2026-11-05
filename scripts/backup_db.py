"""Copy every row of every table of DATABASE_URL into one gzip file of JSON lines, for a backup before a migration.

    python scripts/backup_db.py [out-file]      (default: backups/<database>-<time>.jsonl.gz)

Read-only: it only runs SELECTs. It prints table names and row counts, never a row. backups/ is not committed.
Restore is by hand (each line is {"table": ..., "row": {...}}; bytes are base64 under {"__b64__": ...})."""

from __future__ import annotations

import base64
import datetime as dt
import decimal
import gzip
import json
import os
import sys
import uuid
from pathlib import Path

from sqlalchemy import MetaData, select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.api.db import make_engine  # noqa: E402


def _plain(v: object) -> object:
    if isinstance(v, bytes | bytearray | memoryview):
        return {"__b64__": base64.b64encode(bytes(v)).decode()}
    if isinstance(v, dt.datetime | dt.date | dt.time):
        return v.isoformat()
    if isinstance(v, decimal.Decimal | uuid.UUID):
        return str(v)
    return v


def main() -> None:
    engine = make_engine()
    meta = MetaData()
    meta.reflect(bind=engine)
    name = engine.url.database or "db"
    default = Path(__file__).resolve().parents[1] / "backups" / f"{Path(name).stem}-{dt.datetime.now():%Y%m%d-%H%M%S}.jsonl.gz"
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else default
    out.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with engine.connect() as conn, gzip.open(out, "wt", encoding="utf-8") as f:
        for table in meta.sorted_tables:
            n = 0
            for row in conn.execute(select(table)).mappings():
                f.write(json.dumps({"table": table.name, "row": {k: _plain(v) for k, v in row.items()}}, ensure_ascii=False) + "\n")
                n += 1
            total += n
            print(f"{table.name}: {n}")
    print(f"backup: {out} ({out.stat().st_size // 1024} KB, {total} rows, {len(meta.sorted_tables)} tables)")


if __name__ == "__main__":
    main()
