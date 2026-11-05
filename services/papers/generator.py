"""generate_paper and make_twin: a check paper from a rule set, a class profile and a seed.

Pure code, no I/O and no AI. Numbers come from a seeded random.Random (never the global state);
every key and wrong answer comes from the bug functions in engine/bugs.py. The same blueprint,
rules version, class profile and seed always give the same paper and the same hash.

Anchor slots have a fixed skill and difficulty (the ones total or ones gap of Form A), so papers
across checks and classes measure the same thing and only the numbers change: before and after
compare on these. Adaptive slots go deeper on what the class profile weights most and skip any
skill marked not assessed; they are for diagnosis and never for claiming improvement.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from functools import cache
from typing import Any, Literal

from engine import bugs as engine_bugs
from services.papers.rules import COMPETENCY_NAMES, Blueprint, RuleSet, Slot, Template

Kind = Literal["pre", "post", "termly"]
Source = Literal["past", "intake", "baseline"]
KIND_CODE = {"pre": "PRE", "post": "POST", "termly": "TERM"}
SECTIONS = ("dictation", "add", "subtract")


class CannotMeet(Exception):
    """The rules cannot be met. Never answered with a weaker paper: the rule is named instead."""

    def __init__(self, rule: str, detail: str) -> None:
        super().__init__(f"{rule}: {detail}")
        self.rule = rule
        self.detail = detail


@dataclass(frozen=True)
class CheckRef:
    """The check a paper belongs to (the phone's check record: id, kind, form, class, term)."""

    id: str
    kind: Kind
    form: str
    class_label: str
    term: int


@dataclass(frozen=True)
class Profile:
    """What the generator knows about a class: class-level weights only, never a child."""

    source: Source
    weights: dict[str, float]  # competency -> weight (share of children who went wrong)
    not_assessed: tuple[str, ...]  # competencies left off the paper (not taught yet)
    language: str
    strength: int | None = None  # children in the class
    built_from: tuple[str, ...] = ()  # check ids the weights came from


@dataclass(frozen=True)
class PaperItem:
    n: int
    slot: int
    template: str
    competency: str
    section: str
    operation: str
    a: int
    b: int
    correct: int
    wrong: dict[str, list[int]]  # tracked error code -> the wrong answers it predicts
    untracked: dict[str, list[int]]  # tallied patterns (never flagged)
    is_anchor: bool
    difficulty: int | None
    twin_of: int | None = None


@dataclass(frozen=True)
class Paper:
    check_id: str
    check_code: str
    form: str
    kind: str
    seed: str
    blueprint: str
    rules_version: int
    profile: dict[str, Any]
    items: tuple[PaperItem, ...]
    not_assessed: tuple[str, ...]
    coverage: dict[str, list[int]]  # error code -> item numbers probing it
    twin_of_paper: str | None = None  # hash of the pre-test this one is the twin of
    custom: bool = False  # hand-written items or wording: always reviewed by a person
    hash: str = field(default="")

    def to_dict(self) -> dict[str, Any]:
        """Plain JSON data (lists, not tuples), as stored and as the verifier reads it."""
        data: dict[str, Any] = json.loads(json.dumps(asdict(self)))
        return data


# --- profiles -----------------------------------------------------------------------------

_CODE_COMPETENCY = {
    "PV-HEARD": "C1",
    "PV-REVERSE": "C1",
    "ADD-NOCARRY": "C2",
    "SUB-SFL": "C3",
    "SUB-NODEC": "C3",
}


def profile_from_counts(
    counts: dict[str, int],
    checked: int,
    language: str,
    built_from: Iterable[str] = (),
    not_assessed: Iterable[str] = (),
) -> Profile:
    """From the latest closed check: class counts only ("9 of 18 went wrong borrowing")."""
    weights: dict[str, float] = {}
    for code, n in counts.items():
        comp = _CODE_COMPETENCY.get(code)
        if comp and checked > 0:
            weights[comp] = max(weights.get(comp, 0.0), n / checked)
    return Profile(
        source="past",
        weights=weights,
        not_assessed=tuple(sorted(set(not_assessed))),
        language=language,
        strength=checked,
        built_from=tuple(built_from),
    )


def profile_from_intake(
    struggles: Iterable[str],
    taught: Iterable[str],
    language: str,
    strength: int | None,
) -> Profile:
    """The teacher's short intake: what the class struggles with, and which topics were taught.
    A topic not taught is not assessed, so no child is flagged for something never taught."""
    taught_set = set(taught)
    not_assessed = tuple(c for c in COMPETENCY_NAMES if c not in taught_set)
    weights = {c: 1.0 for c in struggles if c in taught_set}
    return Profile("intake", weights, not_assessed, language, strength)


def baseline_profile(language: str) -> Profile:
    return Profile("baseline", {}, (), language)


# --- numbers ------------------------------------------------------------------------------


def _bug_fn(name: str) -> Callable[..., frozenset[int]]:
    fn = getattr(engine_bugs, name, None)
    if fn is None:
        raise CannotMeet("bugs", f"no bug function {name} in engine/bugs.py")
    return fn  # type: ignore[no-any-return]


def _correct(op: str, a: int, b: int) -> int:
    return a if op == "dictate" else a + b if op == "add" else a - b


def _difficulty(t: Template, a: int, b: int) -> int | None:
    if t.difficulty == "ones_total":
        return a % 10 + b % 10
    if t.difficulty == "ones_gap":
        return b % 10 - a % 10
    return None


def _fits(t: Template, a: int, b: int) -> bool:
    c = t.constraints
    lo, hi = t.number_range
    if t.operation == "dictate":
        ds = str(a)
        if not lo <= a <= hi or len(ds) != c.get("digits", len(ds)):
            return False
        if c.get("nonzero") and "0" in ds:
            return False
        return not (c.get("tens_ne_ones") and ds[-1] == ds[-2])
    if not (lo <= a <= hi and lo <= b <= hi):
        return False
    ao, bo, at, bt = a % 10, b % 10, a // 10, b // 10
    if t.operation == "add":
        carry = ao + bo >= 10
        if c.get("carry") == "required" and not carry:
            return False
        if c.get("carry") == "forbidden" and carry:
            return False
        if "ones_total" in c and ao + bo != c["ones_total"]:
            return False
        return a + b <= int(c.get("sum_max", 999))
    borrow = ao < bo
    if c.get("borrow") == "required" and not borrow:
        return False
    if c.get("borrow") == "forbidden" and borrow:
        return False
    if at - bt < c.get("tens_gap_min", 0):
        return False
    if "first_ones" in c and ao != c["first_ones"]:
        return False
    if borrow and (bo - ao) in c.get("gap_not", []):
        return False
    return a - b >= int(c.get("result_min", 0))


def item_answers(
    rules: RuleSet, t: Template, a: int, b: int
) -> tuple[dict[str, list[int]], dict[str, list[int]], list[str]]:
    """(tracked wrong answers by code, untracked by code, discrimination problems) for one item."""
    correct = _correct(t.operation, a, b)
    per_bug: dict[str, frozenset[int]] = {}
    problems: list[str] = []
    for bid in t.bugs:
        bug = rules.bug(bid)
        fn = _bug_fn(bug.fn)
        answers = fn(a) if t.operation == "dictate" else fn(a, b)
        if correct in answers:
            problems.append(f"{bid} gives the correct answer {correct}")
        if bug.tracked and not (answers - {correct}):
            problems.append(f"{bid} gives no wrong answer")
        per_bug[bid] = answers - {correct}
    ids = list(per_bug)
    for i, x in enumerate(ids):
        for y in ids[i + 1 :]:
            shared = per_bug[x] & per_bug[y]
            if shared:
                problems.append(f"{x} and {y} give the same wrong answer {min(shared)}")
    wrong: dict[str, set[int]] = {}
    untracked: dict[str, set[int]] = {}
    for bid, answers in per_bug.items():
        for code in rules.bug(bid).counts_for:
            target = wrong if code in _CODE_COMPETENCY else untracked
            target.setdefault(code, set()).update(answers)
    return (
        {k: sorted(v) for k, v in wrong.items() if v},
        {k: sorted(v) for k, v in untracked.items() if v},
        problems,
    )


@cache
def _candidates(rules_key: str, tid: str, difficulty: int | None) -> tuple[tuple[int, int], ...]:
    rules = _RULES_BY_KEY[rules_key]
    t = rules.template(tid)
    lo, hi = t.number_range
    pairs: Iterable[tuple[int, int]]
    if t.operation == "dictate":
        pairs = ((a, 0) for a in range(lo, hi + 1))
    else:
        pairs = ((a, b) for a in range(lo, hi + 1) for b in range(lo, hi + 1))
    out = []
    for a, b in pairs:
        if not _fits(t, a, b):
            continue
        if difficulty is not None and _difficulty(t, a, b) != difficulty:
            continue
        if item_answers(rules, t, a, b)[2]:  # discrimination rule
            continue
        out.append((a, b))
    return tuple(out)


_RULES_BY_KEY: dict[str, RuleSet] = {}


def _key(rules: RuleSet) -> str:
    k = hashlib.sha256(rules.model_dump_json().encode("utf-8")).hexdigest()
    _RULES_BY_KEY.setdefault(k, rules)
    return k


def _template(rules: RuleSet, tid: str) -> Template:
    t = rules.template(tid)
    if t.retired:
        raise CannotMeet("retired", f"template {tid} is retired and cannot be used")
    return t


def _pick(
    rng: random.Random,
    rules: RuleSet,
    t: Template,
    difficulty: int | None,
    avoid: set[tuple[int, int]],
    differ_from: tuple[int, int] | None = None,
) -> tuple[int, int]:
    pool = [
        p
        for p in _candidates(_key(rules), t.id, difficulty)
        if p not in avoid
        and (
            differ_from is None
            or (p[0] != differ_from[0] and (t.operation == "dictate" or p[1] != differ_from[1]))
        )
    ]
    if not pool:
        what = f"difficulty {difficulty}" if difficulty is not None else "its digit pattern"
        raise CannotMeet("constraints", f"no numbers fit template {t.id} with {what}")
    return rng.choice(pool)


def _rng(*parts: object) -> random.Random:
    return random.Random("|".join(map(str, parts)))


def _item(
    rules: RuleSet,
    t: Template,
    n: int,
    slot: Slot,
    a: int,
    b: int,
    difficulty: int | None,
    twin_of: int | None = None,
) -> PaperItem:
    wrong, untracked, problems = item_answers(rules, t, a, b)
    if problems:
        raise CannotMeet("discrimination", f"item {n} ({t.id} {a}, {b}): {problems[0]}")
    section = {"dictate": "dictation", "add": "add", "subtract": "subtract"}[t.operation]
    return PaperItem(
        n=n,
        slot=slot.n,
        template=t.id,
        competency=t.competency,
        section=section,
        operation=t.operation,
        a=a,
        b=b,
        correct=_correct(t.operation, a, b),
        wrong=wrong,
        untracked=untracked,
        is_anchor=slot.kind == "anchor",
        difficulty=difficulty,
        twin_of=twin_of,
    )


def _allocate(bp: Blueprint, weights: dict[str, float], assessed: list[str]) -> list[str]:
    """Spread the adaptive slots over the assessed competencies by weight (largest remainder)."""
    comps = [c for c in assessed if bp.adaptive_templates.get(c)]  # type: ignore[call-overload]
    if not comps or bp.adaptive_count == 0:
        return []
    w = {c: max(0.0, weights.get(c, 0.0)) for c in comps}
    total = sum(w.values())
    if total == 0:
        w, total = {c: 1.0 for c in comps}, float(len(comps))
    raw = {c: bp.adaptive_count * w[c] / total for c in comps}
    counts = {c: int(raw[c]) for c in comps}
    left = bp.adaptive_count - sum(counts.values())
    order = sorted(comps, key=lambda c: (-(raw[c] - counts[c]), -w[c], comps.index(c)))
    for c in order[:left]:
        counts[c] += 1
    by_weight = sorted(comps, key=lambda c: (-w[c], comps.index(c)))
    return [c for c in by_weight for _ in range(counts[c])]


def _coverage(rules: RuleSet, items: Iterable[PaperItem]) -> dict[str, list[int]]:
    cov: dict[str, list[int]] = {}
    for it in items:
        t = rules.template(it.template)
        for bid in t.bugs:
            bug = rules.bug(bid)
            if not bug.tracked:
                continue
            for code in bug.counts_for:
                if it.wrong.get(code):
                    cov.setdefault(code, []).append(it.n)
    return {k: sorted(set(v)) for k, v in cov.items()}


def check_code(check: CheckRef) -> str:
    """The code printed on a paper: its kind and class. Terms are off (correction 9, DECISIONS 2026-11-03), so it no
    longer ends in " · T1"; papers made before keep their stored code, and the app leaves the old suffix out when it
    shows one."""
    return f"{KIND_CODE[check.kind]} · {check.class_label}"


def _finish(
    check: CheckRef,
    seed: object,
    bp: Blueprint,
    rules_version: int,
    profile: Profile,
    items: list[PaperItem],
    rules: RuleSet,
    twin_of_paper: str | None = None,
) -> Paper:
    if not items:
        raise CannotMeet("coverage", "every skill is marked not assessed: nothing to check")
    seen: set[tuple[str, int, int]] = set()
    for it in items:
        k = (it.operation, it.a, it.b)
        if k in seen:
            raise CannotMeet("uniqueness", f"item {it.n} repeats {it.a}, {it.b}")
        seen.add(k)
    cov = _coverage(rules, items)
    assessed_codes = [
        c for c in bp.coverage_codes if _CODE_COMPETENCY.get(c) not in profile.not_assessed
    ]
    for code in assessed_codes:
        if len(cov.get(code, [])) < bp.coverage_min:
            raise CannotMeet(
                "coverage",
                f"{code} is probed by {len(cov.get(code, []))} item(s); "
                f"the blueprint needs at least {bp.coverage_min}",
            )
    prof = asdict(profile)
    paper = Paper(
        check_id=check.id,
        check_code=check_code(check),
        form=check.form,
        kind=check.kind,
        seed=str(seed),
        blueprint=bp.id,
        rules_version=rules_version,
        profile=prof,
        items=tuple(items),
        not_assessed=profile.not_assessed,
        coverage=cov,
        twin_of_paper=twin_of_paper,
    )
    return _with_hash(paper)


def _with_hash(paper: Paper) -> Paper:
    """The hash covers what the paper is (items, form, versions, profile, seed), not which check
    it is attached to, so the same inputs give the same hash."""
    d = paper.to_dict()
    for k in ("check_id", "check_code", "hash"):
        d.pop(k)
    canon = json.dumps(d, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    h = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    return Paper(**{**paper.__dict__, "hash": h})


def generate_paper(
    check: CheckRef,
    profile: Profile,
    rules: RuleSet,
    blueprint_id: str,
    rules_version: int,
    seed: object,
) -> Paper:
    bp = rules.blueprint(blueprint_id)
    # The print language changes the words, never the numbers: it is left out of the seed.
    prof_key = json.dumps({**asdict(profile), "language": None}, sort_keys=True)
    rng = _rng(seed, bp.id, rules_version, prof_key)
    assessed = [c for c in COMPETENCY_NAMES if c not in profile.not_assessed]
    taken: set[tuple[int, int]] = set()
    items: list[PaperItem] = []
    # Anchors: fixed template and difficulty; a skill not assessed is left off.
    for slot in bp.slots:
        if slot.kind != "anchor" or slot.template is None:
            continue
        t = _template(rules, slot.template)
        if t.competency in profile.not_assessed:
            continue
        a, b = _pick(rng, rules, t, slot.difficulty, taken)
        taken.add((a, b))
        items.append(_item(rules, t, len(items) + 1, slot, a, b, slot.difficulty))
    # Adaptive: the deeper variant first, by weight.
    adaptive_slots = [s for s in bp.slots if s.kind == "adaptive"]
    used: dict[str, int] = {}
    # Grouped by section on the paper (dictation, add, take away), like the anchors.
    alloc = sorted(_allocate(bp, profile.weights, assessed), key=list(COMPETENCY_NAMES).index)
    for slot, comp in zip(adaptive_slots, alloc, strict=False):
        options = bp.adaptive_templates[comp]  # type: ignore[index]
        tid = options[used.get(comp, 0) % len(options)]
        used[comp] = used.get(comp, 0) + 1
        t = _template(rules, tid)
        difficulty = None
        if t.difficulty != "none":
            choices = sorted(
                {
                    d
                    for p in _candidates(_key(rules), t.id, None)
                    if (d := _difficulty(t, *p)) is not None
                }
            )
            difficulty = rng.choice(choices) if choices else None
        a, b = _pick(rng, rules, t, difficulty, taken)
        taken.add((a, b))
        items.append(_item(rules, t, len(items) + 1, slot, a, b, difficulty))
    return _finish(check, seed, bp, rules_version, profile, items, rules)


def make_twin(pre: Paper, rules: RuleSet, check: CheckRef, seed: object) -> Paper:
    """The post-test: a twin of every item of `pre` (same template and difficulty, new numbers),
    never repeating a number pair from `pre`. Built from the pre-test only: never adapted to the
    track or to anything learnt since."""
    bp = rules.blueprint(pre.blueprint)
    rng = _rng(seed, "twin", pre.hash)
    slots = {s.n: s for s in bp.slots}
    avoid = {(i.a, i.b) for i in pre.items}
    items: list[PaperItem] = []
    for it in pre.items:
        t = _template(rules, it.template)
        a, b = _pick(rng, rules, t, it.difficulty, avoid, (it.a, it.b))
        avoid.add((a, b))
        items.append(_item(rules, t, it.n, slots[it.slot], a, b, it.difficulty, twin_of=it.n))
    profile = Profile(
        **{
            **pre.profile,
            "not_assessed": tuple(pre.profile["not_assessed"]),
            "built_from": tuple(pre.profile["built_from"]),
        }
    )
    return _finish(check, seed, bp, pre.rules_version, profile, items, rules, pre.hash)


def pilot_paper(check: CheckRef, rules: RuleSet, rules_version: int, form: str) -> Paper:
    """The pilot's printed Form A (or its twin Form B) as an explicit paper on baseline_10."""
    from engine.forms import PILOT_FORMS

    bp = rules.blueprint("baseline_10")
    src = PILOT_FORMS[form]
    items = []
    for slot, it in zip(bp.slots, src.items, strict=True):
        assert slot.template is not None
        t = _template(rules, slot.template)
        if not _fits(t, it.a, it.b) or _difficulty(t, it.a, it.b) != slot.difficulty:
            raise CannotMeet("constraints", f"pilot item {it.n} does not fit {t.id}")
        items.append(
            _item(rules, t, it.n, slot, it.a, it.b, slot.difficulty, it.n if form == "B" else None)
        )
    profile = baseline_profile("hi")
    twin = _with_hash_of_pilot("A", rules, rules_version) if form == "B" else None
    return _finish(check, f"pilot-{form}", bp, rules_version, profile, items, rules, twin)


def _with_hash_of_pilot(form: str, rules: RuleSet, rules_version: int) -> str:
    ref = CheckRef("pilot", "pre", form, "pilot", 1)
    return pilot_paper(ref, rules, rules_version, form).hash
