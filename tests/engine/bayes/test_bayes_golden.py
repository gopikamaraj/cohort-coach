"""Golden cases G1 to G7 (docs/BAYESIAN-MODEL.md 7.3), checked by the independent oracle
(evals/runners/bayes_oracle.py) against engine/bayes, plus 1,000 random cases."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from engine.bugs import sub_nodec, sub_sfl
from evals.runners import bayes_oracle

ORACLE = Path(bayes_oracle.__file__)


def test_the_bug_functions_give_the_numbers_the_spec_assumes() -> None:
    # If these ever differ, stop and report: the bug functions are not changed for the model.
    assert sub_sfl(52, 29) - {23} == {37}
    assert sub_nodec(52, 29) - {23} == {33}
    assert sub_sfl(58, 23) == {35} and sub_nodec(58, 23) == {35}


def test_the_oracle_does_not_import_engine_bayes_or_the_simulator_at_top_level() -> None:
    tree = ast.parse(ORACLE.read_text(encoding="utf-8"))
    top: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            top += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            top.append(node.module or "")
    assert not [m for m in top if m.startswith(("engine.bayes", "engine.simulator"))], top
    assert "engine.bugs" in top
    # the oracle's own formulas never touch engine/bayes: only compare() and compare_golden() do
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name not in ("compare", "compare_golden"):
            assert "engine.bayes" not in ast.unparse(node), node.name


@pytest.fixture(scope="module")
def golden() -> dict:  # type: ignore[type-arg]
    return bayes_oracle.compare_golden()


@pytest.mark.parametrize("case", ["G1", "G2", "G3", "G4", "G5", "G6", "G7"])
def test_golden_case_matches_the_spec_and_the_engine(case: str, golden: dict) -> None:  # type: ignore[type-arg]
    assert golden["spec_values_pass"][case], golden["oracle"][case]
    assert golden["engine_vs_oracle"][case] <= 1e-9


def test_golden_values() -> None:
    g = bayes_oracle.compare_golden()["engine"]
    assert g["G1"] == pytest.approx([0.05, 0.95, 0.25, 0.75])
    assert g["G2"] == 1.0
    assert round(g["G3"], 4) == 0.7109
    assert [round(x, 4) for x in g["G4"]] == [0.4583, 0.4984]
    assert round(g["G5"][0], 4) == 0.03 and round(g["G5"][1], 4) == 0.0110
    assert {h: round(v, 4) for h, v in g["G6"].items()} == {
        "none": 0.1739,
        "target": 0.7391,
        "sibling": 0.0435,
        "no_method": 0.0435,
    }
    assert round(g["G7"][0], 4) == 0.7136 and g["G7"][1] == pytest.approx(0.0, abs=1e-12)


def test_g7_the_planner_chooses_the_item_with_more_information() -> None:
    import numpy as np

    from engine.bayes import belief as bel
    from engine.bayes import response as resp
    from engine.bayes import state as st
    from engine.bayes.content import load_params
    from engine.bayes.planner import roles_for
    from engine.model import ErrorCode
    from engine.simulator import Problem

    p = load_params().defaults
    roles = roles_for(ErrorCode.SUB_SFL)
    b = np.zeros(32)
    for w in (0, 1):
        b[st.index({"place_value": 0, "exchange": 0, "written_step": w, "habit": "target"})] = 0.5
    items = [Problem("sub", 58, 23), Problem("sub", 52, 29)]
    scores = [bel.eig(b, resp.outcomes(i, roles, "core", p)) for i in items]
    assert items[int(np.argmax(scores))] == Problem("sub", 52, 29)


def test_the_oracle_agrees_on_1000_random_cases_within_1e_9() -> None:
    result = bayes_oracle.compare(1000)
    assert result["pass"], result["max_abs_diff"]
    assert result["max"] <= 1e-9
