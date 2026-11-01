"""The two-class scenario: a paper per class and made-up children's answers, all by code.

SIMULATED. Each child's answers start right; each pattern the scenario gives that child then writes
the engine's own wrong answer on the pattern's items (an error function), or the other operation
for confusing signs. The engine's error finder then gives the class counts. Only counts leave here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from engine.bugs import correct_answer, error_answers
from engine.diagnosis import class_profile, diagnose_child
from engine.model import ErrorCode, Form, Item, ItemType, Reading

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "demo" / "scenarios"
DEFAULT = "two_classes_pilot_like"


@cache
def load(name: str = DEFAULT) -> dict[str, Any]:
    data = yaml.safe_load((SCENARIOS / f"{name}.yaml").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _item(n: int, op: str, a: int, b: int) -> Item:
    if op == "dictate":
        return Item(n, ItemType.DICTATION, a)
    if op == "add":
        return Item(n, ItemType.ADD_CARRY, a, b)
    kind = ItemType.SUB_BORROW if a % 10 < b % 10 else ItemType.SUB_ANCHOR
    return Item(n, kind, a, b)


def paper_items(scenario: dict[str, Any], code: str) -> list[dict[str, Any]]:
    """The class's paper as items {n, operation, a, b}: its dictation numbers, then the rest."""
    cls = class_of(scenario, code)
    out = [
        {"n": int(n), "operation": "dictate", "a": int(v), "b": 0}
        for n, v in sorted(cls["dictation"].items(), key=lambda kv: int(kv[0]))
    ]
    out += [
        {"n": int(it["n"]), "operation": it["op"], "a": int(it["a"]), "b": int(it["b"])}
        for it in scenario["paper"]["items"]
    ]
    return sorted(out, key=lambda it: it["n"])


def form_for(scenario: dict[str, Any], code: str) -> Form:
    items = tuple(
        _item(it["n"], it["operation"], it["a"], it["b"]) for it in paper_items(scenario, code)
    )
    return Form(f"{scenario['paper']['name']} · {code}", items)


def class_of(scenario: dict[str, Any], code: str) -> dict[str, Any]:
    for c in scenario["classes"]:
        if c["code"] == code:
            return dict(c)
    raise KeyError(code)


def _pattern_answer(item: Item, error: str) -> int:
    if error == "IN-OP":
        return item.a + item.b if item.type is not ItemType.ADD_CARRY else abs(item.a - item.b)
    wrong = error_answers(item).get(ErrorCode(error))
    if not wrong:
        raise ValueError(f"item {item.n} has no {error} answer")
    return min(wrong)


def answers(scenario: dict[str, Any], code: str) -> list[list[Reading]]:
    """Each child's answers, in roll order of the children with a sheet."""
    form = form_for(scenario, code)
    by_n = {it.n: it for it in form.items}
    patterns = scenario["patterns"]
    rows: list[list[Reading]] = []
    for kinds in class_of(scenario, code)["children"]:
        row: dict[int, Reading] = {it.n: correct_answer(it) for it in form.items}
        for kind in kinds:
            p = patterns[kind]
            for n in p["items"]:
                row[int(n)] = _pattern_answer(by_n[int(n)], str(p["error"]))
        rows.append([row[it.n] for it in form.items])
    return rows


@dataclass(frozen=True)
class ClassCounts:
    """One class's check as the server keeps it: counts only."""

    code: str
    teacher: str
    language: str
    grade: int
    medium: str
    children_checked: int
    counts: dict[str, int]
    possible: dict[str, int] = field(default_factory=dict)
    source: str = "synthetic"  # synthetic | phone | pilot

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "teacher": self.teacher,
            "language": self.language,
            "grade": self.grade,
            "medium": self.medium,
            "children_checked": self.children_checked,
            "counts": dict(self.counts),
            "possible": dict(self.possible),
            "source": self.source,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> ClassCounts:
        return ClassCounts(
            code=str(d["code"]),
            teacher=str(d["teacher"]),
            language=str(d["language"]),
            grade=int(d["grade"]),
            medium=str(d["medium"]),
            children_checked=int(d["children_checked"]),
            counts={k: int(v) for k, v in d["counts"].items()},
            possible={k: int(v) for k, v in (d.get("possible") or {}).items()},
            source=str(d.get("source", "synthetic")),
        )


def counts_from_rows(
    form: Form, rows: list[list[Reading]]
) -> tuple[int, dict[str, int], dict[str, int]]:
    """The engine's error finder over the children's answers: checked, counts, possible counts."""
    profile = class_profile([diagnose_child(form, r) for r in rows])
    counts = {c.value: int(n) for c, n in profile.counts.items() if n}
    possible = {c.value: int(n) for c, n in profile.possible_counts.items() if n}
    return profile.children_checked, counts, possible


def synthetic_class(scenario: dict[str, Any], code: str) -> ClassCounts:
    cls = class_of(scenario, code)
    teacher = str(cls["teacher"])
    checked, counts, possible = counts_from_rows(form_for(scenario, code), answers(scenario, code))
    return ClassCounts(
        code=code,
        teacher=teacher,
        language=str(scenario["teachers"][teacher]["language"]),
        grade=int(scenario["grade"]),
        medium=str(scenario["medium"]),
        children_checked=checked,
        counts=counts,
        possible=possible,
        source="synthetic",
    )
