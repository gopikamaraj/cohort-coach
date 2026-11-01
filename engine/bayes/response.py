"""The response table O(kind | state, item) and the observable outcomes (docs/BAYESIAN-MODEL.md 5.3,
5.4, 6.1).

Kinds: correct, bug_target, bug_sibling, no_answer. A bug kind's number always comes from the bug
function (engine.bugs through engine.simulator.wrong_answers, read-only). The stage of a child sets
the form of an error (core: the bug number; output: says it right, writes it reversed; input-test:
the other operation, a digit swap, or a dictation misread by one digit); the 32 states set how
likely an error is. Pure: no randomness, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from engine.bayes.content import Params
from engine.bayes.state import E_OF, H_OF, HABITS, N_STATES, P_OF, W_OF, Habit, Vector
from engine.model import ErrorCode
from engine.simulator import Problem, wrong_answers

KINDS: tuple[str, ...] = ("correct", "bug_target", "bug_sibling", "no_answer")
K_CORRECT, K_TARGET, K_SIBLING, K_NONE = range(4)
_H = {h: i for i, h in enumerate(HABITS)}


@dataclass(frozen=True)
class Roles:
    """Which error code each habit role means in this session. target is the scenario's error code,
    sibling its pair from content/bayes/families.v1.yaml (None when the family has none)."""

    target: ErrorCode
    sibling: ErrorCode | None
    family: str
    family_codes: tuple[ErrorCode, ...]
    shift: tuple[tuple[ErrorCode, ErrorCode], ...] = ()  # habit shifts under a rule drill

    def code(self, habit: Habit) -> ErrorCode | None:
        return self.target if habit == "target" else self.sibling if habit == "sibling" else None

    def shift_role(self, habit: Habit) -> Habit | None:
        """The role this habit moves to under a rule drill (SUB-SFL -> SUB-NODEC), or None."""
        code = self.code(habit)
        for a, b in self.shift:
            if a == code:
                return self.role(b)
        return None

    def role(self, code: ErrorCode) -> Habit:
        if code == self.target:
            return "target"
        if self.sibling is not None and code == self.sibling:
            return "sibling"
        raise ValueError(f"error code {code.value} is neither the target nor its sibling")


@lru_cache(maxsize=4096)
def wrong_numbers(code: ErrorCode | None, item: Problem) -> tuple[int, ...]:
    """The bug's wrong answers on this item, sorted, the correct answer excluded."""
    return () if code is None else tuple(sorted(wrong_answers(code, item)))


def bites(code: ErrorCode | None, item: Problem) -> bool:
    """True when the bug for `code` gives a wrong number on this item."""
    return bool(wrong_numbers(code, item))


def needs_step(roles: Roles, item: Problem) -> bool:
    """True when at least one bug in the child's family bites on the item."""
    return any(bites(c, item) for c in roles.family_codes)


def response_matrix(item: Problem, roles: Roles, p: Params, delta: float = 0.0) -> Vector:
    """O(kind | s, item) for all 32 states: shape (32, 4), every row sums to 1. Includes the
    collapse rule and priming of strength `delta`."""
    out = np.zeros((N_STATES, 4), dtype=np.float64)
    nm = H_OF == _H["no_method"]
    if not needs_step(roles, item):
        out[:, K_CORRECT] = np.where(nm, p.c_nm_easy, 1.0)
        out[:, K_NONE] = np.where(nm, 1 - p.c_nm_easy, 0.0)
    else:
        pe = (P_OF == 1) & (E_OF == 1)
        g = np.where(pe, p.g_PE, p.g0)
        c = np.where(pe, p.c_none_PE, p.c_none)
        w1 = W_OF == 1
        tgt, sib, none = H_OF == _H["target"], H_OF == _H["sibling"], H_OF == _H["none"]
        # W = 1: right unless she slips; the slip takes the form of her habit
        out[:, K_CORRECT] = np.where(w1, 1 - p.slip, 0.0)
        out[:, K_TARGET] = np.where(w1 & (tgt | none), p.slip, 0.0)
        out[:, K_SIBLING] = np.where(w1 & sib, p.slip, 0.0)
        out[:, K_NONE] = np.where(w1 & nm, p.slip, 0.0)
        # W = 0
        w0 = ~w1
        out[:, K_CORRECT] += np.where(w0 & (tgt | sib), g, 0.0)
        out[:, K_CORRECT] += np.where(w0 & none, c, 0.0)
        out[:, K_CORRECT] += np.where(w0 & nm, p.g_nm, 0.0)
        out[:, K_TARGET] += np.where(w0 & tgt, 1 - g, 0.0)
        out[:, K_SIBLING] += np.where(w0 & sib, 1 - g, 0.0)
        out[:, K_NONE] += np.where(w0 & none, 1 - c, 0.0)
        out[:, K_NONE] += np.where(w0 & nm, 1 - p.g_nm, 0.0)
    # Collapse: a bug kind whose own bug does not bite here answers correct instead.
    for k, code in ((K_TARGET, roles.target), (K_SIBLING, roles.sibling)):
        if not bites(code, item):
            out[:, K_CORRECT] += out[:, k]
            out[:, k] = 0.0
    if delta:
        right = out[:, K_CORRECT].copy()
        out *= 1 - delta
        out[:, K_CORRECT] = right + delta * (1 - right)
    return out


