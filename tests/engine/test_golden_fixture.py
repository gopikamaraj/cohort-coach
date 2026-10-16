"""The doc copy of the golden file stays the human reference; the fixture must match it."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_fixture_is_identical_to_design_doc_copy() -> None:
    doc = (ROOT / "docs/design/pilot_forms.golden.json").read_bytes()
    fixture = (ROOT / "tests/fixtures/pilot_forms.golden.json").read_bytes()
    assert doc == fixture
