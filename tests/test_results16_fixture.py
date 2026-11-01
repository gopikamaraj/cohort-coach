"""The 16-roll class behind e2e/results.spec.ts is what the engine says today."""

from scripts.make_results16 import OUT, render


def test_the_fixture_matches_the_engine() -> None:
    assert OUT.read_text(encoding="utf-8") == render(), "run python scripts/make_results16.py"
