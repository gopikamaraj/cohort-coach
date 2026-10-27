"""The data budget is arithmetic on enforced limits; it says plainly when the target is missed."""

from __future__ import annotations

from scripts.data_budget import TARGET_MB, budget
from services.content.lessons_view import MAX_LESSON_SECONDS
from services.content.publish import KBPS


def test_six_lessons_at_the_cap_are_counted_at_the_enforced_bit_rate() -> None:
    row = next(v for k, v in budget()["rows_mb"].items() if "voice lessons" in k)
    assert row == round(6 * MAX_LESSON_SECONDS * KBPS * 1000 / 8 / 1_000_000, 3)


def test_the_track_fits_the_target_with_text_practice_and_not_with_voice_every_time() -> None:
    b = budget()
    assert b["total_mb_text_practice"] < TARGET_MB
    assert b["within_target_text"] is True
    assert b["within_target_voice"] is False  # said plainly: six voice sessions break the target
    assert b["kind"].startswith("computed")  # never presented as a measured journey


def test_the_total_is_the_sum_of_its_rows() -> None:
    b = budget()
    assert round(sum(b["rows_mb"].values()), 3) == b["total_mb_text_practice"]
