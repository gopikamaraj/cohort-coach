"""Tester tables and views. Coarse data only: no IP, location, contact, user-agent or typed content."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Engine, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from services.api.db import Base


def _now() -> datetime:
    return datetime.now(UTC)


class TesterDevice(Base):
    __tablename__ = "tester_device"

    user_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    nickname: Mapped[str] = mapped_column(String(30))
    nickname_public: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    app_version: Mapped[str] = mapped_column(String(20), default="")
    browser_family: Mapped[str] = mapped_column(String(20), default="other")
    os_family: Mapped[str] = mapped_column(String(20), default="other")
    device_class: Mapped[str] = mapped_column(String(10), default="phone")
    language: Mapped[str] = mapped_column(String(4), default="en")
    installed_pwa: Mapped[bool] = mapped_column(Boolean, default=False)
    invite_source: Mapped[str | None] = mapped_column(String(24), nullable=True)
    is_judge: Mapped[bool] = mapped_column(Boolean, default=False)
    is_team: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_stats: Mapped[bool] = mapped_column(Boolean, default=True)
    consent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class TesterEvent(Base):
    __tablename__ = "tester_event"
    __table_args__ = (
        Index("ix_tester_event_device_ts", "user_id", "ts"),
        Index("ix_tester_event_ts", "ts"),
    )

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    type: Mapped[str] = mapped_column(String(24))
    role: Mapped[str | None] = mapped_column(String(12), nullable=True)
    screen_id: Mapped[str | None] = mapped_column(String(48), nullable=True)
    tour_id: Mapped[str | None] = mapped_column(String(48), nullable=True)
    step_id: Mapped[str | None] = mapped_column(String(48), nullable=True)
    feature_id: Mapped[str | None] = mapped_column(String(48), nullable=True)
    value_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    connection_class: Mapped[str | None] = mapped_column(String(8), nullable=True)


class TesterFeedback(Base):
    __tablename__ = "tester_feedback"
    __table_args__ = (Index("ix_tester_feedback_device_ts", "user_id", "ts"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    role: Mapped[str | None] = mapped_column(String(12), nullable=True)
    screen_id: Mapped[str | None] = mapped_column(String(48), nullable=True)
    rating: Mapped[int] = mapped_column(Integer)
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)


class ChangeLog(Base):
    """The team's "You said, we changed" record, loaded from docs/YOU_SAID_WE_CHANGED.md."""

    __tablename__ = "change_log"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[str] = mapped_column(String(10), index=True)
    feedback_summary: Mapped[str] = mapped_column(Text)
    change_made: Mapped[str] = mapped_column(Text)
    commit_ref: Mapped[str | None] = mapped_column(String(40), nullable=True)


# Plain SQL views for anyone querying the database; the judge screen computes from the same tables.
_OK = "d.consent_stats AND NOT d.is_judge AND NOT d.is_team"
_DAY = "substr(CAST(e.ts AS TEXT), 1, 10)"
VIEWS: dict[str, str] = {
    "v_tester_summary": f"""
        SELECT d.user_id,
               COUNT(DISTINCT CASE WHEN e.type IN ('role_selected','view_as_role') THEN e.role END) AS roles_tried,
               SUM(CASE WHEN e.type = 'tour_completed' THEN 1 ELSE 0 END) AS tours_completed,
               COUNT(DISTINCT CASE WHEN e.type = 'screen_viewed' THEN e.screen_id END) AS screens_viewed,
               COUNT(DISTINCT CASE WHEN e.type = 'feature_used' THEN e.feature_id END) AS features_used,
               COUNT(DISTINCT e.session_id) AS sessions,
               MAX({_DAY}) AS last_seen_day
        FROM tester_device d LEFT JOIN tester_event e ON e.user_id = d.user_id
        WHERE {_OK} GROUP BY d.user_id""",
    "v_role_funnel": f"""
        SELECT 'selected' AS stage, COUNT(DISTINCT e.user_id) AS devices FROM tester_event e
          JOIN tester_device d ON d.user_id = e.user_id
          WHERE {_OK} AND e.type IN ('role_selected','view_as_role')
        UNION ALL
        SELECT 'screen', COUNT(DISTINCT e.user_id) FROM tester_event e
          JOIN tester_device d ON d.user_id = e.user_id
          WHERE {_OK} AND e.type = 'screen_viewed' AND e.screen_id NOT IN ('roles','judge')
        UNION ALL
        SELECT 'feature', COUNT(DISTINCT e.user_id) FROM tester_event e
          JOIN tester_device d ON d.user_id = e.user_id
          WHERE {_OK} AND e.type = 'feature_used'""",
    "v_tour_funnel": f"""
        SELECT e.type || ':' || COALESCE(e.step_id, '') AS stage, COUNT(DISTINCT e.user_id) AS devices
        FROM tester_event e JOIN tester_device d ON d.user_id = e.user_id
        WHERE {_OK} AND e.type IN ('tour_started','tour_step_viewed','tour_completed','tour_skipped')
        GROUP BY e.type, e.step_id""",
    "v_daily_activity": f"""
        SELECT {_DAY} AS day, COUNT(DISTINCT e.user_id) AS testers,
               COUNT(DISTINCT e.session_id) AS sessions, COUNT(*) AS events
        FROM tester_event e JOIN tester_device d ON d.user_id = e.user_id
        WHERE {_OK} GROUP BY {_DAY}""",
}


def ensure_tester_schema(engine: Engine) -> None:
    """Create the tester tables and (re)create the views. Idempotent."""
    tables = [m.__table__ for m in (TesterDevice, TesterEvent, TesterFeedback, ChangeLog)]
    Base.metadata.create_all(engine, tables=tables)  # type: ignore[arg-type]
    with engine.begin() as conn:
        for name, sql in VIEWS.items():
            conn.execute(text(f"DROP VIEW IF EXISTS {name}"))
            conn.execute(text(f"CREATE VIEW {name} AS {sql}"))
