"""Independent oracle for the 32-state Bayesian child model.

Reimplements docs/BAYESIAN-MODEL.md sections 4 to 6 from the document, without importing
engine/bayes or engine/simulator: it reads the parameter, move and family YAML files itself and the
bug functions from engine/bugs.py. Then it checks the golden cases G1 to G7 and 1,000 random
(state, item, move, context) cases against engine/bayes: response rows, transition rows, attention,
forgetting, Bayes updates and expected information gain. Pass: maximum absolute difference <= 1e-9.

    python -m evals.runners.bayes_oracle            # writes evals/out/bayes/oracle.json
    python -m evals.runners.bayes_oracle --no-write

engine/bayes is imported only inside `compare`, never by the oracle's own formulas (a test checks
the module's top-level imports).
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import yaml

from engine.bugs import add_nocarry, pv_heard, pv_reverse, sub_nodec, sub_sfl

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "evals" / "out" / "bayes"
BAYES = ROOT / "content" / "bayes"
TOL = 1e-9

# --- the spec's declarations (section 4), written out again here

HABITS = ("none", "target", "sibling", "no_method")
KINDS = ("correct", "bug_target", "bug_sibling", "no_answer")
STATES: list[tuple[int, int, int, str]] = [
    (pv, e, w, h) for pv in (0, 1) for e in (0, 1) for w in (0, 1) for h in HABITS
]


def flat(pv: int, e: int, w: int, h: str) -> int:
    """((P*2 + E)*2 + W)*4 + H, habit order none, target, sibling, no_method."""
    return ((pv * 2 + e) * 2 + w) * 4 + HABITS.index(h)


Item = tuple[str, int, int]  # (kind, a, b); for a dictation b is 0

BUG_KIND = {
    "SUB-SFL": "sub",
    "SUB-NODEC": "sub",
    "ADD-NOCARRY": "add",
    "PV-HEARD": "dictation",
    "PV-REVERSE": "dictation",
}


def correct_of(item: Item) -> int:
    kind, a, b = item
    return a - b if kind == "sub" else a + b if kind == "add" else a


def wrong(code: str | None, item: Item) -> list[int]:
    """The bug's wrong answers on the item, sorted, the correct answer excluded."""
    if code is None or BUG_KIND[code] != item[0]:
        return []
    kind, a, b = item
    found: set[int] = {
        "SUB-SFL": lambda: sub_sfl(a, b),
        "SUB-NODEC": lambda: sub_nodec(a, b),
        "ADD-NOCARRY": lambda: add_nocarry(a, b),
        "PV-HEARD": lambda: pv_heard(a),
        "PV-REVERSE": lambda: pv_reverse(a),
    }[code]()
    return sorted(found - {correct_of(item)})


def load_params() -> dict[str, float]:
    raw = yaml.safe_load((BAYES / "params.v1.yaml").read_text(encoding="utf-8"))
    return {k: v["default"] for k, v in raw["params"].items()}


def load_moves() -> dict[str, dict[str, Any]]:
    raw = yaml.safe_load((BAYES / "moves.v1.yaml").read_text(encoding="utf-8"))
    out: dict[str, dict[str, Any]] = dict(raw["moves"])
    out["other"] = {"cov_P": 0, "cov_E": 0, "cov_W": 0, "scaf": 0, "conf": 0, "demo": False,
                    "rule_drill": False}  # fmt: skip
    return out


def load_families() -> dict[str, dict[str, Any]]:
    raw = yaml.safe_load((BAYES / "families.v1.yaml").read_text(encoding="utf-8"))
    fams: dict[str, dict[str, Any]] = raw["families"]
    return fams


class Roles:
    def __init__(self, target: str, families: Mapping[str, Mapping[str, Any]]) -> None:
        fam_name, fam = next((n, f) for n, f in families.items() if target in f["codes"])
        self.family = fam_name
        self.target = target
        self.sibling: str | None = (fam.get("siblings") or {}).get(target)
        self.codes: list[str] = list(fam["codes"])
        self.shift: dict[str, str] = dict(fam.get("shift") or {})

    def code(self, h: str) -> str | None:
        return self.target if h == "target" else self.sibling if h == "sibling" else None

    def role(self, code: str) -> str:
        return "target" if code == self.target else "sibling"


# --- 5.2 response table


