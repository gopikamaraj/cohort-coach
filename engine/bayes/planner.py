"""The 32-state Bayesian Practice Class planner (docs/BAYESIAN-MODEL.md section 5).

It returns the legacy contract (engine.simulator.TurnPlan and children as engine.simulator.Child,
with the same field names and types), so the rest of the engine (session, faces, templates, call 1,
call 3, the API) reads it unchanged. The class (names, error per seat, stages, shy child) comes from
the legacy fill_seats, so a seed gives the same class under both models.

Randomness, all from generators of this model's own (never the legacy ones):
  bayes:prior:{seed}:{seat}          one uniform for a child's starting (place_value, exchange)
  bayes:trans:{seed}:{turn}:{seat}   exactly four uniforms per erring child per turn (P, E, W, H)
  bayes:speak:{seed}:{turn}          who speaks when no child is named
  bayes:chorus:{seed}:{turn}         how many others speak, and who
  bayes:answer:{seed}:{turn}:{seat}  exactly two uniforms per answer (the kind, then the number)
The belief engine and the information-gain choice consume none.

Copied from engine/simulator.py rather than imported (private helpers): the mood rule (_mood), the
working said aloud (_steps_for), the chorus line (_chorus_plan), the allowed-number rule and the
finish rule (_finish). Imported read-only: Child, Problem, Step, TurnPlan, MoveEffect, NEUTRAL,
ScenarioConfig, Seat, valid_problem, reasoning_steps, correct_steps, doubt_steps (and wrong_answers
through engine.bayes.response).
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

import numpy as np

from engine.bayes import belief as bel
from engine.bayes.content import (
    NEUTRAL_MOVE,
    MoveSpec,
    Params,
    check_tags,
    load_families,
    load_moves,
    load_note_tags,
    params_from_dict,
)
from engine.bayes.dynamics import (
    TurnContext,
    attention_step,
    attention_target,
    overload,
    priming_delta,
    sample_next,
    transition_matrix,
)
from engine.bayes.response import (
    KINDS,
    Outcome,
    Roles,
    misheard_options,
    needs_step,
    observed,
    outcomes,
    output_form_available,
    p_correct,
    response_row,
    rev,
    wrong_numbers,
)
from engine.bayes.state import StateMap, declaration, index
from engine.model import ErrorCode
from engine.simulator import (
    NEUTRAL,
    Child,
    MoveEffect,
    Problem,
    ScenarioConfig,
    Seat,
    Step,
    TurnPlan,
    correct_steps,
    doubt_steps,
    reasoning_steps,
    valid_problem,
)

MODEL = "bayesian"
ANSWERING = frozenset({"answer", "explain", "work_aloud", "doubt"})


@dataclass(frozen=True)
class SeatModel:
    """The model's own bookkeeping for one seat. `true` and `belief` are None for the correct
    child, who is outside the model and always right."""

    true: StateMap | None
    belief: tuple[float, ...] | None
    since_direct: int = 0  # turns since she was last reached directly
    heavy: tuple[bool, ...] = ()  # heavy moves that reached her directly, newest last
    prime_r: float = 0.0
    prime_age: int = -1  # -1: not primed
    c: int = 0  # correct answers this session on items that need the step
    last_code: str | None = None  # the error code behind her last answer


@dataclass(frozen=True)
class BayesState:
    """A session under the 32-state model. Same reading fields as engine.simulator.SessionState
    (seed, turn, children, problem, next_problem, finished, finished_reason)."""

    seed: int
    turn: int
    children: tuple[Child, ...]
    seats: tuple[SeatModel, ...]
    params: Params
    roles: Roles
    note_tags: tuple[str, ...] = ()
    problem: Problem | None = None
    next_problem: int = 0
    finished: bool = False
    finished_reason: str | None = None
    model: str = MODEL


def roles_for(error: ErrorCode) -> Roles:
    fam = load_families().of(error)
    return Roles(
        target=error,
        sibling=fam.siblings.get(error),
        family=fam.name,
        family_codes=fam.codes,
        shift=tuple(fam.shift.items()),
    )


def first_step_item(config: ScenarioConfig, roles: Roles) -> Problem:
    """The first scenario item that needs the step (for the strength shown before any problem)."""
    for item in config.problems:
        if needs_step(roles, item):
            return item
    return config.problems[0]


def derived_strength(
    seat: SeatModel, child: Child, item: Problem, roles: Roles, p: Params, delta: float
) -> float:
    """strength = 1 - P(correct | true state, item, priming) after the stage channel."""
    if seat.true is None or child.error is None:
        return 0.0
    return round(1.0 - p_correct(index(seat.true), item, roles, child.stage, p, delta), 12)


def new_session(
    config: ScenarioConfig,
    seats: Sequence[Seat],
    seed: int,
    params: Params,
    note_tags: Sequence[str] = (),
) -> BayesState:
    """A new class. Note tags (the closed list in content/bayes/note_tags.v1.yaml) reweight the
    starting (place_value, exchange) draw and the observer's start belief."""
    tags = check_tags(list(note_tags))
    roles = roles_for(config.error)
    factors = load_note_tags()
    pe = bel.tagged_pe(params, tags, factors, roles.family)
    item = first_step_item(config, roles)
    children: list[Child] = []
    models: list[SeatModel] = []
    for i, s in enumerate(seats):
        child = Child(
            name=s.name,
            error=s.error,
            shy=s.shy,
            strength=0.0,
            engagement=config.start_engagement,
            stage=s.stage,
        )
        if s.error is None:
            models.append(SeatModel(None, None))
            children.append(child)
            continue
        diagnosed = roles.role(s.error)
        habit = "no_method" if s.stage == "input-teaching" else diagnosed
        pv, e = bel.draw_pe(pe, random.Random(f"bayes:prior:{seed}:{i}").random())
        true: StateMap = {"place_value": pv, "exchange": e, "written_step": 0, "habit": habit}
        b = bel.observer_start(diagnosed, roles, params, tags, factors)
        seat = SeatModel(true, tuple(float(x) for x in b))
        models.append(seat)
        children.append(
            replace(child, strength=derived_strength(seat, child, item, roles, params, 0.0))
        )
    return BayesState(
        seed=seed,
        turn=0,
        children=tuple(children),
        seats=tuple(models),
        params=params,
        roles=roles,
        note_tags=tags,
    )


