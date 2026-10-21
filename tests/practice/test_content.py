from __future__ import annotations

import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from engine.items import validate_item
from engine.model import ErrorCode, Item, ItemType
from engine.simulator import APPLIES_TO
from services.practice.content import (
    CONTENT,
    LANGS,
    MoveList,
    Rubric,
    Scenario,
    load_personas,
    load_scenario,
    load_templates,
)

ROOT = Path(__file__).resolve().parents[2]
TRACKED = [ErrorCode.PV_HEARD, ErrorCode.ADD_NOCARRY, ErrorCode.SUB_SFL, ErrorCode.SUB_NODEC]


@pytest.mark.parametrize("error", TRACKED)
def test_every_tracked_error_has_a_valid_scenario_movelist_and_rubric(error: ErrorCode) -> None:
    loaded = load_scenario(error.value)
    assert loaded.scenario.error is error
    assert loaded.config.start_strength == 0.9  # CLAUDE.md section 5
    assert loaded.config.max_turns == 40 and loaded.config.finish_streak == 2
    assert 4 <= len(loaded.rubric.points) <= 6
    ids = {m.id for m in loaded.movelist.moves}
    assert {"pose_problem", "ask_explain", "praise", "scold", "tell_rule"} <= ids


def test_move_effects_match_claude_md_section_5() -> None:
    cfg = load_scenario("SUB-SFL").config
    assert cfg.moves["show_bundles"].strength == -0.3
    assert cfg.moves["ask_explain"].strength == -0.2
    assert cfg.moves["check_back"].strength == -0.2
    assert cfg.moves["tell_rule"].strength == -0.05
    assert cfg.moves["praise"].engagement > 0 and cfg.moves["praise"].strength == 0
    assert cfg.moves["scold"].engagement < 0 and cfg.moves["scold"].quiet


@pytest.mark.parametrize("error", TRACKED)
def test_scenario_problems_fit_the_error_and_have_no_collisions(error: ErrorCode) -> None:
    for p in load_scenario(error.value).config.problems:
        assert p.kind == APPLIES_TO[error]
        if p.kind == "sub":
            assert validate_item(Item(7, ItemType.SUB_BORROW, p.a, p.b)) == []
        elif p.kind == "add":
            assert validate_item(Item(3, ItemType.ADD_CARRY, p.a, p.b)) == []
        elif p.a >= 100:
            assert validate_item(Item(1, ItemType.DICTATION, p.a)) == []
        else:  # the design's own 2-digit examples (forty-three): non-zero distinct digits
            assert "0" not in str(p.a) and str(p.a)[0] != str(p.a)[1]


@pytest.mark.parametrize("error", TRACKED)
def test_all_texts_exist_in_three_languages(error: ErrorCode) -> None:
    loaded = load_scenario(error.value)
    for move in loaded.movelist.moves:
        for lang in LANGS:
            assert move.label[lang] and move.description[lang] and move.examples[lang]
    for point in loaded.rubric.points:
        for lang in LANGS:
            assert point.text[lang] and point.try_next[lang]


def test_personas_are_ten_plus_per_language_balanced_and_marker_free() -> None:
    kids = load_personas().children
    assert len(kids) >= 10
    genders = Counter(k.gender for k in kids)
    assert genders["f"] == genders["m"]
    for lang in LANGS:
        names = [k.names[lang] for k in kids]
        assert len(set(names)) == len(names)
    # Temperament only: nothing about caste, religion, region or disability.
    banned = ("caste", "dalit", "hindu", "muslim", "christian", "sikh", "disab", "blind", "deaf",
              "poor", "rich", "village", "tribal")  # fmt: skip
    for k in kids:
        assert not any(b in k.temperament.lower() for b in banned)
    team = {"seema", "shivani", "gopi"}
    assert not team & {k.names["en"].lower() for k in kids}


