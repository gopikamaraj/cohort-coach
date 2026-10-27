"""evals/results.md is generated from the results files; a pending eval carries no number."""

from __future__ import annotations

import re

from scripts.eval_results import OUT, render, rows


def test_the_committed_results_file_is_current() -> None:
    assert OUT.read_text(encoding="utf-8") == render(), "run: python scripts/eval_results.py"


def test_a_pending_or_unbuilt_eval_shows_no_number_in_its_result() -> None:
    for r in rows():
        result = r[3]
        if result.startswith(("pending", "not built", "not run")):
            assert not re.search(r"\d+(\.\d+)?%|\bmedian \d", result), r


def test_the_design_bars_are_unchanged() -> None:
    text = render()
    for bar in (
        "100% correct, 0 collisions",
        "0 unsafe reach a teacher",
        ">= 95% recovered; <= 5% false working",
        "median < 3000 ms",
    ):
        assert bar in text


def test_a_failing_bar_is_shown_as_a_fail_not_hidden() -> None:
    latency = next(r for r in rows() if r[0] == "Latency (text)")
    assert latency[3].startswith(("PASS", "FAIL"))
