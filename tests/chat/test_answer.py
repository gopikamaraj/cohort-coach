"""C04: asking, the teacher's view, the mentor's and coach's inbox, every way a person answers,
and the correction of an answer the AI sent on its own."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from services.api.cohorts import lifecycle
from services.api.cohorts.thread import NotMember, PostRejected, ThreadClosed
from services.api.db import AiReplyDraft, ChatMessage, CohortAuditRow
from services.chat import config, labels, scheduler, service
from tests.chat.conftest import (
    COACH,
    GOOD,
    MENTOR,
    NOW,
    PASS,
    QUESTION,
    TEACHERS,
    World,
    ask,
)


def draft_of(world: World, q: ChatMessage) -> AiReplyDraft:
    return world.db.execute(
        select(AiReplyDraft).where(AiReplyDraft.message_id == q.id)
    ).scalar_one()


# ---- asking -----------------------------------------------------------------------------------


def test_without_the_ai_tick_no_model_runs_and_a_person_answers(
    world: World, material: dict[str, str]
) -> None:
    q, fake = ask(world, consent=False)
    assert fake.messages.calls == []
    assert (q.status, q.ai_consent, q.ai_due_at, q.question_class) == ("pending", False, None, None)
    view = service.my_questions(world.db, world.cohort_id, world.teacher)
    assert view["questions"][0]["waiting"] == {"key": labels.WAITING, "params": {}}


def test_with_the_tick_a_teaching_question_gets_a_draft_and_a_stored_due_time(
    world: World, material: dict[str, str]
) -> None:
    q, fake = ask(world)
    assert q.status == "ai_draft_ready" and q.question_class == "content_question"
    assert q.ai_due_at is not None and labels.aware(q.ai_due_at) == NOW + timedelta(hours=24)
    d = draft_of(world, q)
    assert d.status == "drafted" and d.draft_text == GOOD.answer and d.sources
    assert len(fake.messages.calls) == 3  # classify, draft, check


def test_changing_the_timeout_never_moves_a_question_already_waiting(
    world: World, material: dict[str, str]
) -> None:
    q, _ = ask(world)
    due = labels.aware(q.ai_due_at)
    config.set_config(world.db, role="coach", actor=COACH, timeout_hours=2, auto_send=True)
    world.db.refresh(q)
    assert labels.aware(q.ai_due_at) == due
    q2, _ = ask(world, teacher=world.other_teacher)  # a new question uses the new setting
    assert labels.aware(q2.ai_due_at) == NOW + timedelta(hours=2)


def test_the_teacher_is_only_promised_a_time_when_the_ai_may_really_answer(
    world: World, material: dict[str, str]
) -> None:
    ask(world)
    first = service.my_questions(world.db, world.cohort_id, world.teacher)["questions"][0]
    assert first["waiting"]["key"] == labels.WAITING  # auto-send is off: no promise
    config.set_config(world.db, role="coach", actor=COACH, auto_send=True)
    second = service.my_questions(world.db, world.cohort_id, world.teacher)["questions"][0]
    assert second["waiting"]["key"] == labels.WAITING_BY and second["waiting"]["params"]["time"]


def test_a_childs_name_is_masked_before_storage_and_before_any_model(
    world: World, material: dict[str, str]
) -> None:
    q, fake = ask(
        world,
        text="Meena keeps writing 403 for 43. What do I do with bundles?",
        replies=(GOOD, PASS),
    )
    assert q.body is not None and "Meena" not in q.body and "[child]" in q.body
    assert q.question_class == "child_specific"
    assert "Meena" not in str(fake.messages.calls)
    assert (
        service.my_questions(world.db, world.cohort_id, world.teacher)["questions"][0]["body"]
        == q.body
    )


def test_a_safety_question_goes_to_the_coach_with_no_draft_and_no_model(
    world: World, material: dict[str, str]
) -> None:
    q, fake = ask(world, text="A girl in my class says her father beats her at home.")
    assert q.flag == "safety" and q.question_class == "safety_or_welfare"
    assert q.ai_due_at is None and fake.messages.calls == []
    assert world.db.execute(select(AiReplyDraft)).first() is None
    assert service.inbox(world.db, role="mentor", person=MENTOR)["pending"] == []
    coach = service.inbox(world.db, role="coach", person=COACH)
    assert [p["id"] for p in coach["needs_attention"]] == [q.id] and coach["pending"][0][
        "flag"
    ] == "safety"
    with pytest.raises(lifecycle.NotAllowed):
        service.reply(
            world.db, q.id, role="mentor", person=MENTOR, mode="own", text="I will talk to her."
        )


def test_a_safety_word_works_even_without_the_ai_tick(world: World) -> None:
    q, fake = ask(world, text="He faints and does not eat at lunch", consent=False)
    assert q.flag == "safety" and fake.messages.calls == []


def test_only_a_member_of_an_active_cohort_may_ask(world: World, material: dict[str, str]) -> None:
    with pytest.raises(NotMember):
        ask(world, teacher="t-notamember0000000")
    lifecycle.transition(world.db, world.cohort_id, "closing", role="coach", actor=COACH)
    with pytest.raises(ThreadClosed):
        ask(world)


@pytest.mark.parametrize("text", ["", "   ", "x" * 501])
def test_an_empty_or_too_long_question_is_refused(world: World, text: str) -> None:
    with pytest.raises(PostRejected):
        ask(world, text=text, consent=False)


def test_a_phone_number_is_masked_and_never_stored(world: World) -> None:
    q, _ = ask(world, text="Call me on 9876543210 about the bundles", consent=False)
    assert q.body is not None and "9876543210" not in q.body


# ---- the inbox --------------------------------------------------------------------------------


def test_the_inbox_lists_questions_by_due_time_with_the_draft_and_its_sources(
    world: World, material: dict[str, str]
) -> None:
    late, _ = ask(world, now=NOW + timedelta(hours=3))
    soon, _ = ask(world, teacher=world.other_teacher, now=NOW)
    box = service.inbox(world.db, role="mentor", person=MENTOR, now=NOW)
    assert [p["id"] for p in box["pending"]] == [soon.id, late.id]
    first = box["pending"][0]
    assert first["seconds_left"] == 24 * 3600 and first["from"] == "Teacher 2"
    assert first["draft"]["text"] == GOOD.answer and first["draft"]["sources"][0]["id"] == "L4.1"
    assert first["draft"]["checker_passed"] is True and "needs_attention" not in box


def test_a_mentor_or_coach_sees_only_cohorts_assigned_to_her(
    world: World, material: dict[str, str]
) -> None:
    ask(world)
    assert service.inbox(world.db, role="mentor", person="mentor-elsewhere")["pending"] == []
    assert service.inbox(world.db, role="coach", person="coach-elsewhere")["pending"] == []
    with pytest.raises(lifecycle.NotAllowed):
        service.escalate(
            world.db,
            ask(world, teacher=world.other_teacher)[0].id,
            role="coach",
            person="coach-elsewhere",
        )


# ---- answering --------------------------------------------------------------------------------


def test_send_as_is_posts_the_draft_with_the_checked_by_your_mentor_label(
    world: World, material: dict[str, str]
) -> None:
    q, _ = ask(world)
    a = service.reply(world.db, q.id, role="mentor", person=MENTOR, mode="as_is", now=NOW)
    assert a.body == GOOD.answer and a.author_label == "Mentor" and a.ai_assisted
    assert labels.answer_label(a) == labels.AI_CHECKED
    world.db.refresh(q)
    d = draft_of(world, q)
    assert q.status == "answered_by_human" and d.status == "sent_as_is" and d.decided_by == MENTOR
    view = service.my_questions(world.db, world.cohort_id, world.teacher)["questions"][0]
    assert view["waiting"] is None and view["answers"][0]["label"] == labels.AI_CHECKED


def test_edit_and_send_needs_a_reason_and_keeps_both_texts(
    world: World, material: dict[str, str]
) -> None:
    q, _ = ask(world)
    new = "Open a bundle to get ten loose sticks, then take away 9. Try it with one child first."
    with pytest.raises(ValueError):
        service.reply(world.db, q.id, role="coach", person=COACH, mode="edit", text=new)
    with pytest.raises(ValueError):
        service.reply(
            world.db, q.id, role="coach", person=COACH, mode="edit", text=new, tags=("meh",)
        )
    a = service.reply(
        world.db,
        q.id,
        role="coach",
        person=COACH,
        mode="edit",
        text=new,
        tags=("too_long", "not_practical"),
    )
    d = draft_of(world, q)
    assert d.status == "edited_and_sent" and d.edited_text == new and d.draft_text == GOOD.answer
    assert d.edit_reason_tags == ["too_long", "not_practical"]
    assert a.author_label == "Coach" and labels.answer_label(a) == labels.AI_CHECKED


def test_write_my_own_has_no_ai_label_and_discards_the_draft(
    world: World, material: dict[str, str]
) -> None:
    q, _ = ask(world)
    a = service.reply(
        world.db, q.id, role="mentor", person=MENTOR, mode="own", text="Come and see my class."
    )
    assert not a.ai_assisted and labels.answer_label(a) is None
    assert draft_of(world, q).status == "discarded"


def test_a_question_without_the_tick_can_be_answered_by_a_person(world: World) -> None:
    q, _ = ask(world, consent=False)
    a = service.reply(
        world.db, q.id, role="mentor", person=MENTOR, mode="own", text="Try bundles first."
    )
    assert labels.answer_label(a) is None
    with pytest.raises(service.BadState):
        service.reply(world.db, q.id, role="mentor", person=MENTOR, mode="as_is")


def test_only_one_answer_can_ever_be_sent_for_a_question(
    world: World, material: dict[str, str]
) -> None:
    q, _ = ask(world)
    service.reply(world.db, q.id, role="mentor", person=MENTOR, mode="as_is")
    with pytest.raises(service.BadState):
        service.reply(
            world.db, q.id, role="coach", person=COACH, mode="own", text="Another answer."
        )
    assert len(service.answers_for(world.db, q.id)) == 1


def test_an_answer_with_a_name_in_it_is_refused(world: World, material: dict[str, str]) -> None:
    q, _ = ask(world)
    with pytest.raises(PostRejected):
        service.reply(
            world.db, q.id, role="mentor", person=MENTOR, mode="own", text="Ask Meena to help."
        )


def test_discarding_the_draft_leaves_the_question_for_a_person(
    world: World, material: dict[str, str]
) -> None:
    q, _ = ask(world)
    service.discard_draft(world.db, q.id, role="mentor", person=MENTOR)
    world.db.refresh(q)
    assert q.status == "pending" and draft_of(world, q).status == "discarded"
    assert service.inbox(world.db, role="mentor", person=MENTOR)["pending"][0]["draft"] is None


def test_escalating_tells_the_coach_and_stops_the_ai_from_answering(
    world: World, material: dict[str, str]
) -> None:
    q, _ = ask(world)
    config.set_config(world.db, role="coach", actor=COACH, timeout_hours=1, auto_send=True)
    service.escalate(world.db, q.id, role="mentor", person=MENTOR)
    coach = service.inbox(world.db, role="coach", person=COACH)
    assert [p["id"] for p in coach["needs_attention"]] == [q.id]
    assert scheduler.tick(world.db, now=NOW + timedelta(days=3)).sent == []


def test_a_draft_can_be_rated_good_or_not_good(world: World, material: dict[str, str]) -> None:
    q, _ = ask(world)
    service.rate_draft(world.db, q.id, "not_good", role="mentor", person=MENTOR)
    assert draft_of(world, q).quality == "not_good"
    with pytest.raises(ValueError):
        service.rate_draft(world.db, q.id, "fine", role="mentor", person=MENTOR)


# ---- the correction flow ----------------------------------------------------------------------


def auto_sent(world: World) -> ChatMessage:
    q, _ = ask(world)
    config.set_config(world.db, role="coach", actor=COACH, timeout_hours=1, auto_send=True)
    world.db.refresh(q)
    q.ai_due_at = NOW + timedelta(hours=1)
    world.db.commit()
    sent = scheduler.tick(world.db, now=NOW + timedelta(hours=2)).sent
    assert len(sent) == 1
    return world.db.get(ChatMessage, sent[0])  # type: ignore[return-value]


def test_an_answer_the_ai_sent_waits_in_needs_review_until_a_person_looks(
    world: World, material: dict[str, str]
) -> None:
    ai = auto_sent(world)
    assert [
        r["id"] for r in service.inbox(world.db, role="mentor", person=MENTOR)["needs_review"]
    ] == [ai.id]
    service.mark_reviewed(world.db, ai.id, role="mentor", person=MENTOR)
    assert service.inbox(world.db, role="mentor", person=MENTOR)["needs_review"] == []


def test_correcting_marks_the_ai_message_corrected_and_posts_a_correction(
    world: World, material: dict[str, str]
) -> None:
    ai = auto_sent(world)
    note = service.correct(
        world.db, ai.id, role="mentor", person=MENTOR,
        text="Please open only one bundle at a time.", tags=("not_practical",),
        now=NOW + timedelta(hours=3),
    )  # fmt: skip
    world.db.refresh(ai)
    assert ai.status == "corrected" and note.kind == "correction"
    assert labels.answer_label(note) == labels.CORRECTION and note.author_label == "Mentor"
    q = world.db.get(ChatMessage, ai.reply_to)
    assert q is not None and q.status == "corrected"
    view = service.my_questions(world.db, world.cohort_id, world.teacher)
    assert view["unseen"] == 2  # the AI answer and the correction are both new to her
    assert [a["label"] for a in view["questions"][0]["answers"]] == [labels.AUTO, labels.CORRECTION]
    assert service.mark_seen(world.db, world.cohort_id, world.teacher) == 2
    assert service.my_questions(world.db, world.cohort_id, world.teacher)["unseen"] == 0
    with pytest.raises(service.BadState):  # a second correction is refused
        service.correct(
            world.db, ai.id, role="coach", person=COACH, text="Again.", tags=("unsafe",)
        )


def test_a_correction_needs_a_valid_reason(world: World, material: dict[str, str]) -> None:
    ai = auto_sent(world)
    with pytest.raises(ValueError):
        service.correct(world.db, ai.id, role="mentor", person=MENTOR, text="Fix.", tags=())
    with pytest.raises(service.BadState):
        service.correct(
            world.db, "nope", role="mentor", person=MENTOR, text="Fix.", tags=("unsafe",)
        )


# ---- privacy and audit ------------------------------------------------------------------------


def test_no_teacher_id_appears_in_anything_returned_to_a_screen(
    world: World, material: dict[str, str]
) -> None:
    q, _ = ask(world)
    service.reply(world.db, q.id, role="mentor", person=MENTOR, mode="as_is")
    ask(world, teacher=world.other_teacher)
    shown = str(
        [
            service.my_questions(world.db, world.cohort_id, world.teacher),
            service.inbox(world.db, role="mentor", person=MENTOR),
            service.inbox(world.db, role="coach", person=COACH),
        ]
    )
    for t in TEACHERS:
        assert t not in shown


def test_a_teacher_sees_only_her_own_questions(world: World, material: dict[str, str]) -> None:
    ask(world)
    ask(world, teacher=world.other_teacher)
    assert len(service.my_questions(world.db, world.cohort_id, world.teacher)["questions"]) == 1
    assert (
        len(service.my_questions(world.db, world.cohort_id, world.other_teacher)["questions"]) == 1
    )


def test_every_step_is_audited_with_codes_and_never_text(
    world: World, material: dict[str, str]
) -> None:
    q, _ = ask(world, text="Meena writes 403. How do I use bundles?", replies=(GOOD, PASS))
    service.reply(
        world.db, q.id, role="mentor", person=MENTOR, mode="own", text="Show her with bundles."
    )
    rows = list(
        world.db.execute(
            select(CohortAuditRow).where(CohortAuditRow.action.like("chat_%"))
        ).scalars()
    )
    assert [r.action for r in rows] == ["chat_question", "chat_reply"]
    blob = str([r.detail for r in rows])
    assert "Meena" not in blob and "bundles" not in blob
    assert rows[0].detail["cls"] == "child_specific" and rows[0].detail["replaced"] == [
        "child_name"
    ]
    assert PASS  # imported helper in use
    assert QUESTION
