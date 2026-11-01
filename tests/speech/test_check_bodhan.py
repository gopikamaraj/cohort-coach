"""scripts/check_bodhan.py: keys masked to 4 characters, and an exit code that says which key
failed. Live calls go to the Bodhan mock; no network."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

from services.speech.bodhan import BodhanClient
from tests.speech.bodhan_mock import SPEAK_KEY, TRANSCRIBE_KEY, BodhanMock

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_bodhan.py"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_bodhan", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_bodhan"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BODHAN_SPEAK_API_KEY", SPEAK_KEY)
    monkeypatch.setenv("BODHAN_TRANSCRIBE_API_KEY", TRANSCRIBE_KEY)
    monkeypatch.setenv("BODHAN_API_KEY", "")


def run(mod: ModuleType, mock: BodhanMock, monkeypatch: pytest.MonkeyPatch, *args: str) -> int:
    monkeypatch.setattr(
        mod, "BodhanClient", lambda: BodhanClient(client=mock.client(), sleep=lambda s: None)
    )
    return int(mod.main(list(args)))


def test_no_live_checks_configuration_and_masks_the_keys(
    keys: None, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    mock = BodhanMock()
    assert run(load(), mock, monkeypatch, "--no-live") == 0
    out = capsys.readouterr().out
    assert SPEAK_KEY not in out and TRANSCRIBE_KEY not in out
    assert f"{SPEAK_KEY[:4]}... ({len(SPEAK_KEY)} characters)" in out
    assert "estimated cost" in out and mock.requests == []


def test_a_missing_key_is_exit_1(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("BODHAN_SPEAK_API_KEY", "BODHAN_TRANSCRIBE_API_KEY", "BODHAN_API_KEY"):
        monkeypatch.setenv(var, "")  # set but empty: .env cannot fill it
    monkeypatch.setenv("BODHAN_SPEAK_API_KEY", SPEAK_KEY)
    assert run(load(), BodhanMock(), monkeypatch, "--no-live") == 1


def test_live_round_trip_success_speak_failure_and_transcribe_failure(
    keys: None, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    mod = load()
    assert run(mod, BodhanMock(), monkeypatch) == 0
    out = capsys.readouterr().out
    assert "both keys work" in out and "heard in hi" in out and "request id req-0001" in out
    assert run(mod, BodhanMock(fail=[401]), monkeypatch) == 2
    monkeypatch.setenv("BODHAN_TRANSCRIBE_API_KEY", "wrong-transcribe-key")
    assert run(mod, BodhanMock(), monkeypatch) == 3
    assert "wrong-transcribe-key" not in capsys.readouterr().out
