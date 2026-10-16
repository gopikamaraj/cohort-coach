import json
from pathlib import Path

import numpy as np
import pytest

from engine.evaluation import (
    MIN_CLASSES_PER_ARM,
    ClassChange,
    Group,
    Verdict,
    block_effect,
    confidence_note,
)

GOLDEN = json.loads(
    (Path(__file__).resolve().parents[1] / "fixtures" / "pilot_forms.golden.json").read_text(
        encoding="utf-8"
    )
)


def arms(track: list[float], comparison: list[float]) -> list[ClassChange]:
    return [ClassChange(f"t{i}", Group.TRACK, d) for i, d in enumerate(track)] + [
        ClassChange(f"c{i}", Group.COMPARISON, d) for i, d in enumerate(comparison)
    ]


def constant(track_delta: float, comparison_delta: float, n: int = 20) -> list[ClassChange]:
    return arms([track_delta] * n, [comparison_delta] * n)


def test_exactly_minus_10_with_ci_below_zero_is_working() -> None:
    result = block_effect("SUB-SFL v1", constant(-30.0, -20.0), seed=1)
    assert result.estimate_points == -10.0
    assert result.ci_high < 0
    assert result.verdict is Verdict.WORKING


def test_a_fall_just_short_of_10_is_inconclusive() -> None:
    assert block_effect("v", constant(-29.9, -20.0), seed=1).verdict is Verdict.INCONCLUSIVE


def test_a_fall_of_4_9_points_is_not_working() -> None:
    result = block_effect("v", constant(-24.9, -20.0), seed=1)
    assert result.verdict is Verdict.NOT_WORKING
    assert result.reason == "fall_below_5_or_rise"


def test_exactly_5_points_is_inconclusive_neither_rule_applies() -> None:
    assert block_effect("v", constant(-25.0, -20.0), seed=1).verdict is Verdict.INCONCLUSIVE


def test_a_rise_is_not_working() -> None:
    assert block_effect("v", constant(-10.0, -20.0), seed=1).verdict is Verdict.NOT_WORKING


def test_fewer_than_15_classes_in_either_arm_is_inconclusive() -> None:
    assert MIN_CLASSES_PER_ARM == 15
    big_effect = block_effect("v", constant(-50.0, -10.0, n=14), seed=1)
    assert big_effect.verdict is Verdict.INCONCLUSIVE and big_effect.reason == "too_few_classes"
    lopsided = arms([-50.0] * 20, [-10.0] * 14)
    assert block_effect("v", lopsided, seed=1).verdict is Verdict.INCONCLUSIVE
    assert block_effect("v", constant(-50.0, -10.0, n=15), seed=1).verdict is Verdict.WORKING


def test_a_wide_interval_crossing_zero_is_inconclusive_even_with_a_big_estimate() -> None:
    rng = np.random.default_rng(7)
    track = list(-30 + rng.normal(0, 40, 16))
    comparison = list(-10 + rng.normal(0, 40, 16))
    result = block_effect("v", arms(track, comparison), seed=3)
    assert result.estimate_points is not None and result.ci_low < 0 < result.ci_high
    assert result.verdict is not Verdict.WORKING


def test_empty_arm_is_inconclusive_not_a_crash() -> None:
    result = block_effect("v", arms([-10.0] * 20, []), seed=1)
    assert result.verdict is Verdict.INCONCLUSIVE and result.estimate_points is None


def test_bootstrap_is_deterministic_by_seed() -> None:
    rng = np.random.default_rng(1)
    data = arms(list(rng.normal(-25, 8, 20)), list(rng.normal(-5, 8, 20)))
    one, two = block_effect("v", data, seed=11), block_effect("v", data, seed=11)
    assert one == two
    other = block_effect("v", data, seed=12)
    assert (other.ci_low, other.ci_high) != (one.ci_low, one.ci_high)
    assert other.estimate_points == one.estimate_points


def test_interval_brackets_the_estimate_and_uses_95_percent() -> None:
    rng = np.random.default_rng(2)
    data = arms(list(rng.normal(-25, 8, 30)), list(rng.normal(-5, 8, 30)))
    result = block_effect("v", data, B=2000, seed=5)
    assert result.ci_low < result.estimate_points < result.ci_high
    # about 4 standard errors wide for a 95% interval
    se = float(np.sqrt(8**2 / 30 * 2))
    assert 2.5 * se < result.ci_high - result.ci_low < 5.5 * se


def test_means_and_facts_for_the_explanation_line() -> None:
    result = block_effect("SUB-SFL v1", constant(-30.0, -20.0), seed=1)
    assert result.mean_delta_track == -30.0 and result.mean_delta_comparison == -20.0
    facts = result.facts()
    assert facts["version"] == "SUB-SFL v1"
    assert facts["n_track"] == facts["n_comparison"] == 20
    assert facts["verdict"] == "working"


def test_rules_match_the_golden_text() -> None:
    rules = GOLDEN["block_verdict_rules"]
    assert "15" in rules["inconclusive"] and "10" in rules["working"]


# --- confidence notes and the hide rule --------------------------------------------------


def test_confidence_notes_for_small_samples() -> None:
    assert confidence_note(3) == "from 3 classes, read as directional"
    assert confidence_note(14) == "from 14 classes, read as directional"
    assert confidence_note(15) is None


def test_figures_covering_fewer_than_5_classes_are_hidden() -> None:
    small = block_effect("v", arms([-30.0] * 4, [-10.0] * 20), seed=1)
    assert small.hidden and not block_effect("v", constant(-30.0, -10.0, n=5), seed=1).hidden
    assert small.confidence_note is not None


@pytest.mark.parametrize("n", [15, 16, 40])
def test_no_note_when_both_arms_are_large_enough(n: int) -> None:
    assert block_effect("v", constant(-30.0, -10.0, n=n), seed=1).confidence_note is None


def test_class_changes_turns_two_terms_of_counts_into_point_changes() -> None:
    from engine.evaluation import class_changes
    from engine.grouping import ClassRecord
    from engine.model import ErrorCode

    def rec(cid: str, showing: int, checked: int) -> ClassRecord:
        return ClassRecord(
            cid, "s", "b", "government", 3, "hindi", checked, {ErrorCode.SUB_SFL: showing}
        )

    before = {
        "a": rec("a", 12, 30),
        "b": rec("b", 10, 20),
        "c": rec("c", 5, 20),
        "z": rec("z", 5, 0),
    }
    after = {"a": rec("a", 6, 30), "b": rec("b", 12, 20), "z": rec("z", 1, 10)}
    groups = {"a": Group.TRACK, "b": Group.COMPARISON, "c": Group.TRACK, "z": Group.TRACK}
    changes = class_changes(ErrorCode.SUB_SFL, before, after, groups)
    assert [(c.class_id, c.group, round(c.delta_points, 6)) for c in changes] == [
        ("a", Group.TRACK, -20.0),
        ("b", Group.COMPARISON, 10.0),
    ]  # "c" has no second term and "z" had no children at the first
