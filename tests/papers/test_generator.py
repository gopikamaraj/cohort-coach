"""Paper Studio generator: reproducible, anchors fixed, adaptive items follow the class, and every
rule (coverage, discrimination, uniqueness, twins) holds or the failure names the rule."""

from __future__ import annotations

import pytest

from engine.forms import FORM_A, FORM_B
from services.papers import generator as g
from services.papers.rules import Slot, seed_rules

RULES = seed_rules()
PRE = g.CheckRef(id="c-0123456789:1", kind="pre", form="A", class_label="3A", term=1)
POST = g.CheckRef(id="c-0123456789:2", kind="post", form="B", class_label="3A", term=2)


def profile(**kw: object) -> g.Profile:
    base: dict[str, object] = {
        "source": "baseline",
        "weights": {},
        "not_assessed": (),
        "language": "en",
    }
    base.update(kw)
    return g.Profile(**base)  # type: ignore[arg-type]


def paper(seed: object = 7, bp: str = "standard_10_5", prof: g.Profile | None = None) -> g.Paper:
    return g.generate_paper(PRE, prof or profile(), RULES, bp, 1, seed)


def test_the_same_inputs_give_the_same_paper_and_hash() -> None:
    a, b = paper(), paper()
    assert a == b and a.hash == b.hash and len(a.hash) == 64


def test_a_different_seed_gives_different_numbers() -> None:
    a, b = paper(seed=1), paper(seed=2)
    assert [(i.a, i.b) for i in a.items] != [(i.a, i.b) for i in b.items]
    assert a.hash != b.hash


def test_the_generator_never_touches_the_global_random_state() -> None:
    import random

    random.seed(99)
    before = random.random()
    random.seed(99)
    paper()
    assert random.random() == before


def test_anchors_keep_the_same_skills_and_difficulty_on_every_paper() -> None:
    shapes = set()
    for seed in range(12):
        p = paper(seed=seed)
        anchors = [i for i in p.items if i.is_anchor]
        assert [i.n for i in anchors] == list(range(1, 11))
        shapes.add(tuple((i.template, i.difficulty) for i in anchors))
    assert len(shapes) == 1
    (shape,) = shapes
    assert [d for _, d in shape if d is not None] == [15, 14, 12, 2, 4, 7, 6]


def test_adaptive_items_go_deeper_where_the_class_went_wrong() -> None:
    p = paper(prof=profile(source="past", weights={"C3": 9.0, "C2": 1.0}))
    adaptive = [i for i in p.items if not i.is_anchor]
    assert len(adaptive) == 5
    assert sum(i.competency == "C3" for i in adaptive) >= 4
    first_c3 = next(i for i in adaptive if i.competency == "C3")
    assert first_c3.template == "sub-borrow-zero"  # the deeper variant comes first
    sections = [i.section for i in adaptive]
    assert sections == sorted(sections, key=["dictation", "add", "subtract"].index)


def test_a_skill_marked_not_assessed_is_left_off_the_paper() -> None:
    p = paper(prof=profile(source="intake", weights={"C3": 5.0}, not_assessed=("C3",)))
    assert all(i.competency != "C3" for i in p.items)
    assert p.not_assessed == ("C3",)
    assert "SUB-SFL" not in p.coverage and "SUB-NODEC" not in p.coverage
    assert [i.n for i in p.items] == list(range(1, len(p.items) + 1))


def test_every_error_code_is_probed_at_least_twice() -> None:
    for seed in range(20):
        p = paper(seed=seed)
        for code in ("PV-HEARD", "PV-REVERSE", "ADD-NOCARRY", "SUB-SFL", "SUB-NODEC"):
            assert len(p.coverage[code]) >= 2, (seed, code)


def test_no_two_bug_functions_share_a_wrong_answer_and_none_equals_the_key() -> None:
    for seed in range(20):
        for item in paper(seed=seed).items:
            seen: dict[int, str] = {}
            for code, answers in item.wrong.items():
                assert item.correct not in answers
                for ans in answers:
                    # the heard-and-reversed answer counts for both place-value codes, by design
                    if ans in seen and {seen[ans], code} != {"PV-HEARD", "PV-REVERSE"}:
                        pytest.fail(f"{item} {ans} under {seen[ans]} and {code}")
                    seen[ans] = code


def test_no_item_appears_twice_in_a_paper() -> None:
    for seed in range(20):
        p = paper(seed=seed)
        pairs = [(i.operation, i.a, i.b) for i in p.items]
        assert len(pairs) == len(set(pairs))


