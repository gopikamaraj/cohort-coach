from __future__ import annotations

import pytest

from ai.audit import SqlAuditSink
from ai.calls.c03_feedback import (
    TurnLine,
    feedback_results,
    give_feedback,
    template_feedback,
    transcript_text,
)
from ai.client import CallContext
from ai.guard.badges import Badge
from ai.schemas import Feedback, FeedbackPoint, TryNext, Verdict
from ai.validators.scores import check_no_scores
from services.practice.content import LANGS, load_scenario
from tests.support_ai import FakeClient

PASS = Verdict(passed=True, reason_short="ok", reason_for_user="ok")
RUBRIC = load_scenario("SUB-SFL").rubric
TURNS = [
    TurnLine(1, "Meena, what is 52 minus 29?", "pose_problem", "37, Miss!"),
    TurnLine(2, "Tell me how you got 37.", "ask_explain", "2 minus 9 I can't do."),
    TurnLine(3, "Here is 52: 5 bundles and 2 sticks. Take away 9 sticks.", "show_bundles", ""),
    TurnLine(4, "That is wrong again! Pay attention!", "scold", "Yes, Miss."),
]
NUMS = frozenset({52, 29, 37, 9, 5, 2, 66, 23})


@pytest.fixture(autouse=True)
def _key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")


def good() -> Feedback:
    return Feedback(
        strengths=[
            FeedbackPoint(rubric_point="ask_explain", turn_id=2, quote="Tell me how you got 37",
                          comment="You asked Meena to explain, which showed you her thinking."),
            FeedbackPoint(rubric_point="show_bundles", turn_id=3, quote="5 bundles and 2 sticks",
                          comment="You showed 52 with bundles and sticks."),
        ],
        try_next=TryNext(rubric_point="check_back",
                         suggestion="You could also have her add back: 37 + 29 = 66, not 52."),
    )  # fmt: skip


def run(sink: SqlAuditSink, replies: list[object], lang: str = "en", scolded: bool = False):  # type: ignore[no-untyped-def]
    fake = FakeClient(replies)  # type: ignore[arg-type]
    card, call = give_feedback(
        TURNS, rubric=RUBRIC, language=lang, allowed_numbers=NUMS, scolded=scolded,
        context=CallContext(mode="live", sink=sink, client=fake),
    )  # fmt: skip
    return card, call, fake


def test_a_good_card_passes_every_check_and_is_badged(sink: SqlAuditSink) -> None:
    card, _, fake = run(sink, [good(), PASS])
    assert card.source == "ai" and card.badge is Badge.CHECKED
    assert [s.point for s in card.strengths] == ["ask_explain", "show_bundles"]
    assert card.strengths[0].quote == "Tell me how you got 37"  # verbatim in turn 2
    assert card.try_next.point == "check_back" and card.note is None
    assert len(fake.messages.calls) == 2  # the feedback, then the checker


def test_her_words_are_wrapped_as_untrusted_and_labels_come_from_code(sink: SqlAuditSink) -> None:
    _, _, fake = run(sink, [good(), PASS])
    text = fake.messages.calls[0]["messages"][0]["content"][-1]["text"]
    assert "<transcript>" in text and "T2 teacher: Tell me how you got 37." in text
    assert '"move_id": "ask_explain"' in text and '"scolded": false' in text


def test_an_invented_quote_is_rejected_then_the_template_card_is_used(sink: SqlAuditSink) -> None:
    bad = good().model_copy(deep=True)
    bad.strengths[0].quote = "Please explain your reasoning carefully"
    card, call, fake = run(sink, [bad])
    assert card.source == "template" and card.badge is Badge.NONE
    assert call is not None and call.fallback_used == "template:validators"
    assert len(fake.messages.calls) == 2  # one try, one retry
    # The template card is made of her own words and the rubric: every quote is verbatim.
    for s in card.strengths:
        assert s.quote in next(t.teacher_text for t in TURNS if t.turn == s.turn_id)


def test_a_quote_from_a_child_line_is_not_accepted(sink: SqlAuditSink) -> None:
    bad = good().model_copy(deep=True)
    bad.strengths[0].quote = "2 minus 9 I can't do"  # the child's words, not hers
    res = feedback_results(bad, TURNS, RUBRIC, "en", NUMS)
    assert "quote_not_in_her_turn" in [c for r in res for c in r.codes]