# --- copies of legacy helpers (engine/simulator.py), unchanged in behaviour


def mood(child: Child, doubtful: bool = False, small: bool = False) -> str:
    """Copy of simulator._mood, on attention (the engagement field)."""
    if small:
        return "small"
    if doubtful:
        return "doubtful"
    if child.engagement < 0.35:
        return "flat"
    return "bright" if child.engagement > 0.75 else "calm"


def steps_for(
    code: ErrorCode | None, stage: str, p: Problem, answer: int | None
) -> tuple[Step, ...]:
    """Copy of simulator._steps_for, with the error code that produced the answer (a child whose
    habit shifted errs, and explains, by her new code)."""
    if answer is None:
        return ()
    if answer == p.correct:
        return correct_steps(p)
    if stage == "core" and code is not None:
        return reasoning_steps(code, p, answer)
    return ()


def finish(state: BayesState, config: ScenarioConfig) -> BayesState:
    """Copy of simulator._finish."""
    erring = [c for c in state.children if c.error]
    if erring and all(c.streak >= config.finish_streak for c in erring):
        return replace(state, finished=True, finished_reason="all_correct")
    if state.turn >= config.max_turns:
        return replace(state, finished=True, finished_reason="turn_cap")
    return state


# --- one turn


@dataclass
class _Turn:
    """Working state for one turn (not stored)."""

    state: BayesState
    config: ScenarioConfig
    turn: int
    children: list[Child]
    seats: list[SeatModel]
    beliefs: list[np.ndarray | None]
    deltas: list[float]
    drawn: dict[int, Outcome]
    predicted: dict[int, float]  # the observer's P(correct) just before each fresh answer


