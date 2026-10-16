"""Item constraints, collision checks and the (parallel) form generator.

Every constraint here is a rule from CLAUDE.md section 5. Nothing here calls an AI.
"""

from __future__ import annotations

import random
from functools import cache

from engine.bugs import (
    add_whole_ones,
    both_heard_and_reversed,
    correct_answer,
    probes,
    raw_error_answers,
)
from engine.model import Form, Item, ItemType

# The check: 2 dictation, 3 addition with carrying, 1 anchor subtraction, 4 with borrowing.
FORM_LAYOUT: tuple[ItemType, ...] = (
    ItemType.DICTATION,
    ItemType.DICTATION,
    ItemType.ADD_CARRY,
    ItemType.ADD_CARRY,
    ItemType.ADD_CARRY,
    ItemType.SUB_ANCHOR,
    ItemType.SUB_BORROW,
    ItemType.SUB_BORROW,
    ItemType.SUB_BORROW,
    ItemType.SUB_BORROW,
)


def constraint_problems(item: Item) -> list[str]:
    """Structural rules per item type. Empty list = the item has the right shape."""
    out: list[str] = []
    a, b = item.a, item.b
    at, ao, bt, bo = a // 10, a % 10, b // 10, b % 10
    match item.type:
        case ItemType.DICTATION:
            if not 100 <= a <= 999:
                out.append("dictation number must have 3 digits")
            else:
                h, t, o = a // 100, a // 10 % 10, a % 10
                if 0 in (h, t, o):
                    out.append("dictation digits must be non-zero")
                if t == o:
                    out.append("dictation tens and ones digits must differ")
        case ItemType.ADD_CARRY:
            if not (10 <= a <= 99 and 10 <= b <= 99):
                out.append("addition operands must have 2 digits")
            if ao + bo < 10:
                out.append("addition must carry (ones total at least 10)")
            if a + b > 99:
                out.append("addition sum must be at most 99")
        case ItemType.SUB_ANCHOR:
            if not (10 <= a <= 99 and 10 <= b <= 99):
                out.append("subtraction operands must have 2 digits")
            if ao < bo:
                out.append("anchor subtraction must not borrow")
            if at <= bt:
                out.append("anchor tens digit must be larger")
        case ItemType.SUB_BORROW:
            if not (10 <= a <= 99 and 10 <= b <= 99):
                out.append("subtraction operands must have 2 digits")
            if ao >= bo:
                out.append("borrowing subtraction needs a smaller ones digit in the first number")
            if at <= bt:
                out.append("borrowing subtraction needs a larger tens digit in the first number")
            if bo - ao == 5:
                out.append("ones-digit gap of 5 is not allowed")
            if a - b < 10:
                out.append("borrowing subtraction result must be at least 10")
    return out


def collision_problems(item: Item) -> list[str]:
    """Rules that stop an item from telling two causes apart (or hiding an error)."""
    out: list[str] = []
    correct = correct_answer(item)
    raw = raw_error_answers(item)
    for code in probes(item):
        answers = raw.get(code, frozenset())
        if not answers:
            out.append(f"{code} has no wrong answer on this item")
        elif correct in answers:
            out.append(f"{code} answer equals the correct answer {correct}")
    codes = list(raw)
    for i, first in enumerate(codes):
        for second in codes[i + 1 :]:
            shared = raw[first] & raw[second]
            if shared:
                out.append(f"{first} and {second} give the same wrong answer {min(shared)}")
    both = both_heard_and_reversed(item)
    for code, answers in raw.items():
        if both & answers:
            out.append(f"heard-and-reversed answer {min(both & answers)} collides with {code}")
    if correct in both:
        out.append("heard-and-reversed answer equals the correct answer")
    if item.type is ItemType.ADD_CARRY:
        untracked = add_whole_ones(item.a, item.b)
        for code, answers in raw.items():
            if untracked & answers:
                out.append(f"untracked whole-ones answer collides with {code}")
        if correct in untracked:
            out.append("untracked whole-ones answer equals the correct answer")
    return out


