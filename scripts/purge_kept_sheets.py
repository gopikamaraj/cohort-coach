"""Delete kept answer sheets whose 60 days have passed (never one before).

    python scripts/purge_kept_sheets.py

The API also sweeps whenever a sheet is kept or listed; run this daily as well (Cloud Scheduler,
cron), so sheets go on time even when nobody opens the app. Needs DATABASE_URL and the sheets
bucket (GCS_SHEETS_BUCKET) like the API. Prints how many sheets it deleted; never prints a key.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import sessionmaker  # noqa: E402

from ai.config import load_env  # noqa: E402
from services.api.db import make_engine  # noqa: E402
from services.sheets_keep.api import get_store, purge_expired  # noqa: E402


def main() -> int:
    load_env()
    store = get_store()
    if store is None:
        print("No sheets bucket is set (GCS_SHEETS_BUCKET): nothing to delete.")
        return 0
    with sessionmaker(make_engine())() as db:
        print(f"deleted {purge_expired(db, store)} kept sheet(s) past their retention")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
