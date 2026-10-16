"""Code validators (gate 1) and the rule-based pre-filter (gate 1b).

A validator returns a list of `Violation`. Violations carry a code and a short detail made from
facts (numbers, counts), never a copy of teacher text, so they are safe to log.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Violation:
    code: str
    detail: str = ""


@dataclass(frozen=True)
class ValidatorResult:
    name: str
    violations: tuple[Violation, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.violations

    @property
    def codes(self) -> list[str]:
        return [v.code for v in self.violations]
