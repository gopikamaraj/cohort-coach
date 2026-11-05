"""The two-class scenario, the cohort rule with both settings, and the next-lesson decision."""

from __future__ import annotations

import pytest

from engine.grouping import COHORT_MIN
from services.cohort_run import formation, next_lesson, scenario, settings
from services.content.track import load_track

SC = scenario.load()


def test_the_scenario_copies_the_pilot_patterns_and_is_stable() -> None:
    a = scenario.synthetic_class(SC, "3A")
    b = scenario.synthetic_class(SC, "3B")
    assert (a.children_checked, b.children_checked) == (16, 18)
    # 2-item rule: only the child who subtracts wrongly after borrowing (all four items) shows
    assert a.counts == {"SUB-NODEC": 1}
    assert a.possible == {"SUB-SFL": 4, "ADD-NOCARRY": 3, "PV-HEARD": 3}
    assert b.counts == {"SUB-NODEC": 2}
    assert b.possible == {"SUB-SFL": 5, "ADD-NOCARRY": 4}
    assert scenario.synthetic_class(SC, "3A") == a  # same file, same answers


def test_the_scenario_has_no_name_and_is_labelled_simulated() -> None:
    assert "simulated" in SC["label"].lower()
    for cls in SC["classes"]:
        assert set(cls) <= {
            "code",
            "teacher",
            "strength",
            "no_sheet",
            "absent",
            "dictation",
            "children",
        }
    assert set(SC["teachers"]) == {"T1", "T2"}  # labels, never names


def test_each_class_has_its_own_dictation_numbers() -> None:
    a = scenario.paper_items(SC, "3A")
    b = scenario.paper_items(SC, "3B")
    assert [it["a"] for it in a[:2]] == [305, 496]
    assert [it["a"] for it in b[:2]] == [346, 728]
    assert len(a) == len(b) == 15


PROD = settings.CohortSettings(COHORT_MIN, False, "production")
PILOT = settings.CohortSettings(2, True, "pilot_demo")
PILOT_TWO_ITEM = settings.CohortSettings(2, False, "pilot_demo")


def classes() -> list[scenario.ClassCounts]:
    return [scenario.synthetic_class(SC, "3A"), scenario.synthetic_class(SC, "3B")]


# Updated 4 Nov 2026 to the current rules (DECISIONS.md): the 25% share line was removed on 2 Nov (an error is eligible
# when 1 child shows it and 10 were checked), and there is one cohort per mistake, holding every class that shows it
# (decided 4 Nov). The old tests expected no cohort, or one SUB-SFL cohort chosen through each class's single track.
def test_production_rules_make_the_two_classes_wait_for_fifteen_and_say_why() -> None:
    out = formation.form(classes(), PROD)
    assert out["status"] == "waiting_for_classes"  # was no_cohort under the 25% line
    (w,) = out["waiting"]
    assert (w["error"], w["classes"], w["have"], w["min_classes"]) == ("SUB-NODEC", ["3A", "3B"], 2, 15)
    reasons = {c["code"]: c["errors"]["SUB-SFL"] for c in out["classes"]}
    assert reasons["3A"]["code"] == "under_line" and reasons["3A"]["showing"] == 0  # nobody shows SUB-SFL on two questions
    assert reasons["3A"]["ignored_single"] == 4  # seen on one question only, not counted


def test_single_question_probes_alone_still_wait_for_fifteen_classes() -> None:
    s = settings.CohortSettings(COHORT_MIN, True, "production")
    out = formation.form(classes(), s)
    assert out["status"] == "waiting_for_classes"
    have = {w["error"]: w["have"] for w in out["waiting"]}  # one waiting cohort per mistake
    assert have == {"ADD-NOCARRY": 2, "PV-HEARD": 1, "SUB-NODEC": 2, "SUB-SFL": 2}
    assert all(w["min_classes"] == 15 for w in out["waiting"])


def test_two_classes_without_single_question_probes_form_a_sub_nodec_cohort() -> None:
    out = formation.form(classes(), PILOT_TWO_ITEM)  # was no_cohort under the 25% line
    assert out["status"] == "formed"
    (c,) = out["cohorts"]
    assert c["error"] == "SUB-NODEC" and c["classes"] == ["3A", "3B"] and (c["showing"], c["checked"]) == (3, 34)


