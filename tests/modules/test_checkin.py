# ruff: noqa: E501
"""Part C: the private check-in, and the masked summary she may share with her cohort only if she agrees."""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ai.schemas import FeedbackReview, FollowUpPick
from services.api.db import Base, ChatMessage, CohortAuditRow, ThreadPost, make_engine
from services.api.main import create_app
from services.api.profiles import get_session
from services.modules import api as modules_api
from services.modules import checkin, review
from services.modules.models import CheckinShare
from tests.modules.test_service_and_jobs import T0

STRINGS = Path(__file__).resolve().parents[2] / "strings"
DEVICES = [f"{i:016x}" for i in range(1, 7)]  # DEVICES[0] is T1, [1] is T2, [5] stays outside
BODY = {
    "check_id": "c-abc:1",
    "name": "My class: the smaller digit",
    "errors": ["SUB-SFL"],
    "counts": {"SUB-SFL": 5},
    "children_checked": 16,
}
NOTE = "Ravi could not open the ten and the children were quiet."


def h(role: str, device: str | None = None, person: str | None = None) -> dict[str, str]:
    out = {"X-Role": role}
    who = person or device or (f"{role}-demo" if role != "teacher" else None)  # a staff account is a user too
    if who:
        out["X-User"] = who
    return out


class World:
    def __init__(
        self, c: TestClient, factory: sessionmaker[Session], cohort: str, track: str
    ) -> None:
        self.c, self.factory, self.cohort, self.track = c, factory, cohort, track
        self.t1 = h("teacher", DEVICES[0])
        self.t2 = h("teacher", DEVICES[1])

    def url(self, tail: str, n: int = 1) -> str:
        return f"/api/modules/tracks/{self.track}/modules/{n}/{tail}"

    def answer(self, answer: str = "partly", note: str = NOTE) -> None:
        r = self.c.post(
            self.url("feedback"), json={"answer": answer, "note": note}, headers=self.t1
        )
        assert r.status_code == 200, r.text

    def posts(self, headers: dict[str, str] | None = None) -> list[dict[str, Any]]:
        r = self.c.get(f"/api/cohorts/{self.cohort}/thread", headers=headers or self.t2)
        assert r.status_code == 200, r.text
        return list(r.json()["posts"])

    def draft(self, **fields: bool) -> dict[str, Any]:
        r = self.c.post(self.url("checkin/draft"), json={"fields": fields or None}, headers=self.t1)
        assert r.status_code == 200, r.text
        return dict(r.json())

    def share(self, text: str | None = None, **kw: Any) -> Any:
        body = {"text": text if text is not None else self.draft()["text"], **kw}
        return self.c.post(self.url("checkin/share"), json=body, headers=self.t1)


