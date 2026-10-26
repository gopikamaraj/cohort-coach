"""Content versions and the two keys (addendum v3.1 section D).

    draft -> in_review -> approved -> active -> retired

The coach's approval is gate 3 (`coach_approve`); the programme officer's activation switches the
content on for the block (`officer_activate`). Neither alone publishes. A body never changes once
written: an edit makes a new version, and the version in use stays in use until the new one is
active. Every step writes an audit row (role, pseudonymous id, action, version).

Roles are passed in by the caller, which got them from the server's session (never from the
request body). One person may hold both roles; each step is still a separate action.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from services.api.db import ContentAudit, ContentVersion

__all__ = [
    "BadState",
    "ContentVersion",
    "NotAllowed",
    "active_version",
    "body_hash",
    "coach_approve",
    "create_draft",
    "edit",
    "officer_activate",
    "retire",
    "return_to_draft",
    "submit_for_review",
]

STATUSES = ("draft", "in_review", "approved", "active", "retired")
EDITOR_ROLES = ("coach", "officer", "system")


class NotAllowed(PermissionError):
    """The role may not take this step."""


class BadState(ValueError):
    """The version is not in a state that allows this step."""


def body_hash(body: dict[str, Any]) -> str:
    blob = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


def _audit(
    db: Session, role: str, actor: str, action: str, v: ContentVersion, **detail: Any
) -> None:
    db.add(
        ContentAudit(
            role=role,
            actor=actor,
            action=action,
            content_type=v.content_type,
            content_id=v.content_id,
            version=v.version,
            detail=detail,
        )
    )


def _need_role(role: str, allowed: tuple[str, ...], what: str) -> None:
    if role not in allowed:
        raise NotAllowed(f"Only {' or '.join(allowed)} can {what}.")


def _get(db: Session, version_id: str) -> ContentVersion:
    v = db.get(ContentVersion, version_id)
    if v is None:
        raise BadState("That version does not exist.")
    return v


def _next_number(db: Session, content_type: str, content_id: str) -> int:
    top = db.execute(
        select(func.max(ContentVersion.version)).where(
            ContentVersion.content_type == content_type, ContentVersion.content_id == content_id
        )
    ).scalar_one()
    return (top or 0) + 1


def create_draft(
    db: Session,
    content_type: str,
    content_id: str,
    body: dict[str, Any],
    actor: str,
    role: str,
    *,
    parent: int | None = None,
) -> ContentVersion:
    _need_role(role, EDITOR_ROLES, "write a draft")
    v = ContentVersion(
        id=uuid.uuid4().hex,
        content_type=content_type,
        content_id=content_id,
        version=_next_number(db, content_type, content_id),
        status="draft",
        body=body,
        content_hash=body_hash(body),
        parent_version=parent,
        created_by=actor,
    )
    db.add(v)
    _audit(db, role, actor, "create", v, parent=parent)
    db.commit()
    return v


def edit(
    db: Session, version_id: str, body: dict[str, Any], actor: str, role: str
) -> ContentVersion:
    """An edit is a new draft version. The old version, and its status, are untouched."""
    old = _get(db, version_id)
    return create_draft(db, old.content_type, old.content_id, body, actor, role, parent=old.version)


def submit_for_review(db: Session, version_id: str, actor: str, role: str) -> ContentVersion:
    _need_role(role, EDITOR_ROLES, "send a draft for review")
    v = _get(db, version_id)
    if v.status != "draft":
        raise BadState(f"A {v.status} version cannot be sent for review.")
    v.status = "in_review"
    _audit(db, role, actor, "submit", v)
    db.commit()
    return v


def coach_approve(db: Session, version_id: str, actor: str, role: str) -> ContentVersion:
    """The coach's key: gate 3. The content is approved, not yet in use."""
    _need_role(role, ("coach",), "approve content")
    v = _get(db, version_id)
    if v.status != "in_review":
        raise BadState(f"Only a version in review can be approved, not a {v.status} one.")
    v.status = "approved"
    v.coach_approved_by = actor
    v.coach_approved_at = datetime.now(UTC)
    _audit(db, role, actor, "approve", v)
    db.commit()
    return v


def return_to_draft(
    db: Session, version_id: str, actor: str, role: str, *, reason: str
) -> ContentVersion:
    """The coach asks for changes: the version goes back to a draft, with a structured reason."""
    _need_role(role, ("coach",), "send content back")
    v = _get(db, version_id)
    if v.status != "in_review":
        raise BadState(f"Only a version in review can be sent back, not a {v.status} one.")
    v.status = "draft"
    _audit(db, role, actor, "return", v, reason=reason)
    db.commit()
    return v


def officer_activate(db: Session, version_id: str, actor: str, role: str) -> ContentVersion:
    """The officer's key: switch an approved version on for the block. The version it replaces
    is retired in the same step, so exactly one version of an item is in use."""
    _need_role(role, ("officer",), "switch content on")
    v = _get(db, version_id)
    if v.status != "approved" or not v.coach_approved_by:
        raise BadState("Only content the coach has approved can be switched on.")
    current = active_version(db, v.content_type, v.content_id)
    if current is not None and current.id != v.id:
        current.status = "retired"
        _audit(db, role, actor, "retire", current, replaced_by=v.version)
    v.status = "active"
    v.officer_activated_by = actor
    v.officer_activated_at = datetime.now(UTC)
    _audit(db, role, actor, "activate", v, coach=v.coach_approved_by, officer=actor)
    db.commit()
    return v


def retire(db: Session, version_id: str, actor: str, role: str) -> ContentVersion:
    _need_role(role, ("officer",), "switch content off")
    v = _get(db, version_id)
    if v.status != "active":
        raise BadState("Only content that is on can be switched off.")
    v.status = "retired"
    _audit(db, role, actor, "retire", v)
    db.commit()
    return v


def active_version(db: Session, content_type: str, content_id: str) -> ContentVersion | None:
    return db.execute(
        select(ContentVersion).where(
            ContentVersion.content_type == content_type,
            ContentVersion.content_id == content_id,
            ContentVersion.status == "active",
        )
    ).scalar_one_or_none()