def _answer(
    t: _Turn, i: int, problem: Problem
) -> tuple[int | None, bool, ErrorCode | None, int | None]:
    """A fresh answer: the kind from the response table (with priming), the stage form, the
    number from the bug function. Two uniforms, always. Then the observer's update."""
    child, seat = t.children[i], t.seats[i]
    if child.error is None or seat.true is None:
        return problem.correct, True, None, problem.correct
    p, roles = t.state.params, t.state.roles
    rng = random.Random(f"bayes:answer:{t.state.seed}:{t.turn}:{i}")
    u_kind, u_pick = rng.random(), rng.random()
    row = response_row(index(seat.true), problem, roles, p, t.deltas[i])
    acc, kind = 0.0, KINDS[-1]
    for k, prob in zip(KINDS, row, strict=True):
        acc += float(prob)
        if u_kind < acc:
            kind = k
            break
    result: tuple[int | None, bool, ErrorCode | None, int | None]
    if kind == "correct":
        result = (problem.correct, True, None, problem.correct)
    elif child.stage == "output":
        result = (
            (problem.correct, False, child.error, rev(problem.correct))
            if output_form_available(problem)
            else (problem.correct, True, None, problem.correct)
        )
    elif child.stage == "input-test":
        opts = misheard_options(problem)
        if opts:
            n = opts[min(int(u_pick * len(opts)), len(opts) - 1)]
            result = (n, False, child.error, n)
        else:
            result = (problem.correct, True, None, problem.correct)
    elif kind in ("bug_target", "bug_sibling"):
        code = roles.target if kind == "bug_target" else roles.sibling
        wrong = wrong_numbers(code, problem)
        n = wrong[min(int(u_pick * len(wrong)), len(wrong) - 1)]
        result = (n, False, code, n)
    else:  # no_answer: no method yet, she says no number
        result = (None, False, child.error, None)
    answer, correct, code, _ = result
    key = observed(child.stage, answer, correct)
    t.drawn[i] = key
    b = t.beliefs[i]
    if b is not None:
        outs = outcomes(problem, roles, child.stage, p, t.deltas[i])
        like = dict(outs)
        right = ("correct",) if child.stage in ("output", "input-test") else ("n", problem.correct)
        t.predicted[i] = bel.predictive_correct(b, like[right])
        t.beliefs[i] = bel.update(b, like[key])
    t.seats[i] = replace(
        seat,
        c=seat.c + (1 if correct and needs_step(roles, problem) else 0),
        last_code=code.value if code is not None else None,
    )
    return result


def _choose_problem(t: _Turn, addressed: str | None) -> tuple[Problem, list[dict[str, Any]]]:
    """The scenario item with the highest expected information gain, for the addressed child or
    summed over the erring children when the move is to the class or to no one. Ties go to the
    earliest item; the problem just used is not repeated unless it is the only one."""
    cfg, st = t.config, t.state
    names = [c.name for c in t.children]
    if addressed in names:
        who = [names.index(str(addressed))]
    else:
        who = list(range(len(t.children)))
    who = [i for i in who if t.beliefs[i] is not None]
    candidates = list(cfg.problems)
    if len(candidates) > 1 and st.problem is not None:
        candidates = [c for c in candidates if c != st.problem] or list(cfg.problems)
    ranking: list[dict[str, Any]] = []
    best: Problem | None = None
    best_score = -1.0
    for item in candidates:
        score = 0.0
        for i in who:
            b = t.beliefs[i]
            assert b is not None
            outs = outcomes(item, st.roles, t.children[i].stage, st.params, t.deltas[i])
            score += bel.eig(b, outs)
        ranking.append({"problem": [item.kind, item.a, item.b], "eig_bits": score})
        if score > best_score + 1e-12:
            best, best_score = item, score
    assert best is not None
    return best, ranking


