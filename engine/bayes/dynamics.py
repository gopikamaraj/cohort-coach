"""How an erring child's hidden state changes in one turn, and attention, overload and priming
(docs/BAYESIAN-MODEL.md 5.5 to 5.8). Pure: the true state is sampled from four uniforms the caller
draws; the observer uses the transition matrix built by enumeration of the same rules.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from engine.bayes.content import MoveSpec, Params
from engine.bayes.response import Roles
from engine.bayes.state import (
    E_OF,
    H_OF,
    HABITS,
    N_STATES,
    P_OF,
    W_OF,
    Habit,
    StateMap,
    Vector,
    assemble,
)

_H = {h: i for i, h in enumerate(HABITS)}


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


@dataclass(frozen=True)
class TurnContext:
    """What one child's transition depends on this turn, all observable by the teacher's side.

    r: reach (1 direct, the scenario's overhear share for the rest of the room, 0 for a neutral
    move); a: attention used in the formulas (after this turn's filter step); ov: overload units;
    c: her correct answers so far this session on items that need the step."""

    move: MoveSpec
    r: float
    a: float
    ov: float
    c: int


def p_learn(cov: float, fit: float, ctx: TurnContext, p: Params) -> float:
    """sigmoid(beta0 + beta_cov cov r + beta_fit fit + beta_scaf scaf r + beta_att (a - 0.5)
    - beta_over ov) when cov r > 0, else 0."""
    if cov * ctx.r <= 0:
        return 0.0
    return sigmoid(
        p.beta0
        + p.beta_cov * cov * ctx.r
        + p.beta_fit * fit
        + p.beta_scaf * ctx.move.scaf * ctx.r
        + p.beta_att * (ctx.a - 0.5)
        - p.beta_over * ctx.ov
    )


def p_break(e: int, ctx: TurnContext, p: Params) -> float:
    """sigmoid(gamma0 + gamma_conf conf r + gamma_E E + gamma_att (a - 0.5)) when conf r > 0."""
    if ctx.move.conf * ctx.r <= 0:
        return 0.0
    return sigmoid(
        p.gamma0
        + p.gamma_conf * ctx.move.conf * ctx.r
        + p.gamma_E * e
        + p.gamma_att * (ctx.a - 0.5)
    )


def hazard(h0: float, c: int, p: Params) -> float:
    """Per-turn forgetting hazard h0 exp(-c / c0)."""
    return h0 * math.exp(-c / p.c0)


def fit_e(pv: int, p: Params) -> float:
    return 1.0 if pv == 1 else p.fit_E_noP


def fit_w(e: int, p: Params) -> float:
    return 1.0 if e == 1 else p.fit_W_noE


def habit_probs(state: StateMap, ctx: TurnContext, roles: Roles, p: Params) -> tuple[float, float]:
    """(p_break, p_shift) for a child holding the target or sibling habit, scaled so the two sum to
    at most 1; (0, 0) for none and no_method."""
    habit = str(state["habit"])
    if habit not in ("target", "sibling"):
        return 0.0, 0.0
    e, w = int(state["exchange"]), int(state["written_step"])
    pb = p_break(e, ctx, p)
    shifts = roles.shift_role(habit) is not None  # type: ignore[arg-type]
    ps = p.shift_rate * ctx.r if (ctx.move.rule_drill and e == 0 and w == 0 and shifts) else 0.0
    total = pb + ps
    if total > 1:
        pb, ps = pb / total, ps / total
    return pb, ps


def learn_probs(state: StateMap, ctx: TurnContext, p: Params) -> dict[str, float]:
    """For each concept: p_learn if it is 0 now, else the forgetting hazard."""
    pv, e, w = int(state["place_value"]), int(state["exchange"]), int(state["written_step"])
    m = ctx.move
    return {
        "place_value": p_learn(m.cov_P, 1.0, ctx, p) if pv == 0 else hazard(p.h0_P, ctx.c, p),
        "exchange": p_learn(m.cov_E, fit_e(pv, p), ctx, p) if e == 0 else hazard(p.h0_E, ctx.c, p),
        "written_step": (
            p_learn(m.cov_W, fit_w(e, p), ctx, p) if w == 0 else hazard(p.h0_W, ctx.c, p)
        ),
    }


def transition_matrix(ctx: TurnContext, roles: Roles, p: Params) -> Vector:
    """T[s, s'] for this turn, enumerated from the rules for every start state; rows sum to 1."""
    m = ctx.move
    h_p, h_e, h_w = hazard(p.h0_P, ctx.c, p), hazard(p.h0_E, ctx.c, p), hazard(p.h0_W, ctx.c, p)
    l_p = p_learn(m.cov_P, 1.0, ctx, p)
    l_e = np.array([p_learn(m.cov_E, fit_e(0, p), ctx, p), p_learn(m.cov_E, fit_e(1, p), ctx, p)])
    l_w = np.array([p_learn(m.cov_W, fit_w(0, p), ctx, p), p_learn(m.cov_W, fit_w(1, p), ctx, p)])
    p1 = np.where(P_OF == 0, l_p, 1 - h_p)
    e1 = np.where(E_OF == 0, l_e[P_OF], 1 - h_e)
    w1 = np.where(W_OF == 0, l_w[E_OF], 1 - h_w)
    pp = np.stack([1 - p1, p1], axis=1)
    pe = np.stack([1 - e1, e1], axis=1)
    pwh = np.zeros((N_STATES, 2, len(HABITS)))
    pb_by_e = np.array([p_break(0, ctx, p), p_break(1, ctx, p)])
    for hname in HABITS:
        rows = H_OF == _H[hname]
        hi = _H[hname]
        for w_next in (0, 1):
            pw = np.where(rows, w1 if w_next == 1 else 1 - w1, 0.0)
            if hname in ("target", "sibling"):
                to = roles.shift_role(hname)
                pb = pb_by_e[E_OF]
                drill = m.rule_drill and to is not None
                ps = np.where(drill & (E_OF == 0) & (W_OF == 0), p.shift_rate * ctx.r, 0.0)
                total = pb + ps
                scale = np.where(total > 1, 1 / np.maximum(total, 1e-300), 1.0)
                pb, ps = pb * scale, ps * scale
                pwh[:, w_next, _H["none"]] += pw * pb
                if to is not None:
                    pwh[:, w_next, _H[to]] += pw * ps
                pwh[:, w_next, hi] += pw * (1 - pb - ps)
            elif hname == "no_method" and w_next == 1:
                # the written step learned this turn ends "no method"; already known keeps it
                pwh[:, 1, _H["none"]] += np.where(W_OF == 0, pw, 0.0)
                pwh[:, 1, hi] += np.where(W_OF == 1, pw, 0.0)
            else:
                pwh[:, w_next, hi] += pw
    return assemble([(("place_value",), pp), (("exchange",), pe), (("written_step", "habit"), pwh)])


def sample_next(
    state: StateMap, ctx: TurnContext, roles: Roles, p: Params, u: Sequence[float]
) -> tuple[StateMap, dict[str, float]]:
    """The next true state from exactly four uniforms (place_value, exchange, written_step, habit),
    and the probabilities used (for the debug trace)."""
    if len(u) != 4:
        raise ValueError("exactly four uniforms per child per turn")
    q = learn_probs(state, ctx, p)
    nxt: StateMap = dict(state)
    for axis, ui in zip(("place_value", "exchange", "written_step"), u[:3], strict=True):
        if int(state[axis]) == 0:
            nxt[axis] = 1 if ui < q[axis] else 0  # learned
        else:
            nxt[axis] = 0 if ui < q[axis] else 1  # forgotten
    pb, ps = habit_probs(state, ctx, roles, p)
    h = str(state["habit"])
    if h in ("target", "sibling"):
        to: Habit | None = roles.shift_role(h)  # type: ignore[arg-type]
        if u[3] < pb:
            nxt["habit"] = "none"
        elif to is not None and u[3] < pb + ps:
            nxt["habit"] = to
    elif h == "no_method" and int(state["written_step"]) == 0 and int(nxt["written_step"]) == 1:
        nxt["habit"] = "none"
    return nxt, {**{f"p_{k}": v for k, v in q.items()}, "p_break": pb, "p_shift": ps}


# --- attention, overload, priming


def alpha(p: Params) -> float:
    return 1 - math.exp(-1 / p.tau)


def attention_target(
    base: float, eng: float, r: float, direct: bool, neglected: bool, ov: float, p: Params
) -> float:
    """clamp(base + K_push eng r + addressed_bonus [direct] - neglect [neglected]
    - overload_drag ov, 0, 1)."""
    t = (
        base
        + p.K_push * eng * r
        + (p.addressed_bonus if direct else 0.0)
        - (p.neglect if neglected else 0.0)
        - p.overload_drag * ov
    )
    return min(1.0, max(0.0, t))


def attention_step(a: float, target: float, p: Params) -> float:
    """a_(t+1) = a_t + alpha (target_t - a_t), alpha = 1 - exp(-1 / tau)."""
    return a + alpha(p) * (target - a)


def overload(n_heavy: int, p: Params) -> float:
    """ov = max(0, n_heavy - ov_free)."""
    return float(max(0, n_heavy - p.ov_free))


def priming_delta(prime_r: float, age: int, p: Params) -> float:
    """delta0 r rho^age while 0 <= age < prime_window, else 0 (age -1 means not primed)."""
    if age < 0 or age >= p.prime_window or prime_r <= 0:
        return 0.0
    return float(p.delta0 * prime_r * p.rho**age)
