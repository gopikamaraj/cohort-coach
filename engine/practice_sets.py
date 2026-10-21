"""Practice sets for the tracks: two levels (without regrouping, then with), never a check item.

The pilot forms stay a clean measure only if no lesson or practice set teaches their items, so
every pair on Form A or Form B (either order) is excluded here. Pure and deterministic in `seed`.
"""

from __future__ import annotations

import random
from typing import Literal

from engine.forms import PILOT_FORMS
from engine.items import is_valid
from engine.model import Item, ItemType

Kind = Literal["sub", "add"]
Level = Literal[1, 2]


def check_pairs() -> frozenset[frozenset[int]]:
    """Every computation item on every pilot form, as an unordered pair of numbers."""
    return frozenset(
        frozenset((item.a, item.b))
        for form in PILOT_FORMS.values()
        for item in form.items
        if item.type is not ItemType.DICTATION
    )


def _candidates(kind: Kind, level: Level) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for a in range(20, 100):
        for b in range(11, a):
            ao, bo = a % 10, b % 10
            if kind == "sub":
                regroup = ao < bo
                if (level == 2) != regroup or a // 10 == b // 10:
                    continue
                if regroup and not is_valid(Item(0, ItemType.SUB_BORROW, a, b)):
                    continue
            else:
                if b >= 100 or a + b > 99 and level == 1:
                    continue
                carry = ao + bo >= 10
                if (level == 2) != carry:
                    continue
                if carry and not is_valid(Item(0, ItemType.ADD_CARRY, a, b)):
                    continue
            out.append((a, b))
    return out


def practice_set(kind: Kind, level: Level, seed: int, n: int = 6) -> list[tuple[int, int]]:
    """`n` problems (a, b), subtraction a - b or addition a + b; none is a check item."""
    banned = check_pairs()
    pool = [p for p in _candidates(kind, level) if frozenset(p) not in banned]
    return random.Random(seed).sample(pool, n)
