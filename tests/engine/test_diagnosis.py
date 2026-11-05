import pytest

from engine.diagnosis import MIN_HITS, class_profile, diagnose_child, probe_items
from engine.forms import FORM_A
from engine.model import ChildDiagnosis, ErrorCode, Mark, Reading
from engine.normalize import normalize_answer

# Form A: correct answers are 346 728 85 74 82 35 38 26 43 54
CORRECT: list[Reading] = [346, 728, 85, 74, 82, 35, 38, 26, 43, 54]
H, R, N, SFL, NODEC = (
    ErrorCode.PV_HEARD,
    ErrorCode.PV_REVERSE,
    ErrorCode.ADD_NOCARRY,
    ErrorCode.SUB_SFL,
    ErrorCode.SUB_NODEC,
)


def answers(**changes: Reading) -> list[Reading]:
    """CORRECT with item overrides, e.g. answers(i3=75, i4=64)."""
    out = list(CORRECT)
    for key, value in changes.items():
        out[int(key[1:]) - 1] = value
    return out


def child(**changes: Reading) -> ChildDiagnosis:
    return diagnose_child(FORM_A, answers(**changes))


def test_rule_constants_match_the_scoring_pack() -> None:
    assert MIN_HITS == 2
    assert probe_items(FORM_A, H) == (1, 2)
    assert probe_items(FORM_A, R) == (1, 2)
    assert probe_items(FORM_A, N) == (3, 4, 5)
    assert probe_items(FORM_A, SFL) == (7, 8, 9, 10)
    assert probe_items(FORM_A, NODEC) == (7, 8, 9, 10)


def test_all_correct_shows_nothing() -> None:
    d = child()
    assert d.shows == frozenset()
    assert not d.anchor_wrong and d.other_count == 0


def test_one_hit_is_not_a_pattern_two_hits_are() -> None:
    assert child(i3=75).shows == frozenset()
    assert child(i3=75, i5=72).shows == {N}
    assert child(i7=42).shows == frozenset()
    assert child(i7=42, i10=66).shows == {SFL}
    assert child(i8=36, i9=53).shows == {NODEC}


def test_dictation_needs_both_items() -> None:
    assert child(i1=30046).shows == frozenset()
    assert child(i1=30046, i2=70028).shows == {H}
    assert child(i1=364, i2=782).shows == {R}
    assert child(i1=30046, i2=782).shows == frozenset()  # one of each is not a pattern


def test_heard_and_reversed_answer_counts_for_both() -> None:
    assert child(i1=30064, i2=70082).shows == {H, R}
    assert child(i1=30064, i2=782).shows == {R}  # 30064 counts for R; item 2 only reversed
    assert child(i1=30064, i2=70028).shows == {H}


def test_blank_and_unreadable_never_count() -> None:
    d = child(i3=75, i4="blank", i5="unreadable")
    assert d.shows == frozenset()
    assert d.blank_count == 1 and d.unreadable_count == 1
    assert child(i3=75, i4="blank", i5=72).shows == {N}


def test_wrong_anchor_is_flagged_and_items_7_to_10_still_scored() -> None:
    d = child(i6=25, i7=42, i8=34)
    assert d.anchor_wrong
    assert d.shows == {SFL}
    assert child(i6="blank").anchor_wrong is False


def test_other_and_untracked_tallies() -> None:
    d = child(i3=715, i4=614, i5=99)
    assert d.other_count == 3
    assert d.untracked == {"ADD-WHOLE-ONES": 2}
    assert d.shows == frozenset()
    assert d.marks[2].kind is Mark.OTHER


def test_devanagari_answer_normalises_before_diagnosis() -> None:
    raw = ["३४६", "७२८", "85", "74", "82", "35", "38", "26", "43", "54"]
    d = diagnose_child(FORM_A, [normalize_answer(x) for x in raw])
    assert d.shows == frozenset() and d.other_count == 0


def test_wrong_number_of_answers_is_rejected() -> None:
    with pytest.raises(ValueError):
        diagnose_child(FORM_A, [1, 2, 3])