def validate_item(item: Item) -> list[str]:
    """All reasons the item is not usable. Empty list = valid."""
    problems = constraint_problems(item)
    # Collision checks assume a well-formed item, but a bad shape can collide too (gap of 5),
    # so run them whenever the operands are in range.
    in_range = item.type is ItemType.DICTATION and 100 <= item.a <= 999
    in_range = in_range or (
        item.type is not ItemType.DICTATION and 10 <= item.a <= 99 and 10 <= item.b <= 99
    )
    if in_range:
        problems += collision_problems(item)
    return problems


def is_valid(item: Item) -> bool:
    return not validate_item(item)


def parallel_signature(form: Form) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """(ones totals of the addition items, ones gaps of the borrowing items) in item order."""
    totals = tuple(i.a % 10 + i.b % 10 for i in form.items if i.type is ItemType.ADD_CARRY)
    gaps = tuple(i.b % 10 - i.a % 10 for i in form.items if i.type is ItemType.SUB_BORROW)
    return totals, gaps


@cache
def _valid_shape(kind: ItemType, a: int, b: int) -> bool:
    """Validity ignores the item number, so cache by (type, a, b)."""
    return is_valid(Item(0, kind, a, b))


def _dictation_candidates() -> list[Item]:
    return [
        Item(0, ItemType.DICTATION, 100 * h + 10 * t + o)
        for h in range(1, 10)
        for t in range(1, 10)
        for o in range(1, 10)
        if t != o
    ]


def _add_candidates(total: int) -> list[Item]:
    return [
        Item(0, ItemType.ADD_CARRY, 10 * at + ao, 10 * bt + (total - ao))
        for at in range(1, 10)
        for bt in range(1, 10)
        for ao in range(1, 10)
        if 1 <= total - ao <= 9
    ]


def _anchor_candidates() -> list[Item]:
    return [
        Item(0, ItemType.SUB_ANCHOR, 10 * at + ao, 10 * bt + bo)
        for at in range(2, 10)
        for bt in range(1, at)
        for ao in range(0, 10)
        for bo in range(0, ao + 1)
    ]


def _borrow_candidates(gap: int) -> list[Item]:
    return [
        Item(0, ItemType.SUB_BORROW, 10 * at + ao, 10 * bt + ao + gap)
        for at in range(3, 10)
        for bt in range(1, at - 1)
        for ao in range(0, 10 - gap)
    ]


def _pick(
    rng: random.Random,
    candidates: list[Item],
    n: int,
    old: Item | None,
    taken: set[tuple[int, int]],
) -> Item:
    """Choose a valid candidate whose numbers differ from `old` and from earlier picks."""
    pool = [
        c
        for c in candidates
        if _valid_shape(c.type, c.a, c.b)
        and (old is None or (c.a != old.a and (c.type is ItemType.DICTATION or c.b != old.b)))
        and (c.a, c.b) not in taken
    ]
    chosen = rng.choice(pool)
    taken.add((chosen.a, chosen.b))
    return Item(n, chosen.type, chosen.a, chosen.b)


def generate_form(seed: int, like: Form | None = None) -> Form:
    """A 10-item check, deterministic in `seed`.

    With `like`, a parallel form: the same ones totals in items 3-5 and the same ones gaps in
    items 7-10, with every number different from `like`'s item at the same position.
    """
    rng = random.Random(seed)
    if like is None:
        totals = tuple(rng.sample(range(10, 18), 3))
        gaps = tuple(rng.sample([1, 2, 3, 4, 6, 7, 8, 9], 4))
        olds: list[Item | None] = [None] * 10
    else:
        totals, gaps = parallel_signature(like)
        olds = list(like.items)
    items: list[Item] = []
    taken: set[tuple[int, int]] = set()
    add_i = borrow_i = 0
    for pos, kind in enumerate(FORM_LAYOUT):
        n = pos + 1
        match kind:
            case ItemType.DICTATION:
                cands = _dictation_candidates()
            case ItemType.ADD_CARRY:
                cands = _add_candidates(totals[add_i])
                add_i += 1
            case ItemType.SUB_ANCHOR:
                cands = _anchor_candidates()
            case ItemType.SUB_BORROW:
                cands = _borrow_candidates(gaps[borrow_i])
                borrow_i += 1
        items.append(_pick(rng, cands, n, olds[pos], taken))
    label = f"Generated form (seed {seed})" if like is None else f"Parallel form (seed {seed})"
    return Form(label, tuple(items))
