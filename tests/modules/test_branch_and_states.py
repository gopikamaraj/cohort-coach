"""The branch table (pure code), the module state machine, the reason strings in three languages."""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import pytest

from services.modules import branch, library, states
from services.modules.branch import Done, Plan, Template, next_module

PLAN = Plan(
    "SUB-SFL",
    (Template("a", ("x",)), Template("b", ("y",)), Template("c", ())),
    ("z",),
)
STRINGS = Path(__file__).resolve().parents[2] / "strings"


def hist(*approaches: str) -> list[Done]:
    return [Done(i + 1, a) for i, a in enumerate(approaches)]


# ---- the branch table ----------------------------------------------------------------------------


def test_the_first_module_is_the_first_in_the_plan() -> None:
    got = next_module(PLAN, [], None, 6)
    assert (got.approach, got.branch, got.reason.code) == ("a", "first", "first")


def test_tried_goes_to_the_next_module_in_the_plan() -> None:
    got = next_module(PLAN, hist("a"), "tried", 6)
    assert (got.approach, got.branch, got.smaller) == ("b", "tried", False)


def test_partly_repeats_the_same_approach_as_a_smaller_step() -> None:
    got = next_module(PLAN, hist("a"), "partly", 6)
    assert (got.approach, got.branch, got.smaller) == ("a", "partly", True)


def test_after_a_smaller_step_the_plan_is_rejoined_on_tried() -> None:
    got = next_module(PLAN, [Done(1, "a"), Done(2, "a", "partly")], "tried", 6)
    assert got.approach == "b"


def test_not_yet_gives_a_different_approach_from_the_templates_alternatives() -> None:
    got = next_module(PLAN, hist("a"), "not_yet", 6)
    assert (got.approach, got.branch) == ("x", "not_yet")


def test_not_yet_skips_approaches_already_used() -> None:
    got = next_module(PLAN, hist("a", "x"), "not_yet", 6)
    assert got.approach not in {"a", "x"} and got.approach == "b"  # x has no alternatives left


def test_no_feedback_is_the_planned_next_module_and_is_not_read_as_tried() -> None:
    got = next_module(PLAN, hist("a"), None, 6)
    assert (got.approach, got.branch, got.reason.code) == ("b", "no_feedback", "no_feedback")
    assert got.branch != "tried"


def test_an_approach_is_never_repeated_except_after_partly() -> None:
    for answers in itertools.product(("tried", "not_yet", None), repeat=5):
        done: list[Done] = []
        for answer in (None, *answers):
            got = next_module(PLAN, done, answer, 9)
            if got.stops:
                break
            if got.branch != "partly":
                assert got.approach not in {d.approach for d in done}, (answers, done)
            done.append(Done(len(done) + 1, got.approach or "", got.branch))


def test_the_cap_stops_the_track_with_a_person_to_talk_to() -> None:
    got = next_module(PLAN, hist("a", "b"), "tried", 2)
    assert got.stop == branch.STOP_CAP and got.reason.code == "stop_cap" and got.approach is None


def test_when_the_plan_and_alternatives_run_out_it_stops_and_says_so() -> None:
    p = Plan("PV-REVERSE", (Template("only"),), ())
    got = next_module(p, hist("only"), "not_yet", 6)
    assert got.stop == branch.STOP_EXHAUSTED


def test_a_finished_plan_is_a_normal_end_not_a_referral() -> None:
    got = next_module(PLAN, hist("a", "b", "c"), "tried", 9)
    assert got.stop == branch.STOP_DONE


def test_the_end_date_stops_planning() -> None:
    got = next_module(PLAN, hist("a"), None, 6, past_end=True)
    assert got.stop == branch.STOP_END_DATE


def test_a_bad_answer_is_refused() -> None:
    with pytest.raises(ValueError):
        next_module(PLAN, hist("a"), "great", 6)


def test_partly_repeated_is_still_bounded_by_the_cap() -> None:
    done = [Done(1, "a")]
    out = next_module(PLAN, done, "partly", 2)
    assert out.approach == "a"
    done.append(Done(2, "a", "partly"))
    assert next_module(PLAN, done, "partly", 2).stop == branch.STOP_CAP