def test_a_quote_cited_against_the_wrong_turn_is_not_accepted() -> None:
    bad = good().model_copy(deep=True)
    bad.strengths[0].turn_id = 3
    codes = [c for r in feedback_results(bad, TURNS, RUBRIC, "en", NUMS) for c in r.codes]
    assert "quote_not_in_her_turn" in codes and "strength_without_evidence" in codes


def test_points_must_come_from_the_rubric_and_be_backed_by_a_move_she_made() -> None:
    unknown = good().model_copy(deep=True)
    unknown.strengths[0].rubric_point = "be_kind"
    assert "rubric_point_unknown" in [
        c for r in feedback_results(unknown, TURNS, RUBRIC, "en", NUMS) for c in r.codes
    ]
    unused = good().model_copy(deep=True)
    unused.strengths[1] = FeedbackPoint(
        rubric_point="exchange_ten", turn_id=3, quote="5 bundles", comment="x"
    )
    assert "strength_without_evidence" in [
        c for r in feedback_results(unused, TURNS, RUBRIC, "en", NUMS) for c in r.codes
    ]
    twice = good().model_copy(deep=True)
    twice.strengths[1] = twice.strengths[0].model_copy()
    assert "rubric_point_repeated" in [
        c for r in feedback_results(twice, TURNS, RUBRIC, "en", NUMS) for c in r.codes
    ]
    badtry = good().model_copy(deep=True)
    badtry.try_next.rubric_point = "invented"
    assert "rubric_point_unknown" in [
        c for r in feedback_results(badtry, TURNS, RUBRIC, "en", NUMS) for c in r.codes
    ]


SCORE_TEXTS = [
    "You got 8/10", "That is 80%", "A good score", "Grade A work", "You earned 4 stars",
    "आपको अच्छे अंक मिले", "நல்ல மதிப்பெண்",
]  # fmt: skip


@pytest.mark.parametrize("text", SCORE_TEXTS)
def test_scores_are_rejected(text: str) -> None:
    assert [v.code for v in check_no_scores(text)] == ["score_found"]
    assert check_no_scores("You asked her to explain: 37 + 29 = 66.") == []


def test_a_score_in_a_comment_fails_the_card(sink: SqlAuditSink) -> None:
    bad = good().model_copy(deep=True)
    bad.strengths[0].comment = "Great, 9/10 for explaining."
    card, _, _ = run(sink, [bad])
    assert card.source == "template"


def test_a_number_that_is_not_in_the_transcript_is_rejected() -> None:
    bad = good().model_copy(deep=True)
    bad.try_next.suggestion = "You could add back: 37 + 29 = 67."
    res = feedback_results(bad, TURNS, RUBRIC, "en", NUMS)
    assert any(c in ("number_not_allowed", "arithmetic_wrong") for r in res for c in r.codes)


def test_the_checker_can_still_hold_back_an_ai_card(sink: SqlAuditSink) -> None:
    fail = Verdict(passed=False, failed_items=["tone"], reason_short="x", reason_for_user="x")
    card, _, _ = run(sink, [good(), fail])
    assert card.source == "template" and card.badge is Badge.NONE


def test_scolding_adds_a_gentle_note_made_by_the_app_not_the_model(sink: SqlAuditSink) -> None:
    card, _, fake = run(sink, [good(), PASS], scolded=True)
    assert card.note and "calm" in card.note.lower()
    assert '"scolded": true' in fake.messages.calls[0]["messages"][0]["content"][-1]["text"]
    card, _, _ = run(sink, [good(), PASS], lang="hi", scolded=True)
    assert card.note and "शांत" in card.note


@pytest.mark.parametrize("lang", LANGS)
def test_the_template_card_passes_the_same_validators_in_every_language(lang: str) -> None:
    fb = template_feedback(TURNS, RUBRIC, lang)
    assert len(fb.strengths) == 2 and fb.try_next.rubric_point == "exchange_ten"
    results = feedback_results(fb, TURNS, RUBRIC, lang, NUMS)
    assert [(r.name, r.codes) for r in results if not r.ok] == []


def test_a_template_card_with_nothing_to_praise_still_gives_an_idea() -> None:
    chat = [TurnLine(1, "hello everyone", "other", "")]
    fb = template_feedback(chat, RUBRIC, "en")
    assert fb.strengths == [] and fb.try_next.rubric_point == "let_answer"


def test_transcript_text_numbers_her_turns() -> None:
    text = transcript_text(TURNS[:2])
    assert text.splitlines()[0] == "T1 teacher: Meena, what is 52 minus 29?"
    assert "T1 child: 37, Miss!" in text
