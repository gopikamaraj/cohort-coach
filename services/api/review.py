"""The review queue and the two keys over HTTP (screen P3).

Reading the queue is for the coach and the officer; approving or returning a draft is the coach's
key; switching approved content on is the officer's. The role comes from the server's session
(see services/api/roles), never from the request body. This router is not mounted in pilot mode.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.client import CallContext
from services.api.db import ContentAudit, ContentVersion
from services.api.practice import AI_CONTEXT
from services.api.profiles import SESSION
from services.api.roles import require
from services.content import configurable, rejections, review, versions
from services.content.track import load_track

router = APIRouter(prefix="/api/review", tags=["review"])

VIEW = Depends(require("content.review_view"))
COACH = Depends(require("content.coach_approve"))
OFFICER = Depends(require("content.officer_activate"))
MENTOR = Depends(require("content.mentor_approve"))
PROPOSE = Depends(require("content.propose"))


def _actor(role: str) -> str:
    """The pseudonymous id of the person acting. Real assignment arrives with P12; until then the
    demo has one per role, and an id never carries a name."""
    return f"{role}-demo"


def _call(fn: Any, *args: Any, **kwargs: Any) -> Any:
    try:
        return fn(*args, **kwargs)
    except versions.NotAllowed as exc:
        raise HTTPException(403, str(exc)) from exc
    except versions.BadState as exc:
        raise HTTPException(409, str(exc)) from exc
    except review.EditBlocked as exc:
        raise HTTPException(422, {"codes": exc.codes, "explanation": exc.explanation}) from exc
    except (configurable.OutOfRange, configurable.NotConfigurable, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc


def _version(v: ContentVersion) -> dict[str, Any]:
    return {
        "id": v.id,
        "content_type": v.content_type,
        "content_id": v.content_id,
        "version": v.version,
        "status": v.status,
        "parent_version": v.parent_version,
        "content_hash": v.content_hash,
        "coach_approved_by": v.coach_approved_by,
        "officer_activated_by": v.officer_activated_by,
        "body": v.body,
    }


# ---- items ------------------------------------------------------------------------------------


@router.get("/items")
def items(status: str | None = None, _: str = VIEW, db: Session = SESSION) -> list[dict[str, Any]]:
    return [asdict(i) for i in review.list_items(db, status=status)]


@router.get("/items/{item_id}")
def item(item_id: str, _: str = VIEW, db: Session = SESSION) -> dict[str, Any]:
    return asdict(_call(review.get_item, db, item_id))


class EditIn(BaseModel):
    script: str = Field(min_length=1, max_length=12000)


@router.post("/items/{item_id}/edit")
def item_edit(
    item_id: str,
    body: EditIn,
    role: str = COACH,
    db: Session = SESSION,
    ctx: CallContext = AI_CONTEXT,
) -> dict[str, Any]:
    return asdict(
        _call(review.save_edit, db, item_id, body.script, _actor(role), role, context=ctx)
    )


@router.post("/items/{item_id}/approve")
def item_approve(item_id: str, role: str = COACH, db: Session = SESSION) -> dict[str, Any]:
    return asdict(_call(review.approve, db, item_id, _actor(role), role))


class RejectIn(BaseModel):
    reason: str
    note: str = Field(default="", max_length=300)


@router.post("/items/{item_id}/reject")
def item_reject(
    item_id: str, body: RejectIn, role: str = COACH, db: Session = SESSION
) -> dict[str, Any]:
    return asdict(
        _call(review.reject, db, item_id, _actor(role), role, reason=body.reason, note=body.note)
    )


@router.post("/items/{item_id}/mentor-approve")
def item_mentor_approve(item_id: str, role: str = MENTOR, db: Session = SESSION) -> dict[str, Any]:
    return asdict(_call(review.mentor_approve, db, item_id, _actor(role), role))


@router.get("/stats")
def stats(_: str = VIEW, db: Session = SESSION) -> dict[str, Any]:
    return asdict(review.stats(db))


# ---- track versions: the two keys -------------------------------------------------------------


class AssembleIn(BaseModel):
    languages: list[str] = Field(min_length=1, max_length=3)


@router.post("/tracks/{track_id}/assemble")
def assemble(
    track_id: str, body: AssembleIn, role: str = PROPOSE, db: Session = SESSION
) -> dict[str, Any]:
    try:
        track = load_track(track_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, "That track does not exist.") from exc
    return _version(
        _call(review.assemble_track_version, db, track, body.languages, _actor(role), role)
    )


@router.get("/versions")
def list_versions(
    content_type: str = "track", _: str = VIEW, db: Session = SESSION
) -> list[dict[str, Any]]:
    rows = db.execute(
        select(ContentVersion)
        .where(ContentVersion.content_type == content_type)
        .order_by(ContentVersion.content_id, ContentVersion.version)
    ).scalars()
    return [_version(v) for v in rows]


@router.post("/versions/{version_id}/approve")
def version_approve(version_id: str, role: str = COACH, db: Session = SESSION) -> dict[str, Any]:
    return _version(_call(versions.coach_approve, db, version_id, _actor(role), role))


class ReturnIn(BaseModel):
    reason: str = Field(max_length=40)


@router.post("/versions/{version_id}/return")
def version_return(
    version_id: str, body: ReturnIn, role: str = COACH, db: Session = SESSION
) -> dict[str, Any]:
    return _version(
        _call(versions.return_to_draft, db, version_id, _actor(role), role, reason=body.reason)
    )


@router.post("/versions/{version_id}/activate")
def version_activate(version_id: str, role: str = OFFICER, db: Session = SESSION) -> dict[str, Any]:
    return _version(_call(versions.officer_activate, db, version_id, _actor(role), role))


@router.post("/versions/{version_id}/retire")
def version_retire(version_id: str, role: str = OFFICER, db: Session = SESSION) -> dict[str, Any]:
    return _version(_call(versions.retire, db, version_id, _actor(role), role))


# ---- settings ---------------------------------------------------------------------------------


@router.get("/settings")
def settings(_: str = VIEW, db: Session = SESSION) -> dict[str, Any]:
    pending = {
        v.content_id: _version(v)
        for v in db.execute(
            select(ContentVersion).where(
                ContentVersion.content_type == configurable.SETTING_TYPE,
                ContentVersion.status.in_(("in_review", "approved")),
            )
        ).scalars()
    }
    return {
        "settings": [
            {
                "key": s.key,
                "unit": s.unit,
                "low": s.low,
                "high": s.high,
                "default": s.default,
                "value": configurable.effective_value(db, s.key),
                "proposed": pending.get(s.key),
            }
            for s in configurable.CONFIGURABLE.values()
        ],
        "fixed": [{"key": k, "rule": v} for k, v in configurable.FIXED.items()],
    }


class SettingIn(BaseModel):
    key: str
    value: int | str | bool | None


@router.post("/settings")
def propose_setting(body: SettingIn, role: str = PROPOSE, db: Session = SESSION) -> dict[str, Any]:
    return _version(_call(configurable.propose, db, body.key, body.value, _actor(role), role))


# ---- audit ------------------------------------------------------------------------------------


@router.get("/audit")
def audit(limit: int = 100, _: str = VIEW, db: Session = SESSION) -> list[dict[str, Any]]:
    rows = db.execute(
        select(ContentAudit).order_by(ContentAudit.id.desc()).limit(min(max(limit, 1), 500))
    ).scalars()
    return [
        {
            "at": r.at.isoformat(),
            "role": r.role,
            "actor": r.actor,
            "action": r.action,
            "content_type": r.content_type,
            "content_id": r.content_id,
            "version": r.version,
            "detail": r.detail,
        }
        for r in rows
    ]


# ---- rejections that may become checker examples ---------------------------------------------


@router.get("/rejections")
def pending_rejections(_: str = VIEW) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in rejections.list_pending():
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        out.append(
            {
                "name": path.stem,
                "reason": data["reason"],
                "language": data["language"],
                "text": data["text"],
                "note": data.get("note", ""),
            }
        )
    return out


class PromoteIn(BaseModel):
    text: str | None = Field(default=None, max_length=4000)


def _pending(name: str) -> Any:
    try:
        return rejections.find_pending(name)
    except FileNotFoundError as exc:
        raise HTTPException(404, "That example is not waiting.") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/rejections/{name}/promote")
def promote_rejection(name: str, body: PromoteIn, role: str = COACH) -> dict[str, str]:
    """Use as checker example: call 7 will be shown it from the next check on."""
    saved = _call(rejections.promote, _pending(name), text=body.text)
    return {"saved": saved.name}


@router.post("/rejections/{name}/discard")
def discard_rejection(name: str, role: str = COACH) -> dict[str, str]:
    rejections.discard(_pending(name))
    return {"discarded": name}