def make_class(n_with: dict[ErrorCode, int], total: int) -> list[ChildDiagnosis]:
    """`total` children; the first n_with[code] children show each code (disjoint groups)."""
    recipes = {
        H: dict(i1=30046, i2=70028),
        R: dict(i1=364, i2=782),
        N: dict(i3=75, i4=64),
        SFL: dict(i7=42, i8=34),
        NODEC: dict(i7=48, i8=36),
    }
    kids: list[ChildDiagnosis] = []
    for code, n in n_with.items():
        kids += [child(**recipes[code]) for _ in range(n)]  # type: ignore[arg-type]
    kids += [child() for _ in range(total - len(kids))]
    return kids


def test_p_is_a_fraction_and_not_rounded() -> None:
    profile = class_profile(make_class({SFL: 1}, 3))
    assert profile.prevalence[SFL] == 1 / 3
    assert profile.children_checked == 3


def test_eligibility_is_one_child_showing_it_with_ten_children_checked() -> None:
    # Replaces test_eligibility_boundary_exactly_25_percent_with_enough_children: the 25% share rule was removed on
    # 2 Nov 2026 (DECISIONS.md). An error is eligible when at least 1 child shows it and at least 10 were checked.
    assert SFL in class_profile(make_class({SFL: 3}, 12)).eligible
    assert SFL in class_profile(make_class({SFL: 3}, 13)).eligible  # 0.2308 was below the old line: eligible now
    assert SFL in class_profile(make_class({SFL: 1}, 40)).eligible  # one child is enough
    assert SFL not in class_profile(make_class({SFL: 0}, 20)).eligible  # nobody shows it


def test_eligibility_needs_ten_children_checked() -> None:
    assert SFL in class_profile(make_class({SFL: 3}, 10)).eligible
    nine = class_profile(make_class({SFL: 3}, 9))
    assert nine.prevalence[SFL] > 0.25 and nine.eligible == () and nine.track is None


def test_track_is_the_highest_p_eligible_error() -> None:
    # Replaces the old expectation (N, SFL): with the 25% line gone NODEC (2 of 20) is eligible as well.
    profile = class_profile(make_class({SFL: 5, N: 7, NODEC: 2}, 20))
    assert profile.eligible == (N, SFL, NODEC)
    assert profile.track == N


def test_pv_heard_beats_a_higher_p_error() -> None:
    profile = class_profile(make_class({H: 5, SFL: 9}, 20))
    assert profile.track == H


def test_pv_reverse_is_never_chosen_as_a_track() -> None:
    only_r = class_profile(make_class({R: 10}, 20))
    assert R in only_r.eligible and only_r.track is None
    with_other = class_profile(make_class({R: 12, NODEC: 6}, 20))
    assert with_other.track == NODEC


def test_tied_p_goes_to_the_first_error_in_code_order() -> None:
    assert class_profile(make_class({N: 6, SFL: 6}, 20)).track == N


def test_counts_and_untracked_roll_up() -> None:
    kids = make_class({N: 2}, 10) + [child(i3=715, i4=614, i6=1)]
    profile = class_profile(kids)
    assert profile.counts[N] == 2 and profile.children_checked == 11
    assert profile.untracked == {"ADD-WHOLE-ONES": 2}
    assert profile.anchor_wrong_count == 1


def test_empty_class_has_no_prevalence_and_no_track() -> None:
    profile = class_profile([])
    assert profile.children_checked == 0 and profile.track is None
    assert all(p == 0.0 for p in profile.prevalence.values())


def test_one_rule_for_every_count_view_confirmed_by_default_possible_on_request() -> None:
    from engine.diagnosis import RULE_CONFIRMED, RULE_POSSIBLE, counts_for_rule, valid_rule

    confirmed = {"SUB-SFL": 3}
    seen_once = {"SUB-SFL": 5, "PV-HEARD": 2}
    assert counts_for_rule(confirmed, seen_once, RULE_CONFIRMED) == {"SUB-SFL": 3}  # seen in two or more questions
    assert counts_for_rule(confirmed, seen_once, RULE_POSSIBLE) == {"SUB-SFL": 5, "PV-HEARD": 2}  # seen in one
    assert counts_for_rule(confirmed, None, RULE_POSSIBLE) == {"SUB-SFL": 3}  # an older result has no once-counts
    assert [valid_rule(x) for x in (1, "2", 3, "x", None)] == [1, 2, 2, 2, 2]
