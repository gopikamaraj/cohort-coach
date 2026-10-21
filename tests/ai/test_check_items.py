"""The no-check-items validator: no content may hold a Form A or Form B item (addendum §E)."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai.validators.check_items import (
    check_items,
    check_pair,
    dictation_numbers,
    forbidden_pairs,
    scan_content,
)

ROOT = Path(__file__).resolve().parents[2]


def codes(v: list) -> list[str]:  # type: ignore[type-arg]
    return [x.code for x in v]


def test_the_forbidden_list_comes_from_the_golden_file() -> None:
    pairs = forbidden_pairs()
    assert len(pairs) == 16  # items 3 to 10 on each of the two forms
    assert frozenset((45, 19)) in pairs and frozenset((87, 52)) in pairs  # item 6 too
    assert dictation_numbers() == {346, 728, 264, 853}


@pytest.mark.parametrize(
    "text",
    [
        "Take 45 - 19 with bundles.",
        "Try 19 − 45 today.",
        "What is 19 + 45?",
        "Ask: forty-five minus nineteen.",
        "Say 74 minus 36 aloud.",
        "Write three hundred and forty-six on the board.",
        "तीन सौ छियालीस लिखो।",
        "Dictate 728 to the class.",
    ],
)
def test_a_check_item_in_text_fails(text: str) -> None:
    assert codes(check_items(text)) and codes(check_items(text))[0] == "check_item"


@pytest.mark.parametrize(
    "text",
    [
        "63 - 28 with bundles: take 2 bundles, then 8 sticks.",
        "Take away 30 from 63, then give 1 back: 63 - 29 is 34.",
        "Is 2 - 6 the same as 6 - 2?",
        "52 - 29: the child writes 37.",
        "We have 45 sticks and 19 children.",  # two numbers but no operation
        "Write forty-three on the slate.",
    ],
)
def test_ordinary_teaching_text_passes(text: str) -> None:
    assert check_items(text) == []


def test_the_message_names_the_form_and_item() -> None:
    v = check_items("Try 45 - 19.")
    assert "Form A item 8" in v[0].detail and "Form B" not in v[0].detail


def test_a_structured_item_fails_in_either_order_and_with_either_operation() -> None:
    assert codes(check_pair(74, "-", 36)) == ["check_item"]
    assert codes(check_pair(36, "+", 74)) == ["check_item"]
    assert check_pair(63, "-", 28) == []


def test_every_file_under_content_passes() -> None:
    hits = scan_content(ROOT / "content")
    assert hits == [], hits


def test_the_scanner_finds_a_planted_item(tmp_path: Path) -> None:
    (tmp_path / "x.yaml").write_text("lines:\n  - 'Take 82 - 39 now'\n", encoding="utf-8")
    assert [h[0].name for h in scan_content(tmp_path)] == ["x.yaml"]
