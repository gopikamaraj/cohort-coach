"""The two-class run over HTTP, with no paid call: a stub AI client that answers nothing (so lessons
fall back to the code-written text and the chat AI abstains) and a fake voice provider."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from ai.client import CallContext
from services.api import practice as practice_api
from services.api.db import Base, ChatMessage, ReviewItem, make_engine
from services.api.main import create_app
from services.api.profiles import get_session
from services.cohort_run import service as svc
from tests.support_ai import FakeClient

RID = "run-0123456789abcdef"
# "Ask the child to show it with bundles of ten." in Hindi: the reply is checked in her language
REPLY_HI = "बच्चे से दस की गड्डियों से दिखाने को कहें।"
API = f"/api/cohort-run/runs/{RID}"


class Speech:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    def synthesize(self, text: str, lang: str, voice: object) -> bytes:
        self.calls += 1
        if self.fail:
            raise ConnectionError("voice provider down")
        return b"RIFF-fake-" + lang.encode()


class Env:
    def __init__(self, c: TestClient, speech: Speech, factory: Any) -> None:
        self.c, self.speech, self.factory = c, speech, factory


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Env]:
    monkeypatch.setenv("JUDGE_MODE", "1")
    monkeypatch.setenv("DEMO_CACHE_DIR", str(tmp_path / "cache"))
    import services.speech.audio as audio

    monkeypatch.setattr(audio, "join_to_file", lambda clips, fmt="mp3": (b"".join(clips), 61.0))
    engine = make_engine(f"sqlite:///{tmp_path / 'run.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    app = create_app()

    def session() -> Iterator[object]:
        with factory() as s:
            yield s

    speech = Speech()
    app.dependency_overrides[get_session] = session
    app.dependency_overrides[practice_api.get_ai_context] = lambda: CallContext(
        mode="stub", client=FakeClient([])
    )
    app.dependency_overrides[practice_api.get_speech] = lambda: speech
    yield Env(TestClient(app), speech, factory)


def ok(r: Any) -> dict[str, Any]:
    assert r.status_code == 200, r.text[:800]
    return dict(r.json())


def start(e: Env) -> None:
    ok(e.c.post("/api/cohort-run/runs", json={"run": RID}))


def both_checks(e: Env) -> dict[str, Any]:
    start(e)
    ok(e.c.post(f"{API}/classes/3A/check", json={"as": "T1"}))
    return ok(e.c.post(f"{API}/classes/3B/check", json={"as": "T2"}))


def lesson(view: dict[str, Any], lid: str) -> dict[str, Any]:
    return next(x for x in view["lessons"] if x["id"] == lid)


# --- flow 1 -------------------------------------------------------------------------------------


def test_refused_outside_the_judge_deployment(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("JUDGE_MODE", "0")
    assert env.c.post("/api/cohort-run/runs", json={"run": RID}).status_code == 404


def test_the_first_class_waits_and_sees_only_her_class(env: Env) -> None:
    start(env)
    v = ok(env.c.post(f"{API}/classes/3A/check", json={"as": "T1"}))
    assert v["status"] == "waiting_for_classes" and v["simulated"] is True
    assert v["class"]["code"] == "3A" and v["cohort"] is None
    assert v["waiting"][0]["have"] == 1 and v["waiting"][0]["min_classes"] == 2
    t2 = ok(env.c.get(API, params={"as": "T2"}))
    assert t2["class"] is None  # T2 has not submitted, and never sees 3A's counts


def test_only_the_classs_teacher_submits_it(env: Env) -> None:
    start(env)
    assert env.c.post(f"{API}/classes/3B/check", json={"as": "T1"}).status_code == 403


def test_a_per_child_payload_is_refused(env: Env) -> None:
    start(env)
    r = env.c.post(
        f"{API}/classes/3A/check",
        json={"as": "T1", "synthetic": False, "children_checked": 16, "rows": [[1, 2, 3]]},
    )
    assert r.status_code == 422


def test_phone_counts_are_checked(env: Env) -> None:
    start(env)
    bad = {"as": "T1", "synthetic": False, "children_checked": 5, "counts": {"SUB-SFL": 9}}
    assert env.c.post(f"{API}/classes/3A/check", json=bad).status_code == 422
    good = {
        "as": "T1",
        "synthetic": False,
        "children_checked": 16,
        "counts": {"SUB-NODEC": 1},
        "possible": {"SUB-SFL": 4},
    }
    v = ok(env.c.post(f"{API}/classes/3A/check", json=good))
    assert v["class"]["source"] == "phone"


def test_the_second_class_forms_the_cohort_automatically(env: Env) -> None:
    v = both_checks(env)
    assert v["status"] == "formed"
    c = v["cohort"]
    assert c["error"] == "SUB-SFL" and c["classes"] == 2 and c["teachers"] == 2
    assert c["labels"] == ["Pilot cohort, two classes", "Based on one question per child"]
    assert c["mentor"]["suggested"] is False and c["mentor"]["reason"] == "no_other_class"
    assert v["class"]["errors"]["SUB-SFL"]["code"] == "in"
    # was under_line (4 of 18, under the 25% line removed on 2 Nov); one cohort per mistake puts her in ADD-NOCARRY too
    assert v["class"]["errors"]["ADD-NOCARRY"]["code"] == "in"
    coach = ok(env.c.get(API, params={"as": "C1"}))
    kinds = [e["kind"] for e in coach["timeline"]]
    assert kinds[:4] == ["check_submitted", "waiting", "check_submitted", "cohort_formed"]


def test_the_coach_button_runs_formation(env: Env) -> None:
    start(env)
    ok(env.c.post(f"{API}/classes/3A/check", json={"as": "T1"}))
    v = ok(env.c.post(f"{API}/form"))
    assert v["status"] == "waiting_for_classes"
    assert v["timeline"][-1]["facts"]["by"] == "coach"


# --- flow 2 -------------------------------------------------------------------------------------


def test_lesson_one_per_language_goes_to_review_then_out(env: Env) -> None:
    both_checks(env)
    coach = ok(env.c.get(API, params={"as": "C1"}))
    by_lang = {x["language"]: x for x in coach["lessons"]}
    assert set(by_lang) == {"en", "hi"}
    assert all(x["status"] == "in_review" for x in coach["lessons"])
    assert by_lang["en"]["sources"][0]["kind"] == "track"
    with env.factory() as db:
        item = db.get(ReviewItem, by_lang["en"]["review_item"])
        assert item is not None and item.status == "pending"
        assert item.content["cohort_id"].startswith("co-run-")
    t1 = ok(env.c.get(API, params={"as": "T1"}))
    assert lesson(t1, "L1-en")["script"] is None  # not before the coach approves
    ok(env.c.post(f"{API}/lessons/L1-en/decide", json={"decision": "approve"}))
    t1 = ok(env.c.get(API, params={"as": "T1"}))
    l1 = lesson(t1, "L1-en")
    assert l1["status"] == "released" and l1["audio"]["seconds"] == 61.0
    assert "4 of 16 children" in l1["script"]  # her class's numbers, filled by code
    assert "{{" not in l1["script"]
    t2 = ok(env.c.get(API, params={"as": "T2"}))
    assert [x["id"] for x in t2["lessons"]] == ["L1-hi"]  # her language's version
    r = env.c.get(f"{API}/lessons/L1-en/audio", params={"as": "T1", "download": "true"})
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    assert env.c.get(f"{API}/lessons/L1-en/audio", params={"as": "T2"}).status_code == 403
    assert env.c.get(f"{API}/lessons/L1-hi/audio", params={"as": "T2"}).status_code == 403


def test_a_voice_failure_leaves_text_logs_it_and_can_be_retried(
    env: Env, caplog: pytest.LogCaptureFixture
) -> None:
    env.speech.fail = True
    with caplog.at_level(logging.WARNING, logger="services.cohort_run.service"):
        both_checks(env)
    assert any("voice failed" in r.message and "lesson=L1-en" in r.message for r in caplog.records)
    assert not any("children" in r.message for r in caplog.records)  # ids only, never the text
    ok(env.c.post(f"{API}/lessons/L1-en/decide", json={"decision": "approve"}))
    l1 = lesson(ok(env.c.get(API, params={"as": "T1"})), "L1-en")
    assert l1["audio"] is None and l1["voice_error"] == "ConnectionError" and l1["script"]
    env.speech.fail = False
    l1 = lesson(ok(env.c.post(f"{API}/lessons/L1-en/voice", json={"as": "T1"})), "L1-en")
    assert l1["audio"] is not None and l1["voice_error"] is None


# --- flow 3 -------------------------------------------------------------------------------------


def released(env: Env) -> None:
    both_checks(env)
    for lid in ("L1-en", "L1-hi"):
        ok(env.c.post(f"{API}/lessons/{lid}/decide", json={"decision": "approve"}))


def test_feedback_only_after_playing_and_the_note_is_masked(env: Env) -> None:
    released(env)
    fb = {"as": "T1", "answer": "not_yet", "note": "Meena still writes 365, roll no 7 too"}
    assert env.c.post(f"{API}/lessons/L1-en/feedback", json=fb).status_code == 409
    ok(env.c.post(f"{API}/lessons/L1-en/played", json={"as": "T1"}))
    v = ok(env.c.post(f"{API}/lessons/L1-en/feedback", json=fb))
    saved = lesson(v, "L1-en")["feedback"]
    assert (
        saved["answer"] == "not_yet" and "Meena" not in saved["note"] and "7" not in saved["note"]
    )
    assert lesson(v, "L1-en")["can_generate"] is True
    coach = ok(env.c.get(API, params={"as": "C1"}))
    l1 = coach["cohorts"][0]["lesson1"]
    assert l1["feedback"] == {"tried": 0, "partly": 0, "not_yet": 1} and l1["plays"] == 1
    assert "Meena" not in json.dumps(coach)


def test_marked_heard_also_opens_feedback(env: Env) -> None:
    released(env)
    ok(env.c.post(f"{API}/lessons/L1-hi/played", json={"as": "T2", "heard": True}))
    v = ok(env.c.post(f"{API}/lessons/L1-hi/feedback", json={"as": "T2", "answer": "tried"}))
    assert lesson(v, "L1-hi")["feedback"]["answer"] == "tried"
    coach = ok(env.c.get(API, params={"as": "C1"}))
    assert coach["cohorts"][0]["lesson1"]["heard"] == 1


@pytest.mark.parametrize(
    ("answer", "day", "mode"),
    [("tried", 2, "next"), ("partly", 1, "smaller_step"), ("not_yet", 3, "other_approach")],
)
def test_generate_next_lesson_follows_her_answer(
    env: Env, answer: str, day: int, mode: str
) -> None:
    released(env)
    ok(env.c.post(f"{API}/lessons/L1-en/played", json={"as": "T1"}))
    ok(env.c.post(f"{API}/lessons/L1-en/feedback", json={"as": "T1", "answer": answer}))
    out = ok(env.c.post(f"{API}/next", json={"as": "T1"}))
    assert out["next"]["decision"]["day"] == day and out["next"]["decision"]["mode"] == mode
    l2 = lesson(out, "L2-T1")
    assert l2["status"] == "in_review" and l2["decision"]["answer"] == answer
    assert env.c.post(f"{API}/next", json={"as": "T1"}).status_code == 409  # once
    ok(env.c.post(f"{API}/lessons/L2-T1/decide", json={"decision": "approve"}))
    l2 = lesson(ok(env.c.get(API, params={"as": "T1"})), "L2-T1")
    assert l2["status"] == "released" and l2["script"]
    if mode == "smaller_step":
        assert "one small step" in l2["script"]


def test_generate_next_needs_feedback_first_and_the_coach_may_press_it(env: Env) -> None:
    released(env)
    assert env.c.post(f"{API}/next", json={"as": "T2"}).status_code == 409
    ok(env.c.post(f"{API}/lessons/L1-hi/played", json={"as": "T2"}))
    ok(env.c.post(f"{API}/lessons/L1-hi/feedback", json={"as": "T2", "answer": "tried"}))
    out = ok(env.c.post(f"{API}/next", json={"as": "C1", "teacher": "T2"}))
    assert out["next"]["lesson"] == "L2-T2"


def test_silence_releases_the_planned_lesson_and_is_not_counted(env: Env) -> None:
    released(env)
    ok(env.c.post(f"{API}/lessons/L1-en/played", json={"as": "T1"}))
    ok(env.c.post(f"{API}/lessons/L1-en/feedback", json={"as": "T1", "answer": "tried"}))
    early = ok(env.c.post(f"{API}/tick", json={"days": 1}))
    assert early["made"] == []
    later = ok(env.c.post(f"{API}/tick", json={"days": 2}))
    assert later["made"] == ["L2-T2"]  # T2 never answered; T1 did, so nothing for her
    l2 = next(x for x in later["lessons"] if x["id"] == "L2-T2")
    assert l2["decision"]["mode"] == "planned" and l2["decision"]["answer"] is None
    c = later["cohorts"][0]["lesson1"]
    assert c["feedback"] == {"tried": 1, "partly": 0, "not_yet": 0} and c["no_answer"] == 1


# --- flow 4 -------------------------------------------------------------------------------------


def test_chat_membership_masking_abstain_coach_reply_and_sharing(env: Env) -> None:
    both_checks(env)
    q = "मीना 703 में से 468 घटाने पर 365 लिखती है। मैं क्या करूँ?"
    name = "मीना"  # a made-up child's name (Meena), in Hindi: T2 writes Hindi
    assert env.c.post(f"{API}/chat/ask", json={"as": "T3", "text": q}).status_code == 403
    v = ok(env.c.post(f"{API}/chat/ask", json={"as": "T2", "text": q, "share": True}))
    mine = v["questions"][0]
    assert name not in mine["body"] and "[child]" in mine["body"] and mine["shared"] is True
    with env.factory() as db:
        stored = db.scalars(select(ChatMessage).where(ChatMessage.kind == "question")).one()
        assert name not in stored.body
    coach = ok(env.c.get(API, params={"as": "C1"}))
    pending = coach["inbox"]["pending"]
    assert len(pending) == 1 and pending[0]["draft"] is None  # the AI abstained (no draft)
    assert coach["cohorts"][0]["chat"]["open"] == 1
    tick = ok(env.c.post(f"{API}/chat/skip"))
    assert tick["tick"]["sent"] == 0  # nothing to auto-send without a draft; a person answers
    ok(env.c.post(f"{API}/chat/{pending[0]['id']}/reply", json={"mode": "own", "text": REPLY_HI}))
    t1 = ok(env.c.get(f"{API}/chat", params={"as": "T1"}))
    (shared,) = t1["cohort_shared"]
    assert name not in shared["body"] and shared["answers"][0]["body"] == REPLY_HI
    assert env.c.get(f"{API}/chat", params={"as": "T3"}).status_code == 403


def test_an_unshared_question_stays_private(env: Env) -> None:
    both_checks(env)
    ok(env.c.post(f"{API}/chat/ask", json={"as": "T1", "text": "How long should a lesson take?"}))
    assert ok(env.c.get(f"{API}/chat", params={"as": "T2"}))["cohort_shared"] == []


# --- flow 5 -------------------------------------------------------------------------------------


def test_role_limits_on_the_coach_view(env: Env) -> None:
    released(env)
    coach = ok(env.c.get(API, params={"as": "C1"}))
    c = coach["cohorts"][0]
    assert (c["classes"], c["teachers"], c["showing"], c["checked"]) == (2, 2, 9, 34)
    assert [x["status"] for x in c["lesson1"]["by_language"]] == ["released", "released"]
    assert c["next_check"] == "awaiting_next_check"
    mentor = ok(env.c.get(API, params={"as": "M1"}))
    assert mentor["cohorts"][0]["id"] == c["id"] and "inbox" not in mentor
    assert ok(env.c.get(API, params={"as": "M2"}))["cohorts"] == []
    officer = ok(env.c.get(API, params={"as": "officer"}))
    assert officer["totals"] == {"cohorts": 1, "classes": None, "feedback": None, "min_cell": 5}
    assert env.c.get(API, params={"as": "nobody"}).status_code == 403


def test_the_coach_view_has_no_child_level_data(env: Env) -> None:
    released(env)
    text = json.dumps(ok(env.c.get(API, params={"as": "C1"})))
    for word in ("roll", "answers", "rows", "child_id"):
        assert word not in text
    assert svc.MIN_CELL == 5


def test_lesson_one_is_worded_by_call_5_when_its_draft_comes_back(env: Env) -> None:
    """Recorded call 5 answers exist for the English lesson 1 (no paid call); Hindi has none, so
    its lesson is written by code from the same approved content. Both go to review."""
    app = env.c.app
    app.dependency_overrides[practice_api.get_ai_context] = lambda: CallContext(mode="recorded")  # type: ignore[attr-defined]
    both_checks(env)
    coach = ok(env.c.get(API, params={"as": "C1"}))
    src = {x["language"]: x["source"] for x in coach["lessons"]}
    assert src == {"en": "ai", "hi": "template"}
    en = next(x for x in coach["lessons"] if x["language"] == "en")
    assert "{{class.count_showing}}" in en["script"] or "{{track.day}}" in en["script"]  # slots
    ok(env.c.post(f"{API}/lessons/L1-en/decide", json={"decision": "approve"}))
    l1 = lesson(ok(env.c.get(API, params={"as": "T1"})), "L1-en")
    assert "{{" not in l1["script"]
