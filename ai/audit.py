"""The audit trail: one row per AI call (table `ai_calls`), metadata only.

Rows hold ids, hashes, token counts, cost, latency and validator codes. They never hold prompt
text, teacher text or model output, so the trail is safe to show to judges.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from functools import cache
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from services.api.db import AiCall, Base, make_engine


class SqlAuditSink:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._factory = session_factory

    def write(self, **fields: Any) -> int:
        with self._factory() as s:
            row = AiCall(**fields)
            s.add(row)
            s.commit()
            return row.id

    def update(self, audit_id: int, **fields: Any) -> None:
        with self._factory() as s:
            row = s.get(AiCall, audit_id)
            if row is None:
                raise KeyError(f"no audit row {audit_id}")
            for k, v in fields.items():
                setattr(row, k, v)
            s.commit()

    def spend_total(self, *, judge: bool | None = None) -> float:
        """USD spent so far. judge=None counts all traffic, True judge only, False non-judge."""
        q = select(func.coalesce(func.sum(AiCall.cost_usd), 0.0))
        if judge is not None:
            q = q.where(AiCall.judge == judge)
        with self._factory() as s:
            return float(s.execute(q).scalar_one())

    def spend_day(self, day: date, *, judge: bool | None = None) -> float:
        start = datetime(day.year, day.month, day.day, tzinfo=UTC)
        q = select(func.coalesce(func.sum(AiCall.cost_usd), 0.0)).where(
            AiCall.created_at >= start, AiCall.created_at < _next_day(start)
        )
        if judge is not None:
            q = q.where(AiCall.judge == judge)
        with self._factory() as s:
            return float(s.execute(q).scalar_one())

    def recent(self, limit: int = 50) -> list[AiCall]:
        with self._factory() as s:
            rows = s.execute(select(AiCall).order_by(AiCall.id.desc()).limit(limit)).scalars()
            out = list(rows)
            s.expunge_all()
            return out


def _next_day(start: datetime) -> datetime:
    from datetime import timedelta

    return start + timedelta(days=1)


@cache
def default_sink() -> SqlAuditSink:
    """Sink on DATABASE_URL (SQLite by default). Creates the tables if they are missing."""
    engine = make_engine()
    Base.metadata.create_all(engine)
    return SqlAuditSink(sessionmaker(engine, expire_on_commit=False))
