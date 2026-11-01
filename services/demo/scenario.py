"""The demo class: children, their answers on the demo paper, the answer file and the truth.

Pure code, seeded. Each child gets a hidden set of errors from the scenario's planted counts; the
child model of the simulated block (data/synthetic/block.py `_answer`) then writes each answer,
through the engine's error functions. The truth is what the child wrote. The answer file
(reads.json) is what a reader would return for each sheet: the truth with a confidence, low on
the hard cases.
No names: children are roll numbers.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

import yaml

from data.synthetic.block import _answer as block_answer
from data.synthetic.block import load_config
from engine.diagnosis import class_profile, diagnose_child
from engine.forms import PILOT_FORMS
from engine.model import ClassProfile, Form, Reading

ROOT = Path(__file__).resolve().parents[2]
SCENARIOS = ROOT / "demo" / "scenarios"
HARD = ("smudge", "crossed", "blank")


@cache
def load_scenario(name: str = "class_3a") -> dict[str, Any]:
    if not name.replace("_", "").isalnum():
        raise ValueError("bad scenario name")
    data = yaml.safe_load((SCENARIOS / f"{name}.yaml").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


@dataclass(frozen=True)
class DemoChild:
    roll: int
    errors: frozenset[str]  # hidden: never shown to the teacher
    answers: tuple[str, ...]  # the truth: what the child wrote ("" for an empty box)
    hard: str | None  # smudge | crossed | blank
    hard_item: int | None  # the box (0-based) that is hard to read
    marks: bool  # writes small carry and borrow marks


@dataclass(frozen=True)
class DemoClass:
    """`form_key` names the paper the children answered (its id, or a built-in form before a paper
    is made); `form` holds that paper's items, from which every answer is written."""

    scenario: str
    seed: int
    class_code: str
    form_key: str
    children: tuple[DemoChild, ...]
    paper_form: Form | None = None

    @property
    def form(self) -> Form:
        return self.paper_form or PILOT_FORMS[self.form_key]

    def sheet_name(self, roll: int) -> str:
        return f"{self.class_code}-roll{roll:02d}.png"


def build_class(
    scenario: dict[str, Any],
    seed: int | None = None,
    form_key: str | None = None,
    paper: tuple[str, Form] | None = None,
) -> DemoClass:
    """The demo class, deterministic in the seed (the scenario's own unless one is given)."""
    seed = int(scenario["seed"] if seed is None else seed)
    # the paper made in step 2 (its id and items); before it exists, the scenario's built-in form
    form_key = paper[0] if paper else (form_key or str(scenario["form"]))
    form = paper[1] if paper else PILOT_FORMS[form_key]
    n = int(scenario["strength"])
    rolls = list(range(1, n + 1))
    rng = random.Random(f"{seed}|demo|{scenario['id']}|{form_key}")
    errors: dict[int, set[str]] = {r: set() for r in rolls}
    for code, count in sorted(scenario["plant"].items()):
        for r in rng.sample(rolls, int(count)):
            errors[r].add(code)
    child_cfg = load_config()["child"]
    hard = {int(roll): kind for kind, roll in scenario.get("hard_cases", {}).items()}
    out = []
    for r in rolls:
        crng = random.Random(f"{seed}|demo|{scenario['id']}|{form_key}|child|{r}")
        answers = [
            str(block_answer(crng, item, frozenset(errors[r]), child_cfg)) for item in form.items
        ]
        kind = hard.get(r)
        hard_item = None
        if kind:
            hard_item = crng.randrange(2, len(answers))  # a sum, not a dictation box
            if kind == "blank":
                answers[hard_item] = ""
        out.append(
            DemoChild(
                roll=r,
                errors=frozenset(errors[r]),
                answers=tuple(answers),
                hard=kind,
                hard_item=hard_item,
                marks=crng.random() < float(scenario.get("marks_share", 0.0)),
            )
        )
    return DemoClass(
        str(scenario["id"]),
        seed,
        str(scenario["class_code"]),
        form_key,
        tuple(out),
        paper[1] if paper else None,
    )


def post_class(
    scenario: dict[str, Any], pre: DemoClass, twin: tuple[str, Form] | None = None
) -> DemoClass:
    """Optional step 12: the same children on the twin paper after the track (the post-test made
    with the pre-test). A child's error goes with the scenario's planted chance; everything else is
    drawn as before."""
    rng = random.Random(f"{pre.seed}|demo|{scenario['id']}|post")
    fixed = scenario.get("post", {}).get("fixed_share", {})
    key, form = twin if twin else ("B", PILOT_FORMS["B"])
    child_cfg = load_config()["child"]
    out = []
    for c in pre.children:
        kept = frozenset(e for e in sorted(c.errors) if rng.random() >= float(fixed.get(e, 0.0)))
        crng = random.Random(f"{pre.seed}|demo|{scenario['id']}|post|child|{c.roll}")
        answers = tuple(str(block_answer(crng, item, kept, child_cfg)) for item in form.items)
        out.append(DemoChild(c.roll, kept, answers, None, None, c.marks))
    return DemoClass(
        pre.scenario, pre.seed, pre.class_code, key, tuple(out), form if twin else None
    )


def _reading(text: str) -> Reading:
    return "blank" if text == "" else int(text)


def truth_profile(demo: DemoClass) -> ClassProfile:
    """The class profile the true answers give (for tests and the reading summary, never shown)."""
    return class_profile(
        [diagnose_child(demo.form, [_reading(a) for a in c.answers]) for c in demo.children]
    )


def _confidence(rng: random.Random) -> float:
    return round(rng.uniform(0.93, 0.995), 3)


def reads_file(demo: DemoClass, check_code: str, paper_hash: str) -> dict[str, Any]:
    """reads.json: what a reader would return for each sheet. The hard boxes get a low confidence
    and the "check" status, so the review step matters. It carries no hidden error and no name."""
    sheets: dict[str, Any] = {}
    for c in demo.children:
        rng = random.Random(f"{demo.seed}|reads|{c.roll}")
        cells = []
        for i, text in enumerate(c.answers):
            if text == "":
                cells.append({"text": "", "status": "blank", "confidence": 0.99})
            elif i == c.hard_item and c.hard in ("smudge", "crossed"):
                low = 0.41 if c.hard == "smudge" else 0.55
                cells.append({"text": text, "status": "check", "confidence": low})
            else:
                cells.append({"text": text, "status": "ok", "confidence": _confidence(rng)})
        sheets[demo.sheet_name(c.roll)] = {
            "roll": c.roll,
            "cells": cells,
            "hard": c.hard,
        }
    return {
        "demo": True,
        "label": "Demo answer file: synthetic sheets, not real children's work",
        "scenario": demo.scenario,
        "seed": demo.seed,
        "class_code": demo.class_code,
        "form": demo.form_key,
        "check_code": check_code,
        "paper_hash": paper_hash,
        "sheets": sheets,
    }


def truth_file(demo: DemoClass) -> dict[str, Any]:
    """truth.json: what each child actually wrote. Used only to score AI reads in the demo reading
    summary; the app never shows it."""
    return {
        "demo": True,
        "seed": demo.seed,
        "form": demo.form_key,
        "answers": {str(c.roll): list(c.answers) for c in demo.children},
    }
