import json
from pathlib import Path

import pytest

from engine.evaluation import (
    Verdict,
    mcnemar_exact,
    paired_table,
    pilot_extra_fall,
    pilot_verdict,
)
from engine.model import ErrorCode

H, R, N, SFL, NODEC = (
    ErrorCode.PV_HEARD,
    ErrorCode.PV_REVERSE,
    ErrorCode.ADD_NOCARRY,
    ErrorCode.SUB_SFL,
    ErrorCode.SUB_NODEC,
)

GOLDEN = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "pilot_forms.golden.json").read_text(
        encoding="utf-8"
    )
)


# --- McNemar exact -----------------------------------------------------------------------


def test_mcnemar_matches_the_golden_value() -> None:
    gold = GOLDEN["mcnemar_exact"]
    assert mcnemar_exact(gold["fixed"], gold["new"]) == gold["p_two_sided"]
    assert round(mcnemar_exact(12, 2), 3) == gold["p_rounded"] == 0.013


def test_mcnemar_edge_cases() -> None:
    assert mcnemar_exact(0, 0) == 1.0
    assert mcnemar_exact(5, 5) == 1.0  # equal discordant pairs: no evidence
    assert mcnemar_exact(0, 6) == mcnemar_exact(6, 0) == 2 * 0.5**6  # two-sided, symmetric
    assert mcnemar_exact(1, 0) == 1.0  # capped at 1


def test_mcnemar_is_symmetric_and_a_probability() -> None:
    for fixed in range(0, 15):
        for new in range(0, 15):
            p = mcnemar_exact(fixed, new)
            assert 0.0 < p <= 1.0 and p == mcnemar_exact(new, fixed)


def test_mcnemar_rejects_negative_counts() -> None:
    with pytest.raises(ValueError):
        mcnemar_exact(-1, 2)


# --- paired table ------------------------------------------------------------------------


def test_paired_table_counts_still_fixed_new_never() -> None:
    pre = {"1": True, "2": True, "3": True, "4": False, "5": False, "6": False, "7": True}
    post = {"1": True, "2": False, "3": False, "4": True, "5": False, "6": False, "9": True}
    table = paired_table(pre, post)
    assert (table.still, table.fixed, table.new, table.never) == (1, 2, 1, 2)
    assert table.paired == 6  # roll 7 (absent post) and 9 (absent pre) are dropped
    assert table.pre_only == 1 and table.post_only == 1


def test_paired_table_empty() -> None:
    table = paired_table({}, {})
    assert table.paired == 0 and mcnemar_exact(table.fixed, table.new) == 1.0


# --- extra fall --------------------------------------------------------------------------


def test_extra_fall_worked_example() -> None:
    pre = {H: 0.10, R: 0.0, N: 0.30, SFL: 0.50, NODEC: 0.20}
    post = {H: 0.05, R: 0.0, N: 0.25, SFL: 0.20, NODEC: 0.10}
    result = pilot_extra_fall(pre, post, SFL)
    # trained fall 30 points; untrained with pre >= 10%: H (5), N (5), NODEC (10): mean 6.67
    assert result.trained_fall == pytest.approx(30.0)
    assert set(result.untrained_used) == {H, N, NODEC}
    assert result.baseline_fall == pytest.approx(20 / 3)
    assert result.extra_fall == pytest.approx(30 - 20 / 3)


def test_untrained_errors_below_10_percent_at_pre_test_are_ignored() -> None:
    pre = {H: 0.09, R: 0.0, N: 0.10, SFL: 0.40, NODEC: 0.0}
    post = {H: 0.0, R: 0.0, N: 0.05, SFL: 0.20, NODEC: 0.0}
    result = pilot_extra_fall(pre, post, SFL)
    assert result.untrained_used == (N,)  # exactly 10% counts; 9% does not
    assert result.extra_fall == pytest.approx(20 - 5)


def test_a_rise_in_an_untrained_error_raises_the_baseline_negative() -> None:
    pre = {N: 0.20, SFL: 0.40}
    post = {N: 0.30, SFL: 0.30}
    result = pilot_extra_fall(pre, post, SFL)
    assert result.baseline_fall == pytest.approx(-10.0)
    assert result.extra_fall == pytest.approx(10 + 10)


def test_extra_baseline_data_points_are_included() -> None:
    pre = {N: 0.20, SFL: 0.40}
    post = {N: 0.15, SFL: 0.20}
    result = pilot_extra_fall(pre, post, SFL, extra_baseline_falls=[15.0])
    assert result.baseline_fall == pytest.approx(10.0)  # mean of 5 and 15
    assert result.extra_fall == pytest.approx(10.0)


def test_no_baseline_means_no_extra_fall() -> None:
    result = pilot_extra_fall({SFL: 0.5, N: 0.05}, {SFL: 0.2, N: 0.0}, SFL)
    assert result.baseline_fall is None and result.extra_fall is None
    assert pilot_verdict(result.extra_fall, 0.001) is Verdict.INCONCLUSIVE


# --- pilot verdict -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("extra", "p", "verdict"),
    [
        (10.0, 0.049, Verdict.WORKING),
        (10.0, 0.05, Verdict.INCONCLUSIVE),  # p must be below 0.05
        (9.9, 0.001, Verdict.INCONCLUSIVE),
        (25.0, 0.2, Verdict.INCONCLUSIVE),
        (5.0, 0.001, Verdict.INCONCLUSIVE),
        (4.9, 0.001, Verdict.NOT_WORKING),
        (0.0, 0.5, Verdict.NOT_WORKING),
        (-8.0, 0.5, Verdict.NOT_WORKING),  # a rise counts here
        (None, 0.01, Verdict.INCONCLUSIVE),
        (12.0, None, Verdict.INCONCLUSIVE),
    ],
)
def test_pilot_verdict_boundaries(extra: float | None, p: float | None, verdict: Verdict) -> None:
    assert pilot_verdict(extra, p) is verdict


def test_pilot_rules_match_the_golden_text() -> None:
    rules = GOLDEN["pilot_verdict_rules"]
    assert "10" in rules["working"] and "0.05" in rules["working"]
    assert "5" in rules["not_working"]
