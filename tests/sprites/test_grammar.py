"""The grammar whitelist: one test per forbidden element, attribute and spec rule."""

from __future__ import annotations

import copy
from typing import Any

import pytest

from services.api.sprites.grammar import BUDGET, compile_item, validate_spec, validate_svg
from services.api.sprites.items import item_ids, load_item
from services.api.sprites.palette import SLOTS, palette

NS = 'xmlns="http://www.w3.org/2000/svg"'


def svg(inner: str, attrs: str = "") -> str:
    return f'<svg {NS} viewBox="0 0 24 24" {attrs}>{inner}</svg>'


# --------------------------------------------------------------------- rendered SVG
@pytest.mark.parametrize(
    "tag",
    [
        "script",
        "foreignObject",
        "image",
        "text",
        "style",
        "animate",
        "animateTransform",
        "tspan",
        "title",
        "desc",
        "set",
        "a",
    ],
)
def test_a_forbidden_element_is_rejected(tag: str) -> None:
    assert f"forbidden_element:{tag}" in validate_svg(svg(f"<{tag}></{tag}>"))


@pytest.mark.parametrize(
    "tag", ["filter", "mask", "pattern", "symbol", "marker", "switch", "iframe"]
)
def test_an_element_outside_the_whitelist_is_rejected(tag: str) -> None:
    assert f"element_not_allowed:{tag}" in validate_svg(svg(f"<{tag}/>"))


@pytest.mark.parametrize("attr", ["onclick", "onload", "onmouseover", "onerror", "OnFocus"])
def test_an_event_attribute_is_rejected(attr: str) -> None:
    assert any(
        r.startswith("event_attribute")
        for r in validate_svg(svg(f'<circle cx="1" cy="1" r="1" {attr}="x()"/>'))
    )


def test_a_style_attribute_is_rejected() -> None:
    assert "style_attribute" in validate_svg(svg('<circle cx="1" cy="1" r="1" style="fill:red"/>'))


@pytest.mark.parametrize(
    "href",
    [
        "http://x.test/a.svg",
        "https://x.test/a",
        "//x.test/a",
        "file:///etc/passwd",
        "data:image/png;base64,AA",
        "javascript:alert(1)",
        "other.svg#a",
    ],
)
def test_an_external_href_is_rejected(href: str) -> None:
    assert "external_href" in validate_svg(svg(f'<use href="{href}"/>'))


def test_a_local_href_is_allowed_but_xlink_is_not_in_the_whitelist() -> None:
    assert (
        validate_svg(svg('<defs><circle id="a" cx="1" cy="1" r="1"/></defs><use href="#a"/>')) == []
    )
    assert any(
        r.startswith("attribute_not_allowed")
        for r in validate_svg(
            svg('<use xlink:href="#a" xmlns:xlink="http://www.w3.org/1999/xlink"/>')
        )
    )


def test_text_inside_the_art_is_rejected() -> None:
    assert "text_node" in validate_svg(svg("<g>hello</g>"))
    assert "text_node" in validate_svg(svg("<g/>tail"))


def test_an_unknown_attribute_class_or_data_value_is_rejected() -> None:
    assert "attribute_not_allowed:filter" in validate_svg(
        svg('<circle cx="1" cy="1" r="1" filter="url(#x)"/>')
    )
    assert any(r.startswith("class_not_allowed") for r in validate_svg(svg('<g class="fancy"/>')))
    assert any(
        r.startswith("data_value")
        for r in validate_svg(svg('<g data-x="<b>"/>'.replace("<b>", "a&lt;b")))
    )


def test_malformed_svg_is_rejected() -> None:
    assert validate_svg("<svg><g></svg>") == ["not_well_formed"]


def test_the_listed_elements_and_their_gradients_are_allowed() -> None:
    ok = svg(
        '<defs><linearGradient id="a" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0%" stop-color="#112233"/>'
        '<stop offset="100%" stop-color="#445566"/></linearGradient>'
        '<radialGradient id="b" cx="1" cy="1" r="2"/>'
        '<clipPath id="c"><rect x="0" y="0" width="2" height="2"/></clipPath></defs>'
        '<g><circle cx="1" cy="1" r="1"/><ellipse cx="1" cy="1" rx="1" ry="2"/>'
        '<line x1="0" y1="0" x2="1" y2="1"/>'
        '<polyline points="0,0 1,1"/><polygon points="0,0 1,1 2,0"/><path d="M0 0L1 1"/></g>'
    )
    assert validate_svg(ok) == []


# ------------------------------------------------------------------------------ specs
def base() -> dict[str, Any]:
    return copy.deepcopy(load_item("ball"))


def test_every_shipped_item_is_valid() -> None:
    for item_id in item_ids():
        assert validate_spec(load_item(item_id)) == [], item_id


