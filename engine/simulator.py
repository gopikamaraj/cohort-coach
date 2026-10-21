"""The Practice Class simulator: five fictional children whose mistakes come from the bug engine.

Pure Python, no I/O, no AI. A turn is a pure function of (state, scenario, move, who was
addressed, the posed problem); randomness comes from a generator seeded by (session seed, turn
number), so a session replays exactly. Claude only supplies the children's words afterwards;
every number a child can say is in `TurnPlan.allowed_numbers`, made here.

Rules (CLAUDE.md section 5): a child with an error answers wrong with probability equal to her
error strength, and the wrong number always comes from the bug function. Moves change strength
and engagement by the amounts in the scenario's move list (tuning parameters, not code).
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Literal

from engine.bugs import add_nocarry, pv_heard, pv_reverse, sub_nodec, sub_sfl
from engine.model import ErrorCode

Kind = Literal["sub", "add", "dictation"]

# Behaviours a move can trigger; the move list in content/ maps every move id to one of these.
BEHAVIOURS = frozenset(
    {"answer", "explain", "work_aloud", "doubt", "agree", "thanks", "quiet", "confused"}
)
APPLIES_TO: dict[ErrorCode, Kind] = {
    ErrorCode.SUB_SFL: "sub",
    ErrorCode.SUB_NODEC: "sub",
    ErrorCode.ADD_NOCARRY: "add",
    ErrorCode.PV_HEARD: "dictation",
    ErrorCode.PV_REVERSE: "dictation",
}
NEUTRAL = ("other", "off_task")
# Where a child's mistake most likely arises (addendum v3.1 F). A "core" child errs by the bug
# function; the others err differently, and every number they say still comes from this module.
STAGES = ("core", "input-teaching", "input-test", "output")


@dataclass(frozen=True)
class Problem:
    """A sum or a dictation. For a dictation `a` is the number said and `b` is unused."""

    kind: Kind
    a: int
    b: int = 0

    @property
    def correct(self) -> int:
        if self.kind == "sub":
            return self.a - self.b
        if self.kind == "add":
            return self.a + self.b
        return self.a


def valid_problem(p: Problem) -> bool:
    """Two-digit sums (as in the check) and 2 to 3-digit dictations."""
    if p.kind == "dictation":
        return 10 <= p.a <= 999
    if not (10 <= p.a <= 99 and 10 <= p.b <= 99):
        return False
    return p.a > p.b if p.kind == "sub" else p.a + p.b <= 99


def wrong_answers(error: ErrorCode, p: Problem) -> frozenset[int]:
    """The wrong answers this error gives on this problem; empty when it does not apply."""
    if APPLIES_TO[error] != p.kind:
        return frozenset()
    if error is ErrorCode.SUB_SFL:
        found = sub_sfl(p.a, p.b)
    elif error is ErrorCode.SUB_NODEC:
        found = sub_nodec(p.a, p.b)
    elif error is ErrorCode.ADD_NOCARRY:
        found = add_nocarry(p.a, p.b)
    elif error is ErrorCode.PV_HEARD:
        found = pv_heard(p.a)
    else:
        found = pv_reverse(p.a)
    return found - {p.correct}


@dataclass(frozen=True)
class Step:
    """One step of a child's working, as data. The words are made later; the numbers are here."""

    op: str
    numbers: tuple[int, ...]


def reasoning_steps(error: ErrorCode, p: Problem, answer: int) -> tuple[Step, ...]:
    """The faulty working that gives `answer` for this error."""
    if error is ErrorCode.SUB_SFL:
        at, ao, bt, bo = p.a // 10, p.a % 10, p.b // 10, p.b % 10
        steps = [Step("cant", (ao, bo))] if ao < bo else []
        steps.append(Step("minus", (max(ao, bo), min(ao, bo), abs(ao - bo))))
        steps.append(Step("minus", (max(at, bt), min(at, bt), abs(at - bt))))
        return tuple(steps)
    if error is ErrorCode.SUB_NODEC:
        at, ao, bt, bo = p.a // 10, p.a % 10, p.b // 10, p.b % 10
        steps = []
        if ao < bo:
            steps += [Step("cant", (ao, bo)), Step("borrow", (ao, ao + 10))]
            steps.append(Step("minus", (ao + 10, bo, ao + 10 - bo)))
        else:
            steps.append(Step("minus", (ao, bo, ao - bo)))
        steps.append(Step("minus", (at, bt, at - bt)))
        return tuple(steps)
    if error is ErrorCode.ADD_NOCARRY:
        at, ao, bt, bt_ = p.a // 10, p.a % 10, p.b // 10, p.b % 10
        total = ao + bt_
        return (
            Step("plus", (ao, bt_, total)),
            Step("write", (total % 10,)),
            Step("plus", (at, bt, at + bt)),
        )
    digits = [int(c) for c in str(p.a)]
    if error is ErrorCode.PV_HEARD:
        if len(digits) == 2:
            return (Step("parts", (digits[0] * 10, digits[1], answer)),)
        h, t, o = digits
        parts: tuple[int, ...]
        if answer == int(f"{h}00{t}{o}"):
            parts = (h * 100, t * 10 + o)
        elif answer == int(f"{h}0{t}{o}"):
            parts = (h * 10, t * 10 + o)
        else:
            parts = (h * 100, t * 10, o)
        return (Step("parts", (*parts, answer)),)
    # PV-REVERSE: puts the ones digit before the tens digit
    return (Step("swap", (digits[-2], digits[-1], answer)),)


