"""Rule versions (two people, immutable once published, retire) and paper approval (auto-approval
only within the rules, custom edits and failures to the queue, spot checks, freeze)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from services.api.db import Base, make_engine
from services.papers import store
from services.papers.models import (
    ClassProfileRow,
    Immutable,
    PaperEvent,
    PaperReview,
    PaperRow,
    RuleTemplate,
    RuleVersion,
)
from services.papers.rules import from_data, seed_rules, to_data

CHECK = {"id": "c-0123456789:1", "kind": "pre", "form": "A", "class_label": "3A", "term": 1}
PAST = {"source": "past", "counts": {"SUB-SFL": 9}, "checked": 18, "language": "en"}


@pytest.fixture
def db(tmp_path: Path) -> Iterator[Session]:
    engine = make_engine(f"sqlite:///{tmp_path / 'p.sqlite'}")
    Base.metadata.create_all(engine)
    with sessionmaker(engine, expire_on_commit=False)() as s:
        store.ensure_seeded(s)
        yield s


def edited_body(**constraints: object) -> dict:
    rules = seed_rules()
    rules.template("sub-borrow").constraints.update(constraints)
    return to_data(rules)


# --- rules ---------------------------------------------------------------------------------


def test_version_1_is_seeded_published_and_matches_the_seed_rules(db: Session) -> None:
    v = db.get(RuleVersion, 1)
    assert v is not None and v.status == "published"
    assert from_data(v.body) == seed_rules()
    assert db.scalars(select(RuleTemplate).where(RuleTemplate.rule_version == 1)).first()
    assert store.ensure_seeded(db) == 1  # idempotent


def test_an_author_cannot_approve_their_own_change(db: Session) -> None:
    n = store.create_draft(db, edited_body(result_min=11), "coach-a").number
    store.submit(db, n, "coach-a")
    with pytest.raises(store.NotAllowed):
        store.publish(db, n, "coach-a")
    v = store.publish(db, n, "coach-b")
    assert v.status == "published" and v.approver == "coach-b"
    assert any("result_min" in line for line in v.diff)
    assert store.published(db).number == n


def test_only_the_author_submits_and_only_a_draft_in_review_is_published(db: Session) -> None:
    n = store.create_draft(db, edited_body(result_min=11), "coach-a").number
    with pytest.raises(store.NotAllowed):
        store.submit(db, n, "coach-b")
    with pytest.raises(store.BadState):
        store.publish(db, n, "coach-b")  # still a draft


def test_a_published_version_cannot_be_edited(db: Session) -> None:
    v = db.get(RuleVersion, 1)
    assert v is not None
    v.body = edited_body(result_min=12)
    with pytest.raises(Immutable):
        db.flush()
    db.rollback()
    row = db.scalars(select(RuleTemplate)).first()
    assert row is not None
    row.skill = "changed"
    with pytest.raises(Immutable):
        db.flush()
    db.rollback()


def test_a_bad_rules_file_is_refused_with_a_reason(db: Session) -> None:
    body = to_data(seed_rules())
    body["templates"][0]["bugs"] = ["no-such-bug"]
    with pytest.raises(ValueError, match="unknown bugs"):
        store.create_draft(db, body, "coach-a")
    with pytest.raises(ValueError):
        store.import_yaml(db, "templates: [1, 2]", "coach-a")


def test_a_retired_version_cannot_be_used_and_a_paper_pins_its_versions(db: Session) -> None:
    n = store.create_draft(db, edited_body(result_min=11), "coach-a").number
    store.submit(db, n, "coach-a")
    store.publish(db, n, "coach-b")
    paper = store.generate(db, CHECK, PAST, "standard_10_5", "en", "teacher-demo", rules_version=1)
    assert paper.rules_version == 1 and paper.blueprint_version == 1
    store.retire(db, 1, "coach-b")
    with pytest.raises(store.NotAllowed, match="retired"):
        store.generate(db, CHECK, PAST, "standard_10_5", "en", "teacher-demo", rules_version=1)
    later = store.generate(db, {**CHECK, "id": "c-9:1"}, PAST, "standard_10_5", "en", "t")
    assert later.rules_version == n


def test_a_draft_version_cannot_be_used(db: Session) -> None:
    n = store.create_draft(db, edited_body(result_min=11), "coach-a").number
    with pytest.raises(store.NotAllowed, match="draft"):
        store.generate(db, CHECK, PAST, "standard_10_5", "en", "t", rules_version=n)


# --- papers --------------------------------------------------------------------------------


def test_a_clean_paper_in_reviewed_words_is_auto_approved_and_logged(db: Session) -> None:
    p = store.generate(db, CHECK, PAST, "standard_10_5", "en", "teacher-demo")
    assert p.status == "auto_approved" and p.findings == []
    ev = db.scalars(select(PaperEvent).where(PaperEvent.paper_id == p.id)).all()
    assert {e.event for e in ev} >= {"generated", "auto_approved"}
    assert all(e.hash == p.hash and e.seed == p.seed for e in ev if e.event == "generated")
    assert store.printable(p)


def test_a_pre_test_makes_its_post_test_twin_frozen_at_once(db: Session) -> None:
    p = store.generate(db, CHECK, PAST, "standard_10_5", "en", "teacher-demo")
    twin = store.twin_of(db, p.id)
    assert twin is not None and twin.form == "B" and twin.kind == "post"
    assert twin.frozen_at is not None and twin.twin_of == p.id
    assert twin.check_code == "POST · 3A" # terms are off (correction 9, DECISIONS 2026-11-03): the code no longer ends in a term (was "POST · 3A · T…")


def test_a_paper_in_words_nobody_has_reviewed_waits_in_the_queue(db: Session) -> None:
    p = store.generate(db, CHECK, PAST, "standard_10_5", "ta", "teacher-demo")
    assert p.status == "queued" and not store.printable(p)
    q = db.scalars(select(PaperReview).where(PaperReview.paper_id == p.id)).one()
    assert q.reason == "unreviewed_words"
    store.approve_paper(db, p.id, "coach-a")
    assert store.printable(db.get(PaperRow, p.id))  # type: ignore[arg-type]


def test_custom_edits_always_go_to_the_queue_before_printing(db: Session) -> None:
    p = store.generate(db, CHECK, PAST, "baseline_10", "en", "teacher-demo")
    c = store.custom_paper(db, p.id, [{"n": 7, "a": 73, "b": 39}], "teacher-demo")
    assert c.custom and c.status == "queued" and not store.printable(c)
    assert (
        db.scalars(select(PaperReview).where(PaperReview.paper_id == c.id)).one().reason == "custom"
    )


def test_a_paper_that_fails_a_check_cannot_be_approved_and_keeps_the_reason(db: Session) -> None:
    p = store.generate(db, CHECK, PAST, "baseline_10", "en", "teacher-demo")
    # 52 - 27 cannot tell SUB-SFL from SUB-NODEC (both 35)
    c = store.custom_paper(db, p.id, [{"n": 7, "a": 52, "b": 27}], "teacher-demo")
    assert c.status == "queued" and any(f["rule"] == "discrimination" for f in c.findings)
    with pytest.raises(store.BadState):
        store.approve_paper(db, c.id, "coach-a")
    r = store.reject_paper(db, c.id, "coach-a", "Item 7 cannot tell the two errors apart.")
    assert r.status == "rejected" and r.rejected_reason and not store.printable(r)


def test_spot_checks_sample_auto_approved_papers_after_the_fact(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PAPER_SPOT_CHECK_EVERY", "1")
    p = store.generate(db, CHECK, PAST, "standard_10_5", "en", "teacher-demo")
    assert p.status == "auto_approved" and store.printable(p)
    q = db.scalars(select(PaperReview).where(PaperReview.paper_id == p.id)).one()
    assert q.reason == "spot_check"
    monkeypatch.setenv("PAPER_SPOT_CHECK_EVERY", "0")
    p2 = store.generate(db, {**CHECK, "id": "c-2:1"}, PAST, "standard_10_5", "en", "t")
    assert not db.scalars(select(PaperReview).where(PaperReview.paper_id == p2.id)).all()


def test_the_default_spot_check_rate_is_one_in_five(db: Session) -> None:
    import hashlib

    hashes = [hashlib.sha256(str(i).encode()).hexdigest() for i in range(1000)]
    sampled = sum(store.spot_checked(h) for h in hashes)
    assert 150 <= sampled <= 250


def test_a_frozen_paper_cannot_change_and_its_check_cannot_get_a_new_paper(db: Session) -> None:
    p = store.generate(db, CHECK, PAST, "standard_10_5", "en", "teacher-demo")
    store.freeze(db, p.id, "teacher-demo")
    row = db.get(PaperRow, p.id)
    assert row is not None and row.frozen_at is not None
    row.status = "rejected"
    with pytest.raises(Immutable):
        db.flush()
    db.rollback()
    with pytest.raises(store.BadState, match="frozen"):
        store.generate(db, CHECK, PAST, "standard_10_5", "en", "teacher-demo")


def test_the_same_check_and_inputs_give_the_same_paper(db: Session) -> None:
    a = store.generate(db, CHECK, PAST, "standard_10_5", "en", "teacher-demo")
    b = store.generate(db, CHECK, PAST, "standard_10_5", "en", "teacher-demo")
    assert a.id == b.id and a.hash == b.hash


def test_the_class_profile_holds_counts_only(db: Session) -> None:
    store.generate(db, CHECK, PAST, "standard_10_5", "en", "teacher-demo")
    rows = db.scalars(select(ClassProfileRow)).all()  # the pre-test and its twin
    assert len(rows) == 2
    for row in rows:
        assert row.source == "past" and row.strength == 18
        assert set(row.skill_weights) <= {"C1", "C2", "C3"}
    cols = {c.name for c in ClassProfileRow.__table__.columns}
    assert not cols & {"name", "child", "roll", "answers", "children"}


def test_the_intake_form_marks_untaught_skills_not_assessed(db: Session) -> None:
    intake = {
        "source": "intake",
        "struggles": ["C2"],
        "taught": ["C1", "C2"],
        "language": "en",
        "strength": 30,
    }
    p = store.generate(db, CHECK, intake, "standard_10_5", "en", "teacher-demo")
    assert p.body["not_assessed"] == ["C3"]
    assert all(i["competency"] != "C3" for i in p.body["items"])


def test_the_phone_key_matches_the_engine_answer_keys_for_the_pilot_paper(db: Session) -> None:
    from engine.export_keys import build_answer_keys

    p = store.sample_paper(db, CHECK, "A", "teacher-demo")
    key = store.phone_key(p)
    want = build_answer_keys()["forms"]["A"]["items"]
    for mine, theirs in zip(key["items"], want, strict=True):
        assert {k: mine[k] for k in theirs} == theirs
        assert mine["anchor"] is True


def test_a_database_made_before_the_column_rename_is_upgraded_on_start(tmp_path: Path) -> None:
    from sqlalchemy import inspect, text

    engine = make_engine(f"sqlite:///{tmp_path / 'old.sqlite'}")
    Base.metadata.create_all(engine)
    with engine.begin() as con:  # the 30 Oct schema: the column had its old name
        con.execute(text("ALTER TABLE rule_template RENAME COLUMN box_format TO answer_format"))
    with sessionmaker(engine, expire_on_commit=False)() as s:
        assert store.ensure_seeded(s) == 1
        cols = {c["name"] for c in inspect(engine).get_columns("rule_template")}
        assert "box_format" in cols and "answer_format" not in cols
        assert s.scalars(select(RuleTemplate)).first() is not None


def test_a_paper_in_two_languages_waits_if_either_wording_is_unreviewed(db: Session) -> None:
    both = store.generate(db, CHECK, PAST, "baseline_10", "en_ta", "teacher-demo")
    assert both.status == "queued" and both.language == "en_ta"
    one = store.generate(db, {**CHECK, "id": "c-3:1"}, PAST, "baseline_10", "en", "teacher-demo")
    assert one.status == "auto_approved"
