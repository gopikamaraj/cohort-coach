"""The class answers together; call 7 and call 1 can be switched off per deployment (.env)."""

from __future__ import annotations

import pytest

from ai.audit import SqlAuditSink
from ai.client import CallContext
from services.practice.session import PracticeSession, TurnResult, start_session, take_turn
from services.practice.stub_client import StubClient


@pytest.fixture
def ctx(sink: SqlAuditSink) -> CallContext:
    return CallContext(mode="stub", sink=sink, client=StubClient())


def calls(sink: SqlAuditSink) -> list[int]:
    return [r.call_id for r in sink.recent(500)]


def name_of(s: PracticeSession, i: int = 1) -> str:
    return s.state.children[i].name


def numbers_in(text: str) -> set[int]:
    return {int(x) for x in "".join(c if c.isdigit() else " " for c in text).split()}


def test_one_to_three_children_speak_and_the_others_use_engine_numbers(ctx: CallContext) -> None:
    sizes: set[int] = set()
    for seed in range(1, 40):
        s = start_session("SUB-SFL", "en", seed=seed)
        r = take_turn(s, text=f"{name_of(s)}, what is 52 minus 29?", context=ctx)
        sizes.add(1 + len(r.others))
        names = [r.speaker, *[o["speaker"] for o in r.others]]
        assert len(set(names)) == len(names) and r.speaker == name_of(s)
        for o in r.others:
            assert o["source"] == "engine" and o["child_text"]
            assert numbers_in(o["child_text"]) <= {52, 29, o["answer"], o["written"]} - {None}
            assert numbers_in(o["child_text_en"]) == numbers_in(o["child_text"])
    assert sizes == {1, 2, 3}


def test_the_other_children_are_in_the_history_and_the_numbers_the_feedback_may_quote(
    ctx: CallContext,
) -> None:
    for seed in range(1, 30):
        s = start_session("SUB-SFL", "en", seed=seed)
        r = take_turn(s, text=f"{name_of(s)}, what is 52 minus 29?", context=ctx)
        if r.others:
            assert s.records[-1].others == [(o["speaker"], o["child_text"]) for o in r.others]
            for o in r.others:
                assert (o["answer"] is None) or (o["answer"] in s.plan_numbers)
            return
    raise AssertionError("no seed gave a chorus")


def test_the_whole_room_hears_a_move_aimed_at_one_child(ctx: CallContext) -> None:
    s = start_session("SUB-SFL", "en", seed=3)
    before = {c.name: (c.strength, c.engagement) for c in s.state.children}
    take_turn(s, text=f"{name_of(s)}, tell me how you got 37.", context=ctx)
    after = {c.name: (c.strength, c.engagement) for c in s.state.children}
    named = name_of(s)
    for name, (strength, engagement) in after.items():
        assert engagement > before[name][1]  # everyone's engagement moved
        if name != named and before[name][0] > 0:
            assert strength < before[name][0]  # the overhearing children with the error eased too
    assert (before[named][0] - after[named][0]) > (
        max(before[n][0] - after[n][0] for n in after if n != named)
    )  # the named child most of all


def test_the_checker_switch_leaves_call_7_out_but_not_the_code_checks(
    ctx: CallContext, sink: SqlAuditSink, monkeypatch: pytest.MonkeyPatch
) -> None:
    s = start_session("SUB-SFL", "en", seed=5)
    take_turn(s, text=f"{name_of(s)}, what is 52 minus 29?", context=ctx)
    assert 7 in calls(sink)  # on by default
    monkeypatch.setenv("PRACTICE_SKIP_CHECKER", "1")
    before = calls(sink).count(7)
    r = take_turn(s, text=f"{name_of(s)}, tell me how you got that.", context=ctx)
    assert calls(sink).count(7) == before  # no new checker call
    assert r.source == "ai" and r.badge == "none"
    assert r.layers["guardrails"]["checker_skipped"] is True
    assert r.layers["guardrails"]["checker"] is None
    assert all(v["ok"] for v in r.layers["guardrails"]["validators"])  # code checks still ran
    assert numbers_in(r.child_text) <= set(r.numbers)


def test_a_line_that_fails_the_code_checks_is_still_replaced_when_call_7_is_off(
    ctx: CallContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PRACTICE_SKIP_CHECKER", "1")

    from ai.schemas import ChildLine
    from services.practice import stub_client

    monkeypatch.setattr(
        stub_client._Messages,
        "_child",
        lambda self, facts: ChildLine(text="It is 999.", english="It is 999."),
    )
    bad = ctx
    s = start_session("SUB-SFL", "en", seed=5)
    r = take_turn(s, text=f"{name_of(s)}, what is 52 minus 29?", context=bad)
    assert r.source == "template" and "999" not in r.child_text


def test_ai_intents_switch_sends_only_the_listed_kinds_to_the_ai(
    ctx: CallContext, sink: SqlAuditSink, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PRACTICE_AI_INTENTS", "explain,work_aloud")
    s = start_session("SUB-SFL", "en", seed=5)
    before = calls(sink).count(1)
    r = take_turn(s, text=f"{name_of(s)}, what is 52 minus 29?", context=ctx)
    assert r.intent == "answer" and r.source == "engine" and r.badge == "none"
    assert calls(sink).count(1) == before  # no child-voice call for an answer
    assert r.child_text == render_line_for(s, r)
    r2 = take_turn(s, text=f"{name_of(s)}, tell me how you got that.", context=ctx)
    assert r2.intent == "explain" and r2.source == "ai"  # an explanation needs the AI
    assert calls(sink).count(1) == before + 1


def render_line_for(s: PracticeSession, r: TurnResult) -> str:
    return render_line_text(s, r.answer)


def render_line_text(s: PracticeSession, answer: int | None) -> str:
    from services.practice.content import load_templates

    return load_templates(s.language).intents["answer"].format(answer=answer)


def test_defaults_are_the_safe_ones(monkeypatch: pytest.MonkeyPatch) -> None:
    from ai.config import practice_ai_intents, practice_skip_checker

    monkeypatch.delenv("PRACTICE_SKIP_CHECKER", raising=False)
    monkeypatch.delenv("PRACTICE_AI_INTENTS", raising=False)
    assert practice_skip_checker() is False and practice_ai_intents() is None
    monkeypatch.setenv("PRACTICE_AI_INTENTS", "explain, work_aloud")
    assert practice_ai_intents() == frozenset({"explain", "work_aloud"})
    monkeypatch.setenv("PRACTICE_AI_INTENTS", "all")
    assert practice_ai_intents() is None
