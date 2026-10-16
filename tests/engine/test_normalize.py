import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from engine.normalize import normalize_answer


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("346", 346),
        (" 346 ", 346),
        ("३४६", 346),  # Devanagari
        ("௩௪௬", 346),  # Tamil
        ("३4६", 346),  # mixed scripts
        ("3 46", 346),  # inner spaces stripped
        ("", "blank"),
        ("   ", "blank"),
        (None, "blank"),
        ("3a6", "unreadable"),
        ("?", "unreadable"),
        ("-5", "unreadable"),
        ("3.5", "unreadable"),
        ("1234567890123", "unreadable"),
        ("٣٤٦", "unreadable"),  # Arabic-Indic: not in the pilot's scripts
    ],
)
def test_normalize(raw: str | None, expected: int | str) -> None:
    assert normalize_answer(raw) == expected


@settings(max_examples=500)
@given(st.integers(min_value=0, max_value=999_999))
def test_ascii_round_trip(n: int) -> None:
    assert normalize_answer(str(n)) == n