def response_row(index: int, item: Problem, roles: Roles, p: Params, delta: float = 0.0) -> Vector:
    row: Vector = response_matrix(item, roles, p, delta)[index]
    return row


# --- stage forms (copies of the legacy helpers in engine/simulator.py: _rev and _misheard, so the
# options are a list and a pick takes one uniform; the forms are identical)


def rev(n: int) -> int:
    return int(str(n)[::-1])


def near(n: int) -> list[int]:
    """Off by one in exactly one digit, same length (copy of simulator._near)."""
    s = str(n)
    out: set[int] = set()
    for i, ch in enumerate(s):
        for d in (-1, 1):
            t = int(ch) + d
            if 0 <= t <= 9 and not (i == 0 and t == 0):
                out.add(int(s[:i] + str(t) + s[i + 1 :]))
    return sorted(out - {n})


def misheard_options(item: Problem) -> list[int]:
    """What an input-test child may answer (the options of simulator._misheard)."""
    if item.kind == "dictation":
        return near(item.a)
    other = abs(item.a - item.b) if item.kind == "add" else item.a + item.b
    swapped = (rev(item.a) + item.b) if item.kind == "add" else rev(item.a) - item.b
    return [x for x in dict.fromkeys([other, swapped]) if x >= 0 and x != item.correct]


def output_form_available(item: Problem) -> bool:
    """An output child writes the answer reversed only when that is a different number."""
    return rev(item.correct) != item.correct and item.correct % 10 != 0


def form_available(stage: str, item: Problem) -> bool:
    if stage == "output":
        return output_form_available(item)
    if stage == "input-test":
        return bool(misheard_options(item))
    return True


# --- observable outcomes

Outcome = tuple[str, int] | tuple[str]


def outcomes(
    item: Problem, roles: Roles, stage: str, p: Params, delta: float = 0.0
) -> list[tuple[Outcome, Vector]]:
    """Each observable outcome y with L(y | s) for all 32 states; for every state the L sum to 1.

    core and input-teaching: the number said (kinds that give the same number are summed; a bug
    kind's number is uniform over its wrong answers), or no number. output and input-test: the
    error form or correct (an error form that does not exist on this item leaves only correct)."""
    m = response_matrix(item, roles, p, delta)
    if stage in ("output", "input-test"):
        if not form_available(stage, item):
            return [(("correct",), np.ones(N_STATES))]
        return [(("correct",), m[:, K_CORRECT]), (("form",), 1 - m[:, K_CORRECT])]
    by_number: dict[int, Vector] = {item.correct: m[:, K_CORRECT].copy()}
    for k, code in ((K_TARGET, roles.target), (K_SIBLING, roles.sibling)):
        wrong = wrong_numbers(code, item)
        for n in wrong:
            by_number.setdefault(n, np.zeros(N_STATES))
            by_number[n] = by_number[n] + m[:, k] / len(wrong)
    out: list[tuple[Outcome, Vector]] = [(("n", n), v) for n, v in sorted(by_number.items())]
    out.append((("none",), m[:, K_NONE]))
    return out


def observed(stage: str, answer: int | None, correct: bool) -> Outcome:
    """The outcome key the observer sees for an answer."""
    if stage in ("output", "input-test"):
        return ("correct",) if correct else ("form",)
    return ("none",) if answer is None else ("n", answer)


def p_correct(
    index: int, item: Problem, roles: Roles, stage: str, p: Params, delta: float
) -> float:
    """P(the answer is right, said and written) for one state, after the stage channel."""
    if stage in ("output", "input-test") and not form_available(stage, item):
        return 1.0
    return float(response_matrix(item, roles, p, delta)[index, K_CORRECT])