def test_coverage_that_cannot_be_met_fails_and_names_the_rule() -> None:
    rules = RULES.model_copy(deep=True)
    bp = rules.blueprint("baseline_10")
    bp.slots = [s for s in bp.slots if s.template != "sub-borrow"] + [
        Slot(n=0, section="subtract", kind="anchor", template="sub-borrow", difficulty=2)
    ]
    for k, s in enumerate(bp.slots):
        s.n = k + 1
    with pytest.raises(g.CannotMeet) as e:
        g.generate_paper(PRE, profile(), rules, "baseline_10", 1, 1)
    assert e.value.rule == "coverage" and "SUB-SFL" in str(e.value)


def test_constraints_that_no_number_satisfies_fail_and_name_the_rule() -> None:
    rules = RULES.model_copy(deep=True)
    rules.template("add-carry").constraints["sum_max"] = 20  # no carrying sum is that small
    with pytest.raises(g.CannotMeet) as e:
        g.generate_paper(PRE, profile(), rules, "baseline_10", 1, 1)
    assert e.value.rule == "constraints" and "add-carry" in str(e.value)


def test_a_retired_template_cannot_be_used() -> None:
    rules = RULES.model_copy(deep=True)
    rules.template("sub-borrow").retired = True
    with pytest.raises(g.CannotMeet) as e:
        g.generate_paper(PRE, profile(), rules, "baseline_10", 1, 1)
    assert e.value.rule == "retired"


def test_form_b_is_a_twin_of_every_form_a_item_and_repeats_no_number_pair() -> None:
    for seed in range(10):
        a = paper(seed=seed)
        b = g.make_twin(a, RULES, POST, seed)
        assert b.form == "B" and len(b.items) == len(a.items)
        a_pairs = {(i.a, i.b) for i in a.items}
        for x, y in zip(a.items, b.items, strict=True):
            assert y.twin_of == x.n and y.template == x.template and y.difficulty == x.difficulty
            assert y.is_anchor == x.is_anchor
            assert (y.a, y.b) not in a_pairs and y.a != x.a


def test_the_twin_is_reproducible_and_never_adapts_to_anything_but_the_pre_test() -> None:
    a = paper()
    assert g.make_twin(a, RULES, POST, 5) == g.make_twin(a, RULES, POST, 5)


def test_the_pilot_forms_import_as_an_explicit_paper_and_its_twin() -> None:
    a = g.pilot_paper(PRE, RULES, 1, "A")
    b = g.pilot_paper(POST, RULES, 1, "B")
    assert [(i.a, i.b) for i in a.items] == [(i.a, i.b) for i in FORM_A.items]
    assert [(i.a, i.b) for i in b.items] == [(i.a, i.b) for i in FORM_B.items]
    assert all(i.is_anchor for i in a.items) and [i.twin_of for i in b.items] == list(range(1, 11))
    assert a.items[2].wrong["ADD-NOCARRY"] == [75]
    # every wrong answer matches the engine's own answer table, item by item
    from engine.bugs import answer_codes, correct_answer

    for form, p in ((FORM_A, a), (FORM_B, b)):
        for src, it in zip(form.items, p.items, strict=True):
            assert it.correct == correct_answer(src)
            mine = {(ans, code) for code, answers in it.wrong.items() for ans in answers}
            theirs = {(ans, c.value) for ans, cs in answer_codes(src).items() for c in cs}
            assert mine == theirs, src


def test_the_check_code_matches_the_check_record() -> None:
    assert paper().check_code == "PRE · 3A" # terms are off (correction 9, DECISIONS 2026-11-03): the code no longer ends in a term (was "PRE · 3A · T1")
    assert g.make_twin(paper(), RULES, POST, 1).check_code == "POST · 3A"  # was "POST · 3A · T2"


def test_the_profile_holds_class_counts_only() -> None:
    p = g.profile_from_counts(
        {"SUB-SFL": 9, "ADD-NOCARRY": 2}, checked=18, language="hi", built_from=["c-1:1"]
    )
    assert p.source == "past" and p.weights["C3"] == pytest.approx(0.5) and p.strength == 18
    assert set(g.Profile.__dataclass_fields__) == {
        "source",
        "weights",
        "not_assessed",
        "language",
        "strength",
        "built_from",
    }


def test_a_different_language_gives_the_same_numbers() -> None:
    en, ta = paper(prof=profile(language="en")), paper(prof=profile(language="ta"))
    assert [(i.a, i.b) for i in en.items] == [(i.a, i.b) for i in ta.items]
