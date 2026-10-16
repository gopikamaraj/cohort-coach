from collections import Counter
from statistics import mean
from typing import Any

import pytest
import yaml

from data.synthetic.block import (
    NAMES_PATH,
    class_records,
    generate_block,
    load_config,
)
from engine.diagnosis import profile_from_counts
from engine.model import ErrorCode

SMALL = {
    "n_schools": 4,
    "schools_per_medium": {"hindi": 2, "tamil": 1, "english": 1},
}

# Every key the output may contain. Anything per-child (answers, roll numbers, names) is absent.
ALLOWED_KEYS = {
    "simulated",
    "label",
    "seed",
    "config_hash",
    "data_hash",
    "block_id",
    "grade",
    "forms",
    "t1",
    "t2",
    "schools",
    "school_id",
    "name",
    "school_type",
    "medium",
    "classes",
    "class_id",
    "teacher_id",
    "teacher_name",
    "section",
    "terms",
    "T1",
    "T2",
    "form_label",
    "children_checked",
    "counts",
    "anchor_wrong_count",
    "untracked",
    "assignments",
    "track",
    "version",
    "arm",
    "stratum",
    "reason",
    "children_showing",
    "cohorts",
    "cohort_id",
    "error",
    "size",
    "cross_block",
    "undersized",
    "class_ids",
    "mentor_slot",
    "unplaced",
    "why",
}
FORBIDDEN_FRAGMENTS = ("child_", "roll", "answer", "photo", "student", "pupil")


@pytest.fixture(scope="module")
def block() -> dict[str, Any]:
    return generate_block()


def walk_keys(node: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(node, dict):
        for k, v in node.items():
            keys.add(k)
            keys |= walk_keys(v)
    elif isinstance(node, list):
        for v in node:
            keys |= walk_keys(v)
    return keys


# --- determinism -------------------------------------------------------------------------


def test_same_seed_gives_the_same_data_hash() -> None:
    one, two = generate_block(SMALL), generate_block(SMALL)
    assert one["data_hash"] == two["data_hash"] and one == two


def test_a_different_seed_gives_different_data() -> None:
    assert generate_block({**SMALL, "seed": 7})["data_hash"] != generate_block(SMALL)["data_hash"]


def test_config_values_are_data_not_code() -> None:
    cfg = load_config()
    assert cfg["seed"] == 2026 and cfg["n_schools"] == 40
    assert sum(cfg["schools_per_medium"].values()) == cfg["n_schools"]


# --- shape of the full block -------------------------------------------------------------


def test_full_block_has_40_schools_and_120_classes(block: dict[str, Any]) -> None:
    assert len(block["schools"]) == 40 and len(block["classes"]) == 120
    per_school = Counter(c["school_id"] for c in block["classes"])
    assert set(per_school.values()) == {3}
    assert block["grade"] == 3


def test_medium_mix_matches_the_config_and_classes_follow_their_school(
    block: dict[str, Any],
) -> None:
    schools = {s["school_id"]: s for s in block["schools"]}
    assert Counter(s["medium"] for s in block["schools"]) == load_config()["schools_per_medium"]
    for c in block["classes"]:
        assert c["medium"] == schools[c["school_id"]]["medium"]


def test_both_terms_hold_counts_for_every_class_and_counts_are_sane(block: dict[str, Any]) -> None:
    ids = {c["class_id"] for c in block["classes"]}
    for term in ("T1", "T2"):
        data = block["terms"][term]["classes"]
        assert set(data) == ids
        for rec in data.values():
            assert 10 <= rec["children_checked"] <= 40
            assert all(0 <= n <= rec["children_checked"] for n in rec["counts"].values())
            assert set(rec["counts"]) == {e.value for e in ErrorCode}
    sizes = [r["children_checked"] for r in block["terms"]["T1"]["classes"].values()]
    assert 26 <= mean(sizes) <= 34


def test_everything_is_labelled_simulated(block: dict[str, Any]) -> None:
    assert block["simulated"] is True
    assert all(s["simulated"] is True for s in block["schools"])
    assert all(c["simulated"] is True for c in block["classes"])
    assert "simulated" in block["label"].lower()


def test_no_per_child_data_in_the_output(block: dict[str, Any]) -> None:
    keys = (
        walk_keys(block)
        - set(block["terms"]["T1"]["classes"])
        - set(block["terms"]["T2"]["classes"])
    )
    keys -= {e.value for e in ErrorCode} | {"ADD-WHOLE-ONES"}
    assert keys <= ALLOWED_KEYS, keys - ALLOWED_KEYS
    assert not [k for k in keys if any(f in k.lower() for f in FORBIDDEN_FRAGMENTS)]


def test_teacher_names_are_fictional_unique_and_balanced(block: dict[str, Any]) -> None:
    names = yaml.safe_load(NAMES_PATH.read_text(encoding="utf-8"))
    teachers = [c["teacher_name"] for c in block["classes"]]
    assert len(set(teachers)) == 120
    first = [t.split()[0] for t in teachers]
    assert all(f in names["female"] or f in names["male"] for f in first)
    female = sum(f in names["female"] for f in first)
    assert abs(female - (120 - female)) <= 1
    assert all(len(t.split()) == 2 and t.split()[1].endswith(".") for t in teachers)


# --- assignments agree with the engine ---------------------------------------------------


def test_assignments_are_exactly_what_the_engine_derives_from_t1(block: dict[str, Any]) -> None:
    records = class_records(block, "T1")
    assigned = {a["class_id"]: a for a in block["assignments"]}
    for r in records:
        profile = profile_from_counts(r.children_checked, r.counts)
        if profile.track is None:
            assert r.class_id not in assigned
        else:
            assert assigned[r.class_id]["track"] == profile.track.value
            assert assigned[r.class_id]["version"] == "v1"
            assert assigned[r.class_id]["arm"] in {"this_term", "next_term"}
    assert len(assigned) > 60  # most classes qualify for a track


def test_cohorts_hold_only_this_term_classes_with_at_most_two_per_school(
    block: dict[str, Any],
) -> None:
    arm = {a["class_id"]: a["arm"] for a in block["assignments"]}
    school = {c["class_id"]: c["school_id"] for c in block["classes"]}
    assert block["cohorts"]
    for cohort in block["cohorts"]:
        assert all(arm[cid] == "this_term" for cid in cohort["class_ids"])
        assert max(Counter(school[cid] for cid in cohort["class_ids"]).values()) <= 2
        assert cohort["mentor_slot"] is True


def test_natural_drift_is_a_few_points_where_nothing_was_trained(block: dict[str, Any]) -> None:
    t1, t2 = block["terms"]["T1"]["classes"], block["terms"]["T2"]["classes"]
    deltas = []
    for a in block["assignments"]:
        if a["arm"] != "next_term":
            continue
        e, cid = a["track"], a["class_id"]
        deltas.append(
            100
            * (
                t2[cid]["counts"][e] / t2[cid]["children_checked"]
                - t1[cid]["counts"][e] / t1[cid]["children_checked"]
            )
        )
    assert -10 <= mean(deltas) <= -2  # "about 5 points" with sampling noise