def response(s: tuple[int, int, int, str], item: Item, roles: Roles, p: Mapping[str, float],
             delta: float) -> list[float]:  # fmt: skip
    pv, e, w, h = s
    needs = any(wrong(c, item) for c in roles.codes)
    if not needs:
        row = [p["c_nm_easy"], 0.0, 0.0, 1 - p["c_nm_easy"]] if h == "no_method" else [1, 0, 0, 0]
    else:
        g = p["g_PE"] if (pv == 1 and e == 1) else p["g0"]
        c = p["c_none_PE"] if (pv == 1 and e == 1) else p["c_none"]
        if w == 1:
            row = {
                "none": [1 - p["slip"], p["slip"], 0, 0],
                "target": [1 - p["slip"], p["slip"], 0, 0],
                "sibling": [1 - p["slip"], 0, p["slip"], 0],
                "no_method": [1 - p["slip"], 0, 0, p["slip"]],
            }[h]
        else:
            row = {
                "target": [g, 1 - g, 0, 0],
                "sibling": [g, 0, 1 - g, 0],
                "none": [c, 0, 0, 1 - c],
                "no_method": [p["g_nm"], 0, 0, 1 - p["g_nm"]],
            }[h]
    row = [float(x) for x in row]
    if not wrong(roles.target, item):
        row[0] += row[1]
        row[1] = 0.0
    if not wrong(roles.sibling, item):
        row[0] += row[2]
        row[2] = 0.0
    if delta:
        right = row[0]
        row = [x * (1 - delta) for x in row]
        row[0] = right + delta * (1 - right)
    return row


def rev(n: int) -> int:
    return int(str(n)[::-1])


def form_exists(stage: str, item: Item) -> bool:
    kind, a, b = item
    corr = correct_of(item)
    if stage == "output":
        return rev(corr) != corr and corr % 10 != 0
    if stage == "input-test":
        if kind == "dictation":
            s = str(a)
            for i, ch in enumerate(s):
                for d in (-1, 1):
                    t = int(ch) + d
                    if 0 <= t <= 9 and not (i == 0 and t == 0):
                        return True
            return False
        other = abs(a - b) if kind == "add" else a + b
        swapped = (rev(a) + b) if kind == "add" else rev(a) - b
        return any(x >= 0 and x != corr for x in (other, swapped))
    return True


def outcome_likelihoods(item: Item, roles: Roles, stage: str, p: Mapping[str, float],
                        delta: float) -> dict[tuple[Any, ...], list[float]]:  # fmt: skip
    """6.1: L(y | s) for each observable outcome y, over the 32 states in flat order."""
    rows = [response(s, item, roles, p, delta) for s in STATES]
    if stage in ("output", "input-test"):
        if not form_exists(stage, item):
            return {("correct",): [1.0] * 32}
        return {("correct",): [r[0] for r in rows], ("form",): [1 - r[0] for r in rows]}
    out: dict[tuple[Any, ...], list[float]] = {("n", correct_of(item)): [r[0] for r in rows]}
    for k, code in ((1, roles.target), (2, roles.sibling)):
        ws = wrong(code, item)
        for n in ws:
            cur = out.setdefault(("n", n), [0.0] * 32)
            out[("n", n)] = [cur[i] + rows[i][k] / len(ws) for i in range(32)]
    out[("none",)] = [r[3] for r in rows]
    return out


# --- 5.5 transitions


