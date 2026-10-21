"""One pseudonymous teacher across channels: linking by a one-time code, expiry, deletion."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from services.api.db import ChannelLink, LinkCode, Teacher
from services.api.flows.engine import FlowEngine
from services.api.flows.links import sign, verify

from .test_engine import DEVICE, onboard


def test_the_same_external_id_is_the_same_teacher_and_ids_are_random(db: Session) -> None:
    eng = FlowEngine(db)
    a = eng.teacher_for("pwa", DEVICE)
    assert eng.teacher_for("pwa", DEVICE).teacher_id == a.teacher_id
    b = eng.teacher_for("telegram", "777")
    assert (
        b.teacher_id != a.teacher_id and a.teacher_id.startswith("t-") and len(a.teacher_id) == 18
    )


def test_a_code_made_in_the_web_app_links_the_bot_to_the_same_teacher_and_state(
    db: Session,
) -> None:
    eng = FlowEngine(db)
    web = eng.teacher_for("pwa", DEVICE)
    onboard(eng, web, "hi")
    code = eng.new_code(web)
    assert len(code) == 8 and code == eng.new_code(web)  # one live code at a time
    bot = eng.link(code, "telegram", "555")
    assert bot is not None and bot.teacher_id == web.teacher_id
    assert eng.teacher_for("telegram", "555").teacher_id == web.teacher_id
    assert eng.start(bot).steps[-1].id == "menu"  # the bot continues where the web app stopped
    assert bot.lang == "hi"
    assert db.get(LinkCode, code) is None  # a code works once


def test_an_unknown_or_expired_code_links_nothing(db: Session) -> None:
    eng = FlowEngine(db)
    web = eng.teacher_for("pwa", DEVICE)
    assert eng.link("NOSUCHCD", "telegram", "555") is None
    code = eng.new_code(web)
    row = db.get(LinkCode, code)
    assert row is not None
    row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()
    assert eng.link(code, "telegram", "555") is None
    assert db.query(ChannelLink).filter_by(channel="telegram").count() == 0


def test_a_bot_teacher_who_links_is_replaced_by_the_web_teacher_and_the_old_record_is_erased(
    db: Session,
) -> None:
    eng = FlowEngine(db)
    bot_first = eng.teacher_for("telegram", "555")
    eng.start(bot_first)
    web = eng.teacher_for("pwa", DEVICE)
    onboard(eng, web, "en")
    eng.link(eng.new_code(web), "telegram", "555")
    assert db.get(Teacher, bot_first.teacher_id) is None  # her earlier, separate record is gone
    assert eng.teacher_for("telegram", "555").teacher_id == web.teacher_id


def test_signed_links_verify_and_a_changed_token_does_not() -> None:
    token = sign({"lang": "ta", "scenario": "SUB-SFL"})
    assert verify(token) == {"lang": "ta", "scenario": "SUB-SFL"}
    assert verify(token[:-2] + "xx") is None
    assert verify("garbage") is None
    assert verify(sign({"lang": "ta"}, ttl_s=-1)) is None  # expired


def test_delete_also_removes_her_consent_history_and_stop_asks_first(db: Session) -> None:
    from services.api.db import Consent

    eng = FlowEngine(db)
    t = eng.teacher_for("pwa", DEVICE)
    onboard(eng, t, "en")
    db.add(Consent(subject_id=DEVICE, scope="counts.v1", granted=True))
    db.commit()
    assert eng.ask_delete(t).steps[-1].id == "confirm_delete"
    assert db.query(Teacher).count() == 1  # asking deletes nothing
    eng.answer(t, "confirm_delete", "yes")
    assert db.query(Consent).filter_by(subject_id=DEVICE).count() == 0


def test_a_judge_flag_in_the_request_does_nothing_unless_the_deployment_is_the_demo(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    eng = FlowEngine(db)
    monkeypatch.setenv("JUDGE_MODE", "0")
    assert eng.teacher_for("telegram", "1", judge=True).judge is False
    monkeypatch.setenv("JUDGE_MODE", "1")
    assert eng.teacher_for("telegram", "2", judge=True).judge is True
