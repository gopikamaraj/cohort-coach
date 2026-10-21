"""Call 10, the demo teacher (judge mode only): approved moves, numbers, no leak, fallback."""

from __future__ import annotations

import pytest

from ai.audit import SqlAuditSink
from ai.calls.c10_demo_teacher import (
    allowed_numbers,
    demo_teacher_turn,
    load_styles,
)
from ai.client import CallContext
from ai.schemas import DemoTeacherTurn
from ai.validators.check_items import check_items
from ai.validators.prefilter import check_prefilter
from engine.simulator import Problem
from services.practice.content import LANGS, load_scenario
from tests.support_ai import FakeClient

KIDS = ["Priya", "Meena", "Ravi", "Anil", "Sita"]
PROBLEM = Problem("sub", 52, 29)


@pytest.fixture(autouse=True)
def _key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")


def run(
    sink: SqlAuditSink,
    replies: list[DemoTeacherTurn],
    *,
    style: str = "experienced",
    turn: int = 2,
    children_said: tuple[str, ...] = ("37, Miss!",),
    language: str = "en",
):
    loaded = load_scenario("SUB-SFL")
    fake = FakeClient(list(replies))
    res = demo_teacher_turn(
        style=style,
        movelist=loaded.movelist,
        language=language,
        children=KIDS,
        transcript=[],
        child_lines=children_said,
        turn=turn,
        problem=PROBLEM,
        context=CallContext(mode="live", sink=sink, client=fake),
    )
    return res, fake


def good(
    move: str = "ask_explain", line: str = "Priya, tell me how you got 37."
) -> DemoTeacherTurn:
    return DemoTeacherTurn(move_id=move, addressed_child="Priya", line=line)


def test_the_two_styles_come_from_content() -> None:
    styles = load_styles()
    assert set(styles) == {"experienced", "struggling"}
    assert not styles["experienced"].may_state_answer and styles["struggling"].may_state_answer
    ids = {m.id for m in load_scenario("SUB-SFL").movelist.moves}
    for s in styles.values():
        assert set(s.moves) <= ids and set(s.script) <= set(s.moves)
        assert s.fallback_move in s.moves


def test_a_good_line_is_used_as_it_stands(sink: SqlAuditSink) -> None:
    res, fake = run(sink, [good()])
    assert res.source == "ai" and res.move_id == "ask_explain" and res.addressed == "Priya"
    assert res.line == "Priya, tell me how you got 37."
    assert len(fake.messages.calls) == 1  # no second call: call 7 is not used on a demo line


def test_a_move_outside_the_styles_approved_list_falls_back_to_the_template(
    sink: SqlAuditSink,
) -> None:
    bad = good("give_the_answer", "The answer is 23.")  # not an experienced move
    res, _ = run(sink, [bad, bad])
    assert res.source == "template" and res.move_id in load_styles()["experienced"].moves
    assert res.run is not None and res.run.fallback_used


def test_an_invented_move_id_is_refused(sink: SqlAuditSink) -> None:
    res, _ = run(sink, [good("shout_loudly", "Quiet!")] * 2)
    assert res.source == "template"


def test_the_experienced_teacher_never_states_the_answer(sink: SqlAuditSink) -> None:
    leak = good("check_back", "The answer is 23, so 23 plus 29 is 52.")
    res, _ = run(sink, [leak, leak])
    assert res.source == "template"
    assert 23 not in allowed_numbers(PROBLEM, may_state_answer=False, child_lines=("37, Miss!",))


def test_the_struggling_teacher_may_state_the_answer_and_only_that(sink: SqlAuditSink) -> None:
    ok = good("give_the_answer", "The answer is 23. Write 23.")
    res, _ = run(sink, [ok], style="struggling")
    assert res.source == "ai" and res.move_id == "give_the_answer"
    other = good("give_the_answer", "The answer is 24.")
    res2, _ = run(sink, [other, other], style="struggling")
    assert res2.source == "template"


def test_a_number_outside_the_scenario_is_refused(sink: SqlAuditSink) -> None:
    res, _ = run(sink, [good("show_bundles", "Show 87 with bundles.")] * 2)
    assert res.source == "template"


def test_a_line_over_25_words_is_refused(sink: SqlAuditSink) -> None:
    long = good("ask_explain", " ".join(["please"] * 26))
    res, _ = run(sink, [long, long])
    assert res.source == "template"


def test_a_check_item_is_refused(sink: SqlAuditSink) -> None:
    res, _ = run(sink, [good("pose_problem", "Who can tell me 45 minus 19?")] * 2, turn=1)
    assert res.source == "template"


def test_the_numbers_children_said_and_their_check_sums_are_allowed() -> None:
    allowed = allowed_numbers(PROBLEM, may_state_answer=False, child_lines=("37, Miss!",))
    assert {52, 29, 37, 66, 10} <= allowed  # 37 + 29 = 66: the adding-back check on her answer


def test_a_child_name_not_in_the_class_is_not_addressed(sink: SqlAuditSink) -> None:
    bad = DemoTeacherTurn(move_id="ask_explain", addressed_child="Zorro", line="Tell me how.")
    res, _ = run(sink, [bad])
    assert res.addressed is None


def test_pose_problem_is_only_allowed_on_the_first_turn(sink: SqlAuditSink) -> None:
    again = good("pose_problem", "Who can tell me 52 minus 29?")
    res, _ = run(sink, [again, again], turn=3)
    assert res.source == "template" and res.move_id != "pose_problem"


@pytest.mark.parametrize("style", ["experienced", "struggling"])
@pytest.mark.parametrize("lang", LANGS)
def test_every_fallback_line_is_safe_and_has_no_number_or_check_item(style: str, lang: str) -> None:
    s = load_styles()[style]
    line = s.fallback_lines[lang]
    assert check_items(line) == [] and check_prefilter(line, lang) == []
    assert not any(ch.isdigit() for ch in line)


def test_the_demo_teacher_refuses_to_run_outside_judge_mode(
    sink: SqlAuditSink, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("JUDGE_MODE", "0")
    with pytest.raises(PermissionError):
        run(sink, [good()])