def test_pilot_settings_form_one_labelled_cohort_per_mistake() -> None:
    out = formation.form(classes(), PILOT)
    assert out["status"] == "formed"
    assert [c["error"] for c in out["cohorts"]] == ["ADD-NOCARRY", "SUB-NODEC", "SUB-SFL"]  # both classes in each
    assert all(c["classes"] == ["3A", "3B"] for c in out["cohorts"])
    c = next(k for k in out["cohorts"] if k["error"] == "SUB-SFL")
    assert c["labels"] == [settings.PILOT_COHORT_LABEL, settings.SINGLE_ITEM_LABEL]
    assert (c["showing"], c["checked"]) == (9, 34)
    assert c["waitlist"] == "none_at_pilot_scale"
    assert c["mentor"] == {"suggested": False, "reason": "no_other_class", "classes_compared": 0}
    assert [(w["error"], w["classes"]) for w in out["waiting"]] == [("PV-HEARD", ["3A"])]  # only 3A shows it
    by = {k["code"]: k for k in out["classes"]}
    assert by["3A"]["errors"]["SUB-SFL"]["code"] == "in"
    assert by["3A"]["errors"]["ADD-NOCARRY"]["code"] == "in"  # was under_line (3 of 16, under 1 in 4)
    assert by["3B"]["errors"]["ADD-NOCARRY"]["showing"] == 4
    assert by["3A"]["cohorts"] == ["ADD-NOCARRY-g3-hindi", "SUB-NODEC-g3-hindi", "SUB-SFL-g3-hindi"]


def test_the_first_class_alone_waits() -> None:
    out = formation.form(classes()[:1], PILOT)
    assert out["status"] == "waiting_for_classes"
    assert out["waiting"][0]["classes"] == ["3A"] and out["waiting"][0]["have"] == 1


def test_settings_come_from_the_environment_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("COHORT_MIN_CLASSES", raising=False)
    monkeypatch.delenv("COHORT_ALLOW_SINGLE_ITEM_PROBES", raising=False)
    p = settings.production()
    assert (p.min_classes, p.allow_single_item_probes) == (15, False)
    monkeypatch.setenv("COHORT_MIN_CLASSES", "2")
    monkeypatch.setenv("COHORT_ALLOW_SINGLE_ITEM_PROBES", "1")
    assert settings.production().min_classes == 2 and settings.production().allow_single_item_probes
    assert settings.for_scenario(SC) == PILOT


def test_a_better_class_is_suggested_as_mentor() -> None:
    a, b = classes()
    good = scenario.ClassCounts("3C", "T3", "en", 3, "hindi", 20, {}, {})
    out = formation.form([a, b, good], PILOT)
    m = next(k for k in out["cohorts"] if k["error"] == "SUB-SFL")["mentor"]
    assert m["suggested"] is False and m["reason"] == "none_did_better"  # block under 1 in 4 (the mentor bar, unchanged)
    strong = [
        scenario.ClassCounts("3A", "T1", "en", 3, "hindi", 16, {"SUB-SFL": 8}, {}),
        scenario.ClassCounts("3B", "T2", "hi", 3, "hindi", 18, {"SUB-SFL": 9}, {}),
        scenario.ClassCounts("3C", "T3", "en", 3, "hindi", 20, {}, {}),
    ]
    m = formation.form(strong, PILOT)["cohorts"][0]["mentor"]
    assert m == {"suggested": True, "class": "3C", "teacher": "T3", "kind": "candidate"}


TRACK = load_track("sub-sfl.v1")


def test_tried_goes_to_the_next_lesson() -> None:
    d = next_lesson.decide(TRACK, [1], 1, "tried")
    assert (d.day, d.mode, d.reason) == (2, "next", "tried_next")


def test_partly_repeats_the_approach_as_a_smaller_step() -> None:
    d = next_lesson.decide(TRACK, [1], 1, "partly")
    assert (d.day, d.mode, d.practice_level) == (1, "smaller_step", 1)


def test_not_yet_picks_another_approach_and_skips_what_she_had() -> None:
    d = next_lesson.decide(TRACK, [1], 1, "not_yet")
    # lesson 1 used ask_explain and order_probe; lesson 2 repeats ask_explain; lesson 3 is new
    assert (d.day, d.mode, d.reason) == (3, "other_approach", "not_yet_other")
    assert d.skipped == ("ask_explain",)


def test_silence_releases_the_planned_lesson() -> None:
    d = next_lesson.decide(TRACK, [1], 1, None)
    assert (d.day, d.mode, d.reason) == (2, "planned", "silence_planned")


def test_the_end_of_the_track() -> None:
    assert next_lesson.decide(TRACK, [1, 2, 3, 4, 5, 6], 6, "tried").mode == "end"
    with pytest.raises(ValueError):
        next_lesson.decide(TRACK, [1], 1, "maybe")
