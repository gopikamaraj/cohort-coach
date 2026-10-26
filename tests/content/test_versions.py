"""P09 T05 (addendum v3.1 section D): content versions and the two keys.

draft -> in review -> approved (the coach's key, gate 3) -> active (the officer's key). Neither
key alone switches content on; every edit makes a new version and the old one stays in use until
the new one is active; every step writes an audit row.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.db import ContentAudit
from services.content import configurable, versions
from services.content.versions import BadState, NotAllowed

COACH = ("coach-7f3a", "coach")
OFFICER = ("officer-21bc", "officer")
AUTHOR = ("build", "coach")
BODY = {"lessons": 6, "note": "SUB-SFL v1"}


def make(db: Session, body: dict[str, object] | None = None) -> versions.ContentVersion:
    return versions.create_draft(db, "track", "sub-sfl", body or BODY, *AUTHOR)


def approved(db: Session) -> versions.ContentVersion:
    v = make(db)
    versions.submit_for_review(db, v.id, *AUTHOR)
    return versions.coach_approve(db, v.id, *COACH)


def test_a_new_draft_is_version_one_and_inactive(db: Session) -> None:
    v = make(db)
    assert (v.version, v.status, v.parent_version) == (1, "draft", None)
    assert versions.active_version(db, "track", "sub-sfl") is None


def test_the_coach_alone_leaves_the_content_inactive(db: Session) -> None:
    v = approved(db)
    assert v.status == "approved"
    assert versions.active_version(db, "track", "sub-sfl") is None


def test_the_officer_cannot_activate_what_the_coach_has_not_approved(db: Session) -> None:
    v = make(db)
    with pytest.raises(BadState):
        versions.officer_activate(db, v.id, *OFFICER)
    versions.submit_for_review(db, v.id, *AUTHOR)
    with pytest.raises(BadState):
        versions.officer_activate(db, v.id, *OFFICER)
    assert versions.active_version(db, "track", "sub-sfl") is None


def test_the_two_keys_switch_it_on_and_the_audit_row_holds_both(db: Session) -> None:
    v = approved(db)
    active = versions.officer_activate(db, v.id, *OFFICER)
    assert active.status == "active"
    assert versions.active_version(db, "track", "sub-sfl").id == v.id  # type: ignore[union-attr]
    row = db.execute(select(ContentAudit).where(ContentAudit.action == "activate")).scalar_one()
    assert row.role == "officer" and row.actor == "officer-21bc" and row.version == 1
    assert row.detail["coach"] == "coach-7f3a" and row.detail["officer"] == "officer-21bc"


def test_each_key_belongs_to_its_own_role(db: Session) -> None:
    v = make(db)
    versions.submit_for_review(db, v.id, *AUTHOR)
    with pytest.raises(NotAllowed):
        versions.coach_approve(db, v.id, "officer-21bc", "officer")
    with pytest.raises(NotAllowed):
        versions.coach_approve(db, v.id, "mentor-1", "mentor")
    versions.coach_approve(db, v.id, *COACH)
    with pytest.raises(NotAllowed):
        versions.officer_activate(db, v.id, "coach-7f3a", "coach")


def test_one_person_holding_both_roles_still_takes_two_separate_steps(db: Session) -> None:
    v = make(db)
    versions.submit_for_review(db, v.id, *AUTHOR)
    versions.coach_approve(db, v.id, "pat-9", "coach")
    assert versions.active_version(db, "track", "sub-sfl") is None  # one step is not both
    versions.officer_activate(db, v.id, "pat-9", "officer")
    assert versions.active_version(db, "track", "sub-sfl") is not None


def test_an_edit_makes_a_new_version_and_the_old_one_stays_in_use(db: Session) -> None:
    v1 = approved(db)
    versions.officer_activate(db, v1.id, *OFFICER)
    v2 = versions.edit(db, v1.id, {"lessons": 6, "note": "SUB-SFL v1, wording fixed"}, *AUTHOR)
    assert (v2.version, v2.status, v2.parent_version) == (2, "draft", 1)
    assert versions.active_version(db, "track", "sub-sfl").id == v1.id  # type: ignore[union-attr]
    versions.submit_for_review(db, v2.id, *AUTHOR)
    versions.coach_approve(db, v2.id, *COACH)
    assert versions.active_version(db, "track", "sub-sfl").id == v1.id  # type: ignore[union-attr]
    versions.officer_activate(db, v2.id, *OFFICER)
    assert versions.active_version(db, "track", "sub-sfl").id == v2.id  # type: ignore[union-attr]
    assert db.get(versions.ContentVersion, v1.id).status == "retired"  # type: ignore[union-attr]


def test_the_old_body_never_changes_when_an_edit_is_made(db: Session) -> None:
    v1 = approved(db)
    versions.edit(db, v1.id, {"lessons": 7}, *AUTHOR)
    assert db.get(versions.ContentVersion, v1.id).body == BODY  # type: ignore[union-attr]


def test_what_is_activated_is_exactly_what_was_approved(db: Session) -> None:
    v = approved(db)
    assert v.content_hash == versions.body_hash(BODY)
    active = versions.officer_activate(db, v.id, *OFFICER)
    assert active.content_hash == versions.body_hash(BODY)


def test_the_coach_can_send_a_draft_back_with_a_reason(db: Session) -> None:
    v = make(db)
    versions.submit_for_review(db, v.id, *AUTHOR)
    back = versions.return_to_draft(db, v.id, *COACH, reason="tone_issue")
    assert back.status == "draft"
    row = db.execute(select(ContentAudit).where(ContentAudit.action == "return")).scalar_one()
    assert row.detail["reason"] == "tone_issue"
    with pytest.raises(NotAllowed):
        versions.return_to_draft(db, v.id, *OFFICER, reason="tone_issue")


def test_illegal_steps_are_refused(db: Session) -> None:
    v = make(db)
    with pytest.raises(BadState):
        versions.coach_approve(db, v.id, *COACH)  # not submitted
    versions.submit_for_review(db, v.id, *AUTHOR)
    with pytest.raises(BadState):
        versions.submit_for_review(db, v.id, *AUTHOR)  # already in review


def test_every_step_writes_an_audit_row_with_role_actor_action_and_version(db: Session) -> None:
    v = approved(db)
    versions.officer_activate(db, v.id, *OFFICER)
    rows = list(db.execute(select(ContentAudit).order_by(ContentAudit.id)).scalars())
    assert [r.action for r in rows] == ["create", "submit", "approve", "activate"]
    for r in rows:
        assert r.role and r.actor and r.content_id == "sub-sfl" and r.version == 1


def test_versions_are_numbered_per_content_item(db: Session) -> None:
    a = versions.create_draft(db, "track", "sub-sfl", {"x": 1}, *AUTHOR)
    b = versions.create_draft(db, "track", "sub-nodec", {"x": 1}, *AUTHOR)
    assert (a.version, b.version) == (1, 1)


# ---- configurable thresholds (D3) -------------------------------------------------------------


def test_only_listed_thresholds_are_configurable_and_each_has_a_safe_range() -> None:
    keys = configurable.CONFIGURABLE
    assert {"stage_routine_threshold_pct", "stage_routine_min_checked", "practice_turn_cap"} <= set(
        keys
    )
    for spec in keys.values():
        assert spec.low <= spec.default <= spec.high
    for fixed in ("eligibility_prevalence_pct", "eligibility_min_children", "verdict_rules"):
        assert fixed in configurable.FIXED
        assert fixed not in keys


def test_a_value_outside_its_range_is_refused(db: Session) -> None:
    with pytest.raises(configurable.OutOfRange):
        configurable.propose(db, "practice_turn_cap", 60, *AUTHOR)
    with pytest.raises(configurable.OutOfRange):
        configurable.propose(db, "practice_turn_cap", 10, *AUTHOR)
    assert versions.active_version(db, "setting", "practice_turn_cap") is None


def test_a_fixed_rule_has_no_write_route(db: Session) -> None:
    with pytest.raises(configurable.NotConfigurable):
        configurable.propose(db, "eligibility_min_children", 5, *AUTHOR)
    with pytest.raises(configurable.NotConfigurable):
        configurable.propose(db, "no_such_setting", 1, *AUTHOR)


def test_a_setting_changes_only_through_the_two_keys(db: Session) -> None:
    assert configurable.effective_value(db, "practice_turn_cap") == 40  # the default
    v = configurable.propose(db, "practice_turn_cap", 30, *AUTHOR)
    assert configurable.effective_value(db, "practice_turn_cap") == 40  # a proposal changes nothing
    versions.coach_approve(db, v.id, *COACH)
    assert configurable.effective_value(db, "practice_turn_cap") == 40  # one key is not enough
    versions.officer_activate(db, v.id, *OFFICER)
    assert configurable.effective_value(db, "practice_turn_cap") == 30


def test_a_bool_or_text_is_not_accepted_as_a_number(db: Session) -> None:
    with pytest.raises(configurable.OutOfRange):
        configurable.propose(db, "practice_turn_cap", True, *AUTHOR)  # type: ignore[arg-type]
    with pytest.raises(configurable.OutOfRange):
        configurable.propose(db, "practice_turn_cap", "30", *AUTHOR)  # type: ignore[arg-type]
