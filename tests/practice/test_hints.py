"""Try with hints: three replies per turn from the move list, no AI, no labels sent."""

from __future__ import annotations

import pytest

from ai.audit import SqlAuditSink
from ai.client import CallContext
from ai.validators.check_items import check_items
from services.practice.hints import hints
from services.practice.session import start_session, take_turn
from services.practice.stub_client import StubClient

LANGS = ("en", "hi", "ta")


@pytest.fixture
def ctx(sink: SqlAuditSink) -> CallContext:
    return CallContext(mode="stub", sink=sink, client=StubClient())


def quality_of(session, move: str) -> str:  # type: ignore[no-untyped-def]
    return next(m.quality for m in session.loaded.movelist.moves if m.id == move)


def test_the_first_turn_offers_posing_a_problem() -> None:
    s = start_session("SUB-SFL", "en", seed=5)
    h = hints(s)
    assert [x["move"] for x in h] == ["pose_problem"] and "52" in h[0]["line"]


def test_later_turns_offer_one_strong_one_mistake_and_one_neutral(ctx: CallContext) -> None:
    s = start_session("SUB-SFL", "en", seed=5)
    take_turn(s, text=hints(s)[0]["line"], context=ctx)
    for _ in range(3):
        h = hints(s)
        assert sorted(quality_of(s, x["move"]) for x in h) == [
            "common_mistake",
            "neutral",
            "strong",
        ]
        assert all(x["line"].strip() for x in h)
        take_turn(s, text=h[0]["line"], context=ctx)


def test_no_quality_label_is_sent_and_the_order_is_not_always_strong_first(
    ctx: CallContext,
) -> None:
    firsts = set()
    for seed in range(8):
        s = start_session("SUB-SFL", "en", seed=seed)
        take_turn(s, text=hints(s)[0]["line"], context=ctx)
        h = hints(s)
        assert set(h[0]) == {"move", "line"}
        firsts.add(quality_of(s, h[0]["move"]))
    assert len(firsts) > 1


def test_hints_are_deterministic_for_a_session_and_turn(ctx: CallContext) -> None:
    a = start_session("SUB-SFL", "en", seed=7)
    b = start_session("SUB-SFL", "en", seed=7)
    for s in (a, b):
        take_turn(s, text=hints(s)[0]["line"], context=ctx)
    assert hints(a) == hints(b)


@pytest.mark.parametrize("error", ["SUB-SFL", "SUB-NODEC"])
@pytest.mark.parametrize("lang", LANGS)
def test_no_hint_line_in_any_language_contains_a_check_item(error: str, lang: str) -> None:
    s = start_session(error, lang, seed=3)
    for m in s.loaded.movelist.moves:
        for line in m.sample_lines.get(lang, []):
            assert check_items(line) == [], (error, lang, m.id, line)
