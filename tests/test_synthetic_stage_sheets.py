"""The synthetic sheet spec: the stage rows and hero expectations agree with the engine.

Rendering is not tested here (it is a slow image job with its own self-check); this checks the
spec, so a change to the rules or the rows cannot drift apart silently. Robustness data only."""

from __future__ import annotations

from engine.forms import PILOT_FORMS
from engine.model import Reading
from engine.normalize import normalize_answer
from engine.stages import classify_child
from scripts.make_synthetic_sheets import HERO_STAGES, STAGE_ROWS, hero_specs, stage_specs


def stages_of(form: str, texts: list[str]) -> list[str]:
    readings: list[Reading] = [normalize_answer(t) for t in texts]
    r = classify_child(PILOT_FORMS[form], readings)
    return (
        ["not attempted"] if r.not_attempted and not r.stages else sorted(s.value for s in r.stages)
    )


def test_the_seven_stage_rows_are_the_ones_in_the_addendum() -> None:
    assert [r[0] for r in STAGE_ROWS] == ["S01", "S02", "S03", "S04", "S05", "S06", "S07"]
    assert STAGE_ROWS[6][1] == "364,782,58,47,28,35,42,34,57,66"  # reversal and SUB-SFL


def test_every_stage_row_gets_its_expected_stage_from_the_engine() -> None:
    for spec in stage_specs():
        assert spec.expected_stages is not None
        assert stages_of(spec.form, spec.texts) == sorted(spec.expected_stages), spec.sheet_id


def test_every_hero_with_an_expectation_gets_it_from_the_engine() -> None:
    heroes = {s.hero_id: s for s in hero_specs()}
    assert set(HERO_STAGES) <= set(heroes)
    for hid, want in HERO_STAGES.items():
        spec = heroes[hid]
        assert spec.expected_stages == want
        assert stages_of(spec.form, spec.texts) == sorted(want), hid


def test_the_stage_sheets_are_their_own_synthetic_set() -> None:
    assert {s.set_name for s in stage_specs()} == {"STG"}
