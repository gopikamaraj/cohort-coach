"""C05: the auto-send gates and the idempotent sweep. The AI's draft goes out on its own only when
every gate holds; otherwise the question keeps waiting for a person and the coach is told once."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from services.api.db import AiReplyDraft, ChatMessage, CohortAuditRow, ReviewItem
from services.chat import config, scheduler, service
from tests.chat.conftest import (
    COACH,
    GOOD,
    MENTOR,
    NOW,
    PASS,
    World,
    ask,
)

LATER = NOW + timedelta(hours=25)


def on(world: World, hours: int = 24, auto_send: bool = True) -> None:
    config.set_config(world.db, role="coach", actor=COACH, timeout_hours=hours, auto_send=auto_send)


def draft_of(world: World, q: ChatMessage) -> AiReplyDraft:
    return world.db.execute(
        select(AiReplyDraft).where(AiReplyDraft.message_id == q.id)
    ).scalar_one()


def test_when_every_gate_holds_the_draft_goes_out_labelled_as_ai(
    world: World, material: dict[str, str]
) -> None:
    on(world)
    q, _ = ask(world)
    result = scheduler.tick(world.db, now=LATER)
    assert len(result.sent) == 1 and result.blocked == {}
    world.db.refresh(q)
    answer = world.db.get(ChatMessage, result.sent[0])
    assert answer is not None and answer.author_role == "ai" and answer.body == GOOD.answer
    assert answer.status == "ai_sent" and answer.reply_to == q.id and answer.ai_assisted
    assert q.status == "ai_sent" and draft_of(world, q).status == "auto_sent"
    assert draft_of(world, q).decided_by == "system"


def test_nothing_is_sent_before_the_due_time(world: World, material: dict[str, str]) -> None:
    on(world)
    q, _ = ask(world)
    assert scheduler.tick(world.db, now=NOW + timedelta(hours=23)).sent == []
    world.db.refresh(q)
    assert q.status == "ai_draft_ready"


def test_auto_send_is_off_until_a_coach_turns_it_on(world: World, material: dict[str, str]) -> None:
    q, _ = ask(world)
    result = scheduler.tick(world.db, now=LATER)
    assert result.sent == [] and result.blocked == {q.id: "auto_send_off"}
    world.db.refresh(q)
    assert q.status == "ai_draft_ready" and q.alert_reason == "auto_send_off"


@pytest.mark.parametrize(
    "text,replies",
    [
        ("Meena keeps writing 403 for 43. How do I use bundles?", (GOOD, PASS)),  # child-specific
        (
            "How should I punish children who do not listen with bundles?",
            (GOOD, PASS),
        ),  # discipline
    ],
)
def test_a_question_that_is_not_a_teaching_question_is_never_sent_on_its_own(
    world: World, material: dict[str, str], text: str, replies: tuple[object, ...]
) -> None:
    on(world)
    q, _ = ask(world, text=text, replies=replies)
    assert q.status == "ai_draft_ready"  # a draft exists, for the mentor only
    assert scheduler.tick(world.db, now=LATER).sent == []
    world.db.refresh(q)
    assert q.status == "ai_draft_ready" and q.alert_reason == "needs_person"


def test_a_safety_question_has_no_draft_and_is_never_sent(
    world: World, material: dict[str, str]
) -> None:
    on(world)
    q, _ = ask(world, text="She comes hungry and her father beats her.")
    assert scheduler.tick(world.db, now=LATER).sent == []
    assert world.db.execute(select(AiReplyDraft)).first() is None and q.status == "pending"


def test_a_question_with_no_answer_from_the_model_is_never_sent(
    world: World, material: dict[str, str]
) -> None:
    from ai.schemas import ChatReply

    on(world)
    q, _ = ask(world, replies=(ChatReply(answer=None, no_answer_reason="no source"),))
    assert q.status == "pending" and draft_of(world, q).status == "discarded"
    assert scheduler.tick(world.db, now=LATER).sent == []


def test_a_draft_the_checker_did_not_pass_is_never_sent(
    world: World, material: dict[str, str]
) -> None:
    on(world)
    q, _ = ask(world)
    d = draft_of(world, q)
    d.checker_result = {**d.checker_result, "passed": False}
    world.db.commit()
    assert scheduler.tick(world.db, now=LATER).blocked == {q.id: "checker"}


def test_a_draft_with_no_sources_is_never_sent(world: World, material: dict[str, str]) -> None:
    on(world)
    q, _ = ask(world)
    d = draft_of(world, q)
    d.sources = []
    world.db.commit()
    assert scheduler.tick(world.db, now=LATER).blocked == {q.id: "no_sources"}


def test_a_draft_whose_source_is_no_longer_approved_is_never_sent(
    world: World, material: dict[str, str]
) -> None:
    on(world)
    q, _ = ask(world)
    item = world.db.get(ReviewItem, material["en4"])
    assert item is not None
    item.status = "rejected"  # the coach withdrew the lesson after the draft was made
    world.db.commit()
    assert scheduler.tick(world.db, now=LATER).blocked == {q.id: "sources_changed"}


def test_a_person_who_answers_first_wins_and_the_ai_sends_nothing(
    world: World, material: dict[str, str]
) -> None:
    on(world)
    q, _ = ask(world)
    service.reply(world.db, q.id, role="mentor", person=MENTOR, mode="own", text="Come and see me.")
    assert scheduler.tick(world.db, now=LATER).sent == []
    assert len(service.answers_for(world.db, q.id)) == 1


def test_a_discarded_draft_cannot_be_sent_by_the_ai(world: World, material: dict[str, str]) -> None:
    on(world)
    q, _ = ask(world)
    service.discard_draft(world.db, q.id, role="mentor", person=MENTOR)
    assert scheduler.tick(world.db, now=LATER).sent == []


def test_a_teacher_gets_at_most_three_ai_replies_a_day(
    world: World, material: dict[str, str]
) -> None:
    on(world)
    for i in range(4):
        ask(world, now=NOW + timedelta(minutes=i))
    result = scheduler.tick(world.db, now=LATER)
    assert len(result.sent) == 3
    assert list(result.blocked.values()) == ["daily_limit"]
    # a day later the fourth may go
    world.db.expire_all()
    assert len(scheduler.tick(world.db, now=LATER + timedelta(days=1)).sent) == 1


def test_a_second_sweep_sends_nothing_more(world: World, material: dict[str, str]) -> None:
    on(world)
    ask(world)
    first = scheduler.tick(world.db, now=LATER)
    second = scheduler.tick(world.db, now=LATER + timedelta(minutes=5))
    assert len(first.sent) == 1 and second.sent == [] and second.blocked == {}
    ai = (
        world.db.execute(select(ChatMessage).where(ChatMessage.author_role == "ai")).scalars().all()
    )
    assert len(ai) == 1


def test_two_sweeps_racing_each_other_send_once(
    world: World, material: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The gates pass in both sweeps, but only the first can claim the question."""
    on(world)
    q, _ = ask(world)
    monkeypatch.setattr(scheduler, "blocker", lambda *a, **k: None)
    other = scheduler.tick(world.db, now=LATER)
    world.db.expire_all()
    # a stale second sweep that still believes the question is waiting
    q.status = "ai_draft_ready"
    from sqlalchemy import update

    world.db.execute(
        update(ChatMessage).where(ChatMessage.id == q.id).values(status="answered_by_human")
    )
    world.db.commit()
    again = scheduler.tick(world.db, now=LATER)
    assert len(other.sent) == 1 and again.sent == []
    ai = (
        world.db.execute(select(ChatMessage).where(ChatMessage.author_role == "ai")).scalars().all()
    )
    assert len(ai) == 1


def test_the_coach_is_alerted_once_however_often_it_sweeps(
    world: World, material: dict[str, str]
) -> None:
    q, _ = ask(world)  # auto-send off
    a = scheduler.tick(world.db, now=LATER)
    b = scheduler.tick(world.db, now=LATER + timedelta(hours=1))
    assert (a.alerted, b.alerted) == (1, 0)
    rows = (
        world.db.execute(select(CohortAuditRow).where(CohortAuditRow.action == "chat_overdue"))
        .scalars()
        .all()
    )
    assert len(rows) == 1 and rows[0].detail == {"reason": "auto_send_off"}
    box = service.inbox(world.db, role="coach", person=COACH, now=LATER)
    assert [p["id"] for p in box["needs_attention"]] == [q.id]
    assert box["needs_attention"][0]["alert_reason"] == "auto_send_off"


def test_the_sweep_can_be_limited_to_some_cohorts(world: World, material: dict[str, str]) -> None:
    on(world)
    ask(world)
    assert scheduler.tick(world.db, now=LATER, cohort_ids=["another"]).sent == []
    assert len(scheduler.tick(world.db, now=LATER, cohort_ids=[world.cohort_id]).sent) == 1