def _chorus_line(
    t: _Turn, i: int, behaviour: str, problem: Problem | None, move_id: str
) -> TurnPlan | None:
    """Copy of simulator._chorus_plan, with this model's answers."""
    child = t.children[i]
    if behaviour in ANSWERING:
        if problem is None:
            return None
        fresh = child.last_answer is None
        if fresh:
            answer, correct, code, written = _answer(t, i, problem)
        else:
            answer, written = child.last_answer, child.last_written
            correct = answer == problem.correct and written == answer
            last = t.seats[i].last_code
            code = None if correct else (ErrorCode(last) if last else child.error)
        intent = "answer" if answer is not None else "confused"
        streak = (child.streak + 1 if correct else 0) if fresh else child.streak
        child = replace(child, last_answer=answer, last_written=written, streak=streak)
        t.children[i] = child
        numbers: set[int] = set()
        if answer is not None:
            numbers |= {problem.a, problem.b} if problem.kind != "dictation" else {problem.a}
            numbers.add(answer)
        if written is not None:
            numbers.add(written)
        return TurnPlan(
            turn=t.turn,
            move_id=move_id,
            behaviour=behaviour,
            speaker=child.name,
            intent=intent,
            problem=problem,
            answer=answer,
            correct=correct if answer is not None else None,
            error_code=code if answer is not None else None,
            steps=(),
            allowed_numbers=frozenset(numbers),
            mood=mood(child),
            written=written,
            stage=child.stage,
            spoken_correct=(answer == problem.correct) if answer is not None else None,
        )
    if behaviour in {"agree", "thanks", "confused"}:
        return TurnPlan(
            turn=t.turn,
            move_id=move_id,
            behaviour=behaviour,
            speaker=child.name,
            intent=behaviour,
            problem=problem,
            answer=None,
            correct=None,
            error_code=None,
            steps=(),
            allowed_numbers=frozenset(),
            mood=mood(child),
            stage=child.stage,
        )
    return None


def plan_turn(
    state: BayesState,
    config: ScenarioConfig,
    move_id: str,
    *,
    addressed: str | None,
    posed: Problem | None,
) -> tuple[TurnPlan, BayesState]:
    plan, nxt, _ = plan_turn_traced(state, config, move_id, addressed=addressed, posed=posed)
    return plan, nxt


