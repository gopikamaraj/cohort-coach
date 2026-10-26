"""P09 T01: the track definition, the strategy library and the templates are data that must stay
valid: six lessons, strategies that fit the error, templates that only name known slots, and no
check item (Form A or B) anywhere in the content."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ai.validators.arithmetic import check_arithmetic
from ai.validators.check_items import check_items, scan_content
from services.content import slots
from services.content.track import load_strategies, load_template, load_track

ROOT = Path(__file__).resolve().parents[2]
CONTENT = ROOT / "content"


def test_sub_sfl_track_has_six_lessons_in_three_languages() -> None:
    track = load_track("sub-sfl.v1")
    assert track.error == "SUB-SFL" and track.version == 1
    assert [lesson.day for lesson in track.lessons] == [1, 2, 3, 4, 5, 6]
    assert set(track.languages) == {"hi", "en", "ta"}
    for lesson in track.lessons:
        assert lesson.topic["en"] and lesson.topic["hi"], lesson.id
    assert len({lesson.id for lesson in track.lessons}) == 6


def test_every_lesson_uses_only_strategies_that_fit_the_error() -> None:
    track = load_track("sub-sfl.v1")
    library = load_strategies()
    for lesson in track.lessons:
        assert lesson.strategies, lesson.id
        for sid in lesson.strategies:
            assert sid in library, (lesson.id, sid)
            assert track.error in library[sid].fits, (lesson.id, sid)


def test_the_order_probe_is_in_the_sub_sfl_lessons_and_practice_levels_are_set() -> None:
    track = load_track("sub-sfl.v1")
    assert any("order_probe" in lesson.strategies for lesson in track.lessons)
    assert {lesson.practice_level for lesson in track.lessons} == {1, 2}


def test_a_track_takes_at_most_three_method_cards() -> None:
    assert len(load_track("sub-sfl.v1").method_cards) <= 3


def test_strategies_are_drafts_until_a_person_approves_them() -> None:
    for strategy in load_strategies().values():
        assert strategy.status in {"draft", "in_review", "approved", "active", "retired"}
        assert strategy.fits
        assert strategy.label["en"] and strategy.label["hi"]


def test_worked_examples_are_correct_and_never_check_items() -> None:
    for strategy in load_strategies().values():
        for example in strategy.worked_examples:
            assert check_arithmetic(example) == [], (strategy.id, example)
            assert check_items(example) == [], (strategy.id, example)


def test_nothing_under_content_holds_a_form_a_or_b_item() -> None:
    hits = scan_content(CONTENT)
    assert hits == [], [(str(p), [v.detail for v in vs]) for p, vs in hits]


@pytest.mark.parametrize("name", ["voice_lesson.v1.md", "model_lesson.v1.md"])
def test_templates_name_only_known_slots(name: str) -> None:
    text = load_template(name)
    used = set(re.findall(r"\{\{\s*([\w.]+)\s*\}\}", text))
    assert used, name
    assert used <= set(slots.SLOT_NAMES), sorted(used - set(slots.SLOT_NAMES))


def test_the_voice_lesson_template_has_the_seven_parts_in_order() -> None:
    text = load_template("voice_lesson.v1.md")
    parts = re.findall(r"^## (.+)$", text, re.M)
    assert [p.split(" (")[0] for p in parts] == [
        "Hook",
        "The mistake in one child's words",
        "The move",
        "A two-line script to use",
        "Try tomorrow",
        "Reflection prompt",
    ]
    assert "550" in text and "650" in text  # the spoken-word range is stated


def test_the_model_lesson_template_marks_child_lines_and_the_check() -> None:
    text = load_template("model_lesson.v1.md")
    for needle in ("Teacher says", "Child says", "Materials", "Timing", "check by adding back"):
        assert needle.lower() in text.lower(), needle


def test_the_slot_registry_is_a_closed_list_with_a_source_for_each() -> None:
    assert slots.SLOT_NAMES
    for name in slots.SLOT_NAMES:
        assert slots.SLOT_SOURCES[name]