def correct_steps(p: Problem) -> tuple[Step, ...]:
    """The correct working, as a child who has understood would say it."""
    if p.kind == "sub":
        at, ao, bt, bo = p.a // 10, p.a % 10, p.b // 10, p.b % 10
        if ao >= bo:
            return (Step("minus", (ao, bo, ao - bo)), Step("minus", (at, bt, at - bt)))
        return (
            Step("open", (at - 1, ao + 10)),
            Step("minus", (ao + 10, bo, ao + 10 - bo)),
            Step("minus", (at - 1, bt, at - 1 - bt)),
        )
    if p.kind == "add":
        at, ao, bt, bo = p.a // 10, p.a % 10, p.b // 10, p.b % 10
        total = ao + bo
        if total < 10:
            return (Step("plus", (ao, bo, total)), Step("plus", (at, bt, at + bt)))
        return (
            Step("plus", (ao, bo, total)),
            Step("write", (total % 10,)),
            Step("carry", (1,)),
            Step("plus", (at, bt, at + bt)),
            Step("plus", (at + bt, 1, at + bt + 1)),
        )
    digits = [int(c) for c in str(p.a)]
    if len(digits) == 2:
        return (Step("tens_ones", (digits[0], digits[1], p.a)),)
    return (Step("hundreds_tens_ones", (digits[0], digits[1], digits[2], p.a)),)


