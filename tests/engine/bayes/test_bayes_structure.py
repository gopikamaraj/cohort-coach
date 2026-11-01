"""Structure of the 32-state model (docs/BAYESIAN-MODEL.md 7.2): the state declaration, rows that
sum to 1, the collapse rule, the stage forms, randomness use, and the starting wrong rate."""

from __future__ import annotations

import itertools
import random

import numpy as np
import pytest

from engine.bayes import belief as bel
from engine.bayes import dynamics as dyn
from engine.bayes import response as resp
from engine.bayes import state as st
from engine.bayes.content import NEUTRAL_MOVE, load_moves, load_note_tags, load_params
from engine.bayes.planner import plan_turn_traced, roles_for
from engine.model import ErrorCode
from engine.simulator import Problem, _misheard, _rev
from evals.runners.bayes_protocols import scenario, start
from services.practice.content import load_scenario

P = load_params().defaults
CODES = (ErrorCode.SUB_SFL, ErrorCode.SUB_NODEC, ErrorCode.ADD_NOCARRY, ErrorCode.PV_HEARD)
SCENARIO_ITEMS = {c: load_scenario(c.value).config.problems for c in CODES}
ALL_ITEMS = [i for items in SCENARIO_ITEMS.values() for i in items] + [
    Problem("sub", 58, 23),
    Problem("add", 23, 41),
    Problem("sub", 70, 25),
]


def test_every_state_map_round_trips_through_array_coordinates() -> None:
    assert st.SHAPE == (2, 2, 2, 4) and st.N_STATES == 32
    seen = set()
    for i in range(32):
        m = st.from_index(i)
        assert st.index(m) == i
        assert st.from_coords(st.coords(m)) == m
        pv, e, w = int(m["place_value"]), int(m["exchange"]), int(m["written_step"])
        assert i == ((pv * 2 + e) * 2 + w) * 4 + st.HABITS.index(m["habit"])  # type: ignore[arg-type]
        seen.add(tuple(m.values()))
    assert len(seen) == 32
    arr = st.to_array(np.arange(32, dtype=np.float64))
    assert arr[1, 0, 1, 2] == st.index(
        {"place_value": 1, "exchange": 0, "written_step": 1, "habit": "sibling"}
    )
    with pytest.raises(ValueError):
        st.index({"place_value": 2, "exchange": 0, "written_step": 0, "habit": "none"})
    with pytest.raises(ValueError):
        st.index({"place_value": 0, "exchange": 0, "written_step": 0, "habit": "lost"})


def test_axis_and_habit_order_are_declared_only_in_state_py() -> None:
    from pathlib import Path

    root = Path(__file__).resolve().parents[3] / "engine" / "bayes"
    for f in root.glob("*.py"):
        if f.name == "state.py":
            continue
        text = f.read_text(encoding="utf-8")
        assert '("none", "target", "sibling", "no_method")' not in text, f.name
        assert '("place_value", "exchange", "written_step", "habit")' not in text, f.name
        assert "ipewh" not in text and "reshape(2, 2, 2, 4)" not in text, f.name


def _contexts() -> list[dyn.TurnContext]:
    moves = [*load_moves().values(), NEUTRAL_MOVE]
    return [
        dyn.TurnContext(m, r, a, ov, c)
        for m in moves
        for r in (0.0, 0.5, 1.0)
        for a in (0.0, 0.37, 1.0)
        for ov in (0.0, 2.0)
        for c in (0, 3)
    ]


@pytest.mark.parametrize("code", CODES, ids=lambda c: c.value)
def test_every_transition_row_sums_to_one(code: ErrorCode) -> None:
    roles = roles_for(code)
    for ctx in _contexts():
        t = dyn.transition_matrix(ctx, roles, P)
        assert t.shape == (32, 32) and (t >= -1e-15).all()
        assert np.allclose(t.sum(axis=1), 1.0, atol=1e-9)


