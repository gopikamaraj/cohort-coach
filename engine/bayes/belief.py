"""The belief engine (observer), soft evidence and expected information gain (docs/BAYESIAN-MODEL.md
section 6). It never reads a child's true state and consumes no randomness.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

import numpy as np

from engine.bayes.content import Factor, Params
from engine.bayes.response import Outcome, Roles
from engine.bayes.state import (
    AXES,
    HABITS,
    N_STATES,
    StateMap,
    Vector,
    from_index,
    mask,
    pe_cells,
)


def pe_weights(p: Params) -> dict[tuple[int, int], float]:
    """The generative prior over (place_value, exchange)."""
    return {
        (0, 0): (1 - p.p_P0) * (1 - p.p_E0_P0),
        (0, 1): (1 - p.p_P0) * p.p_E0_P0,
        (1, 0): p.p_P0 * (1 - p.p_E0_P1),
        (1, 1): p.p_P0 * p.p_E0_P1,
    }


def _factor_applies(f: Factor, family: str) -> bool:
    return not f.families or family in f.families


def tagged_pe(
    p: Params, tags: Sequence[str], factors: Mapping[str, tuple[Factor, ...]], family: str
) -> dict[tuple[int, int], float]:
    """The (place_value, exchange) prior reweighted by the note tags (virtual evidence on those two
    variables only), renormalised. No tags gives exactly the plain prior."""
    w = pe_weights(p)
    if not tags:
        return w
    for tag in tags:
        for f in factors[tag]:
            if not _factor_applies(f, family) or f.variable not in ("place_value", "exchange"):
                continue
            for cell in w:
                v = cell[0] if f.variable == "place_value" else cell[1]
                if v == f.value:
                    w[cell] *= f.ratio
    total = sum(w.values())
    return {k: v / total for k, v in w.items()}


def draw_pe(weights: Mapping[tuple[int, int], float], u: float) -> tuple[int, int]:
    """One uniform over the four cells in row-major order."""
    acc = 0.0
    cells = pe_cells()
    for cell in cells:
        acc += weights[cell]
        if u < acc:
            return cell
    return cells[-1]


def apply_tags(
    b: Vector, tags: Sequence[str], factors: Mapping[str, tuple[Factor, ...]], family: str
) -> Vector:
    """Multiply each state's weight by every applicable tag factor, then renormalise."""
    out = np.asarray(b, dtype=np.float64).copy()
    for tag in tags:
        for f in factors[tag]:
            if _factor_applies(f, family):
                out[mask(**{f.variable: f.value})] *= f.ratio
    return out / out.sum()


def observer_start(
    seat_role: str,
    roles: Roles,
    p: Params,
    tags: Sequence[str] = (),
    factors: Mapping[str, tuple[Factor, ...]] | None = None,
) -> Vector:
    """The observer's starting belief for one erring child: the plain generative (place_value,
    exchange) prior; r_diag on the diagnosed habit and the rest shared equally over the other
    habit values the family allows; written_step 0 with obs_W0; then the note tags, applied to
    every variable they name."""
    allowed = ["none", "target", "no_method"] + (["sibling"] if roles.sibling is not None else [])
    others = [h for h in allowed if h != seat_role]
    habit_w: dict[str, float] = {h: 0.0 for h in HABITS}
    habit_w[seat_role] = p.r_diag
    for h in others:
        habit_w[h] = (1 - p.r_diag) / len(others)
    pe = pe_weights(p)
    b = np.zeros(N_STATES)
    for i in range(N_STATES):
        s = from_index(i)
        pv, e, w = int(s["place_value"]), int(s["exchange"]), int(s["written_step"])
        pw = p.obs_W0 if w == 0 else 1 - p.obs_W0
        b[i] = pe[(pv, e)] * pw * habit_w[str(s["habit"])]
    b = b / b.sum()
    if tags:
        if factors is None:
            raise ValueError("note tags need their factors")
        b = apply_tags(b, tags, factors, roles.family)
    return b


def predict(b: Vector, t: Vector) -> Vector:
    """b <- b T."""
    out: Vector = np.asarray(b, dtype=np.float64) @ t
    return out


def update(b: Vector, likelihood: Vector) -> Vector:
    """b <- normalise(b * L). An outcome no state can produce leaves the belief as it was."""
    post = np.asarray(b, dtype=np.float64) * likelihood
    total = post.sum()
    if total <= 0:
        return np.asarray(b, dtype=np.float64).copy()
    out: Vector = post / total
    return out


def entropy_bits(b: Vector) -> float:
    q = np.asarray(b, dtype=np.float64)
    q = q[q > 0]
    return float(-(q * np.log2(q)).sum())


def marginals(b: Vector) -> dict[str, float | dict[str, float]]:
    """P(place_value=1), P(exchange=1), P(written_step=1) and P(habit = each value)."""
    out: dict[str, float | dict[str, float]] = {}
    for axis in AXES:
        if axis == "habit":
            out["habit"] = {h: float(b[mask(habit=h)].sum()) for h in HABITS}
        else:
            out[axis] = float(b[mask(**{axis: 1})].sum())
    return out


def most_likely(b: Vector) -> StateMap:
    return from_index(int(np.argmax(b)))


def predictive_correct(b: Vector, p_correct_by_state: Vector) -> float:
    """The observer's P(correct) for an item: sum over states of b(s) P(correct | s)."""
    return float(np.dot(b, p_correct_by_state))


def eig(b: Vector, outs: Sequence[tuple[Outcome, Vector]]) -> float:
    """EIG = H(b) - sum_y P(y | b) H(b | y), in bits."""
    h0 = entropy_bits(b)
    expected = 0.0
    for _, like in outs:
        py = float(np.dot(b, like))
        if py <= 0:
            continue
        expected += py * entropy_bits(b * like / py)
    return max(0.0, h0 - expected) if math.isfinite(h0) else 0.0