@pytest.mark.parametrize("shape", ["text", "image", "foreignObject", "script", "use", "g", "style"])
def test_a_spec_shape_outside_the_whitelist_is_rejected(shape: str) -> None:
    s = base()
    s["parts"].append({"shape": shape, "fill": "item_a"})
    assert f"shape_not_allowed:{shape}" in validate_spec(s)


@pytest.mark.parametrize("value", ["#ff0000", "red", "rgb(1,2,3)", "url(#x)", "item_c"])
def test_a_fill_that_is_not_a_palette_slot_is_rejected(value: str) -> None:
    s = base()
    s["parts"][0]["fill"] = value
    out = validate_spec(s)
    assert "paint_not_a_slot:fill" in out


def test_a_raw_hex_anywhere_in_a_spec_is_rejected() -> None:
    s = base()
    s["alt"]["note"] = "#abcdef"
    assert "raw_colour" in validate_spec(s)


def test_a_stroke_must_be_a_slot_too() -> None:
    s = base()
    s["parts"][0]["stroke"] = "#000"
    assert "paint_not_a_slot:stroke" in validate_spec(s)


@pytest.mark.parametrize("key", ["onclick", "href", "style", "class", "filter", "opacity"])
def test_an_attribute_outside_the_whitelist_is_rejected(key: str) -> None:
    s = base()
    s["parts"][0][key] = "x"
    assert f"attribute_not_allowed:{key}" in validate_spec(s)


def test_numbers_must_be_integers() -> None:
    s = base()
    s["parts"][0]["r"] = 9.5
    assert "number_not_integer" in validate_spec(s)
    s = base()
    s["parts"][0]["cx"] = True
    assert "number_not_integer" in validate_spec(s)
    s = base()
    s["parts"][0]["stroke_width"] = 1.5
    assert "number_not_integer" in validate_spec(s)


def test_path_points_and_transform_are_pattern_checked() -> None:
    s = base()
    s["parts"][1]["d"] = "M0 0 <script>"
    assert "bad_path_data" in validate_spec(s)
    s = copy.deepcopy(load_item("pencil"))
    s["parts"][0]["points"] = "1,2 evil"
    assert "bad_points" in validate_spec(s)
    s = base()
    s["parts"][0]["transform"] = "matrix(1 0 0 1 0 0)"
    assert "bad_transform" in validate_spec(s)
    s = base()
    s["parts"][0]["transform"] = "translate(2 3) rotate(45 12 12)"
    assert "bad_transform" not in validate_spec(s)


def test_the_viewbox_and_category_are_fixed() -> None:
    s = base()
    s["viewBox"] = [0, 0, 32, 32]
    assert "viewbox_not_fixed" in validate_spec(s)
    s = base()
    s["category"] = "avatar"
    assert "category_mismatch" in validate_spec(s)


def test_id_version_alt_key_and_topics_are_required() -> None:
    for key, rule in (
        ("id", "bad_id"),
        ("version", "bad_version"),
        ("alt", "alt_key_format"),
        ("topics", "topics_missing"),
        ("parts", "no_parts"),
    ):
        s = base()
        del s[key]
        assert rule in validate_spec(s), key
    s = base()
    s["id"] = "Bad Id"
    assert "bad_id" in validate_spec(s)
    s = base()
    s["alt"] = {"key": "sprite.item.Ball Caps"}
    assert "alt_key_format" in validate_spec(s)


def test_a_missing_required_attribute_is_rejected() -> None:
    s = base()
    del s["parts"][0]["r"]
    assert "missing:r" in validate_spec(s)


def test_a_gradient_may_only_use_palette_slots() -> None:
    s = base()
    s["defs"][0]["stops"][0]["color"] = "red"
    assert "gradient_stop" in validate_spec(s)
    s = base()
    s["defs"][0]["type"] = "pattern"
    assert "gradient_type" in validate_spec(s)


# -------------------------------------------------------------------------- budgets
def test_every_item_is_within_two_kilobytes() -> None:
    for item_id in item_ids():
        size = len(compile_item(load_item(item_id), palette()).encode())
        assert size <= BUDGET["item"], (item_id, size)


def test_an_item_over_budget_is_rejected() -> None:
    s = base()
    s["parts"] += [
        {
            "shape": "path",
            "d": "M0 0 L24 24 " * 12,
            "fill": "none",
            "stroke": "ink",
            "stroke_width": 1,
        }
    ] * 12
    assert any(r.startswith("over_budget") for r in validate_spec(s))


def test_rendered_items_contain_only_palette_colours() -> None:
    from .helpers import hexes

    for name in ("default", "warm", "cool", "high_contrast"):
        pal = palette(name)
        for item_id in item_ids():
            assert hexes(compile_item(load_item(item_id), pal)) <= {v.lower() for v in pal.values()}


def test_slots_are_the_nine_named_ones() -> None:
    assert SLOTS == (
        "skin",
        "hair",
        "cloth_a",
        "cloth_b",
        "accent",
        "item_a",
        "item_b",
        "mat",
        "ink",
    )