@pytest.mark.parametrize("code", CODES, ids=lambda c: c.value)
def test_every_response_row_and_outcome_set_sums_to_one(code: ErrorCode) -> None:
    roles = roles_for(code)
    for item, delta in itertools.product(ALL_ITEMS, (0.0, 0.15, 0.3)):
        m = resp.response_matrix(item, roles, P, delta)
        assert np.allclose(m.sum(axis=1), 1.0, atol=1e-9) and (m >= 0).all()
        for stage in ("core", "output", "input-test", "input-teaching"):
            outs = resp.outcomes(item, roles, stage, P, delta)
            assert np.allclose(sum(v for _, v in outs), 1.0, atol=1e-9)


def test_the_sampler_agrees_with_the_matrix() -> None:
    roles = roles_for(ErrorCode.SUB_SFL)
    ctx = dyn.TurnContext(load_moves()["tell_rule"], 1.0, 0.7, 0.0, 1)
    s = {"place_value": 1, "exchange": 0, "written_step": 0, "habit": "target"}
    row = dyn.transition_matrix(ctx, roles, P)[st.index(s)]
    rng = random.Random(3)
    counts = np.zeros(32)
    n = 40000
    for _ in range(n):
        nxt, _ = dyn.sample_next(s, ctx, roles, P, [rng.random() for _ in range(4)])
        counts[st.index(nxt)] += 1
    assert np.abs(counts / n - row).max() < 0.01


def test_the_collapse_rule_moves_a_bug_that_does_not_bite_to_correct() -> None:
    # Two-digit subtraction never separates the two bugs (both bite exactly when borrowing), but
    # dictating 55 does: PV-HEARD writes 505, PV-REVERSE gives 55 back, which is right.
    roles = roles_for(ErrorCode.PV_HEARD)
    item = Problem("dictation", 55)
    assert resp.bites(ErrorCode.PV_HEARD, item) and not resp.bites(ErrorCode.PV_REVERSE, item)
    sib = st.index({"place_value": 0, "exchange": 0, "written_step": 0, "habit": "sibling"})
    tgt = st.index({"place_value": 0, "exchange": 0, "written_step": 0, "habit": "target"})
    m = resp.response_matrix(item, roles, P)
    assert m[sib, resp.K_SIBLING] == 0 and m[sib, resp.K_CORRECT] == 1.0
    assert m[tgt, resp.K_TARGET] == pytest.approx(1 - P.g0)
    w1 = st.index({"place_value": 0, "exchange": 0, "written_step": 1, "habit": "sibling"})
    assert m[w1, resp.K_CORRECT] == 1.0  # the sibling's slip collapses too
    for a in range(21, 99):  # and confirm the claim about two-digit subtraction
        for b in range(11, a):
            q = Problem("sub", a, b)
            assert resp.bites(ErrorCode.SUB_SFL, q) == resp.bites(ErrorCode.SUB_NODEC, q)
    add = roles_for(ErrorCode.ADD_NOCARRY)
    m = resp.response_matrix(Problem("add", 47, 25), add, P)
    assert (m[:, resp.K_SIBLING] == 0).all()  # no sibling in the addition family


def test_on_an_item_that_needs_no_step_every_state_but_no_method_is_right() -> None:
    roles = roles_for(ErrorCode.SUB_SFL)
    item = Problem("sub", 58, 23)
    assert not resp.needs_step(roles, item)
    m = resp.response_matrix(item, roles, P)
    for i in range(32):
        if st.habit_of(i) == "no_method":
            assert m[i, resp.K_CORRECT] == pytest.approx(P.c_nm_easy)
            assert m[i, resp.K_NONE] == pytest.approx(1 - P.c_nm_easy)
        else:
            assert m[i, resp.K_CORRECT] == 1.0
    none_w0 = st.index({"place_value": 0, "exchange": 0, "written_step": 0, "habit": "none"})
    assert m[none_w0, resp.K_CORRECT] == 1.0


def test_stage_forms_match_the_legacy_forms() -> None:
    for item in ALL_ITEMS + [Problem("dictation", 43), Problem("dictation", 417)]:
        legacy_out = {_misheard(item, random.Random(k)) for k in range(300)}
        options = set(resp.misheard_options(item))
        assert legacy_out - {None} == options, item
        assert resp.rev(item.correct) == _rev(item.correct)
        legacy_reversible = _rev(item.correct) != item.correct and item.correct % 10 != 0
        assert resp.output_form_available(item) == legacy_reversible