def sig(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def p_learn(cov: float, fit: float, m: Mapping[str, Any], r: float, a: float, ov: float,
            p: Mapping[str, float]) -> float:  # fmt: skip
    if cov * r <= 0:
        return 0.0
    return sig(p["beta0"] + p["beta_cov"] * cov * r + p["beta_fit"] * fit
               + p["beta_scaf"] * m["scaf"] * r + p["beta_att"] * (a - 0.5)
               - p["beta_over"] * ov)  # fmt: skip


def hazard(h0: float, c: int, p: Mapping[str, float]) -> float:
    return h0 * math.exp(-c / p["c0"])


def transition_row(
    s: tuple[int, int, int, str],
    m: Mapping[str, Any],
    r: float,
    a: float,
    ov: float,
    c: int,
    roles: Roles,
    p: Mapping[str, float],
) -> list[float]:
    pv, e, w, h = s
    # P(next value = 1) per concept
    q_p = p_learn(m["cov_P"], 1.0, m, r, a, ov, p) if pv == 0 else 1 - hazard(p["h0_P"], c, p)
    fit_e = 1.0 if pv == 1 else p["fit_E_noP"]
    q_e = p_learn(m["cov_E"], fit_e, m, r, a, ov, p) if e == 0 else 1 - hazard(p["h0_E"], c, p)
    fit_w = 1.0 if e == 1 else p["fit_W_noE"]
    q_w = p_learn(m["cov_W"], fit_w, m, r, a, ov, p) if w == 0 else 1 - hazard(p["h0_W"], c, p)
    pb = ps = 0.0
    shift_to: str | None = None
    if h in ("target", "sibling"):
        if m["conf"] * r > 0:
            pb = sig(p["gamma0"] + p["gamma_conf"] * m["conf"] * r + p["gamma_E"] * e
                     + p["gamma_att"] * (a - 0.5))  # fmt: skip
        code = roles.code(h)
        if code in roles.shift:
            shift_to = roles.role(roles.shift[code])
        if m["rule_drill"] and e == 0 and w == 0 and shift_to is not None:
            ps = p["shift_rate"] * r
        if pb + ps > 1:
            pb, ps = pb / (pb + ps), ps / (pb + ps)
    row = [0.0] * 32
    for pv2 in (0, 1):
        f_p = q_p if pv2 == 1 else 1 - q_p
        for e2 in (0, 1):
            f_e = q_e if e2 == 1 else 1 - q_e
            for w2 in (0, 1):
                f_w = q_w if w2 == 1 else 1 - q_w
                for h2 in HABITS:
                    if h in ("target", "sibling"):
                        f_h = (pb if h2 == "none" else 0.0) + (ps if h2 == shift_to else 0.0)
                        if h2 == h:
                            f_h += 1 - pb - ps
                    elif h == "no_method":
                        flips = w == 0 and w2 == 1
                        f_h = float(h2 == ("none" if flips else "no_method"))
                    else:
                        f_h = float(h2 == h)
                    row[flat(pv2, e2, w2, h2)] += f_p * f_e * f_w * f_h
    return row


# --- 5.7 attention


def attention(a: float, base: float, eng: float, r: float, direct: bool, neglected: bool,
              ov: float, p: Mapping[str, float]) -> float:  # fmt: skip
    target = (base + p["K_push"] * eng * r + (p["addressed_bonus"] if direct else 0.0)
              - (p["neglect"] if neglected else 0.0) - p["overload_drag"] * ov)  # fmt: skip
    target = min(1.0, max(0.0, target))
    alpha = 1 - math.exp(-1 / p["tau"])
    return a + alpha * (target - a)


# --- 6.1, 6.3


def bayes_update(b: Sequence[float], like: Sequence[float]) -> list[float]:
    post = [x * y for x, y in zip(b, like, strict=True)]
    z = sum(post)
    return [x / z for x in post] if z > 0 else list(b)


def entropy(b: Sequence[float]) -> float:
    return -sum(x * math.log2(x) for x in b if x > 0)


def eig(b: Sequence[float], likes: Mapping[Any, Sequence[float]]) -> float:
    total = 0.0
    for like in likes.values():
        py = sum(x * y for x, y in zip(b, like, strict=True))
        if py > 0:
            total += py * entropy([x * y / py for x, y in zip(b, like, strict=True)])
    return entropy(b) - total


# --- golden cases


def golden(p: Mapping[str, float], families: Mapping[str, Any], moves: Mapping[str, Any]
           ) -> dict[str, dict[str, Any]]:  # fmt: skip
    roles = Roles("SUB-SFL", families)
    i1, i2 = ("sub", 52, 29), ("sub", 58, 23)
    out: dict[str, dict[str, Any]] = {}
    g1a = response((0, 0, 0, "target"), i1, roles, p, 0)
    g1b = response((1, 1, 0, "target"), i1, roles, p, 0)
    out["G1"] = {
        "wrong_SFL": wrong("SUB-SFL", i1),
        "wrong_NODEC": wrong("SUB-NODEC", i1),
        "P0E0": g1a[:2],
        "P1E1": g1b[:2],
        "expected": {"P0E0": [0.05, 0.95], "P1E1": [0.25, 0.75], "number": 37},
    }
    out["G2"] = {
        "wrong_SFL": wrong("SUB-SFL", i2),
        "wrong_NODEC": wrong("SUB-NODEC", i2),
        "correct": response((0, 0, 0, "target"), i2, roles, p, 0)[0],
        "expected": 1.0,
    }
    m = moves["show_bundles"]
    out["G3"] = {"p_learn_E": p_learn(m["cov_E"], 1.0, m, 1.0, 0.6, 0.0, p), "expected": 0.7109}
    a1 = attention(0.6, 0.6, -0.3, 1.0, True, False, 0.0, p)
    a2 = attention(a1, 0.6, 0.0, 0.0, False, False, 0.0, p)
    out["G4"] = {"a1": a1, "a2": a2, "expected": [0.4583, 0.4984]}
    out["G5"] = {"c0": hazard(p["h0_W"], 0, p), "c2": hazard(p["h0_W"], 2, p),
                 "expected": [0.03, 0.0110]}  # fmt: skip
    b = [0.0] * 32
    for h, v in (("target", 0.85), ("sibling", 0.05), ("none", 0.05), ("no_method", 0.05)):
        b[flat(0, 0, 0, h)] = v
    post = bayes_update(b, outcome_likelihoods(i1, roles, "core", p, 0)[("n", 23)])
    out["G6"] = {h: post[flat(0, 0, 0, h)] for h in HABITS} | {
        "expected": {"target": 0.7391, "sibling": 0.0435, "none": 0.1739, "no_method": 0.0435}
    }
    b = [0.0] * 32
    b[flat(0, 0, 0, "target")] = b[flat(0, 0, 1, "target")] = 0.5
    e1 = eig(b, outcome_likelihoods(i1, roles, "core", p, 0))
    e2 = eig(b, outcome_likelihoods(i2, roles, "core", p, 0))
    out["G7"] = {"eig_52_29": e1, "eig_58_23": e2, "chooses": "52-29" if e1 > e2 else "58-23",
                 "expected": [0.7136, 0.0, "52-29"]}  # fmt: skip
    return out


def golden_pass(g: Mapping[str, Mapping[str, Any]]) -> dict[str, bool]:
    def near(x: float, y: float) -> bool:
        return abs(x - y) <= 5e-5  # the spec's values are rounded to 4 decimals

    return {
        "G1": g["G1"]["wrong_SFL"] == [37] and g["G1"]["wrong_NODEC"] == [33]
        and all(near(x, y) for x, y in zip(g["G1"]["P0E0"], [0.05, 0.95], strict=True))
        and all(near(x, y) for x, y in zip(g["G1"]["P1E1"], [0.25, 0.75], strict=True)),
        "G2": g["G2"]["wrong_SFL"] == [] and g["G2"]["wrong_NODEC"] == []
        and near(g["G2"]["correct"], 1.0),
        "G3": near(round(g["G3"]["p_learn_E"], 4), 0.7109),
        "G4": near(round(g["G4"]["a1"], 4), 0.4583) and near(round(g["G4"]["a2"], 4), 0.4984),
        "G5": near(g["G5"]["c0"], 0.03) and near(round(g["G5"]["c2"], 4), 0.0110),
        "G6": all(near(round(g["G6"][h], 4), v) for h, v in g["G6"]["expected"].items()),
        "G7": near(round(g["G7"]["eig_52_29"], 4), 0.7136) and near(g["G7"]["eig_58_23"], 0.0)
        and g["G7"]["chooses"] == "52-29",
    }  # fmt: skip


# --- comparison against engine/bayes (the only place it is imported)


def compare(n: int = 1000, seed: int = 20261101) -> dict[str, Any]:
    import numpy as np

    from engine.bayes import belief as ebel
    from engine.bayes import dynamics as edyn
    from engine.bayes import response as eresp
    from engine.bayes import state as est
    from engine.bayes.content import NEUTRAL_MOVE
    from engine.bayes.content import load_moves as e_moves
    from engine.bayes.content import load_params as e_params
    from engine.bayes.planner import roles_for
    from engine.model import ErrorCode
    from engine.simulator import Problem

    p = load_params()
    families = load_families()
    moves = load_moves()
    ep = e_params().defaults
    emoves = e_moves()
    scen_items: list[Item] = []
    for f in sorted((ROOT / "content" / "scenarios").glob("*.yaml")):
        raw = yaml.safe_load(f.read_text(encoding="utf-8"))
        scen_items += [(q["kind"], q["a"], q["b"]) for q in raw["problems"]]
    extra: list[Item] = [("sub", 58, 23), ("sub", 64, 31), ("add", 23, 41), ("sub", 70, 25),
                         ("add", 45, 35), ("dictation", 55, 0), ("dictation", 300, 0)]  # fmt: skip
    items = scen_items + extra
    codes = ["SUB-SFL", "SUB-NODEC", "ADD-NOCARRY", "PV-HEARD"]
    rng = random.Random(seed)
    diffs: dict[str, float] = {k: 0.0 for k in
                               ("response", "transition", "attention", "forgetting", "update",
                                "eig")}  # fmt: skip
    worst: dict[str, Any] = {}

    def note(kind: str, d: float, case: dict[str, Any]) -> None:
        if d > diffs[kind]:
            diffs[kind] = d
            worst[kind] = case

    def eng_move(mid: str) -> Any:
        return emoves.get(mid, NEUTRAL_MOVE)

    for _ in range(n):
        target = rng.choice(codes)
        roles_o = Roles(target, families)
        roles_e = roles_for(ErrorCode(target))
        kinds = {
            "SUB-SFL": "sub",
            "SUB-NODEC": "sub",
            "ADD-NOCARRY": "add",
            "PV-HEARD": "dictation",
        }
        pool = [it for it in items if it[0] == kinds[target]] if rng.random() < 0.85 else items
        item = rng.choice(pool)
        s = rng.choice(STATES)
        idx = flat(*s)
        assert est.from_index(idx) == {"place_value": s[0], "exchange": s[1],
                                        "written_step": s[2], "habit": s[3]}  # fmt: skip
        mid = rng.choice([*moves])
        m = moves[mid]
        r = rng.choice([0.0, 0.5, 1.0])
        a = rng.random()
        ov = float(rng.choice([0, 0, 1, 2]))
        c = rng.randrange(0, 7)
        delta = rng.choice([0.0, rng.uniform(0, 0.4)])
        stage = rng.choice(["core", "core", "output", "input-test", "input-teaching"])
        prob = Problem(item[0], item[1], item[2])  # type: ignore[arg-type]
        case = {"target": target, "item": item, "state": s, "move": mid, "r": r, "a": a,
                "ov": ov, "c": c, "delta": delta, "stage": stage}  # fmt: skip
        # response row
        mine = response(s, item, roles_o, p, delta)
        theirs = list(eresp.response_row(idx, prob, roles_e, ep, delta))
        note("response", max(abs(x - y) for x, y in zip(mine, theirs, strict=True)), case)
        # transition row
        ctx = edyn.TurnContext(eng_move(mid), r, a, ov, c)
        mine_t = transition_row(s, m, r, a, ov, c, roles_o, p)
        theirs_t = list(edyn.transition_matrix(ctx, roles_e, ep)[idx])
        note("transition", max(abs(x - y) for x, y in zip(mine_t, theirs_t, strict=True)), case)
        # attention
        eng = rng.choice([-0.3, -0.1, 0.0, 0.05, 0.1, 0.15])
        direct, neglected = rng.random() < 0.5, rng.random() < 0.3
        mine_a = attention(a, 0.6, eng, r, direct, neglected, ov, p)
        theirs_a = edyn.attention_step(
            a, edyn.attention_target(0.6, eng, r, direct, neglected, ov, ep), ep
        )
        note("attention", abs(mine_a - theirs_a), case)
        # forgetting
        for h0 in ("h0_P", "h0_E", "h0_W"):
            note("forgetting", abs(hazard(p[h0], c, p) - edyn.hazard(getattr(ep, h0), c, ep)), case)
        # Bayes update on a random belief and a random possible outcome
        b = [rng.random() ** 3 for _ in range(32)]
        z = sum(b)
        b = [x / z for x in b]
        likes_o = outcome_likelihoods(item, roles_o, stage, p, delta)
        likes_e = dict(eresp.outcomes(prob, roles_e, stage, ep, delta))
        assert set(likes_o) == set(likes_e), (likes_o.keys(), likes_e.keys())
        y = rng.choice(sorted(likes_o, key=str))
        mine_u = bayes_update(b, likes_o[y])
        theirs_u = list(ebel.update(np.array(b), np.asarray(likes_e[y])))
        note("update", max(abs(x - y2) for x, y2 in zip(mine_u, theirs_u, strict=True)), case)
        theirs_e = ebel.eig(np.array(b), list(likes_e.items()))
        note("eig", abs(eig(b, likes_o) - theirs_e), case)
    return {"cases": n, "max_abs_diff": diffs, "worst_cases": worst,
            "max": max(diffs.values()), "pass": max(diffs.values()) <= TOL}  # fmt: skip


def compare_golden() -> dict[str, Any]:
    """G1-G7 from the oracle, then the same quantities from engine/bayes, side by side."""
    import numpy as np

    from engine.bayes import belief as ebel
    from engine.bayes import dynamics as edyn
    from engine.bayes import response as eresp
    from engine.bayes import state as est
    from engine.bayes.content import load_moves as e_moves
    from engine.bayes.content import load_params as e_params
    from engine.bayes.planner import roles_for
    from engine.model import ErrorCode
    from engine.simulator import Problem

    p = load_params()
    g = golden(p, load_families(), load_moves())
    ok = golden_pass(g)
    ep = e_params().defaults
    roles = roles_for(ErrorCode.SUB_SFL)
    i1, i2 = Problem("sub", 52, 29), Problem("sub", 58, 23)

    def ix(pv: int, e: int, w: int, h: str) -> int:
        return est.index({"place_value": pv, "exchange": e, "written_step": w, "habit": h})

    b6 = np.zeros(32)
    for h, v in (("target", 0.85), ("sibling", 0.05), ("none", 0.05), ("no_method", 0.05)):
        b6[ix(0, 0, 0, h)] = v
    post = ebel.update(b6, dict(eresp.outcomes(i1, roles, "core", ep))[("n", 23)])
    b7 = np.zeros(32)
    b7[ix(0, 0, 0, "target")] = b7[ix(0, 0, 1, "target")] = 0.5
    a1 = edyn.attention_step(0.6, edyn.attention_target(0.6, -0.3, 1.0, True, False, 0, ep), ep)
    engine_vals = {
        "G1": [*eresp.response_row(ix(0, 0, 0, "target"), i1, roles, ep)[:2],
               *eresp.response_row(ix(1, 1, 0, "target"), i1, roles, ep)[:2]],
        "G2": float(eresp.response_row(ix(0, 0, 0, "target"), i2, roles, ep)[0]),
        "G3": edyn.p_learn(0.9, edyn.fit_e(1, ep),
                           edyn.TurnContext(e_moves()["show_bundles"], 1.0, 0.6, 0.0, 0), ep),
        "G4": [a1, edyn.attention_step(
            a1, edyn.attention_target(0.6, 0.0, 0.0, False, False, 0, ep), ep)],
        "G5": [edyn.hazard(ep.h0_W, 0, ep), edyn.hazard(ep.h0_W, 2, ep)],
        "G6": {h: float(post[ix(0, 0, 0, h)]) for h in HABITS},
        "G7": [ebel.eig(b7, eresp.outcomes(i1, roles, "core", ep)),
               ebel.eig(b7, eresp.outcomes(i2, roles, "core", ep))],
    }  # fmt: skip
    oracle_vals = {
        "G1": [*g["G1"]["P0E0"], *g["G1"]["P1E1"]],
        "G2": g["G2"]["correct"],
        "G3": g["G3"]["p_learn_E"],
        "G4": [g["G4"]["a1"], g["G4"]["a2"]],
        "G5": [g["G5"]["c0"], g["G5"]["c2"]],
        "G6": {h: g["G6"][h] for h in HABITS},
        "G7": [g["G7"]["eig_52_29"], g["G7"]["eig_58_23"]],
    }

    def flatv(v: Any) -> list[float]:
        if isinstance(v, dict):
            return [float(v[h]) for h in HABITS]
        if isinstance(v, list):
            return [float(x) for x in v]
        return [float(v)]

    diff = {
        k: max(
            abs(x - y) for x, y in zip(flatv(oracle_vals[k]), flatv(engine_vals[k]), strict=True)
        )
        for k in oracle_vals
    }
    return {"oracle": g, "engine": engine_vals, "spec_values_pass": ok, "engine_vs_oracle": diff,
            "pass": all(ok.values()) and max(diff.values()) <= TOL}  # fmt: skip


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1000)
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args(argv)
    gold = compare_golden()
    rand = compare(args.n)
    for k, ok in gold["spec_values_pass"].items():
        print(
            f"{k}: {'PASS' if ok else 'FAIL'}  engine vs oracle {gold['engine_vs_oracle'][k]:.2e}"
        )
    print(f"random cases: {rand['cases']}, max |diff| by part:")
    for k, v in rand["max_abs_diff"].items():
        print(f"  {k:<11} {v:.2e}")
    ok = gold["pass"] and rand["pass"]
    print(
        f"oracle: {'PASS' if ok else 'FAIL'} "
        f"(max {max(rand['max'], *gold['engine_vs_oracle'].values()):.2e}, bar 1e-9)"
    )
    if not args.no_write:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "oracle.json").write_text(
            json.dumps({"golden": gold, "random": rand, "pass": ok}, indent=1, default=str) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {(OUT / 'oracle.json').relative_to(ROOT)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
