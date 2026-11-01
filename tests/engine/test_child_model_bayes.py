"""The Bayesian child model (SIMULATOR_MODEL=bayesian) and the switch that picks it.

The legacy model's behaviour is pinned by test_simulator_golden.py and the existing simulator tests;
these tests cover the Bayesian model and what both modes must share.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import replace

import pytest

from engine.child_model import (
    LEGACY,
    BayesianModel,
    BayesParams,
    LegacyModel,
    model_from_env,
)
from engine.model import ErrorCode
from engine.simulator import (
    MoveEffect,
    Problem,
    ScenarioConfig,
    SessionState,
    TurnPlan,
    fill_seats,
    new_session,
    plan_turn,
    state_from_dict,
    state_to_dict,
    wrong_answers,
)
from services.practice.content import load_scenario

BAYES = BayesianModel()
SFL = load_scenario("SUB-SFL")
CFG = SFL.config


def seats(stages: bool = True) -> tuple:  # type: ignore[type-arg]
    mix = SFL.scenario.stage_mix if stages else ()
    return fill_seats({}, 0, CFG.error, SFL.scenario.seat_mix, stage_mix=mix)


def start(
    seed: int = 5, model: object = BAYES, cfg: ScenarioConfig = CFG, stages: bool = True
) -> SessionState:
    return new_session(cfg, seats(stages), seed, model)  # type: ignore[arg-type]


SCRIPT: list[tuple[str, int | None]] = [
    ("pose_problem", 1), ("ask_explain", 1), ("show_bundles", None), ("exchange_ten", 1),
    ("pose_problem", 2), ("check_back", 2), ("scold", 3), ("praise", None),
    ("pose_problem", 3), ("show_bundles", 3), ("pose_problem", None), ("other", None),
]  # fmt: skip


def run(
    state: SessionState, script: list[tuple[str, int | None]], cfg: ScenarioConfig = CFG
) -> tuple[list[TurnPlan], SessionState]:
    plans = []
    for move, seat in script:
        if state.finished:
            break
        to = state.children[seat].name if seat is not None else None
        plan, state = plan_turn(state, cfg, move, addressed=to, posed=None)
        plans.append(plan)
    return plans, state


def drill(
    move: str, seed: int, model: object = BAYES, stages: bool = True
) -> tuple[list[TurnPlan], SessionState]:
    """The BAYESIAN-CHECK 2.10 round: pose a problem to a child, then the move to her, round the
    four children with an error, until the session ends."""
    state = start(seed, model, stages=stages)
    erring = [i for i, c in enumerate(state.children) if c.error]
    plans: list[TurnPlan] = []
    k = 0
    while not state.finished:
        i = erring[k % len(erring)]
        p, state = run(state, [("pose_problem", i), (move, i)])
        plans += p
        k += 1
    return plans, state


def _view(plans: list[TurnPlan]) -> list[tuple[object, ...]]:
    return [
        (
            p.speaker,
            p.intent,
            p.answer,
            p.written,
            p.correct,
            tuple((c.speaker, c.answer) for c in p.chorus),
        )
        for p in plans
    ]


# --- determinism, ranges, individual differences


def test_the_same_seed_gives_the_same_session_and_seed_6_differs_from_seed_5() -> None:
    a_plans, a = run(start(5), SCRIPT)
    b_plans, b = run(start(5), SCRIPT)
    assert _view(a_plans) == _view(b_plans) and state_to_dict(a) == state_to_dict(b)
    assert [p.trace for p in a_plans] == [p.trace for p in b_plans]
    c_plans, c = run(start(6), SCRIPT)
    assert (_view(c_plans), state_to_dict(c)["children"]) != (
        _view(a_plans),
        state_to_dict(a)["children"],
    )


def test_belief_and_derived_strength_stay_between_0_and_1() -> None:
    for seed in range(1, 41):
        for move in ("show_bundles", "ask_explain", "tell_rule", "repeat_rule_louder"):
            plans, state = drill(move, seed)
            for p in plans:
                for row in p.trace:
                    assert 0.0 <= row.belief <= 1.0 and 0.0 <= row.strength <= 1.0
            for c in state.children:
                assert 0.0 <= c.strength <= 1.0
                assert c.belief is None or 0.0 <= c.belief <= 1.0


def test_starting_beliefs_and_responsiveness_differ_by_child_and_by_seed() -> None:
    s5, s6 = start(5), start(6)
    kids5 = [c for c in s5.children if c.error]
    assert len({c.belief for c in kids5}) == len(kids5)
    assert len({c.responsiveness for c in kids5}) == len(kids5)
    assert [c.belief for c in kids5] != [c.belief for c in s6.children if c.error]
    beliefs = [c.belief for seed in range(1, 201) for c in start(seed).children if c.error]
    mean = sum(beliefs) / len(beliefs)  # type: ignore[arg-type]
    assert abs(mean - (1 - CFG.start_strength)) < 0.02  # prior mean is 1 - start_strength
    rs = [c.responsiveness for seed in range(1, 201) for c in start(seed).children if c.error]
    assert abs(sum(rs) / len(rs) - 1.0) < 0.05 and all(0 <= r <= 2 for r in rs)  # type: ignore[arg-type, operator]


def test_legacy_children_all_still_start_at_the_start_strength_with_no_belief() -> None:
    for seed in (1, 5, 99):
        for c in start(seed, LEGACY).children:
            assert c.strength == (CFG.start_strength if c.error else 0.0)
            assert c.belief is None and c.responsiveness is None and c.last_gain is None


def test_the_prior_comes_from_its_own_generators_not_the_turn_generator() -> None:
    a = start(5)
    random.seed(12345)  # the global generator plays no part
    b = start(5)
    assert a == b
    seat = next(i for i, c in enumerate(a.children) if c.error)
    k = BAYES.params.prior_concentration
    want = random.Random(f"bayes-prior:5:{seat}").betavariate(k * 0.1, k * 0.9)
    assert a.children[seat].belief == round(want, 9)


# --- the move-to-learning map and the update


def test_the_move_effect_to_learning_probability_table() -> None:
    table = {m: BAYES.learn_probability(e.strength, CFG) for m, e in CFG.moves.items()}
    assert BAYES.effect_scale(CFG) == 0.3
    assert {
        m: table[m] for m in ("show_bundles", "exchange_ten", "decomposition")
    } == dict.fromkeys(("show_bundles", "exchange_ten", "decomposition"), 0.6)
    assert table["compensation"] == 0.5
    assert table["ask_explain"] == table["check_back"] == table["order_probe"] == 0.4
    assert table["tell_rule"] == 0.1 and table["repeat_rule_louder"] == 0.04
    assert (
        table["pose_problem"]
        == table["praise"]
        == table["scold"]
        == table["give_the_answer"]
        == 0.0
    )


def test_a_stronger_move_never_gives_a_smaller_gain_from_the_same_state() -> None:
    kid = next(c for c in start(5).children if c.error)
    moves = sorted(CFG.moves.items(), key=lambda kv: abs(kv[1].strength))
    for belief in (0.0, 0.1, 0.5, 0.9):
        for r in (0.3, 1.0, 1.9):
            k = replace(kid, belief=belief, responsiveness=r)
            gains = [
                BAYES.learn(k, e.strength, 1.0, CFG)[2] if e.strength else 0.0 for _, e in moves
            ]
            assert gains == sorted(gains)


@pytest.mark.parametrize(
    "tier",
    [
        ("show_bundles", "exchange_ten", "decomposition"),
        ("ask_explain", "check_back", "order_probe"),
    ],
)
def test_moves_with_the_same_effect_give_identical_sessions(tier: tuple[str, ...]) -> None:
    """Same children, answers and beliefs turn by turn. (check_back's behaviour is `doubt` and the
    other two -0.20 moves are `explain`, so the kind of line differs; what the children learn and
    answer does not.)"""

    def what(plans: list[TurnPlan]) -> list[tuple[object, ...]]:
        return [(p.speaker, p.answer, p.written, p.correct, p.trace) for p in plans]

    for seed in (1, 5, 17):
        runs = [drill(m, seed) for m in tier]
        first = (what(runs[0][0]), state_to_dict(runs[0][1]))
        assert all((what(p), state_to_dict(s)) == first for p, s in runs[1:])


def test_an_overheard_move_gives_exactly_half_the_direct_gain_from_the_same_state() -> None:
    kid = next(c for c in start(5).children if c.error)
    for belief in (0.0, 0.2, 0.7):
        for r in (0.5, 1.0, 1.9):  # 1.9 x 0.6 > 1: the cap applies before halving
            k = replace(kid, belief=belief, responsiveness=r)
            for e in (-0.3, -0.2, -0.05):
                direct = BAYES.learn(k, e, 1.0, CFG)[2]
                heard = BAYES.learn(k, e, CFG.overhear, CFG)[2]
                assert CFG.overhear == 0.5 and heard == direct / 2


def test_in_a_turn_the_named_child_learns_directly_and_the_room_overhears() -> None:
    state = start(5)
    named = state.children[1].name
    plan, after = plan_turn(state, CFG, "show_bundles", addressed=named, posed=None)
    vias = {row.name: row.via for row in plan.trace}
    assert vias[named] == "direct"
    assert {v for n, v in vias.items() if n != named} == {"overhear"}
    rows = {row.name: row for row in plan.trace}
    assert rows[named].t == 0.6 and all(r.t == 0.3 for n, r in rows.items() if n != named)
    for c0, c1 in zip(state.children, after.children, strict=True):
        if c0.error:
            assert c1.belief is not None and c0.belief is not None and c1.belief > c0.belief


def test_a_move_with_no_effect_teaches_no_one() -> None:
    state = start(5)
    plan, after = plan_turn(state, CFG, "praise", addressed=state.children[1].name, posed=None)
    assert all(row.via is None and row.gain == 0.0 for row in plan.trace)
    assert [c.belief for c in after.children] == [c.belief for c in state.children]


def test_a_scold_makes_only_the_child_reached_go_quiet() -> None:
    state = start(5)
    plan, after = plan_turn(state, CFG, "scold", addressed=state.children[2].name, posed=None)
    assert [c.quiet_turns > 0 for c in after.children] == [False, False, True, False, False]
    assert [c.belief for c in after.children] == [c.belief for c in state.children]


def test_a_move_that_raises_strength_is_refused_by_the_bayesian_model() -> None:
    bad = replace(CFG, moves={**CFG.moves, "drill_wrong": MoveEffect("agree", 0.1, 0.0, False)})
    with pytest.raises(ValueError, match="raise error strength"):
        new_session(bad, seats(), 5, BAYES)
    new_session(bad, seats(), 5, LEGACY)  # legacy has no such rule


# --- shared rules: chorus, stages, bug functions, end of session, the correct child


def test_chorus_up_to_three_speak_and_the_first_speaker_is_the_same_without_a_chorus() -> None:
    # As in the legacy chorus test: each turn is planned twice from the same state, with and without
    # a chorus (later turns may differ, since a child who joins in keeps her answer and streak).
    solo = replace(CFG, chorus_max=1)
    sizes: set[int] = set()
    for seed in range(1, 31):
        state = start(seed)
        for move, seat in SCRIPT:
            if state.finished:
                break
            to = state.children[seat].name if seat is not None else None
            q, _ = plan_turn(state, solo, move, addressed=to, posed=None)
            p, state = plan_turn(state, CFG, move, addressed=to, posed=None)
            assert (p.speaker, p.intent, p.answer, p.written, p.correct) == (
                q.speaker, q.intent, q.answer, q.written, q.correct,
            )  # fmt: skip
            sizes.add(1 + len(p.chorus) if p.speaker else 0)
            # a child joining in does not change anyone's belief: only the move does
            assert [r.belief for r in p.trace] == [r.belief for r in q.trace]
            assert len({c.speaker for c in p.chorus} | {p.speaker}) == 1 + len(p.chorus)
    assert max(sizes) == 3 and 2 in sizes


def test_stages_err_the_same_way_under_the_bayesian_model() -> None:
    # start_strength 1 and GUESS 0: every child with an error holds it fully (P(wrong) = 1)
    sure = BayesianModel(BayesParams(guess=0.0))
    cfg = replace(CFG, start_strength=1.0)
    state = new_session(cfg, seats(), 5, sure)
    by_stage = {c.stage: c.name for c in state.children if c.error}
    p = Problem("sub", 52, 29)
    out, _ = plan_turn(state, cfg, "pose_problem", addressed=by_stage["output"], posed=p)
    assert out.answer == 23 and out.written == 32 and out.correct is False
    test_, _ = plan_turn(state, cfg, "pose_problem", addressed=by_stage["input-test"], posed=p)
    # the other operation (52 + 29); the digit swap 25 - 29 is below zero, so not an option
    assert test_.answer == 81 and test_.answer in test_.allowed_numbers
    teach_cfg = replace(cfg)
    teach_seats = tuple(replace(s, stage="input-teaching") if s.error else s for s in seats())
    st = new_session(teach_cfg, teach_seats, 5, sure)
    lost, _ = plan_turn(st, teach_cfg, "pose_problem", addressed=st.children[1].name, posed=p)
    assert lost.answer is None and lost.intent == "confused" and not lost.allowed_numbers
    for seed in range(1, 21):
        plans, _ = drill("ask_explain", seed)
        for plan in plans:
            for q in (plan, *plan.chorus):
                for n in (q.answer, q.written):
                    assert n is None or n in q.allowed_numbers


def test_every_wrong_answer_of_a_core_child_comes_from_her_bug_function() -> None:
    wrongs = 0
    for seed in range(1, 41):
        plans, state = drill("tell_rule", seed, stages=False)
        by_name = {c.name: c for c in state.children}
        for plan in plans:
            for q in (plan, *plan.chorus):
                if q.answer is not None and q.correct is False and q.problem is not None:
                    err = by_name[q.speaker].error  # type: ignore[index]
                    assert err is not None and q.answer in wrong_answers(err, q.problem)
                    wrongs += 1
    assert wrongs > 100


@pytest.mark.parametrize("model", [LEGACY, BAYES], ids=["legacy", "bayesian"])
def test_a_session_ends_only_when_every_child_with_the_error_is_right_twice_or_at_40(
    model: object,
) -> None:
    reasons = set()
    for seed in range(1, 31):
        for move in ("show_bundles", "repeat_rule_louder"):
            plans, state = drill(move, seed, model)
            assert state.finished
            erring = [c for c in state.children if c.error]
            if state.finished_reason == "all_correct":
                assert all(c.streak >= CFG.finish_streak for c in erring) and state.turn <= 40
            else:
                assert state.finished_reason == "turn_cap" and state.turn == CFG.max_turns
            reasons.add(state.finished_reason)
    assert reasons == {"all_correct", "turn_cap"}


@pytest.mark.parametrize("model", [LEGACY, BAYES], ids=["legacy", "bayesian"])
def test_the_correct_child_is_always_right(model: object) -> None:
    for seed in range(1, 31):
        plans, state = drill("tell_rule", seed, model)
        correct_name = next(c.name for c in state.children if c.error is None)
        assert next(c for c in state.children if c.error is None).strength == 0.0
        for plan in plans:
            for q in (plan, *plan.chorus):
                if q.speaker == correct_name and q.answer is not None:
                    assert q.correct is True


def test_the_turn_generator_makes_the_same_draws_under_both_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No new draws: per turn, the session generator's random() (who speaks, and the right-or-wrong
    test of each answer) is called as often as in legacy. Picking which wrong answer uses
    getrandbits, and happens only after a wrong draw, in both models; it is not counted here."""
    import engine.simulator as sim

    counts: dict[str, int] = {}

    class Counting(random.Random):
        def __init__(self, x: object = None) -> None:
            super().__init__(x)  # type: ignore[arg-type]
            self.key = str(x)

        def random(self) -> float:
            counts[self.key] = counts.get(self.key, 0) + 1
            return super().random()

        def getrandbits(self, k: int) -> int:  # keeps choice() on getrandbits, as in Random
            return super().getrandbits(k)

    monkeypatch.setattr(sim.random, "Random", Counting)
    seen = {}
    for name, model in (("legacy", LEGACY), ("bayesian", BAYES)):
        counts.clear()
        run(start(5, model, stages=False), SCRIPT)
        # The per-turn generator ("seed:turn"). The prior generators ("bayes-...") are the model's;
        # the chorus generator's sequence already depends on right-or-wrong outcomes under legacy (a
        # wrong answer picks its number from it before the next child is picked), so it is not equal
        # draw for draw when outcomes differ, in either model.
        seen[name] = {
            k: v
            for k, v in counts.items()
            if not k.startswith("bayes-") and not k.endswith(":chorus")
        }
    assert seen["legacy"] == seen["bayesian"] and seen["legacy"]


