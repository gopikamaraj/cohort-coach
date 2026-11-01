"""A made-up class of 16 on Form A for the results-page tests, with the engine's own reading of it.

Writes apps/pwa/e2e/fixtures/results16.json: the answers each roll types (no child, no real data), and
what the Python engine says about every cell, every child and the class. The browser tests compare
what the results page shows with this file, so the page is checked against the engine, not against
itself. `--check` fails if the file is out of date.

    python scripts/make_results16.py [--check]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.bugs import correct_answer  # noqa: E402
from engine.diagnosis import class_profile, diagnose_child  # noqa: E402
from engine.forms import PILOT_FORMS  # noqa: E402
from engine.normalize import normalize_answer  # noqa: E402

OUT = ROOT / "apps" / "pwa" / "e2e" / "fixtures" / "results16.json"
FORM = "A"

# Form A: 1 and 2 dictation (346, 728), 3-5 carrying, 6 simple subtraction, 7-10 borrowing.
# Each child is the correct answers with these question numbers changed to these answers.
CHILDREN: list[dict[int, str]] = [
    {},  # 1 all correct
    {},  # 2 all correct
    {10: "50"},  # 3 one wrong answer that matches no mistake
    {7: "42", 8: "34", 9: "57", 10: "66"},  # 4 takes the smaller digit from the larger on four
    {7: "42", 9: "57"},  # 5 the same mistake on two
    {8: "34"},  # 6 the same mistake once: possible, not confirmed
    {7: "42", 8: "34", 9: "57"},  # 7
    {7: "48", 8: "36"},  # 8 borrows but does not reduce the tens
    {9: "53", 10: "64"},  # 9
    {1: "3046", 2: "7028"},  # 10 writes numbers as they sound
    {1: "364", 2: "782", 3: "75", 4: "64"},  # 11 swaps tens and ones; drops the carried ten
    {3: "75", 4: "64", 5: "72"},  # 12 drops the carried ten on all three
    {5: "11", 6: "", 7: "42"},  # 13 one box left blank, one wrong answer with no mistake, one SFL
    {1: "30046", 2: "999"},  # 14 heard once (possible) and a wrong answer with no mistake
    {
        3: "75",
        4: "614",
        7: "42",
        8: "34",
    },  # 15 drops a carry once; writes both totals (untracked); SFL twice
    {1: "3046", 2: "70028", 7: "42", 10: "66"},  # 16 heard twice; SFL twice
]


def rows() -> list[list[str]]:
    form = PILOT_FORMS[FORM]
    base = [str(correct_answer(item)) for item in form.items]
    return [[patch.get(q + 1, v) for q, v in enumerate(base)] for patch in CHILDREN]


def build() -> dict[str, object]:
    form = PILOT_FORMS[FORM]
    table = rows()
    children = []
    for i, row in enumerate(table):
        d = diagnose_child(form, [normalize_answer(cell or None) for cell in row])
        children.append(
            {
                "roll": i + 1,
                "answers": row,
                "cells": [
                    {"kind": m.kind.value, "codes": sorted(c.value for c in m.codes)}
                    for m in d.marks
                ],
                "shows": sorted(c.value for c in d.shows),
            }
        )
    profile = class_profile(
        [diagnose_child(form, [normalize_answer(c or None) for c in r]) for r in table]
    )
    return {
        "form": FORM,
        "children": children,
        "class": {
            "checked": profile.children_checked,
            "counts": {k.value: v for k, v in profile.counts.items()},
            "track": profile.track.value if profile.track else None,
            "untracked": dict(profile.untracked),
        },
    }


def render() -> str:
    return json.dumps(build(), indent=2, ensure_ascii=False) + "\n"


def main(argv: list[str]) -> int:
    text = render()
    if "--check" in argv:
        same = OUT.exists() and OUT.read_text(encoding="utf-8") == text
        print(("ok    " if same else "STALE ") + str(OUT.relative_to(ROOT)))
        return 0 if same else 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