def plan_turn_traced(
    state: BayesState,
    config: ScenarioConfig,
    move_id: str,
    *,
    addressed: str | None,
    posed: Problem | None,
) -> tuple[TurnPlan, BayesState, dict[str, Any]]:
    """One turn: the plan (legacy contract), the next state, and the debug trace (never in the API
    response)."""
    if state.finished:
        raise ValueError("the session is finished")
    neutral = move_id in NEUTRAL
    if neutral:
        effect = MoveEffect("confused", 0.0, 0.0, False)
        spec: MoveSpec = NEUTRAL_MOVE
    elif move_id in config.moves:
        effect = config.moves[move_id]
        spec = load_moves()[move_id]
    else:
        raise ValueError(f"unknown move {move_id!r}")
    p, roles = state.params, state.roles
    turn = state.turn + 1
    names = [c.name for c in state.children]
    named = addressed in names
    was_quiet = {c.name: c.quiet_turns > 0 for c in state.children}
    before = {c.name: c.strength for c in state.children}

    # 1-2. Reach, attention, overload, priming.
    reach: list[float] = []
    direct: list[bool] = []
    for c in state.children:
        if neutral:
            reach.append(0.0)
            direct.append(False)
        elif named:
            reach.append(1.0 if c.name == addressed else config.overhear)
            direct.append(c.name == addressed)
        else:
            reach.append(1.0)
            direct.append(True)
    children = list(state.children)
    seats = list(state.seats)
    deltas: list[float] = []
    ovs: list[float] = []
    for i, (c, seat) in enumerate(zip(children, seats, strict=True)):
        since = 0 if direct[i] else seat.since_direct + 1
        heavy = (*seat.heavy, direct[i] and spec.max_cov >= p.heavy_cov)[-p.ov_window :]
        ov = overload(sum(heavy), p)
        target = attention_target(
            config.start_engagement,
            effect.engagement,
            reach[i],
            direct[i],
            since >= p.neglect_after,
            ov,
            p,
        )
        a = attention_step(c.engagement, target, p)
        if spec.demo and reach[i] > 0:
            prime_r, age = reach[i], 0
        elif seat.prime_age >= 0 and seat.prime_age + 1 < p.prime_window:
            prime_r, age = seat.prime_r, seat.prime_age + 1
        else:
            prime_r, age = 0.0, -1
        deltas.append(priming_delta(prime_r, age, p))
        ovs.append(ov)
        seats[i] = replace(seat, since_direct=since, heavy=heavy, prime_r=prime_r, prime_age=age)
        children[i] = replace(
            c,
            engagement=a,
            quiet_turns=config.quiet_turns if (effect.quiet and direct[i]) else c.quiet_turns,
        )

    # 3. Transitions: the true state (transition generator) and the observer's predict step.
    beliefs: list[np.ndarray | None] = []
    trace_rows: list[dict[str, Any]] = []
    for i, seat in enumerate(seats):
        if seat.true is None or seat.belief is None:
            beliefs.append(None)
            continue
        ctx = TurnContext(spec, reach[i], children[i].engagement, ovs[i], seat.c)
        rng = random.Random(f"bayes:trans:{state.seed}:{turn}:{i}")
        u = [rng.random() for _ in range(4)]
        true_next, probs = sample_next(seat.true, ctx, roles, p, u)
        beliefs.append(bel.predict(np.asarray(seat.belief), transition_matrix(ctx, roles, p)))
        seats[i] = replace(seat, true=true_next)
        trace_rows.append({"seat": i, "reach": reach[i], "overload": ovs[i], **probs})

    t = _Turn(state, config, turn, children, seats, beliefs, deltas, {}, {})

    # 5. The problem: the posed one if valid; where legacy takes the scenario's next, the item with
    # the highest information gain. Reused otherwise.
    problem, next_problem = state.problem, state.next_problem
    ranking: list[dict[str, Any]] | None = None
    if effect.behaviour == "answer" and not neutral:
        if posed is not None and valid_problem(posed):
            problem = posed
        else:
            problem, ranking = _choose_problem(t, addressed)
            next_problem += 1
        t.children = [replace(c, last_answer=None) for c in t.children]
    elif effect.behaviour in ANSWERING and problem is None:
        problem, ranking = _choose_problem(t, addressed)
        next_problem += 1

    # 6. Who speaks. The shy child only when named; quiet children do not volunteer.
    speaker: Child | None = None
    if named:
        speaker = t.children[names.index(addressed)]  # type: ignore[arg-type]
    else:
        pool = [c for c in t.children if not c.shy and not was_quiet[c.name]]
        if pool:
            srng = random.Random(f"bayes:speak:{state.seed}:{turn}")
            speaker = srng.choices(pool, weights=[c.engagement + 0.05 for c in pool], k=1)[0]

    # 8. The speaker's answer (mirrors plan_turn in engine/simulator.py).
    intent = effect.behaviour
    answer: int | None = None
    correct: bool | None = None
    code: ErrorCode | None = None
    steps: tuple[Step, ...] = ()
    written: int | None = None
    doubtful = small = False
    if speaker is None:
        intent = "silent"
    elif was_quiet[speaker.name] and effect.behaviour != "quiet":
        intent = "quiet"
    elif effect.behaviour == "quiet":
        small = True
    elif intent in ANSWERING and problem is not None:
        idx = names.index(speaker.name)
        now = t.children[idx]
        if intent in ("answer", "work_aloud") or now.last_answer is None:
            answer, correct, code, written = _answer(t, idx, problem)
        else:
            answer, written = now.last_answer, now.last_written
            correct = answer == problem.correct and written == answer
            last = t.seats[idx].last_code
            code = None if correct else (ErrorCode(last) if last else now.error)
        if intent in ("work_aloud", "explain"):
            steps = steps_for(code, now.stage, problem, answer)
        elif intent == "doubt" and answer is not None:
            steps = doubt_steps(problem, answer)
            doubtful = not correct
        if answer is None:
            intent = "confused"
        streak = (
            (now.streak + 1 if correct else 0)
            if intent in {"answer", "work_aloud"}
            or (now.last_answer is None and intent in {"explain", "doubt"})
            else now.streak
        )
        t.children[idx] = replace(now, last_answer=answer, last_written=written, streak=streak)

    # 7. The chorus, from its own generator: the first speaker is the same with or without it.
    chorus: list[TurnPlan] = []
    if (
        speaker is not None
        and config.chorus_max > 1
        and effect.behaviour != "quiet"
        and intent not in {"silent", "quiet"}
    ):
        crng = random.Random(f"bayes:chorus:{state.seed}:{turn}")
        want = crng.randint(1, config.chorus_max) - 1
        pool = [
            c for c in t.children if c.name != speaker.name and not c.shy and not was_quiet[c.name]
        ]
        for _ in range(min(want, len(pool))):
            pick = crng.choices(pool, weights=[c.engagement + 0.05 for c in pool], k=1)[0]
            pool.remove(pick)
            sub = _chorus_line(t, names.index(pick.name), effect.behaviour, problem, move_id)
            if sub is not None:
                chorus.append(sub)

    # 9. Bookkeeping: quiet counters, strengths, the trace, the finish check.
    item = problem if problem is not None else first_step_item(config, roles)
    out_children: list[Child] = []
    for i, c in enumerate(t.children):
        if was_quiet[c.name]:
            c = replace(c, quiet_turns=max(0, c.quiet_turns - 1))
        b = t.beliefs[i]
        seat = t.seats[i]
        if b is not None:
            seat = replace(seat, belief=tuple(float(x) for x in b))
            t.seats[i] = seat
        c = replace(c, strength=derived_strength(seat, c, item, roles, p, t.deltas[i]))
        out_children.append(c)
    teaching = spec.max_cov > 0 or spec.conf > 0
    strength_before = {
        c.name: before[c.name]
        for i, c in enumerate(out_children)
        if c.error and teaching and reach[i] > 0
    }
    strength_after = {
        c.name: c.strength
        for i, c in enumerate(out_children)
        if c.error and teaching and reach[i] > 0
    }

    numbers: set[int] = set()
    if problem is not None and (answer is not None or steps):
        numbers |= {problem.a, problem.b} if problem.kind != "dictation" else {problem.a}
    if answer is not None:
        numbers.add(answer)
    if written is not None:
        numbers.add(written)
    for s in steps:
        numbers |= set(s.numbers)
    speaker_now = next((c for c in out_children if speaker and c.name == speaker.name), None)
    plan = TurnPlan(
        turn=turn,
        move_id=move_id,
        behaviour=effect.behaviour,
        speaker=speaker.name if speaker else None,
        intent=intent,
        problem=problem,
        answer=answer,
        correct=correct,
        error_code=code,
        steps=steps,
        allowed_numbers=frozenset(numbers),
        mood=mood(speaker_now, doubtful, small) if speaker_now else "calm",
        strength_before=strength_before,
        strength_after=strength_after,
        written=written,
        stage=speaker_now.stage if speaker_now else "core",
        spoken_correct=(answer == problem.correct) if (answer is not None and problem) else None,
        chorus=tuple(chorus),
    )
    nxt = replace(
        state,
        turn=turn,
        children=tuple(out_children),
        seats=tuple(t.seats),
        problem=problem,
        next_problem=next_problem,
    )
    nxt = finish(nxt, config)
    return plan, nxt, _trace(nxt, move_id, trace_rows, ranking, t)