def test_exactly_four_transition_draws_per_erring_child_per_turn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import engine.bayes.planner as planner

    draws: dict[str, int] = {}

    class Counting(random.Random):
        def __init__(self, seed: object = None) -> None:
            super().__init__(seed)  # type: ignore[arg-type]
            self.key = str(seed)
            draws.setdefault(self.key, 0)

        def random(self) -> float:
            draws[self.key] = draws.get(self.key, 0) + 1
            return super().random()

    monkeypatch.setattr(planner.random, "Random", Counting)
    loaded, _ = scenario()
    state = start("bayesian", 7)
    erring = [i for i, c in enumerate(state.children) if c.error]
    for turn, move in enumerate(["pose_problem", "show_bundles", "other", "tell_rule"], start=1):
        _, state, _ = plan_turn_traced(state, loaded.config, move, addressed=None, posed=None)
        trans = {k: v for k, v in draws.items() if k.startswith(f"bayes:trans:7:{turn}:")}
        assert sorted(trans) == sorted(f"bayes:trans:7:{turn}:{i}" for i in erring)
        assert all(v == 4 for v in trans.values())
    answers = {k: v for k, v in draws.items() if k.startswith("bayes:answer:")}
    assert answers and all(v == 2 for v in answers.values())


def test_the_belief_engine_and_eig_consume_no_randomness(monkeypatch: pytest.MonkeyPatch) -> None:
    roles = roles_for(ErrorCode.SUB_SFL)
    py_state, np_state = random.getstate(), np.random.get_state()

    def refuse(*_: object, **__: object) -> None:
        raise AssertionError("randomness used")

    monkeypatch.setattr(random, "Random", refuse)
    b = bel.observer_start("target", roles, P, ["pv_shaky", "rule_drilled"], load_note_tags())
    ctx = dyn.TurnContext(load_moves()["show_bundles"], 1.0, 0.6, 0.0, 0)
    b = bel.predict(b, dyn.transition_matrix(ctx, roles, P))
    item = Problem("sub", 52, 29)
    outs = resp.outcomes(item, roles, "core", P, 0.3)
    b = bel.update(b, dict(outs)[("n", 37)])
    bel.eig(b, outs)
    bel.marginals(b)
    bel.entropy_bits(b)
    assert random.getstate() == py_state
    assert all(
        np.array_equal(x, y) if isinstance(x, np.ndarray) else x == y
        for x, y in zip(np.random.get_state(), np_state, strict=True)
    )


def test_the_mean_starting_wrong_rate_for_a_target_child_is_0_902() -> None:
    roles = roles_for(ErrorCode.SUB_SFL)
    item = Problem("sub", 52, 29)
    pe = bel.pe_weights(P)
    wrong = 0.0
    for (pv, e), w in pe.items():
        i = st.index({"place_value": pv, "exchange": e, "written_step": 0, "habit": "target"})
        wrong += w * (1 - resp.response_matrix(item, roles, P)[i, resp.K_CORRECT])
    assert wrong == pytest.approx(0.902, abs=1e-12)


def test_soft_evidence_with_no_tags_is_exactly_the_plain_prior() -> None:
    roles = roles_for(ErrorCode.SUB_SFL)
    tags = load_note_tags()
    assert bel.tagged_pe(P, [], tags, "subtraction") == bel.pe_weights(P)
    plain = bel.observer_start("target", roles, P)
    assert np.array_equal(bel.observer_start("target", roles, P, [], tags), plain)
    secure = bel.observer_start("target", roles, P, ["pv_secure"], tags)
    assert secure[st.mask(place_value=1)].sum() > plain[st.mask(place_value=1)].sum()
    drilled = bel.observer_start("target", roles, P, ["rule_drilled"], tags)
    assert drilled[st.mask(habit="sibling")].sum() > plain[st.mask(habit="sibling")].sum()
    add = roles_for(ErrorCode.ADD_NOCARRY)
    a_plain = bel.observer_start("target", add, P)
    a_drilled = bel.observer_start("target", add, P, ["rule_drilled"], tags)
    assert a_drilled[st.mask(habit="sibling")].sum() == 0 == a_plain[st.mask(habit="sibling")].sum()
    assert np.isclose(
        a_drilled[st.mask(habit="target")].sum(), a_plain[st.mask(habit="target")].sum()
    )
