"""C01: the coach's timeout and auto-send settings. Server-side range, coach only, per-cohort
override, due time fixed when a question is asked, every change audited."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from services.api.cohorts import lifecycle
from services.api.db import CohortAuditRow
from services.chat import config
from tests.chat.conftest import COACH, MENTOR, OFFICER, World

NOW = datetime(2026, 10, 29, 9, 0, tzinfo=UTC)


def test_the_defaults_are_24_hours_and_auto_send_off(world: World) -> None:
    e = config.effective(world.db, world.cohort_id)
    assert (e.timeout_hours, e.auto_send, e.source) == (24, False, "default")


@pytest.mark.parametrize("bad", [0, -1, 169, 1000, 2.5, "24", None, True])
def test_a_timeout_outside_1_to_168_or_not_a_whole_number_is_refused(
    world: World, bad: object
) -> None:
    if bad is None:  # None means "leave it as it is", not an invalid value
        config.set_config(world.db, role="coach", actor=COACH, timeout_hours=None, auto_send=True)
        return
    with pytest.raises(config.ChatConfigError):
        config.set_config(world.db, role="coach", actor=COACH, timeout_hours=bad)
    assert config.effective(world.db, world.cohort_id).timeout_hours == 24


@pytest.mark.parametrize("ok", [1, 24, 72, 168])
def test_the_whole_range_is_accepted(world: World, ok: int) -> None:
    assert (
        config.set_config(world.db, role="coach", actor=COACH, timeout_hours=ok).timeout_hours == ok
    )


@pytest.mark.parametrize("role,actor", [("mentor", MENTOR), ("officer", OFFICER), ("teacher", "x")])
def test_only_the_coach_can_change_it(world: World, role: str, actor: str) -> None:
    with pytest.raises(lifecycle.NotAllowed):
        config.set_config(world.db, role=role, actor=actor, timeout_hours=48)
    assert config.effective(world.db, world.cohort_id).source == "default"


def test_a_cohort_setting_beats_the_global_one(world: World) -> None:
    config.set_config(world.db, role="coach", actor=COACH, timeout_hours=48)
    assert config.effective(world.db, world.cohort_id) == config.Effective(48, False, "global")
    config.set_config(
        world.db,
        role="coach",
        actor=COACH,
        cohort_id=world.cohort_id,
        timeout_hours=6,
        auto_send=True,
    )
    assert config.effective(world.db, world.cohort_id) == config.Effective(6, True, "cohort")
    assert config.effective(world.db, "another-cohort").timeout_hours == 48  # global still applies


def test_a_coach_changes_only_a_cohort_she_is_assigned_to(world: World) -> None:
    with pytest.raises(lifecycle.NotAllowed):
        config.set_config(
            world.db, role="coach", actor="coach-other", cohort_id=world.cohort_id, timeout_hours=6
        )


def test_the_due_time_is_the_ask_time_plus_the_hours_in_force_then(world: World) -> None:
    assert config.due_at(world.db, world.cohort_id, NOW) == NOW + timedelta(hours=24)
    config.set_config(
        world.db, role="coach", actor=COACH, cohort_id=world.cohort_id, timeout_hours=2
    )
    assert config.due_at(world.db, world.cohort_id, NOW) == NOW + timedelta(hours=2)


def test_leaving_a_value_out_keeps_the_current_one(world: World) -> None:
    config.set_config(world.db, role="coach", actor=COACH, timeout_hours=12, auto_send=True)
    e = config.set_config(world.db, role="coach", actor=COACH, auto_send=False)
    assert (e.timeout_hours, e.auto_send) == (12, False)


def test_every_change_is_audited_without_any_text(world: World) -> None:
    config.set_config(world.db, role="coach", actor=COACH, timeout_hours=12, auto_send=True)
    rows = list(
        world.db.execute(
            select(CohortAuditRow).where(CohortAuditRow.action == "chat_config")
        ).scalars()
    )
    assert len(rows) == 1 and rows[0].role == "coach" and rows[0].actor == COACH
    assert rows[0].detail == {"timeout_hours": 12, "auto_send": True}
