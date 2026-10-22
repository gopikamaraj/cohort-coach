"""Topic packs: validation, scenes from templates, no check items, and the two-key lifecycle."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from services.api.sprites.items import load_pack, pack_ids
from services.api.sprites.packs import PackShelf, approve, enable, validate_pack
from services.api.sprites.scene import SceneError, render_template

from .helpers import parse, units

ROOT = Path(__file__).resolve().parents[2]
TABLES = {
    lang: json.loads((ROOT / "strings" / f"{lang}.json").read_text(encoding="utf-8"))
    for lang in ("en", "hi", "ta")
}
PACK = "place-value-add-sub"


@pytest.mark.parametrize("pack_id", pack_ids())
def test_every_shipped_pack_validates(pack_id: str) -> None:
    assert validate_pack(load_pack(pack_id), TABLES) == []


def test_the_shipped_pack_has_the_items_mats_and_templates_that_were_asked_for() -> None:
    pack = load_pack(PACK)
    assert pack["items"] == [
        "stick",
        "bundle_of_ten",
        "counter",
        "ball",
        "mango",
        "pencil",
        "marble",
        "book",
        "ten_frame",
    ]
    assert pack["mats"] == ["place_value_mat", "number_line"]
    kinds = {(t["operation"], t["item"]) for t in pack["templates"]}
    assert {
        ("add", "ball"),
        ("add", "mango"),
        ("add", "pencil"),
        ("sub", "ball"),
        ("sub", "mango"),
        ("sub", "pencil"),
    } <= kinds
    assert pack["status"] == "enabled" and "TODO-HUMAN" in pack["review"]


@pytest.mark.parametrize("lang", ["en", "hi", "ta"])
def test_an_add_scene_draws_both_groups_and_fills_the_sentence_by_code(lang: str) -> None:
    t = render_template(PACK, "add_balls", 23, 14, lang=lang, seed=4)
    assert t.scene.report["count_drawn"] == 37 and t.scene.report["groups"] == [23, 14]
    assert len(units(parse(t.scene.svg))) == 37
    assert "23" in t.text and "14" in t.text and "{" not in t.text


def test_a_subtraction_scene_crosses_out_the_second_number() -> None:
    t = render_template(PACK, "sub_mangoes", 52, 28)
    assert t.scene.report == {
        "item_id": "mango",
        "count_drawn": 52,
        "marked": 28,
        "layout": "cross_out",
    }


def test_a_subtraction_scene_refuses_a_second_number_above_the_first() -> None:
    with pytest.raises(SceneError):
        render_template(PACK, "sub_pencils", 12, 30)


@pytest.mark.parametrize(("a", "b"), [(45, 19), (19, 45), (38, 47), (74, 36), (82, 39), (87, 52)])
def test_a_scene_that_would_teach_a_check_item_is_refused(a: int, b: int) -> None:
    for tpl in ("add_balls", "sub_balls"):
        with pytest.raises(SceneError, match="check item"):
            render_template(PACK, tpl, a, b)


def test_a_pack_whose_template_holds_a_check_item_pair_is_blocked() -> None:
    pack = copy.deepcopy(load_pack(PACK))
    tables = copy.deepcopy(TABLES)
    tables["en"]["sprite.tpl.add_balls"] = "Take 45 - 19 and then {a} more."
    out = validate_pack(pack, tables)
    assert "check_item:add_balls:en" in out and "digit_in_template:add_balls:en" in out


def test_a_template_may_not_hold_literal_numbers_or_unknown_slots() -> None:
    pack = copy.deepcopy(load_pack(PACK))
    tables = copy.deepcopy(TABLES)
    tables["hi"]["sprite.tpl.add_balls"] = "{a} और {c} और 5"
    out = validate_pack(pack, tables)
    assert "unknown_slot:add_balls:hi" in out and "digit_in_template:add_balls:hi" in out


def test_a_pack_with_a_missing_item_layout_or_translation_is_blocked() -> None:
    pack = copy.deepcopy(load_pack(PACK))
    pack["items"].append("unicorn")
    pack["layouts"].append("spiral")
    pack["expressions"].append("furious")
    tables = copy.deepcopy(TABLES)
    del tables["ta"]["sprite.tpl.sub_balls"]
    out = validate_pack(pack, tables)
    assert {
        "unknown_item:unicorn",
        "unknown_layout:spiral",
        "unknown_expression:furious",
        "missing_text:sub_balls:ta",
    } <= set(out)


def test_an_item_that_breaks_the_grammar_blocks_its_pack(monkeypatch: pytest.MonkeyPatch) -> None:
    from services.api.sprites import packs

    bad = copy.deepcopy(packs.load_item("ball"))
    bad["parts"][0]["fill"] = "#ff0000"
    monkeypatch.setattr(packs, "load_item", lambda _id: bad)
    assert any(
        r.startswith("item:") and "paint_not_a_slot" in r
        for r in validate_pack(load_pack(PACK), TABLES)
    )


# ------------------------------------------------------------------------------- lifecycle
def draft() -> dict:
    return {**copy.deepcopy(load_pack(PACK)), "status": "draft", "version": 1}


def test_only_an_enabled_pack_reaches_a_teacher() -> None:
    from services.api.sprites import scene

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(scene, "load_pack", lambda _id: draft())
        with pytest.raises(SceneError, match="enabled pack"):
            render_template(PACK, "add_balls", 2, 3)
        assert (
            render_template(PACK, "add_balls", 2, 3, allow_unapproved=True).scene.report[
                "count_drawn"
            ]
            == 5
        )


def test_the_coach_approves_then_the_officer_enables_and_neither_alone_does() -> None:
    d = draft()
    with pytest.raises(PermissionError):
        approve(d, "officer")
    with pytest.raises(ValueError):
        enable(d, "officer")  # a draft cannot skip the coach
    a = approve(d, "coach")
    with pytest.raises(PermissionError):
        enable(a, "coach")
    with pytest.raises(ValueError):
        approve(a, "coach")
    e = enable(a, "officer")
    assert (d["status"], a["status"], e["status"]) == ("draft", "approved", "enabled")
    assert (d["version"], a["version"], e["version"]) == (1, 2, 3)


def test_an_edit_makes_a_new_version_and_the_enabled_one_stays_in_use_until_both_keys() -> None:
    shelf = PackShelf(enable(approve(draft(), "coach"), "officer"))
    live = shelf.in_use["version"]
    new = shelf.edit({"expressions": ["neutral"]})
    assert new["status"] == "draft" and new["version"] == live + 1
    assert shelf.in_use["version"] == live and shelf.in_use["status"] == "enabled"
    shelf.approve("coach")
    assert shelf.in_use["version"] == live  # approved is not enabled
    shelf.enable("officer")
    assert shelf.in_use["version"] == live + 3 and shelf.pending is None
    assert [h[1] for h in shelf.history][-3:] == ["draft", "approved", "enabled"]
    shelf.edit({})
    with pytest.raises(ValueError):
        shelf.enable("officer")  # an unapproved draft cannot be enabled
