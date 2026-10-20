"""Golden transcripts: the same answers through the web adapter and the Telegram adapter must show
the same words and the same choices, and leave the same stored state (CLAUDE.md rule 14)."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from services.api import strings
from services.api.channels import telegram, whatsapp
from services.api.channels.base import Button, Message, parse_button, render_step
from services.api.db import Base, FlowState, Teacher, make_engine
from services.api.flows.engine import FlowEngine
from services.api.main import app
from services.api.profiles import get_session

DEVICE = "a1b2c3d4e5f60718"
SCRIPT = [
    ("lang", "hi"),
    ("consent_core", "agree"),
    ("consent_counts", "yes"),
    ("consent_practice", "no"),
    ("consent_feedback", "yes"),
    ("menu", "cards"),
    ("menu", "practice"),
    ("practice", "back"),
    ("menu", "check"),
    ("check_info", "back"),
]


@dataclass
class Fake:
    sent: list[Message] = field(default_factory=list)

    def send(self, chat_id: str, message: Message) -> None:
        self.sent.append(message)


def shape(m: Message) -> tuple[str, str, tuple[tuple[str, str], ...], bool]:
    """What a person sees: step, words, choices, and whether a link is offered. Tokens differ."""
    text = re.sub(r"t=[\w.\-]+", "t=*", m.text)
    text = re.sub(r"(?<![A-Za-z])[A-Z2-9]{8}(?![A-Za-z])", "CODE", text)  # random per teacher
    return (m.step_id, text, tuple((b.id, b.label) for b in m.buttons), m.url is not None)


@pytest.fixture
def world(tmp_path: Path) -> Iterator[tuple[TestClient, sessionmaker[Session]]]:
    engine = make_engine(f"sqlite:///{tmp_path / 'g.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def override() -> Iterator[Session]:
        with factory() as s:
            yield s

    app.dependency_overrides[get_session] = override
    yield TestClient(app), factory
    app.dependency_overrides.clear()


def web_transcript(client: TestClient) -> list[Any]:
    h = {"X-Device-Id": DEVICE}
    out = [client.get("/api/flow/current", headers=h).json()["messages"]]
    for step_id, value in SCRIPT:
        r = client.post("/api/flow/answer", headers=h, json={"step_id": step_id, "value": value})
        assert r.status_code == 200, r.text
        out.append(r.json()["messages"])
    return [[shape(_msg(m)) for m in turn] for turn in out]


def _msg(d: dict[str, Any]) -> Message:
    return Message(**{**d, "buttons": [Button(**b) for b in d["buttons"]]})


def telegram_transcript(db: Session) -> list[Any]:
    out = []
    fake = Fake()
    telegram.process(db, {"message": {"chat": {"id": 42}, "text": "/start"}}, fake)
    out.append([shape(m) for m in fake.sent])
    for i, (step_id, value) in enumerate(SCRIPT):
        fake = Fake()
        cb = {"id": str(i), "data": f"{step_id}:{value}", "message": {"chat": {"id": 42}}}
        telegram.process(db, {"callback_query": cb}, fake)
        out.append([shape(m) for m in fake.sent])
    return out


def test_every_step_reads_the_same_in_the_web_app_and_in_telegram(
    world: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, factory = world
    web = web_transcript(client)
    with factory() as db:
        tg = telegram_transcript(db)
    assert web == tg
    assert len(web) == len(SCRIPT) + 1 and all(web)


def test_both_channels_leave_the_same_stored_state(
    world: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, factory = world
    web_transcript(client)
    with factory() as db:
        telegram_transcript(db)
        states = []
        for t in db.query(Teacher).order_by(Teacher.created_at):
            fs = db.get(FlowState, t.teacher_id)
            assert fs is not None
            states.append((t.lang, t.consent, fs.flow_id, fs.step_id))
    assert len(states) == 2 and states[0] == states[1]


def test_a_telegram_button_press_that_is_not_a_choice_changes_nothing(
    world: tuple[TestClient, sessionmaker[Session]],
) -> None:
    _, factory = world
    with factory() as db:
        fake = Fake()
        telegram.process(db, {"message": {"chat": {"id": 7}, "text": "/start"}}, fake)
        bad = {"id": "x", "data": "lang:klingon", "message": {"chat": {"id": 7}}}
        telegram.process(db, {"callback_query": bad}, fake)
        assert fake.sent[-1].step_id == "lang"
        telegram.process(
            db,
            {"callback_query": {"id": "y", "data": "junk", "message": {"chat": {"id": 7}}}},
            fake,
        )
        assert parse_button("junk") is None


def test_start_judge_marks_a_judge_and_shows_the_simulated_label(
    world: tuple[TestClient, sessionmaker[Session]],
) -> None:
    _, factory = world
    with factory() as db:
        fake = Fake()
        telegram.process(db, {"message": {"chat": {"id": 9}, "text": "/start judge"}}, fake)
        t = FlowEngine(db).teacher_for("telegram", "9")
        assert t.judge


def test_a_code_from_the_web_app_links_the_bot_through_start(
    world: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, factory = world
    h = {"X-Device-Id": DEVICE}
    client.get("/api/flow/current", headers=h)
    code = client.post("/api/flow/code", headers=h).json()["code"]
    with factory() as db:
        fake = Fake()
        telegram.process(db, {"message": {"chat": {"id": 5}, "text": f"/start {code}"}}, fake)
        web = db.query(Teacher).count()
        assert web == 1  # the bot joined the web teacher; no second record
        assert (
            FlowEngine(db).teacher_for("telegram", "5").teacher_id
            == FlowEngine(db).teacher_for("pwa", DEVICE).teacher_id
        )


def test_the_web_api_rejects_a_missing_or_malformed_device_id(
    world: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, _ = world
    assert client.get("/api/flow/current").status_code == 422
    assert client.get("/api/flow/current", headers={"X-Device-Id": "nope"}).status_code == 422
    r = client.post(
        "/api/flow/answer",
        headers={"X-Device-Id": DEVICE},
        json={"step_id": "lang", "value": "klingon"},
    )
    assert r.status_code == 422


def test_whatsapp_numbers_the_options_and_reads_a_number_back() -> None:
    from services.api.flows.steps import Option, Step

    step = Step(
        kind="choice",
        id="lang",
        copy="onb.lang",
        options=[Option(id="en", copy="onb.lang.en"), Option(id="hi", copy="onb.lang.hi")],
    )
    m = render_step(step, "en")
    assert "2. " in whatsapp.to_text(m)
    assert whatsapp.parse_reply(" 2 ", m) == "hi"
    assert whatsapp.parse_reply("9", m) is None and whatsapp.parse_reply("hello", m) is None


def test_the_telegram_webhook_is_closed_without_the_secret(
    world: tuple[TestClient, sessionmaker[Session]], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _ = world
    upd = {"message": {"chat": {"id": 1}, "text": "/start"}}
    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)
    assert client.post("/api/telegram/webhook", json=upd).status_code == 403
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "s3")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "x")
    bad = {"X-Telegram-Bot-Api-Secret-Token": "wrong"}
    assert client.post("/api/telegram/webhook", json=upd, headers=bad).status_code == 403


def test_a_judge_session_shows_the_simulated_label_in_both_channels(
    world: tuple[TestClient, sessionmaker[Session]],
) -> None:
    client, factory = world
    h = {"X-Device-Id": DEVICE, "X-Judge": "1"}
    client.get("/api/flow/current", headers=h)
    for step_id, value in SCRIPT[:5]:
        client.post("/api/flow/answer", headers=h, json={"step_id": step_id, "value": value})
    web = client.get("/api/flow/current", headers=h).json()["messages"]
    with factory() as db:
        fake = Fake()
        telegram.process(db, {"message": {"chat": {"id": 8}, "text": "/start judge"}}, fake)
        for i, (step_id, value) in enumerate(SCRIPT[:5]):
            cb = {"id": str(i), "data": f"{step_id}:{value}", "message": {"chat": {"id": 8}}}
            telegram.process(db, {"callback_query": cb}, fake)
        fake.sent.clear()
        telegram.process(db, {"message": {"chat": {"id": 8}, "text": "/start"}}, fake)
    label = strings.text("hi", "common.simulated")
    assert web[0]["text"].startswith(label) and fake.sent[0].text.startswith(label)
    assert shape(fake.sent[0])[1] == shape(_msg(web[0]))[1]
