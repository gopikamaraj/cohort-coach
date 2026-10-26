"""The P3 review queue: the coach edits, approves or rejects what call 5 drafted.

This is gate 3 for track content. A draft arrives here only after code and call 7 passed it
(drafting.store_draft). The coach's edits are re-checked by the same gates, so a human edit cannot
slip past a check. A rejection takes one structured reason, which becomes a pending checker
example. Approving all the parts of a track and assembling a version is the next step; switching
it on is the officer's key (versions.officer_activate).
"""

from __future__ import annotations

import difflib
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.calls.c05_track_draft import gate_script
from ai.client import CallContext
from ai.guard.rejections import RejectionReason
from services.api.db import ContentAudit, ReviewDecision, ReviewItem
from services.content import rejections, versions
from services.content.track import Track

MINOR_EDIT_RATIO = 0.10  # an approved edit changing at most this share of the text is "minor"
OPEN = ("pending", "awaiting_mentor")


class EditBlocked(ValueError):
    """An edit failed a code check or the checker, so it was not saved."""

    def __init__(self, codes: list[str], explanation: str) -> None:
        super().__init__(explanation)
        self.codes = codes
        self.explanation = explanation


@dataclass(frozen=True)
class ItemSummary:
    item_id: str
    content_type: str
    language: str
    kind: str
    day: int
    status: str
    age_hours: float
    explanation: str
    track_id: str


@dataclass(frozen=True)
class ItemDetail:
    item_id: str
    status: str
    badge: str
    language: str
    kind: str
    day: int
    script: str
    original_script: str | None
    results: list[dict[str, Any]]
    slots_used: list[str]
    strategies: list[str]
    explanation: str
    content_status: str  # needs_review | held_by_checker
    method_card_id: str | None
    history: list[dict[str, Any]]


@dataclass(frozen=True)
class Stats:
    decided: int
    approved: int
    rejected: int
    approved_unchanged: int
    approved_minor_edit: int
    approved_major_edit: int
    acceptance_with_minor_edits: float
    median_edit_ratio: float


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def _audit(
    db: Session, role: str, actor: str, action: str, item: ReviewItem, **detail: Any
) -> None:
    db.add(
        ContentAudit(
            role=role,
            actor=actor,
            action=action,
            content_type="review_item",
            content_id=item.item_id,
            version=0,
            detail=detail,
        )
    )


def _item(db: Session, item_id: str) -> ReviewItem:
    row = db.get(ReviewItem, item_id)
    if row is None or row.content_type != "track_draft":
        raise versions.BadState("That item does not exist.")
    return row


def list_items(
    db: Session, *, status: str | None = None, content_type: str = "track_draft"
) -> list[ItemSummary]:
    query = select(ReviewItem).where(ReviewItem.content_type == content_type)
    if status:
        query = query.where(ReviewItem.status == status)
    now = datetime.now(UTC)
    rows = db.execute(query.order_by(ReviewItem.created_at)).scalars()
    return [
        ItemSummary(
            item_id=r.item_id,
            content_type=r.content_type,
            language=r.language,
            kind=str(r.content.get("kind", "")),
            day=int(r.content.get("day", 0)),
            status=r.status,
            age_hours=round((now - _aware(r.created_at)).total_seconds() / 3600, 1),
            explanation=str(r.content.get("explanation", "")),
            track_id=str(r.content.get("track_id", "")),
        )
        for r in rows
    ]


def get_item(db: Session, item_id: str) -> ItemDetail:
    r = _item(db, item_id)
    c = r.content
    decisions = db.execute(
        select(ReviewDecision).where(ReviewDecision.item_id == item_id).order_by(ReviewDecision.id)
    ).scalars()
    return ItemDetail(
        item_id=r.item_id,
        status=r.status,
        badge=r.badge,
        language=r.language,
        kind=str(c.get("kind", "")),
        day=int(c.get("day", 0)),
        script=str(c["script"]),
        original_script=c.get("original_script"),
        results=list(c.get("results", [])),
        slots_used=list(c.get("slots_used", [])),
        strategies=list(c.get("strategies", [])),
        explanation=str(c.get("explanation", "")),
        content_status=str(c.get("status", "needs_review")),
        method_card_id=c.get("method_card_id"),
        history=[
            {
                "decision": d.decision,
                "reason": d.reason,
                "role": d.reviewer_role,
                "at": _aware(d.decided_at).isoformat(),
            }
            for d in decisions
        ],
    )


