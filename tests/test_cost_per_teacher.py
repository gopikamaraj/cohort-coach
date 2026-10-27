"""The cost estimate is arithmetic on measured means and stated assumptions; check it by hand."""

from __future__ import annotations

from pathlib import Path

import yaml

from scripts.cost_per_teacher import ASSUMPTIONS, estimate

MEANS = {
    "check_sheets": 0.001,
    "child_lines": 0.002,
    "move_labels": 0.0001,
    "checks": 0.0001,
    "feedback": 0.01,
    "drafting": 0.1,
}
A = {
    "per_teacher_per_track": {
        "sheets_read": {"low": 10, "high": 10},
        "practice_sessions": {"low": 1, "high": 2},
        "turns_per_session": {"low": 10, "high": 10},
        "feedback_per_session": {"low": 1, "high": 1},
    },
    "drafting": {
        "parts_per_language": 2,
        "languages": {"low": 1, "high": 2},
        "cohort_size": {"low": 5, "high": 10},
        "checks_per_part": 1,
    },
}


def test_the_estimate_is_the_hand_computed_arithmetic() -> None:
    out = estimate(MEANS, A)
    assert out["low"] == {
        "check_sheets": 1.0, "child_lines": 2.0, "move_labels": 0.1, "checks": 0.11,
        "feedback": 1.0, "drafting": 2.002, "total": 6.212,
    }  # fmt: skip
    assert out["high"] == {
        "check_sheets": 1.0, "child_lines": 4.0, "move_labels": 0.2, "checks": 0.22,
        "feedback": 2.0, "drafting": 8.008, "total": 15.428,
    }  # fmt: skip


def test_a_call_with_no_measured_cost_adds_nothing_rather_than_a_guess() -> None:
    out = estimate({}, A)
    assert out["low"]["total"] == 0.0 and out["high"]["total"] == 0.0


def test_the_assumptions_file_has_every_key_the_estimate_reads() -> None:
    a = yaml.safe_load(Path(ASSUMPTIONS).read_text(encoding="utf-8"))
    out = estimate(MEANS, a)
    assert out["low"]["total"] <= out["high"]["total"]