# --- calibration


def test_calibration_the_derived_p_correct_matches_the_drawn_answers() -> None:
    """Many sessions with random moves. For every answer drawn for a core child on a problem her
    error applies to, bucket the model's P(correct) = 1 - strength; the share right in each bucket
    with at least 200 draws must be within 0.05 of the bucket's mean P(correct)."""
    pick = random.Random("calibration")
    moves = [m for m in CFG.moves if m != "scold"]
    buckets: dict[int, list[tuple[float, bool]]] = {}
    for seed in range(1, 401):
        state = start(seed, stages=False)
        problems: dict[int, Problem | None] = {}
        while not state.finished:
            move = pick.choice(moves)
            seat = pick.choice([None, 1, 2, 3, 4])
            to = state.children[seat].name if seat is not None else None
            plan, state = plan_turn(state, CFG, move, addressed=to, posed=None)
            for row in plan.trace:
                kid = next(c for c in state.children if c.name == row.name)
                if row.outcome is None or row.stage != "core" or plan.problem is None:
                    continue
                if not wrong_answers(kid.error, plan.problem):  # type: ignore[arg-type]
                    continue
                p = 1 - row.strength
                buckets.setdefault(min(4, int(p * 5)), []).append((p, row.outcome))
        problems.clear()
    checked = 0
    for b, rows in sorted(buckets.items()):
        if len(rows) < 200:
            continue
        mean_p = sum(p for p, _ in rows) / len(rows)
        share = sum(ok for _, ok in rows) / len(rows)
        assert abs(share - mean_p) <= 0.05, (b, len(rows), mean_p, share)
        checked += 1
    assert checked >= 3