def save_edit(
    db: Session,
    item_id: str,
    script: str,
    actor: str,
    role: str,
    *,
    context: CallContext | None = None,
) -> ItemDetail:
    """Save the coach's edit. The same gates that checked the draft check the edit; if they fail
    nothing is saved."""
    if role != "coach":
        raise versions.NotAllowed("Only the coach can edit a draft in the queue.")
    row = _item(db, item_id)
    if row.status not in OPEN:
        raise versions.BadState(f"A {row.status} item cannot be edited.")
    gate = gate_script(
        script, row.language, str(row.content.get("error", row.target_error or "")), context=context
    )
    if not gate.passed_automatic:
        codes = [c for r in gate.results for c in r.codes]
        if gate.verdict is not None and not gate.verdict.passed:
            codes += gate.verdict.failed_items
        raise EditBlocked(codes, gate.explanation)
    before = str(row.content["script"])
    diff = "\n".join(
        difflib.unified_diff(before.splitlines(), script.splitlines(), "draft", "edit", lineterm="")
    )
    results = [
        {"name": r.name, "ok": r.ok, "codes": r.codes, "details": [v.detail for v in r.violations]}
        for r in gate.results
    ]
    row.content = {
        **row.content,
        "script": script,
        "original_script": row.content.get("original_script") or before,
        "results": results,
        "explanation": gate.explanation,
        "status": "needs_review",
    }
    row.badge = "checked"
    db.add(
        ReviewDecision(item_id=item_id, decision="edit", edit_diff=diff, reviewer_role="reviewer")
    )
    _audit(db, role, actor, "edit", row)
    db.commit()
    return get_item(db, item_id)


def approve(db: Session, item_id: str, actor: str, role: str) -> ItemDetail:
    """The coach's key. Content built from a mentor's card then waits for her approval too."""
    if role != "coach":
        raise versions.NotAllowed("Only the coach can approve a draft.")
    row = _item(db, item_id)
    if row.status != "pending":
        raise versions.BadState(f"A {row.status} item cannot be approved.")
    if row.content.get("status") != "needs_review":
        raise versions.BadState(
            "The checker held this draft. Edit it so it passes the checks, then approve it."
        )
    card = row.content.get("method_card_id")
    row.status = "awaiting_mentor" if card else "approved"
    row.badge = "checked" if card else "checked_reviewed"
    db.add(ReviewDecision(item_id=item_id, decision="approve", reviewer_role="reviewer"))
    _audit(db, role, actor, "approve", row, awaiting_mentor=bool(card))
    db.commit()
    return get_item(db, item_id)


def mentor_approve(db: Session, item_id: str, actor: str, role: str) -> ItemDetail:
    row = _item(db, item_id)
    if role != "mentor" or row.content.get("mentor_id") != actor:
        raise versions.NotAllowed("Only the mentor whose card this is can approve it.")
    if row.status != "awaiting_mentor":
        raise versions.BadState(f"A {row.status} item is not waiting for the mentor.")
    row.status = "approved"
    row.badge = "checked_reviewed"
    db.add(ReviewDecision(item_id=item_id, decision="approve", reviewer_role="mentor"))
    _audit(db, role, actor, "mentor_approve", row)
    db.commit()
    return get_item(db, item_id)


