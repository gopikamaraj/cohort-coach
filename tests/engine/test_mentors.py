from engine.mentors import (
    MentorKind,
    MentorRecord,
    TermChange,
    check_candidate,
    check_improver,
    check_proven,
    find_mentors,
)
from engine.model import ErrorCode

SFL, N = ErrorCode.SUB_SFL, ErrorCode.ADD_NOCARRY


def change(
    prev: tuple[int, int] = (30, 100),
    now: tuple[int, int] = (10, 100),
    consent: bool = True,
) -> TermChange:
    return TermChange(
        error=SFL,
        grade=3,
        medium="hindi",
        prev_children_showing=prev[0],
        prev_children_checked=prev[1],
        now_children_showing=now[0],
        now_children_checked=now[1],
        consent=consent,
    )


def met(check, key: str) -> bool:  # type: ignore[no-untyped-def]
    return next(r.met for r in check.reasons if r.key == key)


# --- proven mentor -----------------------------------------------------------------------


def test_proven_mentor_happy_path_and_reasons_are_returned() -> None:
    check = check_proven(change(), comparison_avg_fall_points=5.0)
    assert check.kind is MentorKind.PROVEN and check.qualifies
    assert {r.key for r in check.reasons} >= {
        "on_track",
        "prev_p_at_least_25",
        "fall_at_least_15_points",
        "fall_at_least_half",
        "enough_children_both_terms",
        "beats_comparison",
        "consent",
    }
    assert all(r.met for r in check.reasons)


def test_a_fall_of_14_points_is_not_enough_15_is() -> None:
    assert not check_proven(change(now=(16, 100)), 5.0).qualifies  # 30 -> 16 = 14 points
    assert not met(check_proven(change(now=(16, 100)), 5.0), "fall_at_least_15_points")
    assert check_proven(change(now=(15, 100)), 5.0).qualifies  # 30 -> 15 = 15 points


def test_fall_must_also_be_at_least_half() -> None:
    # 60% -> 40%: a 20-point fall, but less than half of 60 points
    check = check_proven(change(prev=(60, 100), now=(40, 100)), 5.0)
    assert met(check, "fall_at_least_15_points") and not met(check, "fall_at_least_half")
    assert not check.qualifies
    assert check_proven(change(prev=(60, 100), now=(30, 100)), 5.0).qualifies  # exactly half


def test_prev_p_must_be_at_least_25_percent() -> None:
    assert not check_proven(change(prev=(24, 100), now=(0, 100)), 5.0).qualifies
    assert check_proven(change(prev=(25, 100), now=(10, 100)), 5.0).qualifies


def test_14_children_is_too_few_15_is_enough_in_either_term() -> None:
    assert not check_proven(change(prev=(6, 14), now=(1, 15)), 5.0).qualifies
    assert not check_proven(change(prev=(6, 15), now=(1, 14)), 5.0).qualifies
    assert check_proven(change(prev=(6, 15), now=(1, 15)), 5.0).qualifies


def test_fall_must_beat_the_comparison_groups_average() -> None:
    assert not check_proven(change(), comparison_avg_fall_points=20.0).qualifies  # equal: no
    assert check_proven(change(), comparison_avg_fall_points=19.9).qualifies
    assert not check_proven(change(), comparison_avg_fall_points=None).qualifies  # unknown


def test_consent_is_required() -> None:
    assert not check_proven(change(consent=False), 5.0).qualifies


# --- comparison-group improver -----------------------------------------------------------


def test_improver_meets_the_proven_bar_without_the_track() -> None:
    check = check_improver(change())
    assert check.kind is MentorKind.IMPROVER and check.qualifies
    assert not any(r.key == "on_track" for r in check.reasons)
    assert not check_improver(change(now=(16, 100))).qualifies
    assert not check_improver(change(consent=False)).qualifies


# --- same-term candidate -----------------------------------------------------------------


def test_candidate_needs_p_at_most_5_percent_while_block_is_at_least_25() -> None:
    ok = check_candidate(
        grade=3,
        medium="hindi",
        children_showing=5,
        children_checked=100,
        block_children_showing=250,
        block_children_checked=1000,
        cohort_grade=3,
        cohort_medium="hindi",
        consent=True,
    )
    assert ok.kind is MentorKind.CANDIDATE and ok.qualifies

    def build(**over):  # type: ignore[no-untyped-def]
        args = dict(
            grade=3,
            medium="hindi",
            children_showing=5,
            children_checked=100,
            block_children_showing=250,
            block_children_checked=1000,
            cohort_grade=3,
            cohort_medium="hindi",
            consent=True,
        )
        args.update(over)
        return check_candidate(**args)

    assert not build(children_showing=6).qualifies  # 6% is over 5%
    assert not build(block_children_showing=249).qualifies  # block average 24.9%
    assert not build(medium="tamil").qualifies  # other medium
    assert not build(grade=2).qualifies
    assert not build(consent=False).qualifies
    assert not build(children_checked=9, children_showing=0).qualifies  # too few checked


# --- tier-1 lookup -----------------------------------------------------------------------


def records() -> list[MentorRecord]:
    def rec(tid: str, kind: MentorKind, **kw):  # type: ignore[no-untyped-def]
        base = dict(error=SFL, grade=3, medium="hindi", verified=True)
        base.update(kw)
        return MentorRecord(teacher_id=tid, class_id="c-" + tid, kind=kind, **base)

    return [
        rec("t4", MentorKind.CANDIDATE),
        rec("t2", MentorKind.PROVEN),
        rec("t1", MentorKind.PROVEN),
        rec("t3", MentorKind.IMPROVER),
        rec("t5", MentorKind.PROVEN, medium="tamil"),
        rec("t6", MentorKind.PROVEN, error=N),
        rec("t7", MentorKind.PROVEN, verified=False),
    ]


def test_find_mentors_filters_exactly_and_orders_proven_first() -> None:
    found = find_mentors(records(), SFL, 3, "hindi")
    assert [m.teacher_id for m in found] == ["t1", "t2"]  # proven only, verified only
    wider = find_mentors(records(), SFL, 3, "hindi", statuses=frozenset(MentorKind))
    assert [m.teacher_id for m in wider] == ["t1", "t2", "t3", "t4"]
    unverified = find_mentors(records(), SFL, 3, "hindi", only_verified=False)
    assert [m.teacher_id for m in unverified] == ["t1", "t2", "t7"]
