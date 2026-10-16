from collections import Counter

from hypothesis import given, settings
from hypothesis import strategies as st

from engine.grouping import (
    Arm,
    ClassRecord,
    assign_tracks,
    form_cohorts,
    matched_comparison,
    split_waitlist,
)
from engine.model import ErrorCode

H, R, N, SFL, NODEC = (
    ErrorCode.PV_HEARD,
    ErrorCode.PV_REVERSE,
    ErrorCode.ADD_NOCARRY,
    ErrorCode.SUB_SFL,
    ErrorCode.SUB_NODEC,
)


def rec(
    cid: str,
    counts: dict[ErrorCode, int],
    checked: int = 30,
    school: str | None = None,
    medium: str = "hindi",
    block: str = "B1",
    school_type: str = "government",
) -> ClassRecord:
    return ClassRecord(
        class_id=cid,
        school_id=school or f"S-{cid}",
        block_id=block,
        school_type=school_type,
        grade=3,
        medium=medium,
        children_checked=checked,
        counts=counts,
    )


# --- eligibility and one track per class -------------------------------------------------


def test_eligibility_boundaries() -> None:
    records = [
        rec("a", {SFL: 3}, checked=12),  # 0.25 exactly: eligible
        rec("b", {SFL: 3}, checked=13),  # 0.2308: not
        rec("c", {SFL: 4}, checked=9),  # too few checked
        rec("d", {SFL: 3}, checked=10),  # 0.30 with 10 checked: eligible
    ]
    assigned = {a.class_id for a in assign_tracks(records)}
    assert assigned == {"a", "d"}


def test_one_track_per_class_pv_heard_first_else_highest_p() -> None:
    records = [
        rec("heard", {H: 8, SFL: 15}),
        rec("highest", {N: 9, SFL: 12, NODEC: 10}),
        rec("reverse_only", {R: 20}),
        rec("nothing", {}),
    ]
    by_id = {a.class_id: a for a in assign_tracks(records)}
    assert set(by_id) == {"heard", "highest"}
    assert by_id["heard"].error is H and by_id["heard"].reason == "pv_heard_first"
    assert by_id["highest"].error is SFL and by_id["highest"].reason == "highest_p"


def test_assignment_carries_the_facts_for_its_explanation_line() -> None:
    (a,) = assign_tracks([rec("x", {SFL: 11}, checked=28)])
    assert a.facts() == {
        "class_id": "x",
        "error": "SUB-SFL",
        "children_checked": 28,
        "children_showing": 11,
        "reason": "highest_p",
    }
    assert a.baseline_p == 11 / 28


# --- stratified waitlist split -----------------------------------------------------------


def eligible_pool(n: int, error: ErrorCode = SFL, medium: str = "hindi") -> list[ClassRecord]:
    """n classes with different baseline p, every one eligible for `error`."""
    return [rec(f"{medium[0]}{i:03d}", {error: 8 + i % 12}, medium=medium) for i in range(n)]


def test_split_is_deterministic_by_seed_and_changes_with_it() -> None:
    tracks = assign_tracks(eligible_pool(30))
    one = split_waitlist(tracks, seed=1)
    assert one == split_waitlist(tracks, seed=1)
    assert [e.arm for e in one] != [e.arm for e in split_waitlist(tracks, seed=2)]


@settings(max_examples=100)
@given(n=st.integers(1, 80), seed=st.integers(0, 10**6))
def test_each_stratum_is_balanced_within_one(n: int, seed: int) -> None:
    entries = split_waitlist(assign_tracks(eligible_pool(n)), seed=seed)
    assert len(entries) == n
    by_stratum: dict[int, Counter[Arm]] = {}
    for e in entries:
        by_stratum.setdefault(e.stratum, Counter())[e.arm] += 1
    assert len(by_stratum) == min(3, n)
    for tally in by_stratum.values():
        assert abs(tally[Arm.THIS_TERM] - tally[Arm.NEXT_TERM]) <= 1


def test_strata_are_terciles_of_baseline_p() -> None:
    entries = split_waitlist(assign_tracks(eligible_pool(30)), seed=3)
    by_stratum: dict[int, list[float]] = {}
    for e in entries:
        by_stratum.setdefault(e.stratum, []).append(e.assignment.baseline_p)
    assert max(by_stratum[0]) <= min(by_stratum[1]) and max(by_stratum[1]) <= min(by_stratum[2])


def test_split_groups_by_track_and_medium_separately() -> None:
    pool = eligible_pool(12, SFL, "hindi") + eligible_pool(12, SFL, "tamil") + eligible_pool(12, N)
    entries = split_waitlist(assign_tracks(pool), seed=5)
    groups = Counter((e.assignment.error, e.assignment.medium) for e in entries)
    assert groups == {(SFL, "hindi"): 12, (SFL, "tamil"): 12, (N, "hindi"): 12}
    for key in groups:
        arms = Counter(e.arm for e in entries if (e.assignment.error, e.assignment.medium) == key)
        assert abs(arms[Arm.THIS_TERM] - arms[Arm.NEXT_TERM]) <= 3