@pytest.fixture
def world(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[World]:
    monkeypatch.setenv("JUDGE_MODE", "1")
    monkeypatch.setenv("AI_MODE", "recorded")
    clock = {"t": T0}
    monkeypatch.setattr(modules_api, "clock", lambda: clock["t"])
    monkeypatch.setattr(
        review,
        "review_note",
        lambda **kw: type(
            "R",
            (),
            {
                "output": FeedbackReview(
                    focus_tags=["regrouping"],
                    barrier_tags=["children_confused"],
                    follow_ups=[FollowUpPick(bank_id="fu_where_stuck")],
                    confidence=0.9,
                ),
                "fell_back": False,
                "run": None,
            },
        )(),
    )
    engine = make_engine(f"sqlite:///{tmp_path / 'c.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def session() -> Iterator[Session]:
        with factory() as s:
            yield s

    app = create_app()
    app.dependency_overrides[get_session] = session
    c = TestClient(app)
    made = c.post(
        "/api/cohorts/officer/cohorts",
        json={
            "error": "SUB-SFL",
            "coach_id": "coach-1",
            "mentor_ids": ["mentor-1"],
            "school_count": 7,
        },
        headers=h("officer", person="officer-1"),
    ).json()
    space = made["id"]
    assert (
        c.post(
            f"/api/cohorts/officer/cohorts/{space}/status",
            json={"to": "active"},
            headers=h("officer"),
        ).status_code
        == 200
    )
    for d in DEVICES[:5]:
        assert (
            c.post(
                f"/api/cohorts/{space}/join", json={"consent": True}, headers=h("teacher", d)
            ).status_code
            == 200
        )
    cid = c.post("/api/cohorts/class-only", json=BODY, headers=h("teacher", DEVICES[0])).json()[
        "id"
    ]
    tid = c.post(
        "/api/modules/tracks",
        json={"cohort_id": cid, "error": "SUB-SFL"},
        headers=h("teacher", DEVICES[0]),
    ).json()["id"]
    w = World(c, factory, space, tid)
    w.clock = clock  # type: ignore[attr-defined]
    yield w


# ---- private by default --------------------------------------------------------------------------


def test_nothing_is_in_the_chat_before_she_confirms(world: World) -> None:
    world.answer()
    world.c.post(world.url("review"), headers=world.t1)  # the AI review runs; still private
    world.draft()  # even a draft is not a post
    assert world.posts() == []
    assert world.c.get(world.url("checkin"), headers=world.t1).json()["share"]["shared"] is False


def test_dont_share_leaves_the_chat_empty_and_her_check_in_hers(world: World) -> None:
    world.answer()
    state = world.c.get(world.url("checkin"), headers=world.t1).json()
    assert (
        state["answer"] == "partly"
        and "[child]" in state["note"]
        and "Ravi" not in json.dumps(state)
    )
    assert world.posts() == [] and world.posts(h("mentor", person="mentor-1")) == []
    assert (
        world.c.get(world.url("checkin"), headers=world.t2).status_code == 403
    )  # another teacher's track


def test_her_note_is_visible_to_nobody_else_before_sharing(world: World) -> None:
    world.answer()
    for headers in (world.t2, h("coach"), h("mentor", person="mentor-1"), h("officer")):
        r = world.c.get(world.url("checkin"), headers=headers)
        assert r.status_code in (403, 422), (headers, r.status_code)
        assert NOTE not in r.text
    for path in (
        f"/api/modules/coach/cohorts/{BODY_COHORT(world)}",
        f"/api/modules/mentor/cohorts/{BODY_COHORT(world)}",
    ):
        r = world.c.get(
            path, headers=h("coach", person="coach-1") if "coach" in path else h("mentor", person="mentor-1")
        )
        assert r.status_code == 200
        assert (
            "Ravi" not in r.text and "children were quiet" not in r.text and "[child]" not in r.text
        )
        assert r.json()["modules"][0]["feedback"] == {
            "worked": 0,
            "partly": 1,
            "not_yet": 0,
            "not_tried": 0,
        }


def BODY_COHORT(world: World) -> str:  # noqa: N802 - the class-only cohort id of T1
    with world.factory() as db:
        from services.api.db import ClassCohort

        return str(db.execute(select(ClassCohort.id)).scalar_one())


# ---- the draft is built by code, masked, and blocked when it still identifies someone --------------


def test_the_draft_is_built_by_code_from_the_answer_the_tags_and_the_masked_note(
    world: World,
) -> None:
    world.answer()
    world.c.post(world.url("review"), headers=world.t1)
    text = world.draft()["text"]
    assert text.startswith("Module 1,") and "it partly worked" in text
    assert "[child]" in text and "Ravi" not in text
    assert (
        "The children were confused" in text or "children were confused" in text.lower()
    )  # a validated tag, written by code
    assert "Any ideas for: Opening a ten?" in text
    assert "%" not in text and "roll" not in text.lower()


def test_unticked_parts_are_left_out_and_counts_and_name_are_off_by_default(world: World) -> None:
    world.answer()
    assert "of 16 children" not in world.draft()["text"]  # counts are off by default
    only_how = world.draft(how=True, note=False, help=False, counts=False)["text"]
    assert only_how.startswith("Module 1") and "[child]" not in only_how and "ideas" not in only_how
    with_counts = world.draft(counts=True)["text"]
    assert "5 of 16 children showed this mistake." in with_counts


@pytest.mark.parametrize(
    ("edit", "problem"),
    [
        ("Ravi could not open the ten.", "child_name"),
        ("Roll 14 could not open the ten.", "roll_number"),
        ("Call me on 9876543210 for ideas.", "phone_or_id"),
        ("About 40% of them could not open a ten.", "percent"),
        ("It came from class cc-3fa9b2c1 in my check.", "class_code"),
        ("Mail me at a.b@example.com.", "email"),
    ],
)
def test_share_is_blocked_when_something_identifying_remains(
    world: World, edit: str, problem: str
) -> None:
    world.answer()
    r = world.share(edit)
    assert (
        r.status_code == 422
        and r.json()["detail"]["code"] == "blocked"
        and problem in r.json()["detail"]["problems"]
    )
    assert world.posts() == []
    assert (
        problem
        in world.c.post(world.url("checkin/draft"), json={"text": edit}, headers=world.t1).json()[
            "problems"
        ]
    )


def test_a_summary_that_names_a_child_through_a_relative_is_blocked_too(world: World) -> None:
    world.answer()
    assert world.share("Priya's sister could not do it.").status_code == 422


# ---- sharing ---------------------------------------------------------------------------------------


def test_share_posts_one_anonymous_card_that_peers_the_mentor_and_the_coach_can_see(
    world: World,
) -> None:
    world.answer()
    text = world.draft()["text"]
    r = world.share(text)
    assert r.status_code == 200 and r.json()["share"]["shared"] is True
    for viewer in (
        world.posts(world.t2),
        world.posts(h("mentor", person="mentor-1")),
        world.c.get(
            f"/api/cohorts/coach/cohorts/{world.cohort}/thread",
            headers=h("coach", person="coach-1"),
        ).json(),
    ):
        card = next(p for p in viewer if p.get("kind") == "checkin_summary")
        assert card["author_name"] == "A teacher in this cohort" and card["body"] == text
        assert card["checkin"] == {"module": 1, "answer": "partly", "anonymous": True}
        assert DEVICES[0] not in json.dumps(card) and "teacher_id" not in json.dumps(card)


def test_naming_posts_under_her_chat_name_never_a_real_name(world: World) -> None:
    world.answer()
    world.share(named=True)
    card = next(p for p in world.posts() if p.get("kind") == "checkin_summary")
    assert card["author_name"].startswith("Teacher ") and card["checkin"]["anonymous"] is False


def test_pressing_share_twice_makes_one_post(world: World) -> None:
    world.answer()
    text = world.draft()["text"]
    assert world.share(text).status_code == 200 and world.share(text).status_code == 200
    assert len([p for p in world.posts() if p.get("kind") == "checkin_summary"]) == 1
    with world.factory() as db:
        assert len(db.execute(select(CheckinShare)).scalars().all()) == 1
        assert len(db.execute(select(ThreadPost)).scalars().all()) == 1


def test_an_edit_is_checked_again_on_share_and_stored_with_the_fields_and_the_time(
    world: World,
) -> None:
    world.answer()
    r = world.share(
        "Module 1: it partly worked. Any ideas for a quick warm-up?",
        fields={"how": True, "note": False, "help": False, "counts": False, "name": False},
    )
    assert r.status_code == 200
    with world.factory() as db:
        row = db.execute(select(CheckinShare)).scalar_one()
        assert row.posted_text == "Module 1: it partly worked. Any ideas for a quick warm-up?"
        assert (
            row.fields["note"] is False
            and row.fields["how"] is True
            and row.shared_at is not None
            and row.retracted_at is None
        )


def test_retract_hides_the_card_and_is_audited_and_she_can_share_again(world: World) -> None:
    world.answer()
    world.share()
    r = world.c.post(world.url("checkin/retract"), headers=world.t1)
    assert (
        r.status_code == 200
        and r.json()["share"]["shared"] is False
        and r.json()["share"]["retracted"] is True
    )
    assert [p for p in world.posts() if p.get("kind") == "checkin_summary"] == []
    with world.factory() as db:
        actions = [a.action for a in db.execute(select(CohortAuditRow)).scalars()]
        assert "checkin_shared" in actions and "checkin_retracted" in actions
        row = db.execute(select(CheckinShare)).scalar_one()
        assert row.retracted_at is not None
        assert "partly" not in json.dumps(
            [a.detail for a in db.execute(select(CohortAuditRow)).scalars()]
        )  # ids and codes only
    assert world.share().status_code == 200  # sharing again makes a new post
    assert len([p for p in world.posts() if p.get("kind") == "checkin_summary"]) == 1


def test_share_later_stays_open_until_the_next_module_is_made(world: World) -> None:
    world.answer("worked", "")
    state = world.c.get(world.url("checkin"), headers=world.t1).json()
    assert state["share"]["share_later_open"] is True and state["share"]["can_share"] is True
    world.clock["t"] += timedelta(days=1)  # type: ignore[attr-defined]
    assert (
        world.c.post(f"/api/modules/tracks/{world.track}/next", headers=world.t1).status_code == 200
    )
    r = world.share("Module 1: it worked.")
    assert r.status_code == 409 and r.json()["detail"]["code"] == "share_closed"


def test_a_help_request_goes_through_the_existing_question_flow(world: World) -> None:
    world.answer()
    world.share(ai_help=False)
    with world.factory() as db:
        q = db.execute(select(ChatMessage)).scalars().all()
        assert (
            len(q) == 1
            and q[0].kind == "question"
            and q[0].status == "pending"
            and q[0].ai_consent is False
        )
        assert "Module 1" in (q[0].body or "") and "Ravi" not in (q[0].body or "")


def test_no_help_ticked_asks_no_question(world: World) -> None:
    world.answer()
    world.share(
        world.draft(help=False)["text"],
        fields={"how": True, "note": True, "help": False, "counts": False, "name": False},
    )
    with world.factory() as db:
        assert db.execute(select(ChatMessage)).scalars().all() == []


# ---- who can see the chat ------------------------------------------------------------------------


def test_a_teacher_outside_the_cohort_and_an_officer_cannot_read_the_chat(world: World) -> None:
    world.answer()
    world.share()
    assert (
        world.c.get(
            f"/api/cohorts/{world.cohort}/thread", headers=h("teacher", DEVICES[5])
        ).status_code
        == 403
    )
    assert world.c.get(f"/api/cohorts/{world.cohort}/thread", headers=h("officer")).status_code in (
        403,
        422,
    )


def test_the_thread_must_be_open_to_share(world: World) -> None:
    world.answer()
    with world.factory() as db:  # fewer than 5 members: the thread is read-only
        from services.api.cohorts import thread
        from services.api.db import CohortMember
        from services.modules.models import Track

        mine = db.get(Track, world.track).teacher_id
        for m in (
            db.execute(select(CohortMember).where(CohortMember.cohort_id == world.cohort))
            .scalars()
            .all()
        ):
            if (
                m.teacher_id != mine
                and len(
                    db.execute(select(CohortMember).where(CohortMember.cohort_id == world.cohort))
                    .scalars()
                    .all()
                )
                > 4
            ):
                thread.leave(db, world.cohort, m.teacher_id)
    r = world.share()
    assert r.status_code == 409 and r.json()["detail"]["code"] == "thread_closed"
    assert world.c.get(world.url("checkin"), headers=world.t1).json()["share"]["shared"] is False


# ---- the Open cohort chat button -----------------------------------------------------------------


def test_the_chat_button_state_for_a_member_and_for_a_cohort_with_no_chat(
    world: World, tmp_path: Path
) -> None:
    r = world.c.get(f"/api/modules/tracks/{world.track}/chat", headers=world.t1).json()
    assert (
        r["available"] is True
        and r["cohort_id"] == world.cohort
        and r["open"] is True
        and r["unread"] == 0
    )
    world.answer()
    world.share()
    # a peer's post is new to her; her own is not
    since = (T0 - timedelta(hours=1)).isoformat()
    world.c.post(
        f"/api/cohorts/{world.cohort}/posts",
        json={"body": "I used bundles today and it helped.", "language": "en"},
        headers=world.t2,
    )
    assert (
        world.c.get(
            f"/api/modules/tracks/{world.track}/chat", params={"since": since}, headers=world.t1
        ).json()["unread"]
        == 1
    )
    # a teacher in no chat sees "No peers yet"
    other = h("teacher", DEVICES[5])
    cid = world.c.post(
        "/api/cohorts/class-only", json={**BODY, "check_id": "c-other:1"}, headers=other
    ).json()["id"]
    tid = world.c.post(
        "/api/modules/tracks", json={"cohort_id": cid, "error": "SUB-SFL"}, headers=other
    ).json()["id"]
    r = world.c.get(f"/api/modules/tracks/{tid}/chat", headers=other).json()
    assert r["available"] is False and r["reason"] == "no_peers"
    assert (
        world.c.post(
            f"/api/modules/tracks/{tid}/modules/1/feedback",
            json={"answer": "worked", "note": ""},
            headers=other,
        ).status_code
        == 200
    )
    s = world.c.post(
        f"/api/modules/tracks/{tid}/modules/1/checkin/share",
        json={"text": "Module 1: it worked."},
        headers=other,
    )
    assert s.status_code == 409 and s.json()["detail"]["code"] == "no_peers"


# ---- the safety path ------------------------------------------------------------------------------


def test_a_safety_flag_tells_the_coach_nothing_unless_she_presses_the_button(world: World) -> None:
    world.answer("partly", "a boy was hit at home")
    r = world.c.post(world.url("review"), headers=world.t1).json()
    assert r["state"] == "safety" and r["safety"] is True and r["follow_ups"] == []
    coach = world.c.get(
        f"/api/modules/coach/cohorts/{BODY_COHORT(world)}", headers=h("coach", person="coach-1")
    ).json()
    assert coach["call_me"] == 0 and "hit" not in json.dumps(coach)
    assert world.c.post(world.url("checkin/call-me"), headers=world.t1).status_code == 200
    coach = world.c.get(
        f"/api/modules/coach/cohorts/{BODY_COHORT(world)}", headers=h("coach", person="coach-1")
    ).json()
    assert coach["call_me"] == 1 and "hit" not in json.dumps(coach)
    with world.factory() as db:
        from services.modules.models import ModuleEvent

        ev = db.execute(
            select(ModuleEvent).where(ModuleEvent.event == "call_me_requested")
        ).scalar_one()
        assert ev.detail == {}  # no content
        assert db.execute(select(CheckinShare)).scalars().all() == []  # nothing was shared


def test_the_call_button_is_refused_when_there_is_no_safety_flag(world: World) -> None:
    world.answer("worked", "fine")
    assert world.c.post(world.url("checkin/call-me"), headers=world.t1).status_code == 409


# ---- the whole flow: T1 shares, T2 and the coach see it; and the run where she does not -----------


def test_end_to_end_partly_with_a_name_a_follow_up_a_masked_summary_shared_and_seen(
    world: World,
) -> None:
    world.answer("partly", NOTE)
    rv = world.c.post(world.url("review"), headers=world.t1).json()
    assert rv["state"] == "asked" and rv["follow_ups"][0]["id"] == "fu_where_stuck"
    done = world.c.post(
        world.url("review/answers"),
        json={"answers": [{"id": "fu_where_stuck", "chip": "middle"}]},
        headers=world.t1,
    )
    assert done.status_code == 200 and done.json()["changes"] and "puts" in done.json()["changes"]
    draft = world.draft()
    assert draft["problems"] == [] and "Ravi" not in draft["text"] and "[child]" in draft["text"]
    assert world.share(draft["text"]).status_code == 200
    peer = next(p for p in world.posts(world.t2) if p.get("kind") == "checkin_summary")
    assert peer["body"] == draft["text"] and "Ravi" not in json.dumps(peer)
    coach = world.c.get(
        f"/api/cohorts/coach/cohorts/{world.cohort}/thread", headers=h("coach", person="coach-1")
    ).json()
    assert any(p.get("kind") == "checkin_summary" for p in coach)


def test_end_to_end_when_she_does_not_share_her_peer_sees_nothing(world: World) -> None:
    world.answer("partly", NOTE)
    world.c.post(world.url("review"), headers=world.t1)
    world.c.post(world.url("review/answers"), json={"skip": True}, headers=world.t1)
    assert world.posts(world.t2) == []
    with world.factory() as db:
        assert (
            db.execute(select(ThreadPost)).scalars().all() == []
            and db.execute(select(CheckinShare)).scalars().all() == []
        )


# ---- strings in three languages ---------------------------------------------------------------------


@pytest.mark.parametrize("lang", ["en", "hi", "ta"])
def test_the_check_in_strings_exist_with_their_slots(lang: str) -> None:
    t = json.loads((STRINGS / f"{lang}.json").read_text(encoding="utf-8"))
    for k in (
        "module.checkin.private",
        "module.share.title",
        "module.share.exact",
        "module.share.btn",
        "module.share.no",
        "module.share.edit",
        "module.share.later",
        "module.share.retract",
        "module.chat.open",
        "module.safety.call_me",
        "module.safety.called",
        "module.share.no_peers",
        "module.share.offline",
        "module.card.title",
    ):
        assert t.get(k), (lang, k)
    for f in checkin.FIELDS:
        assert t.get(f"module.share.field.{f}"), (lang, f)
    for a in ("worked", "partly", "not_yet", "not_tried"):
        assert t.get(f"module.share.answer.{a}"), (lang, a)
    assert (
        "{n}" in t["module.share.how"]
        and "{title}" in t["module.share.how"]
        and "{answer}" in t["module.share.how"]
    )
    assert "{k}" in t["module.share.counts"] and "{n}" in t["module.share.counts"]
    assert "%" not in t["module.share.counts"]
    assert "{what}" in t["module.share.blocked"]
    for kind in (
        "child_name",
        "relative",
        "roll_number",
        "phone_or_id",
        "email",
        "percent",
        "class_code",
        "other",
        "empty",
        "length",
    ):
        assert t.get(f"module.share.block.{kind}"), (lang, kind)