def reject(
    db: Session,
    item_id: str,
    actor: str,
    role: str,
    *,
    reason: str,
    note: str = "",
    pending_dir: Path | None = None,
) -> ItemDetail:
    """Reject with one structured reason. The excerpt goes to the pending checker examples."""
    if role != "coach":
        raise versions.NotAllowed("Only the coach can reject a draft.")
    code = RejectionReason(reason)  # a reason outside the list is a ValueError
    row = _item(db, item_id)
    if row.status not in OPEN:
        raise versions.BadState(f"A {row.status} item cannot be rejected.")
    row.status = "rejected"
    db.add(
        ReviewDecision(
            item_id=item_id, decision="reject", reason=code.value, reviewer_role="reviewer"
        )
    )
    _audit(db, role, actor, "reject", row, reason=code.value)
    db.commit()
    rejections.write_pending(
        str(row.content["script"]),
        code,
        row.language,
        item_id=item_id,
        note=note,
        directory=pending_dir,
    )
    return get_item(db, item_id)


def _edit_ratio(item: ReviewItem) -> float:
    original = item.content.get("original_script")
    if not original:
        return 0.0
    return 1.0 - difflib.SequenceMatcher(None, str(original), str(item.content["script"])).ratio()


def stats(db: Session) -> Stats:
    """Review statistics, computed by code from the decisions (rule 1)."""
    rows = list(
        db.execute(
            select(ReviewItem).where(
                ReviewItem.content_type == "track_draft",
                ReviewItem.status.in_(("approved", "rejected")),
            )
        ).scalars()
    )
    approved = [r for r in rows if r.status == "approved"]
    ratios = [_edit_ratio(r) for r in approved]
    unchanged = sum(1 for x in ratios if x == 0)
    minor = sum(1 for x in ratios if 0 < x <= MINOR_EDIT_RATIO)
    major = sum(1 for x in ratios if x > MINOR_EDIT_RATIO)
    decided = len(rows)
    return Stats(
        decided=decided,
        approved=len(approved),
        rejected=decided - len(approved),
        approved_unchanged=unchanged,
        approved_minor_edit=minor,
        approved_major_edit=major,
        acceptance_with_minor_edits=(unchanged + minor) / decided if decided else 0.0,
        median_edit_ratio=statistics.median(ratios) if ratios else 0.0,
    )


def assemble_track_version(
    db: Session, track: Track, languages: str | Sequence[str], actor: str, role: str
) -> versions.ContentVersion:
    """Make a track version from the approved parts, ready for the coach's and officer's keys.
    Every part (six lessons and the model lesson) must be approved in every language asked for."""
    langs = [languages] if isinstance(languages, str) else list(languages)
    body: dict[str, Any] = {
        "track_id": track.id,
        "track_version": track.version,
        "error": track.error,
        "languages": {},
    }
    missing: list[str] = []
    for lang in langs:
        chosen: dict[str, Any] = {}
        approved = db.execute(
            select(ReviewItem)
            .where(
                ReviewItem.content_type == "track_draft",
                ReviewItem.status == "approved",
                ReviewItem.language == lang,
            )
            .order_by(ReviewItem.created_at)
        ).scalars()
        latest: dict[tuple[str, int], ReviewItem] = {}
        for r in approved:
            if r.content.get("track_id") == track.id:
                latest[(str(r.content.get("kind")), int(r.content.get("day", 0)))] = r
        for lesson in track.lessons:
            item = latest.get(("lesson", lesson.day))
            if item is None:
                missing.append(f"lesson {lesson.day} ({lang})")
            else:
                chosen[f"lesson_{lesson.day}"] = {"item_id": item.item_id}
        model = latest.get(("model_lesson", 0))
        if model is None:
            missing.append(f"model lesson ({lang})")
        else:
            chosen["model_lesson"] = {"item_id": model.item_id}
        body["languages"][lang] = chosen
    if missing:
        raise versions.BadState("Approve every part first. Missing: " + ", ".join(missing) + ".")
    draft = versions.create_draft(db, "track", track.id, body, actor, role)
    return versions.submit_for_review(db, draft.id, actor, role)
