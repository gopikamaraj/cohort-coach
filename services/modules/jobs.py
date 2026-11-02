# ruff: noqa: E501
"""The daily job: `python tasks.py modules-due`, run every day at 06:00 Indian time.

For every active track it generates each module that is due (due date on or before the job's day), in
order. A module whose teacher gave feedback uses the real branch; one with none uses `no_feedback`,
and the record says so: silence is never read as success. A missed day is caught up on the next run.
It is safe to run twice. A failure is retried with a growing wait; if it still fails the module is
marked (`failures`) and the coach is told. The clock and the sleep are passed in so tests control them.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from services.modules import library, service, states
from services.modules.models import ModuleEvent, Track, TrackModule

log = logging.getLogger(__name__)
ATTEMPTS = 3


def run_due(
    factory: sessionmaker[Session],
    now: datetime,
    *,
    sleep: Callable[[float], None] = time.sleep,
    attempts: int = ATTEMPTS,
) -> dict[str, Any]:
    """One run. Returns counts only: modules made, failures, tracks closed, coach flags."""
    day = service.job_day(now)
    out = {
        "day": day.isoformat(),
        "generated": 0,
        "failed": 0,
        "closed": 0,
        "flagged": 0,
        "stopped": 0,
    }
    with factory() as db:
        ids = list(db.execute(select(Track.id).where(Track.status == "active")).scalars())
    for track_id in ids:
        _track(factory, track_id, day, now, sleep, attempts, out)
    return out


def _track(
    factory: sessionmaker[Session],
    track_id: str,
    day: Any,
    now: datetime,
    sleep: Callable[[float], None],
    attempts: int,
    out: dict[str, Any],
) -> None:
    while True:
        with factory() as db:
            track = db.get(Track, track_id)
            if track is None or track.status != "active":
                return
            rows = service.modules_of(db, track_id)
            nxt = next((m for m in rows if m.status == states.PLANNED), None)
            if nxt is None or nxt.due_date > day:
                break
            number = nxt.number
        with (
            factory() as db
        ):  # a held module (not tried) is deferred again before the planned one is made
            if service.maybe_defer(db, track_id, number, now):
                continue
        made = _generate_with_retry(factory, track_id, number, now, sleep, attempts, out)
        if not made:
            return  # still failing: the coach was told; the next run tries again
    with factory() as db:
        track = db.get(Track, track_id)
        if track is None or track.status != "active":
            return
        rows = service.modules_of(db, track_id)
        if day > track.end_date and not any(m.status == states.PLANNED for m in rows):
            for m in rows:
                if m.status == states.PLANNED:
                    m.status = states.SKIPPED
            track.status, track.stop_reason = "completed", "end_date"
            service._event(
                db, track, "track_stopped", "system", now, reason="end_date", trigger="due_date"
            )
            db.commit()
            out["closed"] += 1
        out["flagged"] += _flag_no_download(db, track, rows, now)


def _generate_with_retry(
    factory: sessionmaker[Session],
    track_id: str,
    number: int,
    now: datetime,
    sleep: Callable[[float], None],
    attempts: int,
    out: dict[str, Any],
) -> bool:
    for attempt in range(attempts):
        try:
            with factory() as db:
                got = service.generate_module(db, track_id, number, "due_date", now)
            if got.module is None and got.stop:
                out["stopped"] += 1
            elif got.created:
                out["generated"] += 1
            return True
        except Exception:  # noqa: BLE001 - a failed module must not stop the other tracks
            log.warning(
                "modules: generating %s #%s failed (try %s)",
                track_id,
                number,
                attempt + 1,
                exc_info=True,
            )
            if attempt + 1 < attempts:
                sleep(2**attempt)
    with factory() as db:
        track = db.get(Track, track_id)
        row = db.execute(
            select(TrackModule).where(
                TrackModule.track_id == track_id, TrackModule.number == number
            )
        ).scalar_one_or_none()
        if track is not None:
            if row is not None:
                row.failures = (row.failures or 0) + 1
            service._event(db, track, "generate_failed", "system", now, row, number=number)
            service._event(
                db, track, "coach_notified", "system", now, row, reason="generate_failed"
            )
            db.commit()
    out["failed"] += 1
    return False


def _flag_no_download(db: Session, track: Track, rows: list[TrackModule], now: datetime) -> int:
    """A module made N days ago that was never downloaded is flagged to the coach once."""
    flagged = 0
    for m in service._generated(rows):
        if m.audio_ref or m.generated_at is None or m.status != states.READY:
            continue
        generated = (
            m.generated_at if m.generated_at.tzinfo else m.generated_at.replace(tzinfo=now.tzinfo)
        )
        if now - generated < timedelta(days=library.no_download_days()):
            continue
        done = db.execute(
            select(ModuleEvent.id).where(
                ModuleEvent.module_id == m.id, ModuleEvent.event == "no_download_flag"
            )
        ).first()
        if done is None:
            service._event(
                db, track, "no_download_flag", "system", now, m, days=library.no_download_days()
            )
            flagged += 1
    if flagged:
        db.commit()
    return flagged
