import json

import pytest

import engine.evaluation as evaluation
from engine.evaluation import BlockEffect, Verdict
from evals.runners.statistics import BARS, run


def test_bars_are_the_ones_in_the_design() -> None:
    assert BARS == {"recovery": 0.95, "false_working": 0.05}


def test_quick_run_passes_the_bars() -> None:
    result = run(n_null=40, n_planted=40)
    assert result["passed"] is True
    assert result["recovery"] >= 0.95 and result["false_working"] <= 0.05
    assert result["arm_size"] >= 15


def test_run_is_deterministic_and_json_serialisable() -> None:
    one = run(n_null=10, n_planted=10, n_characterise=0)
    assert one == run(n_null=10, n_planted=10, n_characterise=0)
    json.dumps(one)


def test_effect_sizes_and_trial_counts_are_documented_in_the_result() -> None:
    result = run(n_null=9, n_planted=9, n_characterise=4)
    assert result["planted_effects_points"] == [15, 20, 25]
    assert set(result["per_effect"]) >= {"0", "15", "20", "25", "5", "10"}
    assert sum(v["trials"] for k, v in result["per_effect"].items() if k in {"15", "20", "25"}) == 9
    assert result["per_effect"]["0"]["trials"] == 9


def _fake(verdict: Verdict):  # type: ignore[no-untyped-def]
    def fake(version: str, changes: object, **kw: object) -> BlockEffect:
        return BlockEffect(
            version, verdict, "fake", -20.0, -25.0, -15.0, 20, 20, -30.0, -10.0, None
        )

    return fake


def test_the_eval_fails_if_the_test_calls_everything_working(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("evals.runners.statistics.block_effect", _fake(Verdict.WORKING))
    result = run(n_null=20, n_planted=20, n_characterise=0)
    assert result["false_working"] == 1.0 and result["passed"] is False


def test_the_eval_fails_if_the_test_never_finds_a_real_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("evals.runners.statistics.block_effect", _fake(Verdict.INCONCLUSIVE))
    result = run(n_null=20, n_planted=20, n_characterise=0)
    assert result["recovery"] == 0.0 and result["passed"] is False
    assert evaluation.block_effect  # the real function is untouched outside the patch
