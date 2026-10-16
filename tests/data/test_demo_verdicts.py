import json
from pathlib import Path
from typing import Any

import pytest

import engine.evaluation as evaluation
from data.synthetic.block import generate_block, load_config, track_verdicts
from engine.evaluation import Verdict

BLOCK_PATH = Path(__file__).resolve().parents[2] / "data" / "synthetic" / "block_T1T2.json"


@pytest.fixture(scope="module")
def committed() -> dict[str, Any]:
    return json.loads(BLOCK_PATH.read_text(encoding="utf-8"))


def test_sub_sfl_v1_works_and_sub_nodec_v1_does_not(committed: dict[str, Any]) -> None:
    verdicts = track_verdicts(committed)
    sfl, nodec = verdicts["SUB-SFL v1"], verdicts["SUB-NODEC v1"]
    assert sfl.verdict is Verdict.WORKING
    assert sfl.ci_high is not None and sfl.ci_high < 0
    assert sfl.estimate_points is not None and -26 < sfl.estimate_points <= -10
    assert nodec.verdict is Verdict.NOT_WORKING
    assert nodec.estimate_points is not None and nodec.estimate_points > -5
    assert min(sfl.n_track, sfl.n_comparison, nodec.n_track, nodec.n_comparison) >= 15


def test_small_tracks_are_inconclusive_and_say_so(committed: dict[str, Any]) -> None:
    verdicts = track_verdicts(committed)
    for key in ("PV-HEARD v1", "ADD-NOCARRY v1"):
        v = verdicts[key]
        assert v.verdict is Verdict.INCONCLUSIVE and v.reason == "too_few_classes"
        assert v.confidence_note is not None and "read as directional" in v.confidence_note


def test_the_verdict_comes_from_the_evaluation_code(
    committed: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    real = evaluation.block_effect

    def spy(version: str, changes: Any, **kw: Any) -> Any:
        calls.append(version)
        return real(version, changes, **kw)

    monkeypatch.setattr("data.synthetic.block.block_effect", spy)
    track_verdicts(committed)
    assert {"SUB-SFL v1", "SUB-NODEC v1"} <= set(calls)


def test_no_verdict_is_stored_in_the_data(committed: dict[str, Any]) -> None:
    text = json.dumps(committed).lower()
    assert "not_working" not in text and '"working"' not in text and "verdict" not in text


def test_swapping_the_planted_effects_swaps_the_verdicts() -> None:
    """If the verdicts were hardcoded this would not follow the data."""
    tc = load_config()["term_change"]
    swapped = {**tc, "tracks": {**tc["tracks"]}}
    swapped["tracks"]["SUB-SFL"] = {"version": "v1", "extra_fix": 0.0}
    swapped["tracks"]["SUB-NODEC"] = {"version": "v1", "extra_fix": 0.36}
    verdicts = track_verdicts(generate_block({"term_change": swapped}))
    assert verdicts["SUB-SFL v1"].verdict is Verdict.NOT_WORKING
    assert verdicts["SUB-NODEC v1"].verdict is Verdict.WORKING
