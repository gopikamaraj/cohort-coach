from __future__ import annotations

from collections import Counter

import pytest

from ai.client import CallContext
from evals.runners.redteam import BAR, estimate_live_cost, load_cases, run
from tests.support_ai import FakeClient


def test_seed_set_has_12_attacks_across_six_categories_and_three_languages() -> None:
    attacks = [c for c in load_cases() if c["expected"] == "blocked"]
    assert len(attacks) == 12
    assert {c["category"] for c in attacks} == {
        "role_break", "injection", "unsafe_request", "harsh_teacher", "code_mixing", "pii_bait",
    }  # fmt: skip
    assert {c["language"] for c in attacks} == {"en", "hi", "ta"}
    assert all(n == 2 for n in Counter(c["category"] for c in attacks).values())


def test_code_gates_block_every_case_marked_code_and_pass_the_controls() -> None:
    result = run(live=False)
    assert result["missed_ids"] == [] and result["unsafe_reaching_teacher"] == 0
    assert result["controls_wrongly_blocked"] == 0
    assert result["bar"] == BAR


def test_checker_only_cases_are_pending_never_counted_as_passed() -> None:
    result = run(live=False)
    assert result["pending_checker_ids"] == ["rt-05", "rt-06"]
    assert result["passed"] is False  # the bar is not proven until the live run
    assert result["checker_status"].startswith("pending")


def test_live_path_counts_a_checker_pass_as_reaching_a_teacher(
    monkeypatch: pytest.MonkeyPatch, sink: object
) -> None:
    from ai.audit import SqlAuditSink
    from ai.schemas import Verdict

    assert isinstance(sink, SqlAuditSink)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    ok = Verdict(passed=True, reason_short="ok", reason_for_user="ok")
    bad = Verdict(passed=False, failed_items=["stereotypes"], reason_short="x", reason_for_user="x")
    ctx = CallContext(mode="live", sink=sink, client=FakeClient([ok]))
    result = run(live=True, context=ctx)
    assert result["unsafe_reaching_teacher"] == 2  # a checker that passes both stereotype cases
    # Checker calls happen in file order: rt-05, rt-06 (attacks), then the two controls.
    ctx = CallContext(mode="live", sink=sink, client=FakeClient([bad, bad, ok, ok]))
    result = run(live=True, context=ctx)
    assert result["unsafe_reaching_teacher"] == 0 and result["passed"] is True


def test_live_estimate_is_small_and_computed_from_prices() -> None:
    assert 0 < estimate_live_cost(12) < 0.10
