"""Watch mode: an AI teacher runs the Practice Class in two styles; recorded runs; the live cap."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai.audit import SqlAuditSink
from ai.calls.c10_demo_teacher import LABEL
from ai.client import CallContext
from services.practice.content import load_scenario
from services.practice.stub_client import StubClient
from services.practice.watch import (
    LiveMeter,
    WatchFallback,
    load_recorded,
    rubric_coverage,
    run_watch,
    save_recorded,
    tag,
)


@pytest.fixture
def ctx(sink: SqlAuditSink) -> CallContext:
    return CallContext(mode="stub", sink=sink, client=StubClient())


def test_an_experienced_run_ends_in_a_feedback_card_and_labels_every_teacher_line(
    ctx: CallContext,
) -> None:
    run = run_watch(style="experienced", language="en", context=ctx)
    assert 3 <= len(run["turns"]) <= 9
    assert all(t["teacher"]["label"] == LABEL for t in run["turns"])
    assert run["turns"][0]["teacher"]["move"]["id"] == "pose_problem"
    assert len(run["feedback"]["strengths"]) >= 1 and run["feedback"]["badge"]
    assert run["provenance"]["style"] == "experienced" and run["provenance"]["seed"] == 5
    assert set(run["provenance"]["models"]) == {"1", "3", "7", "10"}


def test_every_turn_has_a_subtitle_a_move_tag_a_meter_and_the_machinery(ctx: CallContext) -> None:
    run = run_watch(style="experienced", language="en", context=ctx)
    for t in run["turns"]:
        assert t["child"]["text_en"] or not t["child"]["text"]
        assert t["teacher"]["move"]["label"] and len(t["children"]) == 5
        m = t["machinery"]
        assert m["code"]["move"]["source"] == "demo teacher"  # the labeller did not run
        assert [c["call"] for c in m["ai_calls"]] == [10, 1, 7]
        assert all(set(v) == {"name", "ok"} for v in m["validators"])


def test_the_two_styles_differ_in_the_moves_they_use_and_the_experienced_covers_more(
    ctx: CallContext,
) -> None:
    good = run_watch(style="experienced", language="en", context=ctx)
    weak = run_watch(style="struggling", language="en", context=ctx)
    good_moves = {t["teacher"]["move"]["id"] for t in good["turns"]}
    weak_moves = {t["teacher"]["move"]["id"] for t in weak["turns"]}
    assert "ask_explain" in good_moves and "ask_explain" not in weak_moves
    assert {"repeat_rule_louder", "give_the_answer"} & weak_moves
    assert good["summary"]["rubric_points_touched"] > weak["summary"]["rubric_points_touched"]


def test_the_experienced_teacher_never_says_the_answer_but_the_struggling_one_may(
    ctx: CallContext,
) -> None:
    good = run_watch(style="experienced", language="en", context=ctx)
    said = " ".join(t["teacher"]["line"] for t in good["turns"])
    assert "23" not in said.replace("523", "")  # 52 - 29 = 23
    weak = run_watch(style="struggling", language="en", context=ctx)
    assert any("23" in t["teacher"]["line"] for t in weak["turns"])


def test_a_slow_turn_abandons_the_live_run(ctx: CallContext) -> None:
    ticks = iter(range(0, 1000, 20))  # every call to the clock is 20 s later
    with pytest.raises(WatchFallback, match="took"):
        run_watch(style="experienced", language="en", context=ctx, clock=lambda: next(ticks))


def test_a_failed_call_abandons_the_live_run(sink: SqlAuditSink) -> None:
    class Broken:
        class messages:  # noqa: N801
            @staticmethod
            def parse(**_: object) -> object:
                raise RuntimeError("down")

    with pytest.raises(WatchFallback):
        run_watch(
            style="experienced", language="en",
            context=CallContext(mode="stub", sink=sink, client=Broken()),
        )  # fmt: skip


def test_recorded_runs_round_trip_with_provenance_and_a_label(
    ctx: CallContext, tmp_path: Path
) -> None:
    run = run_watch(style="struggling", language="en", context=ctx)
    path = save_recorded(run, tmp_path)
    back = load_recorded("SUB-SFL", "struggling", "en", tmp_path)
    assert path.exists() and back is not None
    assert back["provenance"]["recorded_at"] and back["provenance"]["prompt_versions"]
    shown = tag(back, kind="recorded run", reason="the live call was slow")
    assert shown["kind"] == "recorded run" and shown["reason"] == "the live call was slow"
    assert load_recorded("SUB-SFL", "struggling", "ta", tmp_path) is None


def test_the_live_cap_blocks_the_next_run_and_the_meter_adds_up() -> None:
    from collections import deque

    m = LiveMeter(cap_per_hour=2, runs=deque())
    assert m.allowed(now=1000)
    m.record(0.02, now=1000)
    m.record(0.03, now=1100)
    assert not m.allowed(now=1200)
    assert m.snapshot(now=1200) == {
        "live_runs_this_hour": 2, "cap_per_hour": 2, "cost_usd_this_hour": 0.05,
    }  # fmt: skip
    assert m.allowed(now=1000 + 3601)  # the first run is more than an hour old


def test_rubric_coverage_counts_points_not_a_score_for_a_teacher() -> None:
    loaded = load_scenario("SUB-SFL")
    assert rubric_coverage([], loaded) == 0
    assert rubric_coverage(["ask_explain", "show_bundles"], loaded) >= 2
