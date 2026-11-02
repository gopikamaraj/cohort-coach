"""Number words a child wrote, read into digits by code."""

import pytest

from services.pilot_demo.numwords import parse


@pytest.mark.parametrize(
    ("words", "number"),
    [
        ("Three hundred fourty six", 346),
        ("seven hundred twenty eight", 728),
        ("Seven hundred and twenty-eight", 728),
        ("three hundred five", 305),
        ("four hundred ninty six", 496),
        ("four thousand ninety six", 4096),
        ("three hundered forty six", 346),
        ("TWENTY", 20),
    ],
)
def test_words_become_digits(words: str, number: int) -> None:
    assert parse(words) == number


@pytest.mark.parametrize("words", [None, "", "   ", "three hundred pizza", "346", "Asha"])
def test_anything_that_is_not_number_words_is_never_guessed(words: str | None) -> None:
    assert parse(words) is None
