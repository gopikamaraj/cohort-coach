"""Eval 1: generated items carry the right wrong answers and no collisions.

For each error type, take N generated problems and compare the engine's wrong-answer set with an
independent oracle written as digit-by-digit column procedures and string building (the engine
uses closed-form arithmetic). Then check, again with the oracle's answers, that no two errors
share a wrong answer and none equals the correct answer.

The oracle is independent of the engine's formulas, not of the spec: the printed pilot answer key
in tests/fixtures/pilot_forms.golden.json is the human reference, checked in tests/engine.

Usage: python -m evals.runners.engine_items [--n 500] [--no-write]
Writes evals/results/engine_items.json. Exit code 1 if the bar is not met.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path
from typing import Any

from engine.bugs import correct_answer, raw_error_answers
from engine.items import generate_form
from engine.model import ErrorCode, Item, ItemType

BASE_SEED = 2026
BAR = {"share_correct": 1.0, "collisions": 0}
RESULT_PATH = Path(__file__).resolve().parents[1] / "results" / "engine_items.json"

ITEM_TYPE_OF = {
    ErrorCode.PV_HEARD: ItemType.DICTATION,
    ErrorCode.PV_REVERSE: ItemType.DICTATION,
    ErrorCode.ADD_NOCARRY: ItemType.ADD_CARRY,
    ErrorCode.SUB_SFL: ItemType.SUB_BORROW,
    ErrorCode.SUB_NODEC: ItemType.SUB_BORROW,
}


def _heard(s: str) -> set[int]:
    """Writes the number as it is said: hundreds digit, "00"/"0", then the rest."""
    h, t, o = s[0], s[1], s[2]
    return {int(h + "00" + t + o), int(h + "0" + t + o), int(h + "00" + t + "0" + o)}


def oracle_answers(code: ErrorCode, item: Item) -> set[int]:
    """The wrong answers a child with this error writes, by column or string procedure."""
    if code in (ErrorCode.PV_HEARD, ErrorCode.PV_REVERSE):
        s = str(item.a)
        if code is ErrorCode.PV_HEARD:
            return _heard(s)
        return {int(s[0] + s[2] + s[1])}
    top, bottom = f"{item.a:02d}", f"{item.b:02d}"
    tens_t, ones_t, tens_b, ones_b = int(top[0]), int(top[1]), int(bottom[0]), int(bottom[1])
    if code is ErrorCode.ADD_NOCARRY:
        ones = (ones_t + ones_b) % 10  # write the ones digit, drop the carried ten
        return {int(str(tens_t + tens_b) + str(ones))}
    if code is ErrorCode.SUB_SFL:
        return {int(str(abs(tens_t - tens_b)) + str(abs(ones_t - ones_b)))}
    if code is ErrorCode.SUB_NODEC:
        if ones_t < ones_b:  # borrow ten for the ones column, forget to cross out the tens
            return {int(str(tens_t - tens_b) + str(ones_t + 10 - ones_b))}
        return {item.a - item.b}
    raise ValueError(code)


def _oracle_collides(item: Item) -> bool:
    """True if the oracle's answers for this item overlap each other or the correct answer."""
    correct = correct_answer(item)
    sets: list[set[int]] = []
    if item.type is ItemType.DICTATION:
        s = str(item.a)
        both = _heard(s[0] + s[2] + s[1])
        sets = [
            oracle_answers(ErrorCode.PV_HEARD, item),
            oracle_answers(ErrorCode.PV_REVERSE, item),
            both,
        ]
    elif item.type is ItemType.ADD_CARRY:
        whole = {int(str(item.a // 10 + item.b // 10) + str(item.a % 10 + item.b % 10))}
        sets = [oracle_answers(ErrorCode.ADD_NOCARRY, item), whole]
    elif item.type is ItemType.SUB_BORROW:
        sets = [oracle_answers(ErrorCode.SUB_SFL, item), oracle_answers(ErrorCode.SUB_NODEC, item)]
    seen: set[int] = {correct}
    for answers in sets:
        if answers & seen:
            return True
        seen |= answers
    return False


def _problems(kind: ItemType, n: int) -> list[Item]:
    items: list[Item] = []
    seed = BASE_SEED
    while len(items) < n:
        items += [i for i in generate_form(seed).items if i.type is kind]
        seed += 1
    return items[:n]


def run(n: int = 500) -> dict[str, Any]:
    per_error: dict[str, dict[str, Any]] = {}
    for code, kind in ITEM_TYPE_OF.items():
        items = _problems(kind, n)
        matched = sum(raw_error_answers(i)[code] == oracle_answers(code, i) for i in items)
        collisions = sum(_oracle_collides(i) for i in items)
        per_error[code.value] = {
            "item_type": kind.value,
            "n": len(items),
            "correct_wrong_answers": matched,
            "share_correct": matched / len(items),
            "collisions": collisions,
        }
    passed = all(
        s["share_correct"] >= BAR["share_correct"] and s["collisions"] <= BAR["collisions"]
        for s in per_error.values()
    )
    return {
        "eval": "engine_items",
        "source": "evals/runners/engine_items.py",
        "date": datetime.date.today().isoformat(),
        "seed": BASE_SEED,
        "problems_per_error": n,
        "bar": BAR,
        "per_error": per_error,
        "passed": passed,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    result = run(args.n)
    for code, s in result["per_error"].items():
        print(
            f"{code:<12} n={s['n']} correct={s['correct_wrong_answers']} "
            f"({s['share_correct']:.0%}) collisions={s['collisions']}"
        )
    print("PASS" if result["passed"] else "FAIL", "(bar: 100% correct, 0 collisions)")
    if not args.no_write:
        RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RESULT_PATH.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
        )
        print(f"wrote {RESULT_PATH.name} in evals/results/")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
