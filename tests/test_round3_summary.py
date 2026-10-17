from __future__ import annotations

import pytest

from scripts.round3_summary import SUS_COLUMNS, summarise, sus_score


def row(code: str, sus: list[int], realism: int = 4, finished: str = "y") -> dict[str, str]:
    base = {
        "participant": code,
        "realism_1to5": str(realism),
        "feedback_useful_1to5": "4",
        "finished_rehearsal": finished,
    }
    return {**base, **{c: str(v) for c, v in zip(SUS_COLUMNS, sus, strict=True)}}


def test_sus_scoring_matches_brookes_rule() -> None:
    assert sus_score([5, 1, 5, 1, 5, 1, 5, 1, 5, 1]) == 100.0  # best possible
    assert sus_score([1, 5, 1, 5, 1, 5, 1, 5, 1, 5]) == 0.0  # worst possible
    assert sus_score([3] * 10) == 50.0
    assert sus_score([4, 2, 4, 2, 4, 2, 4, 2, 4, 2]) == 75.0


@pytest.mark.parametrize("bad", [[3] * 9, [3] * 11, [0] + [3] * 9, [6] + [3] * 9])
def test_a_malformed_response_is_rejected(bad: list[int]) -> None:
    with pytest.raises(ValueError):
        sus_score(bad)


def test_summary_is_computed_and_labelled_directional_for_a_small_group() -> None:
    rows = [
        row("T3-01", [5, 1, 5, 1, 5, 1, 5, 1, 5, 1], realism=5),
        row("T3-02", [3] * 10, realism=3, finished="n"),
        row("T3-03", [4, 2, 4, 2, 4, 2, 4, 2, 4, 2], realism=4),
    ]
    s = summarise(rows)
    assert s["teachers"] == 3 and s["sus_mean"] == round((100 + 50 + 75) / 3, 1)
    assert s["sounds_like_my_class_median"] == 4 and s["finished_rehearsal"] == "2 of 3"
    assert s["confidence_note"] == "from 3 teachers, read as directional"
    assert s["sus_by_participant"] == {"T3-01": 100.0, "T3-02": 50.0, "T3-03": 75.0}


def test_missing_ratings_show_pending_not_a_number() -> None:
    r = row("T3-01", [3] * 10)
    r["realism_1to5"] = ""
    r["feedback_useful_1to5"] = ""
    s = summarise([r])
    assert (
        s["sounds_like_my_class_median"] == "pending" and s["feedback_useful_median"] == "pending"
    )


def test_an_empty_file_is_an_error_not_a_summary() -> None:
    with pytest.raises(ValueError):
        summarise([])
