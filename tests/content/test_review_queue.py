"""P09 T06: the P3 review queue service. The coach edits, approves or rejects what call 5 drafted;
code re-checks every edit; a rejection needs one structured reason; every decision is audited."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.calls.c05_track_draft import draft_part
from ai.client import CallContext
from ai.schemas import TrackPart, Verdict
from services.api.db import ContentAudit, ReviewDecision, ReviewItem
from services.content import drafting, review, versions
from services.content.track import load_track
from tests.ai.test_c05_track_draft import GOOD, PASS
from tests.support_ai import FakeClient

COACH = ("coach-7f3a", "coach")
OFFICER = ("officer-21bc", "officer")
MENTOR = ("mentor-3c1d", "mentor")


def ctx(*replies: object) -> CallContext:
    return CallContext(mode="stub", client=FakeClient(list(replies)))  # type: ignore[arg-type]


def queue(db: Session, day: int = 1, language: str = "en", script: str = GOOD) -> ReviewItem:
    track = load_track("sub-sfl.v1")
    part = TrackPart(kind="lesson", day=day, script=script)
    draft = draft_part(track, "lesson", day, language, context=ctx(part, PASS))
    item = drafting.store_draft(db, draft, track)
    assert item is not None
    return item


def test_the_queue_lists_items_by_status_oldest_first(db: Session) -> None:
    a, b = queue(db, 1), queue(db, 2)
    rows = review.list_items(db, status="pending")
    assert [r.item_id for r in rows] == [a.item_id, b.item_id]
    assert all(r.age_hours >= 0 and r.content_type == "track_draft" for r in rows)
    assert review.list_items(db, status="approved") == []


def test_an_item_shows_its_check_results_and_slots(db: Session) -> None:
    item = queue(db)
    detail = review.get_item(db, item.item_id)
    assert detail.script == GOOD
    assert {r["name"] for r in detail.results} >= {"slots", "arithmetic", "check_items"}
    assert "class.count_showing" in detail.slots_used
    assert detail.explanation


def test_an_edit_is_saved_with_a_diff_and_the_original_is_kept(db: Session) -> None:
    item = queue(db)
    new = GOOD.replace("Try it tomorrow with one child.", "Try it tomorrow with one child, gently.")
    edited = review.save_edit(db, item.item_id, new, *COACH, context=ctx(PASS))
    assert edited.script == new and edited.original_script == GOOD
    decision = db.execute(
        select(ReviewDecision).where(ReviewDecision.decision == "edit")
    ).scalar_one()
    assert "gently" in (decision.edit_diff or "")


def test_an_edit_that_breaks_a_check_is_refused_and_changes_nothing(db: Session) -> None:
    item = queue(db)
    bad = GOOD.replace("63 - 28 = 35", "45 - 19 = 26")  # Form A item 8
    with pytest.raises(review.EditBlocked) as err:
        review.save_edit(db, item.item_id, bad, *COACH, context=ctx(PASS))
    assert "check_item" in err.value.codes
    assert review.get_item(db, item.item_id).script == GOOD


def test_an_edit_the_checker_refuses_is_not_saved(db: Session) -> None:
    item = queue(db)
    fail = Verdict(passed=False, failed_items=["tone"], reason_short="x", reason_for_user="harsh")
    with pytest.raises(review.EditBlocked):
        review.save_edit(db, item.item_id, GOOD + " Do better.", *COACH, context=ctx(fail))
    assert review.get_item(db, item.item_id).script == GOOD


def test_only_the_coach_approves_and_the_badge_is_earned(db: Session) -> None:
    item = queue(db)
    with pytest.raises(versions.NotAllowed):
        review.approve(db, item.item_id, *OFFICER)
    approved = review.approve(db, item.item_id, *COACH)
    assert approved.status == "approved" and approved.badge == "checked_reviewed"
    row = db.get(ReviewItem, item.item_id)
    assert row is not None and row.status == "approved"


def test_an_item_the_checker_held_cannot_be_approved_until_an_edit_passes(db: Session) -> None:
    track = load_track("sub-sfl.v1")
    fail = Verdict(passed=False, failed_items=["tone"], reason_short="x", reason_for_user="harsh")
    draft = draft_part(
        track, "lesson", 1, "en", context=ctx(TrackPart(kind="lesson", day=1, script=GOOD), fail)
    )
    item = drafting.store_draft(db, draft, track)
    assert item is not None
    with pytest.raises(versions.BadState):
        review.approve(db, item.item_id, *COACH)
    review.save_edit(db, item.item_id, GOOD + " Be kind.", *COACH, context=ctx(PASS))
    assert review.approve(db, item.item_id, *COACH).status == "approved"


def test_a_rejection_needs_one_structured_reason_and_leaves_a_pending_example(
    db: Session, tmp_path: Path
) -> None:
    item = queue(db)
    with pytest.raises(ValueError):
        review.reject(db, item.item_id, *COACH, reason="because", pending_dir=tmp_path)
    rejected = review.reject(
        db, item.item_id, *COACH, reason="tone_issue", note="too stern", pending_dir=tmp_path
    )
    assert rejected.status == "rejected"
    files = list(tmp_path.glob("*.yaml"))
    assert len(files) == 1 and "tone_issue" in files[0].read_text(encoding="utf-8")
    decision = db.execute(
        select(ReviewDecision).where(ReviewDecision.decision == "reject")
    ).scalar_one()
    assert decision.reason == "tone_issue"


def test_content_built_from_a_mentors_card_needs_her_approval_too(db: Session) -> None:
    item = queue(db)
    row = db.get(ReviewItem, item.item_id)
    assert row is not None
    row.content = {**row.content, "method_card_id": "card-12", "mentor_id": MENTOR[0]}
    db.commit()
    waiting = review.approve(db, item.item_id, *COACH)
    assert waiting.status == "awaiting_mentor"  # the coach's key is not the last one
    with pytest.raises(versions.NotAllowed):
        review.mentor_approve(db, item.item_id, *COACH)
    final = review.mentor_approve(db, item.item_id, *MENTOR)
    assert final.status == "approved"


def test_every_decision_writes_an_audit_row(db: Session, tmp_path: Path) -> None:
    a, b = queue(db, 1), queue(db, 2)
    review.save_edit(db, a.item_id, GOOD + " Ok.", *COACH, context=ctx(PASS))
    review.approve(db, a.item_id, *COACH)
    review.reject(db, b.item_id, *COACH, reason="wrong_maths", pending_dir=tmp_path)
    actions = [
        r.action
        for r in db.execute(
            select(ContentAudit).where(ContentAudit.content_type == "review_item")
        ).scalars()
    ]
    assert actions == ["edit", "approve", "reject"]


def test_review_statistics_count_unchanged_minor_and_major_edits(
    db: Session, tmp_path: Path
) -> None:
    items = [queue(db, d) for d in (1, 2, 3, 4)]
    review.approve(db, items[0].item_id, *COACH)  # unchanged
    review.save_edit(db, items[1].item_id, GOOD + " Ok.", *COACH, context=ctx(PASS))  # minor
    review.approve(db, items[1].item_id, *COACH)
    major = "Today is about one mistake. Ask her how she got it. 63 - 28 = 35."
    review.save_edit(db, items[2].item_id, major, *COACH, context=ctx(PASS))
    review.approve(db, items[2].item_id, *COACH)
    review.reject(db, items[3].item_id, *COACH, reason="culturally_off", pending_dir=tmp_path)
    s = review.stats(db)
    assert (s.decided, s.approved, s.rejected) == (4, 3, 1)
    assert (s.approved_unchanged, s.approved_minor_edit, s.approved_major_edit) == (1, 1, 1)
    assert s.acceptance_with_minor_edits == pytest.approx(2 / 4)  # a ratio code computed
    assert 0 < s.median_edit_ratio < 1


def test_a_track_version_needs_every_part_approved(db: Session) -> None:
    track = load_track("sub-sfl.v1")
    for d in range(1, 6):  # five of the six lessons, no model lesson
        review.approve(db, queue(db, d).item_id, *COACH)
    with pytest.raises(versions.BadState) as err:
        review.assemble_track_version(db, track, "en", *COACH)
    assert "lesson 6" in str(err.value) and "model" in str(err.value)
