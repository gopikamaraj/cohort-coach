"""The coach's chat settings: how long a question waits for a person, and whether the AI may answer.

Only the coach role changes them. The timeout is a whole number of hours from 1 to 168, checked on
the server (default 24). A cohort's own setting beats the global default. A question's due time is
worked out and stored when it is asked (`due_at`), so changing a setting never moves a question that
is already waiting. Auto-send is off until a coach turns it on. Every change is audited.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from services.api.cohorts import lifecycle
from services.api.db import ChatConfig

DEFAULT_TIMEOUT_HOURS = 24
MIN_TIMEOUT_HOURS = 1
MAX_TIMEOUT_HOURS = 168
DAILY_AI_REPLY_LIMIT = 3  # per teacher per day: a ceiling on what the AI may send on its own
GLOBAL = "global"


class ChatConfigError(ValueError):
    """A setting outside its range, or not a whole number."""


@dataclass(frozen=True)
class Effective:
    timeout_hours: int
    auto_send: bool
    source: str  # cohort | global | default


def effective(db: Session, cohort_id: str) -> Effective:
    for key, source in ((cohort_id, "cohort"), (GLOBAL, "global")):
        row = db.get(ChatConfig, key)
        if row is not None:
            return Effective(row.ai_timeout_hours, row.ai_auto_send_enabled, source)
    return Effective(DEFAULT_TIMEOUT_HOURS, False, "default")


def due_at(db: Session, cohort_id: str, now: datetime) -> datetime:
    """When a question asked now may be answered by the AI. Fixed at that moment."""
    return now + timedelta(hours=effective(db, cohort_id).timeout_hours)


def _check_hours(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ChatConfigError("The timeout must be a whole number of hours.")
    if not MIN_TIMEOUT_HOURS <= value <= MAX_TIMEOUT_HOURS:
        raise ChatConfigError(
            f"The timeout must be between {MIN_TIMEOUT_HOURS} and {MAX_TIMEOUT_HOURS} hours."
        )
    return value


def set_config(
    db: Session,
    *,
    role: str,
    actor: str,
    cohort_id: str | None = None,
    timeout_hours: object = None,
    auto_send: bool | None = None,
) -> Effective:
    """Change a setting for one cohort (cohort_id) or for all (None). Coach only. The cohort must be
    one she is assigned to. Anything not given keeps its current value."""
    if role != "coach":
        raise lifecycle.NotAllowed("Only the coach can change the chat settings.")
    key = GLOBAL
    if cohort_id is not None:
        lifecycle.require_assigned(lifecycle.get(db, cohort_id), "coach", actor)
        key = cohort_id
    current = effective(db, cohort_id or "")
    hours = current.timeout_hours if timeout_hours is None else _check_hours(timeout_hours)
    enabled = current.auto_send if auto_send is None else bool(auto_send)
    row = db.get(ChatConfig, key)
    if row is None:
        row = ChatConfig(
            id=key,
            scope="global" if key == GLOBAL else "cohort",
            cohort_id=cohort_id,
            ai_timeout_hours=hours,
            ai_auto_send_enabled=enabled,
            set_by=actor,
        )
        db.add(row)
    else:
        row.ai_timeout_hours, row.ai_auto_send_enabled, row.set_by = hours, enabled, actor
        row.set_at = datetime.now(UTC)
    lifecycle.audit(db, key, "coach", actor, "chat_config", timeout_hours=hours, auto_send=enabled)
    db.commit()
    return effective(db, cohort_id or "")
