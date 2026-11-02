"""Legacy is unchanged: the golden runs saved before the Bayesian model was added play the same."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.engine.sim_golden import capture

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "sim_legacy_golden.json"


@pytest.mark.parametrize("setting", [None, "legacy"])
def test_legacy_plays_the_saved_golden_runs_turn_for_turn(
    setting: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    if setting is None:
        monkeypatch.delenv("SIMULATOR_MODEL", raising=False)
    else:
        monkeypatch.setenv("SIMULATOR_MODEL", setting)
    saved = json.loads(FIXTURE.read_text(encoding="utf-8"))
    now = json.loads(json.dumps(capture()))  # the same JSON shape (tuples become lists)
    assert len(now["check_script"]) == len(saved["check_script"]) == 40
    assert len(now["every_move"]) == len(saved["every_move"]) == 40
    for kind in saved:
        for got, want in zip(now[kind], saved[kind], strict=True):
            assert got == want, f"{kind} {want['error']} seed {want['seed']} differs"