# --- the switch, serialising, the trace stays out of the API


def test_the_switch_unset_or_legacy_is_legacy_and_bayesian_is_bayesian() -> None:
    assert model_from_env({}) == LEGACY
    assert model_from_env({"SIMULATOR_MODEL": ""}) == LEGACY
    assert model_from_env({"SIMULATOR_MODEL": "legacy"}) == LEGACY
    assert isinstance(model_from_env({"SIMULATOR_MODEL": "bayesian"}), BayesianModel)
    m = model_from_env(
        {"SIMULATOR_MODEL": "bayesian", "BAYES_LEARN_CAP": "0.5", "BAYES_SLIP": "0.1"}
    )
    assert isinstance(m, BayesianModel) and m.params.learn_cap == 0.5 and m.params.slip == 0.1


@pytest.mark.parametrize(
    "env",
    [
        {"SIMULATOR_MODEL": "bayes"},
        {"SIMULATOR_MODEL": "Bayesian"},
        {"SIMULATOR_MODEL": "rules"},
        {"SIMULATOR_MODEL": "bayesian", "BAYES_GUESS": "lots"},
        {"SIMULATOR_MODEL": "bayesian", "BAYES_LEARN_CAP": "2"},
    ],
)
def test_a_bad_setting_is_refused_with_a_clear_message(env: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="SIMULATOR_MODEL|BAYES_"):
        model_from_env(env)


