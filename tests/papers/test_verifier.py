"""The independent verifier: it shares no code with the generator, recomputes every key and wrong
answer from the operands, and names the item and the rule of anything wrong."""

from __future__ import annotations

import ast
import copy
from pathlib import Path
from typing import Any

from services.papers import generator as g
from services.papers import verifier as v
from services.papers.rules import seed_rules

RULES = seed_rules()
PRE = g.CheckRef(id="c-1:1", kind="pre", form="A", class_label="3A", term=1)
POST = g.CheckRef(id="c-1:2", kind="post", form="B", class_label="3A", term=2)
PROFILE = g.baseline_profile("en")


def good() -> dict[str, Any]:
    return g.generate_paper(PRE, PROFILE, RULES, "standard_10_5", 1, 3).to_dict()


def rules_of(findings: list[v.Finding]) -> set[str]:
    return {f.rule for f in findings}


def test_the_verifier_imports_nothing_from_the_generator_or_the_engine() -> None:
    src = Path(v.__file__).read_text(encoding="utf-8")
    names: set[str] = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    assert not {n for n in names if n.startswith(("engine", "services", "ai"))}, names


def test_generated_papers_pass_every_check() -> None:
    for seed in range(15):
        p = g.generate_paper(PRE, PROFILE, RULES, "standard_10_5", 1, seed)
        b = g.make_twin(p, RULES, POST, seed)
        assert v.verify_items(p.to_dict()) == []
        assert v.verify_items(b.to_dict(), twin_source=p.to_dict()) == []


def test_the_pilot_papers_pass_every_check() -> None:
    a = g.pilot_paper(PRE, RULES, 1, "A").to_dict()
    b = g.pilot_paper(POST, RULES, 1, "B").to_dict()
    assert v.verify_items(a) == [] and v.verify_items(b, twin_source=a) == []


def test_a_deliberately_broken_key_is_caught_and_names_the_item() -> None:
    p = good()
    p["items"][3]["correct"] += 1
    found = v.verify_items(p)
    assert "key" in rules_of(found)
    assert any(f.item == 4 for f in found if f.rule == "key")


def test_a_broken_wrong_answer_is_caught() -> None:
    p = good()
    p["items"][7]["wrong"]["SUB-SFL"] = [11]
    assert "wrong_answers" in rules_of(v.verify_items(p))


def test_a_wrong_answer_equal_to_the_key_is_caught() -> None:
    p = good()
    p["items"][2]["wrong"]["ADD-NOCARRY"] = [p["items"][2]["correct"]]
    assert "wrong_equals_key" in rules_of(v.verify_items(p))


def test_coverage_below_two_items_is_caught() -> None:
    p = good()
    p["items"] = [i for i in p["items"] if i["operation"] != "dictate"]
    found = [f for f in v.verify_items(p) if f.rule == "coverage"]
    assert any("PV-HEARD" in f.detail for f in found)


def test_an_item_that_cannot_tell_two_errors_apart_is_caught() -> None:
    p = good()
    it = p["items"][6]
    it.update(a=52, b=27, correct=25, wrong={"SUB-SFL": [35], "SUB-NODEC": [35]})
    assert "discrimination" in rules_of(v.verify_items(p))


def test_a_duplicate_item_is_caught() -> None:
    p = good()
    p["items"][4] = {**copy.deepcopy(p["items"][3]), "n": 5}
    assert "duplicate" in rules_of(v.verify_items(p))


def test_a_twin_that_changes_difficulty_or_repeats_a_pair_is_caught() -> None:
    a = g.generate_paper(PRE, PROFILE, RULES, "baseline_10", 1, 1)
    b = g.make_twin(a, RULES, POST, 1).to_dict()
    bad = copy.deepcopy(b)
    x = a.items[2]  # an addition anchor: copy Form A's numbers into the twin
    bad["items"][2].update(a=x.a, b=x.b, correct=x.correct, wrong=x.wrong, untracked=x.untracked)
    assert "twin" in rules_of(v.verify_items(bad, twin_source=a.to_dict()))
    bad = copy.deepcopy(b)
    bad["items"] = bad["items"][:-1]
    assert "twin" in rules_of(v.verify_items(bad, twin_source=a.to_dict()))


def test_missing_strings_and_missing_glyphs_are_caught() -> None:
    packs = {p.lang: dict(p.strings) for p in RULES.string_packs}
    assert v.verify_strings(packs, v.FONTS) == []
    broken = copy.deepcopy(packs)
    broken["ta"].pop("sec.add")
    assert "strings" in rules_of(v.verify_strings(broken, v.FONTS))
    broken = copy.deepcopy(packs)
    broken["hi"]["sec.add"] = "जोड़ो 加"  # a CJK glyph no paper font has
    found = v.verify_strings(broken, v.FONTS)
    assert "glyphs" in rules_of(found) and any("加" in f.detail for f in found)


def test_boxes_off_the_page_overlapping_or_text_overflowing_are_caught() -> None:
    page = {"w": 210.0, "h": 297.0}
    ok = {
        "page": page,
        "pages": 1,
        "boxes": [
            {"id": "a1", "page": 1, "x": 20, "y": 20, "w": 40, "h": 15},
            {"id": "a2", "page": 1, "x": 70, "y": 20, "w": 40, "h": 15},
        ],
        "overflow": [],
    }
    assert v.verify_layout(ok) == []
    off = copy.deepcopy(ok)
    off["boxes"][1]["x"] = 190
    assert "overflow" in rules_of(v.verify_layout(off))
    lap = copy.deepcopy(ok)
    lap["boxes"][1]["x"] = 50
    assert "overlap" in rules_of(v.verify_layout(lap))
    spill = copy.deepcopy(ok)
    spill["overflow"] = [{"id": "sec.add", "need_mm": 80.0, "have_mm": 60.0}]
    assert "overflow" in rules_of(v.verify_layout(spill))
