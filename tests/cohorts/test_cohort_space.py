"""P11 (reduced): the lifecycle, the posting check, the thread, mentor items, retention."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.validators.thread import check_thread_post
from services.api.cohorts import lifecycle, mentor_items, thread
from services.api.db import CohortAuditRow, CohortSpace, ThreadPost

GOOD = "I used the bundles today and the children liked opening one."


def make(db: Session, status: str = "active", members: int = 6) -> CohortSpace:
    c = lifecycle.create(
        db, error="SUB-SFL", coach_id="coach-1", mentor_ids=["mentor-1"], officer_id="officer-1",
        school_count=6,
    )  # fmt: skip
    if status != "proposed":
        lifecycle.transition(db, c.id, "active", role="officer", actor="officer-1")
    for i in range(members):
        thread.join(db, c.id, f"t-{i:016x}"[:18])
    return c


# ---- the lifecycle ------------------------------------------------------------------------


def test_the_lifecycle_runs_proposed_active_closing_closed_and_audits_each_step(
    db: Session,
) -> None:
    c = make(db, "proposed", 0)
    lifecycle.transition(db, c.id, "active", role="officer", actor="officer-1")
    lifecycle.transition(db, c.id, "closing", role="coach", actor="coach-1")
    lifecycle.transition(
        db, c.id, "closed", role="officer", actor="officer-1", post_test_received=True
    )
    assert db.get(CohortSpace, c.id).status == "closed"  # type: ignore[union-attr]
    actions = [
        a.action for a in db.execute(select(CohortAuditRow).order_by(CohortAuditRow.id)).scalars()
    ]
    assert actions == ["created", "to_active", "to_closing", "to_closed"]


@pytest.mark.parametrize(
    ("start", "to"),
    [("proposed", "closing"), ("proposed", "closed"), ("active", "proposed"), ("closed", "active")],
)
def test_an_illegal_transition_is_refused(db: Session, start: str, to: str) -> None:
    c = make(db, "proposed", 0)
    if start == "active":
        lifecycle.transition(db, c.id, "active", role="officer", actor="o")
    if start == "closed":
        for step in ("active", "closing"):
            lifecycle.transition(db, c.id, step, role="officer", actor="o")
        lifecycle.transition(db, c.id, "closed", role="officer", actor="o", post_test_received=True)
    with pytest.raises(lifecycle.BadTransition):
        lifecycle.transition(db, c.id, to, role="officer", actor="o")


def test_a_cohort_can_be_cancelled_from_proposed_or_active_only(db: Session) -> None:
    a = make(db, "proposed", 0)
    lifecycle.transition(db, a.id, "cancelled", role="officer", actor="o", reason="no teachers")
    b = make(db)
    lifecycle.transition(db, b.id, "cancelled", role="officer", actor="o")
    c = make(db)
    lifecycle.transition(db, c.id, "closing", role="officer", actor="o")
    with pytest.raises(lifecycle.BadTransition):
        lifecycle.transition(db, c.id, "cancelled", role="officer", actor="o")


def test_closing_needs_the_post_test_or_a_stated_reason(db: Session) -> None:
    c = make(db)
    lifecycle.transition(db, c.id, "closing", role="coach", actor="coach-1")
    with pytest.raises(lifecycle.BadTransition):
        lifecycle.transition(db, c.id, "closed", role="officer", actor="o")
    lifecycle.transition(db, c.id, "closed", role="officer", actor="o", reason="schools closed")
    assert "closed without post-test" in (db.get(CohortSpace, c.id).close_reason or "")  # type: ignore[union-attr]


def test_a_coach_can_only_start_closing_her_own_active_cohort(db: Session) -> None:
    c = make(db)
    with pytest.raises(lifecycle.NotAllowed):
        lifecycle.transition(db, c.id, "closing", role="coach", actor="coach-2")
    with pytest.raises(lifecycle.NotAllowed):
        lifecycle.transition(db, c.id, "cancelled", role="coach", actor="coach-1")


def test_the_thread_opens_only_with_five_members_and_figures_under_five_are_hidden(
    db: Session,
) -> None:
    c = make(db, members=4)
    assert lifecycle.thread_state(db, c) == "read_only"
    s = lifecycle.summary(db, c)
    assert s["members"] is None and s["thread"] == "read_only"
    thread.join(db, c.id, "t-extra0000000000"[:18])
    assert lifecycle.thread_state(db, c) == "open"
    assert lifecycle.summary(db, c)["members"] == 5


# ---- the posting check --------------------------------------------------------------------

BLOCKED = [
    ("Meena could not borrow today", "en", "child_name"),
    ("roll no 14 was confused", "en", "roll_number"),
    ("No. 7 child did well", "en", "roll_number"),
    ("Rahul's sister struggled with it", "en", "relationship"),
    ("call me on 9876543210", "en", "pii_phone"),
    ("write to a@b.example", "en", "pii_email"),
    ("मीना को समझ नहीं आया", "hi", "child_name"),
    ("மீனாவுக்கு புரியவில்லை", "ta", "child_name"),
    ("you are stupid", "en", "profanity"),
    ("x" * 501, "en", "too_long"),
]
ALLOWED = [
    (GOOD, "en"),
    ("बच्चों को बंडल पसंद आए", "hi"),
    ("குழந்தைகளுக்கு பிடித்தது", "ta"),
    ("I tried it twice this week and one child needed more time.", "en"),
]


@pytest.mark.parametrize(("text", "lang", "code"), BLOCKED)
def test_the_posting_check_blocks_names_roll_numbers_and_details(
    text: str, lang: str, code: str
) -> None:
    assert code in [v.code for v in check_thread_post(text, lang)]


@pytest.mark.parametrize(("text", "lang"), ALLOWED)
def test_ordinary_text_passes_the_check(text: str, lang: str) -> None:
    assert check_thread_post(text, lang) == []


def test_the_check_is_not_described_as_a_guarantee() -> None:
    assert "not a guarantee" in (
        check_thread_post.__module__ and __import__("ai.validators.thread", fromlist=["x"]).__doc__
    )


# ---- the thread ---------------------------------------------------------------------------


def test_a_member_posts_under_a_system_label_and_the_view_has_no_teacher_id(db: Session) -> None:
    c = make(db)
    p = thread.post_as_teacher(db, c.id, "t-0000000000000000"[:18], GOOD, "en")
    v = thread.view(p)
    assert v["author_name"].startswith("Teacher ") and v["author_kind"] == "teacher"
    assert "teacher_id" not in str(v) and "t-0000" not in str(v)
    names = [
        m
        for (m,) in db.execute(
            select(__import__("services.api.db", fromlist=["x"]).CohortMember.display_name)
        )
    ]
    assert len(set(names)) == len(names)  # unique labels


def test_a_failed_check_stores_nothing_and_asks_her_to_rewrite(db: Session) -> None:
    c = make(db)
    with pytest.raises(thread.PostRejected) as e:
        thread.post_as_teacher(db, c.id, "t-0000000000000000"[:18], "Meena failed again", "en")
    assert "child_name" in e.value.codes
    assert db.execute(select(ThreadPost)).first() is None
    row = db.execute(
        select(CohortAuditRow).where(CohortAuditRow.action == "post_blocked")
    ).scalar_one()
    assert row.detail == {"rules": ["child_name"]}  # the rule, never her text


def test_a_non_member_or_a_read_only_thread_cannot_post(db: Session) -> None:
    c = make(db)
    with pytest.raises(thread.NotMember):
        thread.post_as_teacher(db, c.id, "t-stranger0000000000"[:18], GOOD, "en")
    small = make(db, members=3)
    with pytest.raises(thread.ThreadClosed):
        thread.post_as_teacher(db, small.id, "t-0000000000000000"[:18], GOOD, "en")


def test_a_reported_post_is_held_and_invisible_to_others_until_the_coach_restores_it(
    db: Session,
) -> None:
    c = make(db)
    p = thread.post_as_teacher(db, c.id, "t-0000000000000000"[:18], GOOD, "en")
    thread.report(db, p.id, "t-0000000000000001"[:18])
    assert thread.posts_for(db, c.id) == []  # others see nothing
    assert [x["status"] for x in thread.posts_for(db, c.id, moderator=True)] == ["reported"]
    thread.decide(db, p.id, "restore", actor="coach-1")
    assert [x["id"] for x in thread.posts_for(db, c.id)] == [p.id]


def test_hide_and_restore_are_audited_and_an_identifier_erases_the_text_at_once(
    db: Session,
) -> None:
    c = make(db)
    p = thread.post_as_teacher(db, c.id, "t-0000000000000000"[:18], GOOD, "en")
    thread.decide(db, p.id, "hide", actor="coach-1")
    thread.decide(db, p.id, "restore", actor="coach-1")
    thread.decide(db, p.id, "hide", actor="coach-1", identifier=True)
    assert db.get(ThreadPost, p.id).body is None  # type: ignore[union-attr]
    with pytest.raises(ValueError):
        thread.decide(db, p.id, "restore", actor="coach-1")
    actions = [
        a.action
        for a in db.execute(select(CohortAuditRow)).scalars()
        if a.action.startswith("post_")
    ]
    assert actions.count("post_hide") == 2 and "post_restore" in actions


def test_a_teacher_can_delete_her_own_post_only(db: Session) -> None:
    c = make(db)
    p = thread.post_as_teacher(db, c.id, "t-0000000000000000"[:18], GOOD, "en")
    with pytest.raises(thread.NotMember):
        thread.delete_own(db, p.id, "t-0000000000000001"[:18])
    thread.delete_own(db, p.id, "t-0000000000000000"[:18])
    assert db.get(ThreadPost, p.id).body is None  # type: ignore[union-attr]
    assert thread.posts_for(db, c.id) == []


def test_pinned_posts_come_first_and_staff_post_under_their_role_name(db: Session) -> None:
    c = make(db)
    a = thread.post_as_teacher(db, c.id, "t-0000000000000000"[:18], GOOD, "en")
    b = thread.post_as_staff(
        db, c.id, "coach", "coach-1", "This week: try the bundles twice.", "en"
    )
    assert b.author_name == "Coach"
    thread.decide(db, b.id, "pin", actor="coach-1")
    assert [p["id"] for p in thread.posts_for(db, c.id)] == [b.id, a.id]
    with pytest.raises(thread.PostRejected):
        thread.post_as_staff(db, c.id, "mentor", "mentor-1", "Meena did it", "en")


# ---- retention ----------------------------------------------------------------------------


def test_the_retention_job_erases_held_text_after_7_days_and_closed_thread_after_30(
    db: Session,
) -> None:
    c = make(db)
    a = thread.post_as_teacher(db, c.id, "t-0000000000000000"[:18], GOOD, "en")
    b = thread.post_as_teacher(db, c.id, "t-0000000000000001"[:18], GOOD + " again", "en")
    thread.report(db, a.id, "t-0000000000000001"[:18])
    now = datetime.now(UTC)
    assert thread.purge(db, now=now + timedelta(days=6)) == {
        "held_bodies_erased": 0,
        "thread_text_erased": 0,
    }
    out = thread.purge(db, now=now + timedelta(days=8))
    assert out["held_bodies_erased"] == 1 and db.get(ThreadPost, a.id).body is None  # type: ignore[union-attr]
    assert db.get(ThreadPost, b.id).body is not None  # type: ignore[union-attr]
    lifecycle.transition(db, c.id, "closing", role="officer", actor="o")
    lifecycle.transition(db, c.id, "closed", role="officer", actor="o", post_test_received=True)
    ended = datetime.now(UTC)
    assert thread.purge(db, now=ended + timedelta(days=29))["thread_text_erased"] == 0
    assert thread.purge(db, now=ended + timedelta(days=31))["thread_text_erased"] == 1
    assert db.get(ThreadPost, b.id).body is None  # type: ignore[union-attr]


def test_no_text_is_ever_kept_past_90_days_even_in_an_open_cohort(db: Session) -> None:
    c = make(db)
    p = thread.post_as_teacher(db, c.id, "t-0000000000000000"[:18], GOOD, "en")
    thread.purge(db, now=datetime.now(UTC) + timedelta(days=91))
    assert db.get(ThreadPost, p.id).body is None  # type: ignore[union-attr]


# ---- mentor items -------------------------------------------------------------------------


def item(db: Session, c: CohortSpace) -> str:
    i = mentor_items.create(db, c.id, "mentor-1", "recording")
    mentor_items.submit(db, i.id, "mentor-1")
    return i.id


def test_a_mentor_item_goes_to_the_coach_and_nothing_is_in_use_without_approval(
    db: Session,
) -> None:
    c = make(db)
    i = item(db, c)
    with pytest.raises(mentor_items.BadState):
        mentor_items.mark_in_use(db, i, "v1")  # awaiting the coach: not usable
    mentor_items.decide(db, i, "approve", coach_id="coach-1")
    assert mentor_items.mark_in_use(db, i, "v1").status == "in_use"


def test_changes_or_a_rejection_need_a_reason_code_and_a_clean_note(db: Session) -> None:
    c = make(db)
    i = item(db, c)
    with pytest.raises(ValueError):
        mentor_items.decide(db, i, "reject", coach_id="coach-1")
    with pytest.raises(ValueError):
        mentor_items.decide(
            db, i, "reject", coach_id="coach-1", reason="tone_issue", note="call 9876543210"
        )
    out = mentor_items.decide(
        db, i, "request_changes", coach_id="coach-1", reason="missing_step", note="add the order"
    )
    assert out.status == "changes_requested" and out.reason_code == "missing_step"
    assert mentor_items.submit(db, i, "mentor-1").status == "awaiting_coach"  # she resubmits


def test_a_coach_decides_only_items_in_her_own_cohort(db: Session) -> None:
    c = make(db)
    i = item(db, c)
    with pytest.raises(lifecycle.NotAllowed):
        mentor_items.decide(db, i, "approve", coach_id="coach-2")
    assert mentor_items.awaiting_for_coach(db, "coach-2") == []
    assert [x.id for x in mentor_items.awaiting_for_coach(db, "coach-1")] == [i]


def test_editing_an_item_in_use_makes_a_new_version_and_the_old_stays_until_the_new_is_used(
    db: Session,
) -> None:
    c = make(db)
    i = item(db, c)
    mentor_items.decide(db, i, "approve", coach_id="coach-1")
    mentor_items.mark_in_use(db, i, "v1")
    new = mentor_items.edit(db, i, "mentor-1")
    assert new.id != i and new.version == 2 and new.status == "draft" and new.parent_id == i
    assert db.get(__import__("services.api.db", fromlist=["x"]).MentorItem, i).status == "in_use"  # type: ignore[union-attr]
    mentor_items.submit(db, new.id, "mentor-1")
    mentor_items.decide(db, new.id, "approve", coach_id="coach-1")
    mentor_items.mark_in_use(db, new.id, "v2")
    mentor_items.retire_replaced(db, new.id)
    assert db.get(__import__("services.api.db", fromlist=["x"]).MentorItem, i).status == "retired"  # type: ignore[union-attr]


def test_a_mentor_cannot_create_an_item_in_a_cohort_she_does_not_mentor(db: Session) -> None:
    c = make(db)
    with pytest.raises(lifecycle.NotAllowed):
        mentor_items.create(db, c.id, "mentor-9", "recording")
    with pytest.raises(lifecycle.NotAllowed):
        mentor_items.submit(db, item(db, c), "mentor-9")
