"""The flow engine: step types, transitions, consent, T1, deletion. No channel is involved."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from services.api import strings
from services.api.db import ChannelLink, FlowState, ProfileSync, Teacher
from services.api.flows import FLOWS
from services.api.flows.engine import FlowEngine
from services.api.flows.steps import Step

ROOT = Path(__file__).resolve().parents[2]
DEVICE = "a1b2c3d4e5f60718"
CLASS = "c-4b7f21a9c3"


def onboard(eng: FlowEngine, teacher: Teacher, lang: str = "hi", yes: bool = True) -> list[Step]:
    turn = eng.start(teacher)
    assert turn.steps[-1].id == "lang"
    turn = eng.answer(teacher, "lang", lang)
    assert turn.steps[-1].id == "consent_core"
    turn = eng.answer(teacher, "consent_core", "agree")
    for step_id in ("consent_counts", "consent_practice", "consent_feedback"):
        assert turn.steps[-1].id == step_id, [s.id for s in turn.steps]
        turn = eng.answer(teacher, step_id, "yes" if yes else "no")
    return turn.steps


def add_profile(db: Session, counts: dict[str, int], checked: int = 28) -> None:
    db.add(
        ProfileSync(class_id=CLASS, term="T1", form="A", children_checked=checked, counts=counts,
                    anchor_wrong_count=0, untracked={}, simulated=False)
    )  # fmt: skip
    db.commit()


def test_a_new_teacher_starts_at_the_language_choice(db: Session) -> None:
    eng = FlowEngine(db)
    t = eng.teacher_for("pwa", DEVICE)
    turn = eng.start(t)
    assert [s.id for s in turn.steps] == ["lang"] and turn.steps[0].kind == "choice"
    assert [o.id for o in turn.steps[0].options] == ["en", "hi", "ta"]


def test_the_language_choice_sets_her_language_and_the_welcome_follows_in_it(db: Session) -> None:
    eng = FlowEngine(db)
    t = eng.teacher_for("pwa", DEVICE)
    eng.start(t)
    turn = eng.answer(t, "lang", "ta")
    assert t.lang == "ta" and turn.lang == "ta"
    assert [s.kind for s in turn.steps] == [
        "message",
        "choice",
    ]  # the welcome, then the first consent
    assert strings.text("ta", turn.steps[0].copy) != strings.text("en", turn.steps[0].copy)


def test_a_bad_answer_a_stale_step_and_a_replayed_key_change_nothing(db: Session) -> None:
    eng = FlowEngine(db)
    t = eng.teacher_for("pwa", DEVICE)
    eng.start(t)
    with pytest.raises(ValueError):
        eng.answer(t, "lang", "klingon")
    stale = eng.answer(t, "welcome", "x")  # not the current step
    assert stale.steps[-1].id == "lang"
    first = eng.answer(t, "lang", "hi", key="k1")
    again = eng.answer(t, "lang", "en", key="k1")  # an offline replay with the same key
    assert t.lang == "hi" and again.steps[-1].id == first.steps[-1].id == "consent_core"


def test_consent_is_off_until_she_says_yes_and_declining_asks_again(db: Session) -> None:
    eng = FlowEngine(db)
    t = eng.teacher_for("pwa", DEVICE)
    eng.start(t)
    eng.answer(t, "lang", "en")
    declined = eng.answer(t, "consent_core", "no")
    assert t.consent is None or not t.consent.get("core")
    assert declined.steps[-1].id == "declined"
    assert eng.answer(t, "declined", "again").steps[-1].id == "consent_core"


def test_full_onboarding_stores_each_choice_and_ends_at_the_home_menu(db: Session) -> None:
    eng = FlowEngine(db)
    t = eng.teacher_for("pwa", DEVICE)
    steps = onboard(eng, t, "hi", yes=True)
    assert t.consent and t.consent["core"] and t.consent["counts"] and t.consent["v"] == 1
    assert steps[-1].id == "menu" and steps[-1].kind == "choice"
    st = db.get(FlowState, t.teacher_id)
    assert st is not None and (st.flow_id, st.step_id) == ("t1", "menu")


def test_saying_no_to_the_optional_consents_keeps_them_off(db: Session) -> None:
    eng = FlowEngine(db)
    t = eng.teacher_for("pwa", DEVICE)
    onboard(eng, t, "en", yes=False)
    assert t.consent and t.consent["core"]
    assert not any(t.consent[k] for k in ("counts", "practice_ai", "feedback", "share_rehearsal"))


def test_home_says_what_she_has_done_in_counts_and_offers_the_next_actions(db: Session) -> None:
    eng = FlowEngine(db)
    t = eng.teacher_for("pwa", DEVICE)
    onboard(eng, t, "en")
    menu = eng.start(t).steps
    assert menu[0].copy == "t1.status_none"  # no check yet
    assert {o.id for o in menu[-1].options} >= {"practice", "check", "delete"}
    t.class_id = CLASS
    add_profile(
        db, {"SUB-SFL": 11, "PV-HEARD": 2, "SUB-NODEC": 0, "ADD-NOCARRY": 0, "PV-REVERSE": 0}
    )
    menu = eng.start(t).steps
    assert menu[0].copy == "t1.status" and menu[0].params["n"] == 28
    cards = eng.answer(t, "menu", "cards").steps
    text = " ".join(strings.render(s, "en") for s in cards)
    assert "11 of 28 children" in text and "%" not in text
    assert cards[-1].id == "menu"  # back to the menu


def test_the_practice_link_step_carries_a_signed_link_for_her_language(db: Session) -> None:
    eng = FlowEngine(db)
    t = eng.teacher_for("pwa", DEVICE)
    onboard(eng, t, "ta")
    link = eng.answer(t, "menu", "practice").steps[-1]
    assert link.kind == "link" and link.link and link.link.kind == "practice"
    assert "/practice?t=" in (link.link.url or "")
    assert eng.answer(t, "practice", "back").steps[-1].id == "menu"


def test_a_judge_sees_a_labelled_simulated_class(db: Session) -> None:
    eng = FlowEngine(db)
    t = eng.teacher_for("telegram", "555", judge=True)
    onboard(eng, t, "en")
    steps = eng.start(t).steps
    assert steps[0].simulated and steps[0].copy == "t1.status"
    assert "simulated" in strings.render(steps[0], "en").lower()


def test_delete_my_data_removes_the_teacher_links_state_and_her_class_counts(db: Session) -> None:
    eng = FlowEngine(db)
    t = eng.teacher_for("pwa", DEVICE)
    onboard(eng, t, "en")
    t.class_id = CLASS
    add_profile(db, {"SUB-SFL": 5}, checked=12)
    tid = t.teacher_id
    eng.answer(t, "menu", "delete")
    done = eng.answer(t, "confirm_delete", "yes")
    assert done.steps[-1].copy == "t1.deleted"
    assert db.get(Teacher, tid) is None and db.get(FlowState, tid) is None
    assert db.query(ChannelLink).filter_by(teacher_id=tid).count() == 0
    assert db.query(ProfileSync).filter_by(class_id=CLASS).count() == 0
    assert eng.start(eng.teacher_for("pwa", DEVICE)).steps[-1].id == "lang"  # a fresh start works


def test_every_string_the_flows_use_exists_in_all_three_languages() -> None:
    tables = {
        lang: json.loads((ROOT / "strings" / f"{lang}.json").read_text(encoding="utf-8"))
        for lang in ("en", "hi", "ta")
    }
    used = set(strings.keys_used_by(FLOWS))
    assert len(used) > 20
    for lang, table in tables.items():
        missing = sorted(k for k in used if not table.get(k))
        assert not missing, (lang, missing)


def test_no_flow_string_shows_a_percentage_to_a_teacher() -> None:
    en = json.loads((ROOT / "strings" / "en.json").read_text(encoding="utf-8"))
    for key in strings.keys_used_by(FLOWS):
        assert "%" not in en[key], key
        assert not re.search(r"\d+ ?per ?cent", en[key])
