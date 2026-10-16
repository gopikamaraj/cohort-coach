"""Smoke test: every tasks.py command exits 0 or prints its 'available after PXX' message."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Commands whose phase has not arrived. Remove from this list as phases land.
DEFERRED = {
    "eval": "P13",
    "seed": "P02",
    "budget": "P03",
    "evidence": "P02",
    "readme": "P03",
}


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "tasks.py"), *args],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=60,
    )


@pytest.mark.parametrize("command,phase", sorted(DEFERRED.items()))
def test_deferred_commands_say_when(command: str, phase: str) -> None:
    result = run(command)
    assert result.returncode == 0, result.stderr
    assert f"available after {phase}" in result.stdout


def test_every_documented_command_is_registered() -> None:
    result = run("--list")
    assert result.returncode == 0
    for name in [
        "setup",
        "dev",
        "test",
        "check",
        "eval",
        "seed",
        "export-keys",
        "budget",
        "evidence",
        "readme",
    ]:
        assert name in result.stdout


def test_unknown_command_fails() -> None:
    assert run("nope").returncode != 0


def test_export_keys_check_passes_on_committed_files() -> None:
    result = run("export-keys", "--check")
    assert result.returncode == 0, result.stdout
    assert "STALE" not in result.stdout
