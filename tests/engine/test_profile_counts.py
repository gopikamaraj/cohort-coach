from engine.diagnosis import class_profile, diagnose_child, profile_from_counts
from engine.forms import FORM_A
from engine.model import ErrorCode

H, SFL, N = ErrorCode.PV_HEARD, ErrorCode.SUB_SFL, ErrorCode.ADD_NOCARRY


def test_profile_from_counts_matches_class_profile() -> None:
    kids = [
        diagnose_child(FORM_A, [346, 728, 85, 74, 82, 35, 42, 34, 43, 54]) for _ in range(5)
    ] + [diagnose_child(FORM_A, [346, 728, 85, 74, 82, 35, 38, 26, 43, 54]) for _ in range(7)]
    from_kids = class_profile(kids)
    from_counts = profile_from_counts(12, {SFL: 5})
    assert from_counts.counts == from_kids.counts
    assert from_counts.prevalence == from_kids.prevalence
    assert from_counts.eligible == from_kids.eligible == (SFL,)
    assert from_counts.track == from_kids.track == SFL


def test_missing_codes_count_as_zero_and_nothing_is_rounded() -> None:
    profile = profile_from_counts(30, {N: 11})
    assert profile.counts[H] == 0 and profile.counts[N] == 11
    assert profile.prevalence[N] == 11 / 30


def test_counts_above_children_checked_are_rejected() -> None:
    import pytest

    with pytest.raises(ValueError):
        profile_from_counts(10, {SFL: 11})