# --- cohorts -----------------------------------------------------------------------------


def this_term(records: list[ClassRecord], seed: int = 1):  # type: ignore[no-untyped-def]
    entries = split_waitlist(assign_tracks(records), seed=seed)
    return [e for e in entries if e.arm is Arm.THIS_TERM]


def plain_pool(n: int, block: str = "B1", per_school: int = 1) -> list[ClassRecord]:
    return [
        rec(f"c{block}{i:03d}", {SFL: 12}, school=f"{block}-S{i // per_school}", block=block)
        for i in range(n)
    ]


def entries_for(records: list[ClassRecord]):  # type: ignore[no-untyped-def]
    return split_waitlist(assign_tracks(records), seed=1)


def test_cohorts_have_15_to_20_teachers_and_one_mentor_slot() -> None:
    plan = form_cohorts(entries_for(plain_pool(36)), arm=Arm.THIS_TERM, seed=1)
    assert plan.cohorts and all(c.mentor_slot for c in plan.cohorts)
    for c in plan.cohorts:
        assert 15 <= len(c.class_ids) <= 20 and not c.undersized
    placed = sum(len(c.class_ids) for c in plan.cohorts)
    assert placed + len(plan.unplaced) == sum(
        e.arm is Arm.THIS_TERM for e in entries_for(plain_pool(36))
    )


def test_at_most_two_classes_per_school_per_cohort() -> None:
    plan = form_cohorts(entries_for(plain_pool(90, per_school=3)), arm=Arm.THIS_TERM, seed=2)
    school_of = {r.class_id: r.school_id for r in plain_pool(90, per_school=3)}
    for c in plan.cohorts:
        counts = Counter(school_of[cid] for cid in c.class_ids)
        assert max(counts.values()) <= 2


def test_a_third_class_from_one_school_is_left_unplaced_when_one_cohort_only() -> None:
    records = [rec(f"x{i}", {SFL: 12}, school="ONE") for i in range(3)] + [
        rec(f"y{i}", {SFL: 12}) for i in range(40)
    ]
    plan = form_cohorts(entries_for(records), arm=Arm.THIS_TERM, seed=1)
    school_of = {r.class_id: r.school_id for r in records}
    for c in plan.cohorts:
        assert Counter(school_of[cid] for cid in c.class_ids)["ONE"] <= 2


def test_small_pool_forms_one_undersized_cohort_flagged_cross_block() -> None:
    plan = form_cohorts(entries_for(plain_pool(20)), arm=Arm.THIS_TERM, seed=1)
    (cohort,) = plan.cohorts
    assert cohort.undersized and cohort.cross_block
    assert len(cohort.class_ids) < 15 and not plan.unplaced


def test_block_with_enough_teachers_stays_within_the_block() -> None:
    records = plain_pool(80, "B1") + plain_pool(10, "B2")
    plan = form_cohorts(entries_for(records), arm=Arm.THIS_TERM, seed=1)
    b1 = [c for c in plan.cohorts if c.block_id == "B1"]
    assert b1 and all(not c.cross_block for c in b1)
    assert any(c.cross_block and c.block_id is None for c in plan.cohorts)


def test_cohort_forming_is_deterministic() -> None:
    entries = entries_for(plain_pool(60))
    assert form_cohorts(entries, Arm.THIS_TERM, seed=4) == form_cohorts(
        entries, Arm.THIS_TERM, seed=4
    )


# --- matched comparison fallback ---------------------------------------------------------


def test_matched_comparison_needs_same_grade_medium_type_and_p_within_5_points() -> None:
    target = assign_tracks([rec("t", {SFL: 12}, checked=30)])[0]  # p = 0.40
    pool = assign_tracks(
        [
            rec("same", {SFL: 13}, checked=30),  # 0.433: ok
            rec("edge", {SFL: 14}, checked=30),  # 0.4667: 6.7 points: no
            rec("exact5", {SFL: 15}, checked=50),  # 0.30: 10 points: no
            rec("edge5", {SFL: 18}, checked=50),  # 0.36: 4 points: ok
            rec("othermedium", {SFL: 12}, medium="tamil"),
            rec("othertype", {SFL: 12}, school_type="private"),
            rec("othererror", {N: 12}),
        ]
    )
    assert [a.class_id for a in matched_comparison(target, pool)] == ["same", "edge5"]


def test_matched_comparison_boundary_is_exact_5_points() -> None:
    target = assign_tracks([rec("t", {SFL: 10}, checked=20)])[0]  # 0.50
    pool = assign_tracks([rec("in", {SFL: 11}, checked=20), rec("out", {SFL: 12}, checked=20)])
    assert [a.class_id for a in matched_comparison(target, pool)] == ["in"]  # 5.0 in, 10.0 out