def test_a_bad_setting_stops_the_api_at_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.api.main import create_app

    monkeypatch.setenv("SIMULATOR_MODEL", "bayes")
    with pytest.raises(ValueError, match="SIMULATOR_MODEL must be legacy or bayesian"):
        create_app()
    monkeypatch.setenv("SIMULATOR_MODEL", "bayesian")
    create_app()


def test_a_session_keeps_its_model_after_the_environment_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services.practice.session import start_session

    monkeypatch.setenv("SIMULATOR_MODEL", "bayesian")
    s = start_session("SUB-SFL", "en", seed=5)
    monkeypatch.setenv("SIMULATOR_MODEL", "legacy")
    state = s.state
    for move, seat in SCRIPT[:4]:
        to = state.children[seat].name if seat is not None else None
        plan, state = plan_turn(state, s.loaded.config, move, addressed=to, posed=None)
        assert isinstance(state.model, BayesianModel) and plan.trace
    monkeypatch.delenv("SIMULATOR_MODEL")
    assert start_session("SUB-SFL", "en", seed=5).state.model == LEGACY
    assert isinstance(state.model, BayesianModel)


@pytest.mark.parametrize("model", [LEGACY, BAYES], ids=["legacy", "bayesian"])
def test_the_session_state_is_plain_data_and_round_trips(model: object) -> None:
    _, state = run(start(5, model), SCRIPT[:6])
    data = json.loads(json.dumps(state_to_dict(state)))
    assert state_from_dict(data) == state


def test_legacy_turns_carry_no_trace_and_bayesian_trace_is_not_in_the_api_response() -> None:
    from services.practice.session import _engine_layer

    legacy_plans, _ = run(start(5, LEGACY), SCRIPT)
    assert all(p.trace == () for p in legacy_plans)
    plans, _ = run(start(5), SCRIPT)
    assert all(p.trace for p in plans)
    layer = json.dumps(_engine_layer(plans[2]))
    assert "belief" not in layer and "trace" not in layer and "responsiveness" not in layer


def test_derived_strength_formula() -> None:
    p = BAYES.params
    for b in (0.0, 0.1, 0.5, 1.0):
        assert math.isclose(
            BAYES.derived_strength(b), (1 - b) * (1 - p.guess) + b * p.slip, abs_tol=1e-9
        )
    assert isinstance(LegacyModel(), LegacyModel) and ErrorCode.SUB_SFL is CFG.error
