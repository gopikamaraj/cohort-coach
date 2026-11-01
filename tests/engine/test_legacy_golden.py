"""The legacy simulator is untouched by the 32-state Bayesian build: its file hash and its golden
runs (every scenario, seeds 1 to 20, two scripts) are the ones saved before the build began."""

from __future__ import annotations

import json

import pytest

from tests.engine.legacy_golden import FIXTURE, HASH_FILE, capture, simulator_hash


def test_engine_simulator_py_is_byte_for_byte_the_recorded_file() -> None:
    assert simulator_hash() == HASH_FILE.read_text(encoding="utf-8").split()[0]


def _same(now: dict, saved: dict) -> None:  # type: ignore[type-arg]
    assert set(now) == set(saved)
    for kind in saved:
        assert len(now[kind]) == len(saved[kind]) == 80
        for got, want in zip(now[kind], saved[kind], strict=True):
            assert got == want, f"{kind} {want['error']} seed {want['seed']} differs"


@pytest.mark.parametrize("setting", [None, "legacy"])
def test_legacy_plays_every_saved_run_turn_for_turn(
    setting: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    if setting is None:
        monkeypatch.delenv("SIMULATOR_MODEL", raising=False)
    else:
        monkeypatch.setenv("SIMULATOR_MODEL", setting)
    saved = json.loads(FIXTURE.read_text(encoding="utf-8"))
    _same(json.loads(json.dumps(capture())), saved)