def _trace(
    st: BayesState,
    move_id: str,
    rows: list[dict[str, Any]],
    ranking: list[dict[str, Any]] | None,
    t: _Turn,
) -> dict[str, Any]:
    """Debug only: true states, belief marginals, entropy, p_learn values, attention, overload,
    priming and the information-gain ranking. Never part of the API response."""
    by_seat = {r["seat"]: r for r in rows}
    children = []
    for i, (c, seat) in enumerate(zip(st.children, st.seats, strict=True)):
        if seat.true is None or seat.belief is None:
            continue
        b = np.asarray(seat.belief)
        habit = str(seat.true["habit"])
        code = st.roles.code(habit)  # type: ignore[arg-type]
        children.append(
            {
                "name": c.name,
                "seat_code": c.error.value if c.error else None,
                "stage": c.stage,
                "true": {**seat.true, "habit_code": code.value if code else None},
                "marginals": bel.marginals(b),
                "entropy_bits": bel.entropy_bits(b),
                "most_likely": bel.most_likely(b),
                "attention": c.engagement,
                "priming": t.deltas[i],
                "outcome": list(t.drawn[i]) if i in t.drawn else None,
                "predicted_correct": t.predicted.get(i),
                **{k: v for k, v in by_seat.get(i, {}).items() if k != "seat"},
            }
        )
    return {"turn": st.turn, "move": move_id, "eig_ranking": ranking, "children": children}