# ---- the state machine ---------------------------------------------------------------------------


def test_every_state_is_listed_and_every_pair_is_legal_or_not_as_declared() -> None:
    assert set(states.TRANSITIONS) == set(states.STATES)
    for old, new in itertools.product(states.STATES, repeat=2):
        legal = new in states.TRANSITIONS[old]
        assert states.can(old, new) is legal
        if legal:
            states.check(old, new)
        else:
            with pytest.raises(states.IllegalTransition):
                states.check(old, new)


def test_the_main_path_is_legal() -> None:
    path = [
        states.PLANNED,
        states.READY,
        states.DOWNLOADED,
        states.FEEDBACK_GIVEN,
        states.COMPLETED,
    ]
    for a, b in itertools.pairwise(path):
        assert states.can(a, b)


def test_silence_then_a_late_answer_is_legal_but_nothing_leaves_a_finished_state() -> None:
    assert states.can(states.READY, states.EXPIRED) and states.can(
        states.EXPIRED, states.FEEDBACK_GIVEN
    )
    for end in (states.COMPLETED, states.SKIPPED):
        assert not states.TRANSITIONS[end]


# ---- reasons in three languages -----------------------------------------------------------------


@pytest.mark.parametrize("lang", ["en", "hi", "ta"])
def test_every_reason_code_has_a_sentence_in_every_language(lang: str) -> None:
    table = json.loads((STRINGS / f"{lang}.json").read_text(encoding="utf-8"))
    for code in branch.REASONS:
        text = table.get(f"module.reason.{code}")
        assert text, (lang, code)
        if code in ("tried", "partly", "not_yet", "no_feedback"):
            assert "{n}" in text and "{prev}" in text, (lang, code)
        if code == "first":
            assert "{n}" in text


def test_the_not_yet_reason_names_both_modules() -> None:
    from services.modules.service import reason_text

    out = reason_text({"code": "not_yet", "n": 3, "prev": 2}, "en")
    assert (
        out == "Module 3 is a different approach because you told us Module 2 is not yet working."
    )


def test_no_user_facing_string_still_says_lesson_for_a_module() -> None:
    en = json.loads((STRINGS / "en.json").read_text(encoding="utf-8"))
    for key, value in en.items():
        if key.startswith("module."):
            assert "lesson" not in value.lower(), key


# ---- the library ---------------------------------------------------------------------------------


@pytest.mark.parametrize("error", ["SUB-SFL", "SUB-NODEC", "ADD-NOCARRY", "PV-HEARD", "PV-REVERSE"])
def test_every_planned_approach_has_text_in_english(error: str) -> None:
    for approach in library.plan_for(error).approaches():
        mt = library.module_text(error, approach, False, "en")
        assert not mt.omitted, (error, approach, mt.omitted)
        assert {p.id for p in mt.parts} >= {"purpose", "steps", "check"}


def test_an_error_with_no_plan_gets_one_module_and_says_so() -> None:
    assert not library.has_plan("ADD-WHOLE-ONES")
    assert library.planned_length("ADD-WHOLE-ONES") == 1


def test_the_smaller_step_text_is_the_first_step_only() -> None:
    full = library.module_text("SUB-SFL", "exchange_ten", False, "en")
    small = library.module_text("SUB-SFL", "exchange_ten", True, "en")
    steps = lambda m: next(p for p in m.parts if p.id == "steps").items  # noqa: E731
    assert len(steps(small) or []) == 1 and len(steps(full) or []) > 1
    assert small.parts[0].id == "smaller_step"


def test_a_missing_language_shows_english_with_a_note() -> None:
    mt = library.module_text("SUB-SFL", "ask_explain", False, "ta")
    assert any(p.fallback for p in mt.parts) and all(p.text or p.items for p in mt.parts)


def test_the_plan_file_only_names_approaches_the_library_has() -> None:
    for error in library.config()["errors"]:
        for approach in library.plan_for(error).approaches():
            assert library.module_text(error, approach, False, "en").parts, (error, approach)
