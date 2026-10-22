"""Avatars, expressions, palettes, PNG: determinism, totality of the table, contrast, rendering."""

from __future__ import annotations

import hashlib
import itertools
import json
import re
from pathlib import Path

import pytest

from services.api.sprites.avatar import (
    avatar_svg,
    expression_ids,
    look_from_seed,
    look_problems,
    persona_look,
    personas,
    seat_row,
)
from services.api.sprites.expression import ChildState, all_targets, expression_for, registered
from services.api.sprites.golden import cases, golden, render_case
from services.api.sprites.grammar import BUDGET, validate_svg
from services.api.sprites.items import item_ids, load_item
from services.api.sprites.layouts import place_value_mat
from services.api.sprites.palette import (
    CVD,
    contrast,
    palette,
    palette_names,
    rgb,
    simulate,
)
from services.api.sprites.png import svg_to_png

from .helpers import hexes, parse

ROOT = Path(__file__).resolve().parents[2]
PNG = b"\x89PNG\r\n\x1a\n"


def h(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


# --------------------------------------------------------------------------- determinism
def test_the_same_persona_seed_gives_the_same_svg_hash_across_runs() -> None:
    fixture = json.loads((ROOT / "tests/fixtures/sprite_golden.json").read_text(encoding="utf-8"))
    want = {c["case"]["persona"]: c["sha256"] for c in fixture["cases"]
            if c["case"]["fn"] == "avatar" and c["case"]["expression"] == "neutral"
            and c["case"]["mouth"] == "closed"}  # fmt: skip
    assert set(want) == set(personas())
    for pid, digest in want.items():  # the fixture was written by an earlier run
        assert h(avatar_svg(persona_look(pid)["look"], "neutral", "closed")) == digest, pid


def test_a_seed_gives_one_look_and_different_seeds_differ() -> None:
    assert look_from_seed(1234) == look_from_seed(1234)
    looks = {json.dumps(look_from_seed(s), sort_keys=True) for s in range(200)}
    assert len(looks) > 100


def test_a_persona_record_may_override_the_look_but_keeps_its_seed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services.api.sprites import avatar

    base = persona_look("meena")
    rec = dict(avatar.personas()["meena"])
    rec["look"] = {"accessory": "bag", "skin": 5}
    original = dict(avatar.personas())
    monkeypatch.setattr(avatar, "personas", lambda: {**original, "meena": rec})
    over = avatar.persona_look("meena")
    assert (
        over["seed"] == base["seed"]
        and over["look"]["accessory"] == "bag"
        and over["look"]["skin"] == 5
    )
    assert {k: v for k, v in over["look"].items() if k not in ("accessory", "skin")} == {
        k: v for k, v in base["look"].items() if k not in ("accessory", "skin")
    }


def test_every_persona_is_in_the_approved_pool() -> None:
    import yaml

    pool = {
        c["id"]
        for c in yaml.safe_load(
            (ROOT / "content/personas/children.v1.yaml").read_text(encoding="utf-8")
        )["children"]
    }
    assert set(personas()) <= pool


def test_every_look_is_valid_and_every_avatar_is_within_the_grammar_and_budget() -> None:
    for seed in range(60):
        look = look_from_seed(seed)
        assert look_problems(look) == []
        for expr in expression_ids():
            svg = avatar_svg(look, expr)
            assert validate_svg(svg) == [] and len(svg.encode()) <= BUDGET["avatar"]


def test_a_bad_look_or_expression_is_refused() -> None:
    look = look_from_seed(1)
    with pytest.raises(ValueError):
        avatar_svg({**look, "hair_style": "hair_z"})
    with pytest.raises(ValueError):
        avatar_svg(look, "furious")
    assert "unknown_accessory" in look_problems({**look, "accessory": "crown"})


def test_both_mouth_frames_are_in_the_svg_and_one_starts_hidden() -> None:
    look = look_from_seed(3)
    for start, hidden in (("closed", "mouth-open"), ("open", "mouth-closed")):
        root = parse(avatar_svg(look, "thinking", start))
        mouths = [e for e in root.iter() if "mouth" in e.attrib.get("class", "").split()]
        assert len(mouths) == 2
        assert [m.attrib.get("opacity") for m in mouths if hidden in m.attrib["class"]] == ["0"]


def test_the_seat_row_holds_five_avatars_and_the_speaker_has_her_mouth_open() -> None:
    kids = [
        {"look": look_from_seed(i), "expression": "neutral", "speaking": i == 2} for i in range(5)
    ]
    svg = seat_row(kids)
    assert validate_svg(svg) == [] and svg.count('class="seat"') == 5
    seats = [e for e in parse(svg) if e.attrib.get("class") == "seat"]
    open_visible = [
        s
        for s in seats
        if any(
            "mouth-open" in g.attrib.get("class", "") and "opacity" not in g.attrib
            for g in s.iter()
        )
    ]
    assert len(open_visible) == 1


def test_no_part_name_carries_a_gender_marker() -> None:
    text = (ROOT / "content/sprites/avatar_parts.v1.json").read_text(encoding="utf-8").lower()
    for word in (
        "boy",
        "girl",
        "male",
        "female",
        "turban",
        "hijab",
        "bindi",
        "cross",
        "tilak",
        "wheelchair",
    ):
        assert not re.search(rf"\b{word}\b", text), word


# --------------------------------------------------------------------- expression table
def test_every_state_maps_to_a_registered_expression_with_no_gaps() -> None:
    intents = [
        "answer",
        "explain",
        "work_aloud",
        "doubt",
        "agree",
        "thanks",
        "quiet",
        "confused",
        "silent",
        "anything_new",
    ]
    grid = itertools.product(
        [True, False],
        intents,
        [True, False, None],
        [0.0, 0.34, 0.35, 0.9],
        [0.0, 0.65, 0.66, 1.0],
        [True, False],
        [True, False],
    )
    reg = registered()
    n = 0
    for speaking, intent, correct, eng, st, quiet, shy in grid:
        out = expression_for(ChildState(speaking, intent, correct, eng, st, quiet, shy))
        assert out in reg, (speaking, intent, correct, eng, st, quiet, shy)
        n += 1
    assert n > 2000


def test_the_table_reaches_every_registered_expression_and_only_those() -> None:
    assert all_targets() == registered()


def test_the_table_says_what_a_teacher_would_expect() -> None:
    def s(**kw: object) -> ChildState:
        base = dict(
            speaking=True,
            intent="answer",
            correct=True,
            engagement=0.6,
            strength=0.0,
            quiet=False,
            shy=False,
        )
        return ChildState(**{**base, **kw})  # type: ignore[arg-type]

    assert expression_for(s()) == "got_it"
    assert expression_for(s(correct=False, strength=0.9)) == "wrong_answer"
    assert expression_for(s(intent="confused", correct=None)) == "confused"
    assert expression_for(s(quiet=True)) == "shy"
    assert expression_for(s(speaking=False, shy=True)) == "shy"
    assert expression_for(s(speaking=False, engagement=0.1)) == "distracted"
    assert expression_for(s(speaking=False, strength=0.9)) == "thinking"
    assert expression_for(s(speaking=False, strength=0.1)) == "neutral"


# ------------------------------------------------------------------ palettes and contrast
@pytest.mark.parametrize("name", palette_names())
@pytest.mark.parametrize("kind", list(CVD))
def test_item_colours_stay_visible_against_the_mat_under_colour_blindness(
    name: str, kind: str
) -> None:
    pal = palette(name)
    mat = simulate(pal["mat"], kind)
    for slot in ("item_a", "item_b", "ink", "accent"):
        assert contrast(simulate(pal[slot], kind), mat) >= 3.0, (name, kind, slot)


@pytest.mark.parametrize("name", palette_names())
def test_item_colours_have_contrast_against_the_mat_for_normal_vision(name: str) -> None:
    pal = palette(name)
    for slot in ("item_a", "item_b", "ink", "accent"):
        assert contrast(rgb(pal[slot]), rgb(pal["mat"])) >= 3.0, (name, slot)


def test_meaning_never_rests_on_colour_alone_items_differ_by_silhouette() -> None:
    seen = {}
    for item_id in item_ids():
        spec = load_item(item_id)
        seen[item_id] = tuple((p["shape"], p.get("d", p.get("points", ""))) for p in spec["parts"])
    assert len(set(seen.values())) == len(seen)  # no two items have the same shapes


# ------------------------------------------------------------------------------- PNG
@pytest.mark.parametrize("item_id", item_ids())
def test_every_item_renders_to_a_png(item_id: str) -> None:
    from services.api.sprites.layouts import row

    png = svg_to_png(row(load_item(item_id), 5, palette()).svg, 240)
    assert png.startswith(PNG) and len(png) > 200


@pytest.mark.parametrize("expr", expression_ids())
@pytest.mark.parametrize("mouth", ["closed", "open"])
def test_every_expression_renders_to_a_png(expr: str, mouth: str) -> None:
    png = svg_to_png(avatar_svg(look_from_seed(4), expr, mouth), 128)
    assert png.startswith(PNG) and len(png) > 200


def test_both_mats_render_to_a_png() -> None:
    from services.api.sprites.layouts import number_line

    assert svg_to_png(place_value_mat(load_item("stick"), 47, palette()).svg).startswith(PNG)
    assert svg_to_png(number_line(0, 20, [7], palette()).svg).startswith(PNG)


def test_png_refuses_svg_outside_the_grammar() -> None:
    with pytest.raises(ValueError):
        svg_to_png('<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>')


def test_mat_static_part_is_within_six_kilobytes() -> None:
    assert len(place_value_mat(load_item("stick"), 0, palette()).svg.encode()) <= BUDGET["mat"]


# --------------------------------------------------------------------------- golden
def test_every_golden_case_renders_within_the_grammar_with_palette_colours_only() -> None:
    for case in cases():
        svg = render_case(case)
        assert validate_svg(svg) == [], case
        pal = palette(case.get("palette", "default"))
        assert hexes(svg) <= {v.lower() for v in pal.values()} | _avatar_hexes()


def _avatar_hexes() -> set[str]:
    from services.api.sprites.palette import cloth_colours, hair_colours, skin_tones

    return {c.lower() for c in (*skin_tones(), *hair_colours(), *cloth_colours())}


def test_the_committed_golden_file_matches_the_engine() -> None:
    path = ROOT / "tests/fixtures/sprite_golden.json"
    want = json.dumps(golden(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    assert path.read_text(encoding="utf-8") == want
