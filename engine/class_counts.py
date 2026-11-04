"""A class's counts, worked out from the entered answers and the paper's own form: the one place the numbers behind
the coach and officer views come from (decided 3 Nov 2026, DECISIONS.md). The phone also writes counts with each
class result, but the server does not trust them: it recomputes from the answers it holds, so a number on an
officer page is always the engine's, never a copy that could have drifted.

Pure: no I/O. Counts only; nothing per child leaves this function.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from engine.diagnosis import RULE_CONFIRMED, RULE_POSSIBLE, counts_for_rule, diagnose_child
from engine.model import ErrorCode, Form, Mark
from engine.normalize import normalize_answer


@dataclass(frozen=True)
class ClassCount:
    children_checked: int
    confirmed: dict[str, int] = field(default_factory=dict)  # children who show the error on two or more questions (the 2-item rule)
    seen_once: dict[str, int] = field(default_factory=dict)  # children who made the error on one or more questions

    def under(self, min_hits: int) -> dict[str, int]:
        """The counts under the rule: 2 confirmed, 1 possible."""
        return counts_for_rule(self.confirmed, self.seen_once, min_hits)


def count_class(form: Form, rows: Sequence[Sequence[str]], absent: Sequence[int] = (), only_items: frozenset[int] | None = None) -> ClassCount:
    """Children checked and children per error, from each entered row (a row with no answer typed is not a child
    checked, and an absent roll is skipped). With `only_items` (item numbers) only those items are read: a
    before-and-after uses the anchor items alone, because adaptive items never count in a comparison."""
    keep = [q for q, item in enumerate(form.items) if only_items is None or item.n in only_items]
    if len(keep) != len(form.items):
        form = Form(form.label, tuple(form.items[q] for q in keep))
    skip = {int(i) for i in absent}
    checked = 0
    confirmed: dict[str, int] = {}
    once: dict[str, int] = {}
    for i, row in enumerate(rows):
        if i in skip or not any(str(c).strip() for c in row):
            continue
        cells = [str(row[q]) if q < len(row) else "" for q in keep]
        child = diagnose_child(form, [normalize_answer(c if c.strip() else None) for c in cells])
        checked += 1
        for code in child.shows:
            confirmed[code.value] = confirmed.get(code.value, 0) + 1
        seen: set[ErrorCode] = set()
        for mark in child.marks:
            if mark.kind is Mark.ERROR:
                seen.update(mark.codes)
        for code in seen:
            once[code.value] = once.get(code.value, 0) + 1
    return ClassCount(checked, confirmed, once)


__all__ = ["RULE_CONFIRMED", "RULE_POSSIBLE", "ClassCount", "count_class"]
