"""P09 T03: call 5 drafts one lesson (or the model lesson) in one language; code checks it before it
can reach the review queue. No paid call: a fake client stands in for the model."""

from __future__ import annotations

import json
import re

import pytest

from ai.calls.c05_track_draft import (
    PartDraft,
    build_payload,
    draft_part,
    review_content,
)
from ai.client import CallContext
from ai.schemas import TrackPart, Verdict
from services.content.track import load_track
from tests.support_ai import FakeClient

GOOD = (
    "Today's lesson is about one mistake. {{class.count_showing}} of {{class.children_checked}} "
    "children made it. A child takes the smaller digit from the larger. For {{class.example_a}} "
    "minus {{class.example_b}} she writes {{class.example_wrong_answer}}. The right answer is "
    "{{class.example_correct_answer}}. Ask her how she got it. Then show it with bundles of ten: "
    "63 - 28 = 35. Try it tomorrow with one child."
)
PASS = Verdict(passed=True, reason_short="ok", reason_for_user="ok")


def ctx(*replies: object, retries_ok: bool = True) -> CallContext:
    return CallContext(mode="stub", client=FakeClient(list(replies)))  # type: ignore[arg-type]


def part(script: str, day: int = 1) -> TrackPart:
    return TrackPart(kind="lesson", day=day, script=script)


def test_the_payload_carries_the_error_strategies_slots_and_no_class_number() -> None:
    track = load_track("sub-sfl.v1")
    payload = build_payload(track, "lesson", 1, "en", method_cards=())
    trusted = payload.trusted
    assert trusted["error"] == "SUB-SFL" and trusted["language"] == "en"
    assert {s["id"] for s in trusted["strategies"]} == {"ask_explain", "order_probe"}
    assert "class.count_showing" in trusted["slots"]
    assert trusted["practice_level"] == 1
    # the instructions may say "never write a percentage"; no actual class figure may be in them
    flat = json.dumps(trusted)
    assert "%" not in flat
    assert not re.search(r"\d+ of \d+ children", flat)


def test_method_cards_are_sent_whole_as_mentor_text_and_capped_at_three() -> None:
    track = load_track("sub-sfl.v1")
    cards = [f"card {i}" for i in range(5)]
    payload = build_payload(track, "lesson", 2, "en", method_cards=cards)
    assert payload.untrusted["mentor_text"].count("card ") == 3


def test_a_clean_draft_passes_the_gates_and_goes_to_review() -> None:
    track = load_track("sub-sfl.v1")
    draft = draft_part(track, "lesson", 1, "en", context=ctx(part(GOOD), PASS))
    assert isinstance(draft, PartDraft)
    assert draft.status == "needs_review"
    assert draft.part is not None and draft.gate is not None and draft.gate.passed_automatic
    assert draft.gate.releasable is False  # a person reviews it next: not releasable yet
    assert "Waiting" in draft.explanation or "Checked" in draft.explanation


def test_wrong_arithmetic_is_blocked_before_the_queue() -> None:
    track = load_track("sub-sfl.v1")
    bad = GOOD.replace("63 - 28 = 35", "63 - 28 = 36")
    draft = draft_part(track, "lesson", 1, "en", context=ctx(part(bad)))
    assert draft.status == "held_by_code" and draft.part is None
    assert any("arithmetic_wrong" in r.codes for r in draft.results)
    assert "maths" in draft.explanation.lower()


def test_a_form_item_in_the_draft_is_blocked_and_names_the_form_and_item() -> None:
    track = load_track("sub-sfl.v1")
    bad = GOOD.replace("63 - 28 = 35", "45 - 19 = 26")
    draft = draft_part(track, "lesson", 1, "en", context=ctx(part(bad)))
    assert draft.status == "held_by_code"
    detail = " ".join(v.detail for r in draft.results for v in r.violations)
    assert "Form" in detail and "item" in detail


def test_a_literal_class_count_is_blocked() -> None:
    track = load_track("sub-sfl.v1")
    bad = GOOD.replace("{{class.count_showing}} of {{class.children_checked}}", "11 of 28")
    draft = draft_part(track, "lesson", 1, "en", context=ctx(part(bad)))
    assert draft.status == "held_by_code"
    assert any("class_number_literal" in r.codes for r in draft.results)


def test_an_unknown_slot_is_blocked() -> None:
    track = load_track("sub-sfl.v1")
    draft = draft_part(
        track, "lesson", 1, "en", context=ctx(part(GOOD + " {{class.secret_number}}"))
    )
    assert draft.status == "held_by_code"
    assert any("slot_unknown" in r.codes for r in draft.results)


def test_an_intentional_child_mistake_is_allowed_when_tagged() -> None:
    track = load_track("sub-sfl.v1")
    tagged = GOOD + " Meena writes 52 - 29 = [child: 37]. Ask her to explain."
    draft = draft_part(track, "lesson", 1, "en", context=ctx(part(tagged), PASS))
    assert draft.status == "needs_review"


def test_the_checker_can_hold_a_draft_that_passed_the_code_checks() -> None:
    track = load_track("sub-sfl.v1")
    fail = Verdict(passed=False, failed_items=["tone"], reason_short="x", reason_for_user="harsh")
    draft = draft_part(track, "lesson", 1, "en", context=ctx(part(GOOD), fail))
    assert draft.status == "held_by_checker"
    assert draft.part is not None  # kept so a person can see what was held and why


def test_the_model_lesson_is_drafted_the_same_way() -> None:
    track = load_track("sub-sfl.v1")
    script = GOOD + " Teacher says: Open a bundle. Child says: Now I have 12."
    draft = draft_part(
        track,
        "model_lesson",
        0,
        "en",
        context=ctx(TrackPart(kind="model_lesson", day=0, script=script), PASS),
    )
    assert draft.status == "needs_review" and draft.kind == "model_lesson"


def test_no_output_from_the_model_is_reported_not_hidden() -> None:
    track = load_track("sub-sfl.v1")
    draft = draft_part(track, "lesson", 1, "en", context=ctx(None))
    assert draft.status == "no_output" and draft.part is None


def test_the_review_content_is_stored_with_its_check_results_and_slots() -> None:
    track = load_track("sub-sfl.v1")
    draft = draft_part(track, "lesson", 1, "en", context=ctx(part(GOOD), PASS))
    content = review_content(draft, track)
    assert content["track_id"] == "sub-sfl.v1" and content["day"] == 1
    assert content["script"] == GOOD
    assert "class.count_showing" in content["slots_used"]
    assert {r["name"] for r in content["results"]} >= {"slots", "arithmetic", "check_items"}
    assert content["strategies"] == ["ask_explain", "order_probe"]
    assert content["todo_human"].startswith("TODO-HUMAN(Seema)")


@pytest.mark.parametrize("bad_kind", ["lessons", "", "model"])
def test_an_unknown_part_kind_is_refused(bad_kind: str) -> None:
    track = load_track("sub-sfl.v1")
    with pytest.raises(ValueError):
        draft_part(track, bad_kind, 1, "en", context=ctx(part(GOOD)))