def doubt_steps(p: Problem, answer: int) -> tuple[Step, ...]:
    """Checking `answer` the way the move suggests; the numbers show whether it holds."""
    if p.kind == "sub":
        back = answer + p.b
        return (
            (Step("addback", (answer, p.b, back, p.a)),)
            if back != p.a
            else (Step("plus", (answer, p.b, back)),)
        )
    if p.kind == "add":
        back = answer - p.b
        return (
            (Step("takeaway", (answer, p.b, back, p.a)),)
            if back != p.a
            else (Step("minus", (answer, p.b, back)),)
        )
    return (
        (Step("size", (answer, p.a)),)
        if answer != p.a
        else (Step("tens_ones", (p.a // 10, p.a % 10, p.a)),)
    )


@dataclass(frozen=True)
class MoveEffect:
    behaviour: str
    strength: float  # change to the error strength of each child it reaches
    engagement: float
    quiet: bool  # the child goes quiet for `quiet_turns`


@dataclass(frozen=True)
class ScenarioConfig:
    error: ErrorCode
    start_strength: float
    start_engagement: float
    max_turns: int
    finish_streak: int
    quiet_turns: int
    problems: tuple[Problem, ...]
    moves: Mapping[str, MoveEffect]
    material_moves: Mapping[str, str]


@dataclass(frozen=True)
class Seat:
    name: str
    error: ErrorCode | None
    shy: bool
    stage: str = "core"


@dataclass(frozen=True)
class Child:
    name: str
    error: ErrorCode | None
    shy: bool
    strength: float
    engagement: float
    streak: int = 0
    quiet_turns: int = 0
    last_answer: int | None = None
    stage: str = "core"
    last_written: int | None = None


@dataclass(frozen=True)
class SessionState:
    seed: int
    turn: int
    children: tuple[Child, ...]
    problem: Problem | None = None
    next_problem: int = 0
    finished: bool = False
    finished_reason: str | None = None


@dataclass(frozen=True)
class TurnPlan:
    turn: int
    move_id: str
    behaviour: str
    speaker: str | None
    intent: str
    problem: Problem | None
    answer: int | None
    correct: bool | None
    error_code: ErrorCode | None
    steps: tuple[Step, ...]
    allowed_numbers: frozenset[int]
    mood: str
    strength_before: Mapping[str, float] = field(default_factory=dict)
    strength_after: Mapping[str, float] = field(default_factory=dict)
    note: str = ""
    written: int | None = None  # what the child writes on the slate (the spoken answer is `answer`)
    stage: str = "core"
    spoken_correct: bool | None = None  # is the number she says right (she may write it wrong)


def _clamp(v: float) -> float:
    return round(min(1.0, max(0.0, v)), 9)


def new_session(config: ScenarioConfig, seats: Sequence[Seat], seed: int) -> SessionState:
    children = tuple(
        Child(
            name=s.name,
            error=s.error,
            shy=s.shy,
            strength=config.start_strength if s.error else 0.0,
            engagement=config.start_engagement,
            stage=s.stage,
        )
        for s in seats
    )
    return SessionState(seed=seed, turn=0, children=children)


def is_finished(state: SessionState, config: ScenarioConfig) -> bool:
    erring = [c for c in state.children if c.error]
    if erring and all(c.streak >= config.finish_streak for c in erring):
        return True
    return state.turn >= config.max_turns


def _finish(state: SessionState, config: ScenarioConfig) -> SessionState:
    erring = [c for c in state.children if c.error]
    if erring and all(c.streak >= config.finish_streak for c in erring):
        return replace(state, finished=True, finished_reason="all_correct")
    if state.turn >= config.max_turns:
        return replace(state, finished=True, finished_reason="turn_cap")
    return state


def _rev(n: int) -> int:
    return int(str(n)[::-1])


def _near(n: int) -> list[int]:
    """Off by one in exactly one digit, same length: what a child who misheard might write."""
    s = str(n)
    out: set[int] = set()
    for i, ch in enumerate(s):
        for d in (-1, 1):
            t = int(ch) + d
            if 0 <= t <= 9 and not (i == 0 and t == 0):
                out.add(int(s[:i] + str(t) + s[i + 1 :]))
    return sorted(out - {n})


def _misheard(p: Problem, rng: random.Random) -> int | None:
    """What an input-test child answers: the other operation, swapped digits, or one digit off."""
    if p.kind == "dictation":
        near = _near(p.a)
        return rng.choice(near) if near else None
    other = abs(p.a - p.b) if p.kind == "add" else p.a + p.b
    swapped = (_rev(p.a) + p.b) if p.kind == "add" else _rev(p.a) - p.b
    options = [x for x in dict.fromkeys([other, swapped]) if x >= 0 and x != p.correct]
    return rng.choice(options) if options else None


def _answer(
    child: Child, p: Problem, rng: random.Random
) -> tuple[int | None, bool, ErrorCode | None, int | None]:
    """The child answer (spoken), whether it is right all the way through, the error code, and
    what she writes. Wrong with probability = strength; the wrong number is always the engine's:
    the bug function (core), the other operation or a digit swap (input-test), the correct answer
    written the wrong way round (output), or no number at all (input-teaching)."""
    if child.error:
        if child.stage == "core":
            wrong = sorted(wrong_answers(child.error, p))
            if wrong and rng.random() < child.strength:
                n = rng.choice(wrong)
                return n, False, child.error, n
        elif child.stage == "output":
            reversible = _rev(p.correct) != p.correct and p.correct % 10 != 0
            if reversible and rng.random() < child.strength:
                return p.correct, False, child.error, _rev(p.correct)
        elif child.stage == "input-test":
            heard = _misheard(p, rng) if rng.random() < child.strength else None
            if heard is not None:
                return heard, False, child.error, heard
        elif child.stage == "input-teaching" and rng.random() < child.strength:
            return None, False, child.error, None
    return p.correct, True, None, p.correct


def _mood(child: Child, doubtful: bool = False, small: bool = False) -> str:
    if small:
        return "small"
    if doubtful:
        return "doubtful"
    if child.engagement < 0.35:
        return "flat"
    return "bright" if child.engagement > 0.75 else "calm"


def plan_turn(
    state: SessionState,
    config: ScenarioConfig,
    move_id: str,
    *,
    addressed: str | None,
    posed: Problem | None,
) -> tuple[TurnPlan, SessionState]:
    """One turn. Returns the plan (who speaks, what numbers) and the next state."""
    if state.finished:
        raise ValueError("the session is finished")
    if move_id in NEUTRAL:
        effect = MoveEffect("confused", 0.0, 0.0, False)
    elif move_id in config.moves:
        effect = config.moves[move_id]
    else:
        raise ValueError(f"unknown move {move_id!r}")
    turn = state.turn + 1
    rng = random.Random(f"{state.seed}:{turn}")
    by_name = {c.name: c for c in state.children}
    target_names = [addressed] if addressed in by_name else [c.name for c in state.children]

    # The current problem: a posed one if valid, else the scenario's next; reused otherwise.
    problem, next_problem = state.problem, state.next_problem
    children = list(state.children)
    needs_problem = effect.behaviour in {"answer", "explain", "work_aloud", "doubt"}
    if effect.behaviour == "answer" and move_id not in NEUTRAL:
        if posed is not None and valid_problem(posed):
            problem = posed
        else:
            problem = config.problems[next_problem % len(config.problems)]
            next_problem += 1
        children = [replace(c, last_answer=None) for c in children]
    elif needs_problem and problem is None:
        problem = config.problems[next_problem % len(config.problems)]
        next_problem += 1

    # Move effects on the children it reaches. Quiet children at the start stay quiet this turn.
    was_quiet = {c.name: c.quiet_turns > 0 for c in children}
    before: dict[str, float] = {}
    after: dict[str, float] = {}
    for i, c in enumerate(children):
        if c.name not in target_names:
            continue
        strength = c.strength
        if c.error and effect.strength:
            before[c.name] = c.strength
            strength = _clamp(c.strength + effect.strength)
            after[c.name] = strength
        children[i] = replace(
            c,
            strength=strength,
            engagement=_clamp(c.engagement + effect.engagement),
            quiet_turns=config.quiet_turns if effect.quiet else c.quiet_turns,
        )

    # Who speaks. The shy child only when named.
    speaker: Child | None = None
    if addressed in by_name:
        speaker = children[[c.name for c in children].index(addressed)]
    else:
        pool = [c for c in children if not c.shy and not was_quiet[c.name]]
        if pool:
            weights = [c.engagement + 0.05 for c in pool]
            speaker = rng.choices(pool, weights=weights, k=1)[0]

    intent = effect.behaviour
    answer: int | None = None
    correct: bool | None = None
    code: ErrorCode | None = None
    steps: tuple[Step, ...] = ()
    written: int | None = None
    doubtful = False
    small = False
    if speaker is None:
        intent = "silent"
    elif was_quiet[speaker.name] and effect.behaviour != "quiet":
        intent = "quiet"
    elif effect.behaviour == "quiet":
        small = True
    elif intent in {"answer", "explain", "work_aloud", "doubt"} and problem is not None:
        idx = [c.name for c in children].index(speaker.name)
        now = children[idx]
        if intent == "answer" or now.last_answer is None:
            answer, correct, code, written = _answer(now, problem, rng)
        else:
            answer, written = now.last_answer, now.last_written
            correct = answer == problem.correct and written == answer
            code = None if correct else now.error
        if intent == "work_aloud":
            # Working it with materials: she gets it right unless the error still holds.
            answer, correct, code, written = _answer(now, problem, rng)
            steps = _steps_for(now, problem, answer)
        elif intent == "explain":
            steps = _steps_for(now, problem, answer)
        elif intent == "doubt" and answer is not None:
            steps = doubt_steps(problem, answer)
            doubtful = not correct
        if answer is None:  # no method yet: she cannot say a number, so she says she is lost
            intent = "confused"
        streak = (
            (now.streak + 1 if correct else 0)
            if intent in {"answer", "work_aloud"}
            or (now.last_answer is None and intent in {"explain", "doubt"})
            else now.streak
        )
        children[idx] = replace(now, last_answer=answer, last_written=written, streak=streak)

    # Quiet counters tick down for children who were quiet when the turn began.
    children = [
        replace(c, quiet_turns=max(0, c.quiet_turns - 1)) if was_quiet[c.name] else c
        for c in children
    ]
    numbers: set[int] = set()
    if problem is not None and (answer is not None or steps):
        numbers |= {problem.a, problem.b} if problem.kind != "dictation" else {problem.a}
    if answer is not None:
        numbers.add(answer)
    if written is not None:
        numbers.add(written)
    for s in steps:
        numbers |= set(s.numbers)
    speaker_now = None
    if speaker is not None:
        speaker_now = next(c for c in children if c.name == speaker.name)
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
        mood=_mood(speaker_now, doubtful, small) if speaker_now else "calm",
        strength_before=before,
        strength_after=after,
        written=written,
        stage=speaker_now.stage if speaker_now else "core",
        spoken_correct=(answer == problem.correct) if (answer is not None and problem) else None,
    )
    nxt = replace(
        state,
        turn=turn,
        children=tuple(children),
        problem=problem,
        next_problem=next_problem,
    )
    return plan, _finish(nxt, config)


def _wrong_steps(child: Child, p: Problem, answer: int) -> tuple[Step, ...]:
    return reasoning_steps(child.error, p, answer) if child.error else correct_steps(p)


def _steps_for(child: Child, p: Problem, answer: int | None) -> tuple[Step, ...]:
    """The working she says aloud. Right when her spoken answer is right (an output child works it
    out correctly and only writes it wrong); the error's own working for a core child's wrong
    answer; none when she has no method yet or misheard the question."""
    if answer is None:
        return ()
    if answer == p.correct:
        return correct_steps(p)
    return _wrong_steps(child, p, answer) if child.stage == "core" else ()


def fill_seats(
    counts: Mapping[ErrorCode, int],
    checked: int,
    target: ErrorCode,
    mix: Mapping[ErrorCode, int],
    names: Sequence[str] = ("Child 1", "Child 2", "Child 3", "Child 4", "Child 5"),
    n_seats: int = 5,
    stage_mix: Sequence[str] = (),
) -> tuple[Seat, ...]:
    """Fill the seats to match the class's error mix.

    Seat 0 is always correct. If 40% of the class shows an error, 2 of the 5 seats get it. At most
    n_seats - 1 children have an error, the target error always has a seat, and with no class
    counts the scenario's default mix is used. One child is shy: the last child with an error, or
    a correct child when only one child has an error.
    """
    max_err = n_seats - 1
    relevant = {c: counts.get(c, 0) for c in mix}
    total = sum(relevant.values())
    if checked <= 0 or total == 0:
        allocation = dict(mix)
        n_err = min(max_err, sum(allocation.values()))
    else:
        n_err = min(max_err, max(1, round(n_seats * total / checked)))
        allocation = _apportion(relevant, n_err)
        if allocation.get(target, 0) == 0 and relevant.get(target, 0) > 0:
            donor = max(allocation, key=lambda k: allocation[k])
            allocation[donor] -= 1
            allocation[target] = 1
        if allocation.get(target, 0) == 0:  # the scenario drills this error: it always has a seat
            donor = max(allocation, key=lambda k: allocation[k])
            allocation[donor] -= 1
            allocation[target] = 1
    # Trim to max_err and order: target error first, then the rest by code.
    codes: list[ErrorCode | None] = []
    for code in sorted(allocation, key=lambda c: (c is not target, c.value)):
        codes += [code] * allocation[code]
    codes = codes[:max_err]
    codes += [None] * (n_seats - 1 - len(codes))
    errs = [c for c in codes if c is not None]
    shy_idx = (
        max(i for i, c in enumerate(codes) if c is not None)
        if len(errs) >= 2
        else (max(i for i, c in enumerate(codes) if c is None))
    )
    ordered: list[ErrorCode | None] = [None, *codes]
    bad = [m for m in stage_mix if m not in STAGES]
    if bad:
        raise ValueError(f"unknown stage {bad[0]!r}; use one of {', '.join(STAGES)}")
    # stage_mix is read down the seats after the always-correct one; extra seats stay core
    stages = ["core", *stage_mix, *["core"] * n_seats][:n_seats]
    seats = [
        Seat(names[i], code, shy=(i - 1 == shy_idx), stage=stages[i] if code else "core")
        for i, code in enumerate(ordered)
    ]
    return tuple(seats)


def _apportion(weights: Mapping[ErrorCode, int], seats: int) -> dict[ErrorCode, int]:
    """Largest-remainder split of `seats` in proportion to the weights."""
    total = sum(weights.values())
    exact = {k: seats * v / total for k, v in weights.items()}
    out = {k: int(x) for k, x in exact.items()}
    left = seats - sum(out.values())
    for k in sorted(exact, key=lambda k: (-(exact[k] - out[k]), k.value))[:left]:
        out[k] += 1
    return out
