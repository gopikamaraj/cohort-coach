"""Small shared pieces: the audit row, the settings table, and the code formats.

Codes (school, class, teacher) are short pseudonymous labels the programme made up. They are
checked for shape here so that a sentence, a name with spaces or an email cannot be saved as one.
This is a guard, not a guarantee: the page tells the coordinator to use codes, never names.
"""

from __future__ import annotations

import os
import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ai.config import pilot_audio_max
from services.api.db import PilotAudit, PilotConfig

CODE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{1,23}$")
CLASS_CODE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,11}$")
CONSENT_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ./_-]{2,59}$")
LANGUAGES = ("en", "hi", "ta")

DEFAULT_AUDIO_COUNT = 3
DEFAULT_RETENTION_DAYS = 90
MIN_RETENTION_DAYS = 7
MAX_RETENTION_DAYS = 365


def audit(db: Session, actor: str, action: str, target: str = "", **detail: Any) -> None:
    """One audit row. `detail` holds ids and counts only; never a name, a script or a photo."""
    db.add(PilotAudit(actor=actor, action=action, target=target, detail=detail))
    db.commit()


def get_setting(db: Session, key: str, default: Any) -> Any:
    row = db.get(PilotConfig, key)
    return row.value if row is not None else default


def set_setting(db: Session, key: str, value: Any, actor: str) -> None:
    row = db.get(PilotConfig, key)
    if row is None:
        db.add(PilotConfig(key=key, value=value, updated_by=actor))
    else:
        row.value = value
        row.updated_by = actor
    db.flush()


def audio_count(db: Session) -> int:
    """The number of audio files asked for, kept inside 1..PILOT_AUDIO_MAX even if the maximum
    was lowered after it was saved."""
    value = int(get_setting(db, "audio_count", DEFAULT_AUDIO_COUNT))
    return max(1, min(value, pilot_audio_max()))


def retention_days(db: Session) -> int:
    default = int(os.environ.get("PILOT_RETENTION_DAYS") or DEFAULT_RETENTION_DAYS)
    return int(get_setting(db, "retention_days", default))


def check_code(value: str, what: str, pattern: re.Pattern[str] = CODE) -> str:
    value = value.strip()
    if not pattern.match(value):
        raise HTTPException(
            422, f"The {what} must be a short code (letters, digits and dashes), not a name."
        )
    return value
