"""Tester API. Mounted only when TESTER_STATS=1 and not in pilot mode (see main.create_app).

Nothing here reads the caller's address, location or user-agent, and uvicorn's access line for these
paths is dropped (see `quiet_access_log`), so no IP reaches an application log from this feature.
"""

from __future__ import annotations

import csv
import hmac
import io
import logging
import os
import re
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.config import judge_mode
from ai.validators.pii import check_pii
from services.api.identity import user_of
from services.api.profiles import get_session
from services.api.ratelimit import RateLimiter
from services.tester.evidence import delete_device, evidence
from services.tester.models import TesterDevice, TesterEvent, TesterFeedback, ensure_tester_schema

router = APIRouter(prefix="/api", tags=["tester"])
_limit_events = RateLimiter("tester_events", 60)
_limit_other = RateLimiter("tester_other", 30)

HASH = r"^[0-9a-f]{64}$"  # unused since the user id replaced the device hash
SLUG = r"^[A-Za-z0-9_.:-]{1,48}$"
EVENT_TYPES = (
    "session_start", "session_end", "role_selected", "view_as_role", "screen_viewed", "tour_started",
    "tour_step_viewed", "tour_completed", "tour_skipped", "feature_used", "sample_input_run",
    "error_shown", "offline_session", "install_accepted",
)  # fmt: skip
TAGS = ("easy", "confusing", "useful", "slow", "voice_problem", "hard_to_read")
MAX_BATCH = 50
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
DIGITS = re.compile(r"(?<!\d)\+?\d(?:[\d\s().-]{5,}\d)(?!\d)")
_ready: set[int] = set()


def mask_contacts(text: str) -> str:
    """Hide phone numbers and email addresses in a comment before it is saved."""
    return DIGITS.sub("[number hidden]", EMAIL.sub("[email hidden]", text))


_BASE_SESSION = Depends(get_session)


def tester_session(db: Session = _BASE_SESSION) -> Session:
    engine = db.get_bind()
    if id(engine) not in _ready:
        ensure_tester_schema(engine)  # type: ignore[arg-type]
        _ready.add(id(engine))
    return db


SESSION = Depends(tester_session)


class ProfileIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    consent_stats: bool
    nickname: str = Field(min_length=1, max_length=30)
    nickname_public: bool = False
    app_version: str = Field("", max_length=20)
    browser_family: Literal["chrome", "safari", "firefox", "edge", "samsung", "other"] = "other"
    os_family: Literal["android", "ios", "windows", "macos", "linux", "other"] = "other"
    device_class: Literal["phone", "tablet", "desktop"] = "phone"
    language: Literal["en", "hi", "ta"] = "en"
    installed_pwa: bool = False
    invite_source: str | None = Field(None, pattern=r"^[a-z0-9-]{1,24}$")
    is_judge: bool = False
    team_token: str | None = Field(None, max_length=80)

    @field_validator("nickname")
    @classmethod
    def _plain_nickname(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("A nickname needs at least one character.")
        if check_pii(v) or EMAIL.search(v) or DIGITS.search(v):
            raise ValueError("A nickname must not hold a phone number, email or ID number.")
        return v


class EventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(pattern=r"^[A-Za-z0-9-]{8,64}$")
    session_id: str = Field(pattern=r"^[A-Za-z0-9-]{8,64}$")
    ts: int = Field(ge=1_700_000_000_000, le=4_000_000_000_000)  # milliseconds since 1970
    type: Literal[
        "session_start", "session_end", "role_selected", "view_as_role", "screen_viewed",
        "tour_started", "tour_step_viewed", "tour_completed", "tour_skipped", "feature_used",
        "sample_input_run", "error_shown", "offline_session", "install_accepted",
    ]  # fmt: skip
    role: Literal["teacher", "mentor", "coach", "officer", "admin", "judge"] | None = None
    screen_id: str | None = Field(None, pattern=SLUG)
    tour_id: str | None = Field(None, pattern=SLUG)
    step_id: str | None = Field(None, pattern=SLUG)
    feature_id: str | None = Field(None, pattern=SLUG)
    value: dict[str, str | int | bool] | None = None
    connection_class: Literal["offline", "slow", "fast"] | None = None

    @field_validator("value")
    @classmethod
    def _small_value(
        cls, v: dict[str, str | int | bool] | None
    ) -> dict[str, str | int | bool] | None:
        if v is None:
            return v
        if len(v) > 6 or any(len(k) > 24 for k in v):
            raise ValueError("value is too large")
        for x in v.values():
            if isinstance(x, str) and not re.fullmatch(r"[A-Za-z0-9_.:-]{0,32}", x):
                raise ValueError("value holds only short codes, never typed text")
        return v


class EventsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    events: list[EventIn] = Field(max_length=MAX_BATCH)


class FeedbackIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["teacher", "mentor", "coach", "officer", "admin", "judge"] | None = None
    screen_id: str | None = Field(None, pattern=SLUG)
    rating: int = Field(ge=1, le=5)
    tags: list[Literal["easy", "confusing", "useful", "slow", "voice_problem", "hard_to_read"]] = (
        Field(default_factory=list, max_length=3)
    )
    comment: str | None = Field(None, max_length=500)


def salt() -> str:
    return os.environ.get("TESTER_SALT") or "cc-tester-v1"


def retention_days() -> int:
    try:
        return max(1, int(os.environ.get("TESTER_RETENTION_DAYS") or 90))
    except ValueError:
        return 90


@router.get("/tester/config")
def config() -> dict[str, Any]:
    """Tells the app the feature is on, and the fixed salt it mixes into the device hash."""
    return {"enabled": True, "salt": salt(), "retention_days": retention_days()}


def _consented(db: Session, user_id: str) -> TesterDevice:
    row = db.get(TesterDevice, user_id)
    if row is None or not row.consent_stats:
        raise HTTPException(403, "Sharing is off for this device.")
    return row


@router.post("/tester/profile", dependencies=[Depends(_limit_other)])
def post_profile(body: ProfileIn, uid: str = Depends(user_of), db: Session = SESSION) -> dict[str, Any]:
    if not body.consent_stats:
        raise HTTPException(403, "Nothing is stored without consent.")
    team_token = os.environ.get("TESTER_TEAM_TOKEN", "")
    is_team = (
        bool(team_token)
        and body.team_token is not None
        and hmac.compare_digest(body.team_token, team_token)
    )
    now = datetime.now(UTC)
    row = db.get(TesterDevice, uid)
    if row is None:
        row = TesterDevice(user_id=uid, created_at=now, consent_at=now)
        db.add(row)
    row.consent_stats = True
    row.nickname = body.nickname
    row.nickname_public = body.nickname_public
    row.last_seen_at = now
    row.app_version = body.app_version
    row.browser_family = body.browser_family
    row.os_family = body.os_family
    row.device_class = body.device_class
    row.language = body.language
    row.installed_pwa = body.installed_pwa
    row.invite_source = body.invite_source or row.invite_source
    row.is_judge = row.is_judge or body.is_judge  # a tag, once set, is not cleared by the client
    row.is_team = row.is_team or is_team
    db.commit()
    return {"stored": True}


@router.post("/tester/events", dependencies=[Depends(_limit_events)])
def post_events(body: EventsIn, uid: str = Depends(user_of), db: Session = SESSION) -> dict[str, Any]:
    device = _consented(db, uid)
    ids = [e.event_id for e in body.events]
    have = (
        set(db.scalars(select(TesterEvent.event_id).where(TesterEvent.event_id.in_(ids))))
        if ids
        else set()
    )
    fresh = 0
    seen: set[str] = set()
    for e in body.events:
        if e.event_id in have or e.event_id in seen:
            continue
        seen.add(e.event_id)
        db.add(
            TesterEvent(
                event_id=e.event_id, user_id=uid, session_id=e.session_id,
                ts=datetime.fromtimestamp(e.ts / 1000, UTC), type=e.type, role=e.role,
                screen_id=e.screen_id, tour_id=e.tour_id, step_id=e.step_id, feature_id=e.feature_id,
                value_json=dict(e.value) if e.value else None, connection_class=e.connection_class,
            )
        )  # fmt: skip
        fresh += 1
    device.last_seen_at = datetime.now(UTC)
    db.commit()
    return {"accepted": fresh, "duplicates": len(body.events) - fresh}


@router.post("/tester/feedback", dependencies=[Depends(_limit_other)])
def post_feedback(body: FeedbackIn, uid: str = Depends(user_of), db: Session = SESSION) -> dict[str, Any]:
    _consented(db, uid)
    comment = mask_contacts(body.comment.strip()) if body.comment and body.comment.strip() else None
    db.add(
        TesterFeedback(
            user_id=uid, role=body.role, screen_id=body.screen_id, rating=body.rating,
            tags=list(dict.fromkeys(body.tags)), comment=comment,
        )
    )  # fmt: skip
    db.commit()
    return {"stored": True}


@router.delete("/tester/me")
def delete_me(uid: str = Depends(user_of), db: Session = SESSION) -> dict[str, Any]:
    return {"deleted": delete_device(db, uid)}


def _judge_only(x_role: str | None = Header(default=None)) -> None:
    if not judge_mode() or (x_role or "").lower() != "judge":
        raise HTTPException(403, "The Testing evidence view is for the judge role in the demo.")


@router.get("/judge/testing-evidence", dependencies=[Depends(_judge_only)])
def testing_evidence(include_flagged: bool = Query(False), db: Session = SESSION) -> dict[str, Any]:
    return evidence(db, include_flagged)


def _team_only(x_team_token: str | None = Header(default=None)) -> None:
    expected = os.environ.get("TESTER_TEAM_TOKEN", "")
    if not expected or x_team_token is None or not hmac.compare_digest(x_team_token, expected):
        raise HTTPException(403, "A team token is needed.")


@router.get("/team/testing-export", dependencies=[Depends(_team_only)])
def testing_export(db: Session = SESSION) -> Response:
    """CSV of feedback with comments, for the team's analysis. A tester is a running number, never an id."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        ["date", "tester", "is_judge", "is_team", "role", "screen", "rating", "tags", "comment"]
    )
    devs = {d.user_id: d for d in db.scalars(select(TesterDevice))}
    for f in db.scalars(select(TesterFeedback).order_by(TesterFeedback.ts)):
        d = devs.get(f.user_id)
        w.writerow(
            [
                f.ts.date().isoformat(),
                list(devs).index(f.user_id) + 1 if f.user_id in devs else 0,
                bool(d and d.is_judge),
                bool(d and d.is_team),
                f.role,
                f.screen_id,
                f.rating,
                ";".join(f.tags or []),
                f.comment or "",
            ]
        )
    return Response(buf.getvalue(), media_type="text/csv")


def run_retention(db: Session) -> dict[str, int]:
    from services.tester.evidence import purge_older_than

    return purge_older_than(db, datetime.now(UTC), retention_days())


class _DropTesterAccess(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return (
            "/api/tester" not in record.getMessage()
            and "/api/team/testing" not in record.getMessage()
        )


def quiet_access_log() -> None:
    """uvicorn's access line carries the caller's address; drop it for the tester paths."""
    log = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, _DropTesterAccess) for f in log.filters):
        log.addFilter(_DropTesterAccess())