# --- plain data


def to_dict(state: BayesState) -> dict[str, Any]:
    """The session as plain data (JSON-ready): true states as maps, each belief as a list of 32
    floats with the axis declaration, and the counters."""
    return {
        "model": MODEL,
        "seed": state.seed,
        "turn": state.turn,
        "error": state.roles.target.value,
        "params": state.params.as_dict(),
        "note_tags": list(state.note_tags),
        "axes": declaration(),
        "children": [
            {
                "name": c.name,
                "error": c.error.value if c.error else None,
                "shy": c.shy,
                "strength": c.strength,
                "engagement": c.engagement,
                "streak": c.streak,
                "quiet_turns": c.quiet_turns,
                "last_answer": c.last_answer,
                "stage": c.stage,
                "last_written": c.last_written,
            }
            for c in state.children
        ],
        "seats": [
            {
                "true": dict(s.true) if s.true is not None else None,
                "belief": list(s.belief) if s.belief is not None else None,
                "since_direct": s.since_direct,
                "heavy": list(s.heavy),
                "prime_r": s.prime_r,
                "prime_age": s.prime_age,
                "c": s.c,
                "last_code": s.last_code,
            }
            for s in state.seats
        ],
        "problem": [state.problem.kind, state.problem.a, state.problem.b]
        if state.problem
        else None,
        "next_problem": state.next_problem,
        "finished": state.finished,
        "finished_reason": state.finished_reason,
    }


def from_dict(data: Mapping[str, Any]) -> BayesState:
    if data.get("model") != MODEL:
        raise ValueError("not a bayesian session")
    if data.get("axes") != declaration():
        raise ValueError("the belief axes do not match engine/bayes/state.py")
    pr = data.get("problem")
    return BayesState(
        seed=data["seed"],
        turn=data["turn"],
        children=tuple(
            Child(**{**c, "error": ErrorCode(c["error"]) if c["error"] else None})
            for c in data["children"]
        ),
        seats=tuple(
            SeatModel(
                true=dict(s["true"]) if s["true"] is not None else None,
                belief=tuple(s["belief"]) if s["belief"] is not None else None,
                since_direct=s["since_direct"],
                heavy=tuple(s["heavy"]),
                prime_r=s["prime_r"],
                prime_age=s["prime_age"],
                c=s["c"],
                last_code=s["last_code"],
            )
            for s in data["seats"]
        ),
        params=params_from_dict(data["params"]),
        roles=roles_for(ErrorCode(data["error"])),
        note_tags=tuple(data["note_tags"]),
        problem=Problem(pr[0], pr[1], pr[2]) if pr else None,
        next_problem=data["next_problem"],
        finished=data["finished"],
        finished_reason=data["finished_reason"],
    )