@pytest.mark.parametrize("lang", LANGS)
def test_child_line_templates_cover_every_intent_and_step_op(lang: str) -> None:
    t = load_templates(lang)
    assert {
        "answer",
        "explain",
        "work_aloud",
        "doubt",
        "agree",
        "thanks",
        "quiet",
        "confused",
    } <= set(t.intents)
    ops = {"cant", "minus", "plus", "borrow", "open", "write", "carry", "parts", "tens_ones",
           "hundreds_tens_ones", "addback", "takeaway", "size", "swap"}  # fmt: skip
    assert ops <= set(t.steps)
    assert "{answer}" in t.intents["answer"]


def test_a_rubric_that_names_an_unknown_move_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import services.practice.content as c

    c.load_scenario.cache_clear()
    root = tmp_path / "content"
    for sub in ("scenarios", "movelists", "rubrics"):
        (root / sub).mkdir(parents=True)
    src = CONTENT
    (root / "scenarios/sub-sfl.v1.yaml").write_text(
        (src / "scenarios/sub-sfl.v1.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (root / "movelists/sub-sfl.v1.yaml").write_text(
        (src / "movelists/sub-sfl.v1.yaml").read_text(encoding="utf-8"), encoding="utf-8"
    )
    rubric = yaml.safe_load((src / "rubrics/sub-sfl.v1.yaml").read_text(encoding="utf-8"))
    rubric["points"][0]["move_ids"] = ["no_such_move"]
    (root / "rubrics/sub-sfl.v1.yaml").write_text(
        yaml.safe_dump(rubric, allow_unicode=True), encoding="utf-8"
    )
    monkeypatch.setattr(c, "CONTENT", root)
    try:
        with pytest.raises(ValueError, match="unknown moves"):
            c.load_scenario("SUB-SFL")
    finally:
        c.load_scenario.cache_clear()


def test_schema_rules() -> None:
    langs = {"en": "a", "hi": "a", "ta": "a"}
    bad_move = {
        "id": "other", "behaviour": "answer", "strength": 0, "engagement": 0,
        "label": langs, "description": langs, "examples": {k: ["a"] for k in langs},
    }  # fmt: skip
    with pytest.raises(ValidationError):
        MoveList.model_validate({"error": "SUB-SFL", "version": 1, "moves": [bad_move]})
    with pytest.raises(ValidationError):
        Rubric.model_validate({"error": "SUB-SFL", "version": 1, "points": []})
    raw = yaml.safe_load((CONTENT / "scenarios/sub-sfl.v1.yaml").read_text(encoding="utf-8"))
    raw["problems"][0] = {"kind": "sub", "a": 5, "b": 29}
    with pytest.raises(ValidationError):
        Scenario.model_validate(raw)


def test_exported_json_schemas_are_current() -> None:
    done = subprocess.run(
        [sys.executable, "scripts/export_content_schemas.py", "--check"],
        cwd=ROOT, capture_output=True, text=True,
    )  # fmt: skip
    assert done.returncode == 0, done.stdout


@pytest.mark.parametrize("error", [ErrorCode.SUB_SFL, ErrorCode.SUB_NODEC])
def test_subtraction_scenarios_have_strategies_and_hint_lines(error: ErrorCode) -> None:
    moves = {m.id: m for m in load_scenario(error.value).movelist.moves}
    assert {"decomposition", "compensation", "repeat_rule_louder", "give_the_answer"} <= set(moves)
    assert moves["decomposition"].strategy and moves["compensation"].strategy
    assert (error is ErrorCode.SUB_SFL) == ("order_probe" in moves)
    for quality in ("strong", "common_mistake", "neutral"):
        with_lines = [m for m in moves.values() if m.quality == quality and m.sample_lines]
        assert with_lines, (error, quality)
        for m in with_lines:
            assert set(m.sample_lines) == set(LANGS), m.id
            assert all(line.strip() for ls in m.sample_lines.values() for line in ls), m.id


def test_the_new_moves_keep_the_effect_rules() -> None:
    cfg = load_scenario("SUB-SFL").config
    assert cfg.moves["decomposition"].strength < 0 < cfg.moves["decomposition"].engagement
    assert cfg.moves["repeat_rule_louder"].strength > cfg.moves["show_bundles"].strength
    assert cfg.moves["give_the_answer"].strength == 0.0
