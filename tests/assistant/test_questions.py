"""The question banks, and the pure function that picks the top five."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.assistant import answer, questions
from services.assistant.rubric import load as load_rubric
from services.assistant.scopes import ROLES, scopes

ROOT = Path(__file__).resolve().parents[2]
ROWS = {r.id for r in load_rubric()}


def bank(role: str) -> list[questions.Question]:
    raw = json.loads((ROOT / scopes()[role].question_bank).read_text(encoding="utf-8"))
    return questions.parse_bank(raw)


@pytest.mark.parametrize(
    ("role", "minimum"),
    [("teacher", 10), ("mentor", 10), ("coach", 10), ("officer", 10), ("judge", 40)],
)
def test_each_role_has_enough_questions(role: str, minimum: int) -> None:
    assert len(bank(role)) >= minimum


@pytest.mark.parametrize("role", ROLES)
def test_every_question_is_well_formed(role: str) -> None:
    seen: set[str] = set()
    for q in bank(role):
        assert q.id not in seen
        seen.add(q.id)
        assert q.text["en"].strip().endswith("?"), q.id
        assert set(q.screens) <= set(questions.VALID_SCREENS), q.id
        assert set(q.criteria) <= set(questions.VALID_CRITERIA), q.id
        assert set(q.rubric_rows) <= ROWS, (q.id, set(q.rubric_rows) - ROWS)
        assert all(1 <= s <= 12 for s in q.steps), q.id
        assert q.query.strip()


def test_every_judge_question_is_tagged_with_a_criterion_and_rests_on_rubric_rows() -> None:
    for q in bank("judge"):
        assert q.rubric_rows, q.id
    tagged = {c for q in bank("judge") for c in q.criteria}
    assert tagged == set(questions.VALID_CRITERIA)  # all four judging criteria are covered


def test_every_rubric_row_is_reachable_from_a_judge_question() -> None:
    reached = {i for q in bank("judge") for i in q.rubric_rows}
    assert reached == ROWS, sorted(ROWS - reached)


def test_teacher_mentor_and_coach_questions_come_with_hindi_and_tamil_drafts() -> None:
    for role in ("teacher", "mentor", "coach"):
        for q in bank(role):
            assert q.text.get("hi") and q.text.get("ta"), (role, q.id)
    for role in ("officer", "judge"):  # answered in English
        assert scopes()[role].answers_in == "en"


def test_the_same_context_always_gives_the_same_five() -> None:
    b = bank("judge")
    for screen in questions.VALID_SCREENS:
        for step in (None, 1, 4, 9):
            first = [q.id for q in questions.top_five(b, screen, step)]
            assert len(first) == 5
            assert first == [q.id for q in questions.top_five(list(b), screen, step)]
            assert len(set(first)) == 5


def test_the_five_follow_the_screen_and_the_step() -> None:
    b = bank("judge")
    on_practice = {q.id for q in questions.top_five(b, "practice")}
    assert "j10" in on_practice  # "How does the Practice Class work, and is it proven?"
    on_aimap = {q.id for q in questions.top_five(b, "aimap")}
    assert on_aimap != on_practice and {"j03", "j18"} <= on_aimap
    step9 = [q.id for q in questions.top_five(b, "any", step=9)]
    assert "j02" in step9 and "j39" in step9  # the assistant step of the test path
    t = bank("teacher")
    assert questions.top_five(t, "check")[0].id == "t06"  # how do I enter the check
    assert (
        questions.top_five(t, "practice")[0].id == "t03"
    )  # screens beat order; ties keep the bank's order


def test_the_pick_ignores_the_clock_history_and_language() -> None:
    import inspect

    assert list(inspect.signature(questions.top_five).parameters) == ["bank", "screen", "step"]


def test_suggested_returns_the_role_language_and_criterion_tags() -> None:
    j = answer.suggested(scopes()["judge"], "practice", None, "ta")
    assert len(j) == 5 and all(
        q["criteria"] for q in j
    )  # judges see the criterion each question maps to
    assert all(
        q["text"].isascii() for q in j
    )  # judges and officers are answered in English whatever the language
    t = answer.suggested(scopes()["teacher"], "home", None, "ta")
    assert len(t) == 5 and not any(q["criteria"] for q in t)  # teachers see no judging jargon
    assert any(not q["text"].isascii() for q in t)  # a teacher's questions come in her language
    hi = answer.suggested(scopes()["coach"], "review", None, "hi")
    assert any(not q["text"].isascii() for q in hi)
