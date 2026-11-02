"""The demo class and its cohorts: deterministic, planted as the scenario says, labelled,
no names."""

from __future__ import annotations

import json

from engine.model import ErrorCode
from services.demo import cohorts, scenario

S = scenario.load_scenario()


def counts_of(demo: scenario.DemoClass) -> dict[str, int]:
    return {k.value: v for k, v in scenario.truth_profile(demo).counts.items()}


def test_the_same_seed_gives_the_same_class_and_a_new_seed_a_different_one() -> None:
    a, b = scenario.build_class(S), scenario.build_class(S)
    assert a == b
    assert scenario.build_class(S, seed=7).children != a.children
    assert scenario.reads_file(a, "PRE · 3A · T1", "h") == scenario.reads_file(
        b, "PRE · 3A · T1", "h"
    )


def test_two_errors_sit_above_the_line_and_one_below_and_the_track_is_sub_sfl() -> None:
    p = scenario.truth_profile(scenario.build_class(S))
    assert p.children_checked == 20
    assert set(p.eligible) == {ErrorCode.SUB_SFL, ErrorCode.ADD_NOCARRY}
    assert 0 < p.counts[ErrorCode.PV_HEARD] < 5  # below 25% of 20
    assert p.track is ErrorCode.SUB_SFL


def test_three_cohorts_form_and_her_class_is_in_one_and_eligible_for_two() -> None:
    demo = scenario.build_class(S)
    plan = cohorts.plan(S, counts_of(demo), 20)
    assert [c["error"] for c in plan["cohorts"]] == ["ADD-NOCARRY", "PV-HEARD", "SUB-SFL"]
    mine = {c["error"]: c for c in plan["cohorts"]}
    assert mine["SUB-SFL"]["includes_you"] and plan["you"]["arm"] == "this_term"
    assert mine["ADD-NOCARRY"]["you_eligible"] and mine["ADD-NOCARRY"]["you_next_term"]
    assert not mine["PV-HEARD"]["you_eligible"]
    assert sum(c["includes_you"] for c in plan["cohorts"]) == 1  # one track a term (CLAUDE.md)
    assert sum(c["you_eligible"] for c in plan["cohorts"]) == 2
    assert plan["simulated"] and plan["other_classes"] == 24 and plan["schools"] == 8
    assert cohorts.plan(S, counts_of(demo), 20) == plan  # deterministic


def test_the_answer_file_marks_the_hard_cases_and_holds_no_truth_or_hidden_errors() -> None:
    demo = scenario.build_class(S)
    reads = scenario.reads_file(demo, "PRE · 3A · T1", "hash")
    assert reads["demo"] is True and "synthetic" in reads["label"]
    assert set(reads["sheets"]) == {f"3A-roll{r:02d}.png" for r in range(1, 21)}
    hard = {v["hard"]: v for v in reads["sheets"].values() if v["hard"]}
    assert set(hard) == {"smudge", "crossed", "blank"}
    assert min(c["confidence"] for c in hard["smudge"]["cells"]) < 0.6
    assert any(c["status"] == "check" for c in hard["crossed"]["cells"])
    assert any(c["status"] == "blank" for c in hard["blank"]["cells"])
    text = json.dumps(reads)
    assert "errors" not in text and "SUB-SFL" not in text and "name" not in text


def test_the_officer_view_hides_any_cell_under_five_classes() -> None:
    demo = scenario.build_class(S)
    plan = cohorts.plan(S, counts_of(demo), 20)
    dash = cohorts.dashboard(plan)
    assert dash["simulated"] and dash["min_cell"] == 5
    for row in dash["cohorts"] + dash["by_error"]:
        assert row["classes"] is None or row["classes"] >= 5
    pv = next(r for r in dash["cohorts"] if r["error"] == "PV-HEARD")
    assert pv["classes"] is None  # a cohort of 2 classes is hidden
    after = cohorts.before_after(
        S, counts_of(demo), 20, scenario.truth_profile(scenario.post_class(S, demo))
    )
    assert next(r for r in after if r["error"] == "PV-HEARD")["before"] is None
    sfl = next(r for r in after if r["error"] == "SUB-SFL")
    assert sfl["after"] < sfl["before"]


def test_the_post_test_is_the_same_children_on_the_twin_paper() -> None:
    demo = scenario.build_class(S)
    post = scenario.post_class(S, demo)
    assert post.form_key == "B" and len(post.children) == 20
    assert [c.roll for c in post.children] == [c.roll for c in demo.children]
    assert (
        scenario.truth_profile(post).counts[ErrorCode.SUB_SFL]
        < scenario.truth_profile(demo).counts[ErrorCode.SUB_SFL]
    )
