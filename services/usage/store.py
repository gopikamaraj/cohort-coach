# ruff: noqa: E501
"""The shared store: the app's own database (SQLite locally, Postgres on Cloud Run), which every instance
uses. Entries are separate rows, so parallel inserts cannot overwrite each other; the in-flight counter
is changed with one atomic UPDATE. Rows older than 24 hours are removed as new ones are written."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from services.usage import models
from services.usage.models import UsageAction

TTL = timedelta(hours=24)
_lock = threading.Lock()
_factory: sessionmaker[Session] | None = None
_last_purge = 0.0


def factory() -> sessionmaker[Session]:
    global _factory
    with _lock:
        if _factory is None:
            from services.api.db import Base, make_engine

            engine = make_engine()
            Base.metadata.create_all(engine)
            _factory = sessionmaker(engine, expire_on_commit=False)
        return _factory


def set_factory(f: sessionmaker[Session] | None) -> None:
    """Tests point the ledger at their own database."""
    global _factory, _last_purge
    with _lock:
        _factory = f
        _last_purge = 0.0


def purge(db: Session) -> None:
    cutoff = datetime.now(UTC) - TTL
    db.execute(delete(models.UsageEntry).where(models.UsageEntry.started_at < cutoff))
    db.execute(delete(UsageAction).where(UsageAction.created_at < cutoff))


def maybe_purge(db: Session, now: Callable[[], float] = time.monotonic) -> None:
    global _last_purge
    t = now()
    if t - _last_purge > 600:
        _last_purge = t
        purge(db)


def open_action(db: Session, action_id: str, name: str) -> None:
    """Make the action row if it is new, then count one more request in flight (atomic)."""
    if db.get(UsageAction, action_id) is None:
        try:
            db.add(UsageAction(id=action_id, name=name[:40]))
            db.commit()
        except IntegrityError:  # another instance made it first
            db.rollback()
    db.execute(
        update(UsageAction)
        .where(UsageAction.id == action_id)
        .values(inflight=UsageAction.inflight + 1, updated_at=datetime.now(UTC))
    )
    db.commit()


def close_action(db: Session, action_id: str) -> None:
    db.execute(
        update(UsageAction)
        .where(UsageAction.id == action_id)
        .values(inflight=UsageAction.inflight - 1, updated_at=datetime.now(UTC))
    )
    db.commit()
