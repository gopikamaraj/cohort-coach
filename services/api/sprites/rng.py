"""A tiny seeded generator shared, step for step, with the TypeScript renderer (xorshift32).

Integer arithmetic only, so Python and TypeScript draw byte-identical SVG from the same seed.
"""

from __future__ import annotations

M = 0xFFFFFFFF


class Rng:
    def __init__(self, seed: int) -> None:
        self.state = ((seed * 2654435761) + 1) & M or 1

    def next(self) -> int:
        x = self.state
        x = (x ^ (x << 13)) & M
        x = (x ^ (x >> 17)) & M
        x = (x ^ (x << 5)) & M
        self.state = x
        return x

    def below(self, n: int) -> int:
        """An integer in 0..n-1."""
        return self.next() % n

    def shuffle(self, items: list[int]) -> list[int]:
        """Fisher-Yates, in place; returns the list."""
        for i in range(len(items) - 1, 0, -1):
            j = self.below(i + 1)
            items[i], items[j] = items[j], items[i]
        return items
