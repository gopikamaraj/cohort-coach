# ruff: noqa: E501
"""Run the daily module job once (06:00 Indian time, every day): `python tasks.py modules-due`.

Generates every improvement-track module that is due and still planned, with no feedback unless the
teacher gave some. Safe to run twice; catches up a missed day. Prints counts only.

  --now 2026-11-17T06:00:00+05:30   pretend it is this moment (for a check; default is the real time)
  --loop                            run again every day at 06:00 (a development fallback; in production
                                    use Cloud Scheduler, see docs/help/coach.md)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import sessionmaker  # noqa: E402

from services.api.db import Base, make_engine  # noqa: E402
from services.modules import jobs  # noqa: E402
from services.modules.service import IST, JOB_HOUR  # noqa: E402


def once(now: datetime) -> dict[str, object]:
    engine = make_engine()
    Base.metadata.create_all(engine)
    return jobs.run_due(sessionmaker(engine, expire_on_commit=False), now)


def seconds_to_next(now: datetime) -> float:
    local = now.astimezone(IST)
    nxt = local.replace(hour=JOB_HOUR, minute=0, second=0, microsecond=0)
    if nxt <= local:
        nxt += timedelta(days=1)
    return (nxt - local).total_seconds()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--now", help="an ISO time with offset, for a check")
    ap.add_argument("--loop", action="store_true")
    args = ap.parse_args()
    if args.now:
        print(json.dumps(once(datetime.fromisoformat(args.now))))
        return 0
    print(json.dumps(once(datetime.now(UTC))))
    while args.loop:
        time.sleep(seconds_to_next(datetime.now(UTC)))
        print(json.dumps(once(datetime.now(UTC))), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
