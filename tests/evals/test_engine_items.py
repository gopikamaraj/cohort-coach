import json

import pytest

from engine.model import ErrorCode, Item, ItemType
from evals.runners.engine_items import BAR, oracle_answers, run


def test_oracle_matches_the_design_examples() -> None:
    assert oracle_answers(ErrorCode.PV_HEARD, Item(1, ItemType.DICTATION, 346)) == {
        30046,
        3046,
        300406,
    }
    assert oracle_answers(ErrorCode.PV_REVERSE, Item(1, ItemType.DICTATION, 346)) == {364}
    assert oracle_answers(ErrorCode.ADD_NOCARRY, Item(3, ItemType.ADD_CARRY, 47, 25)) == {62}
    assert oracle_answers(ErrorCode.SUB_SFL, Item(7, ItemType.SUB_BORROW, 52, 29)) == {37}
    assert oracle_answers(ErrorCode.SUB_NODEC, Item(7, ItemType.SUB_BORROW, 52, 29)) == {33}


def test_run_reports_every_error_at_100_percent_with_no_collisions() -> None:
    result = run(n=60)
    assert result["passed"] is True
    assert set(result["per_error"]) == {c.value for c in ErrorCode}
    for stats in result["per_error"].values():
        assert stats["n"] == 60
        assert stats["share_correct"] == 1.0
        assert stats["collisions"] == 0
    assert result["bar"] == BAR


def test_run_is_deterministic() -> None:
    assert run(n=30) == run(n=30)


def test_the_eval_can_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    """A deliberately broken error function must show up as a failed eval."""
    import engine.bugs

    monkeypatch.setattr(engine.bugs, "sub_sfl", lambda a, b: frozenset({0}))
    result = run(n=30)
    assert result["passed"] is False
    assert result["per_error"]["SUB-SFL"]["share_correct"] < 1.0
    assert result["per_error"]["PV-HEARD"]["share_correct"] == 1.0


def test_result_is_json_serialisable() -> None:
    json.dumps(run(n=10))
