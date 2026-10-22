"""Child avatars: a composition of parts, built deterministically from a persona record.

A persona record (content/sprites/personas.v1.json) holds a seed and optional look overrides. The
look is derived from the seed, and the same look and expression always give the same SVG. Names
come from the approved persona pool, never the roster; part styles are neutral (`hair_a` ...), and
no part carries a gender, caste, religion or disability marker.
"""

from __future__ import annotations

import json
from functools import cache
from typing import Any

from services.api.sprites.grammar import part_markup, validate_svg
from services.api.sprites.palette import (
    SPRITES,
    cloth_colours,
    hair_colours,
    palette,
    skin_tones,
)
from services.api.sprites.rng import Rng

LOOK_KEYS = (
    "body",
    "skin",
    "hair_style",
    "hair_colour",
    "outfit",
    "cloth_a",
    "cloth_b",
    "accessory",
)
BG = "mat"


@cache
def parts() -> dict[str, Any]:
    return json.loads((SPRITES / "avatar_parts.v1.json").read_text(encoding="utf-8"))  # type: ignore[no-any-return]


@cache
def expressions() -> dict[str, Any]:
    return json.loads((SPRITES / "expressions.v1.json").read_text(encoding="utf-8"))  # type: ignore[no-any-return]


@cache
def personas() -> dict[str, dict[str, Any]]:
    data = json.loads((SPRITES / "personas.v1.json").read_text(encoding="utf-8"))
    return {p["id"]: p for p in data["personas"]}


def expression_ids() -> list[str]:
    return list(expressions()["expressions"])


def look_from_seed(seed: int) -> dict[str, Any]:
    """The same seed always gives the same look."""
    rng = Rng(seed)
    p = parts()
    return {
        "body": sorted(p["bodies"])[rng.below(len(p["bodies"]))],
        "skin": rng.below(len(skin_tones())),
        "hair_style": sorted(p["hair_styles"])[rng.below(len(p["hair_styles"]))],
        "hair_colour": rng.below(len(hair_colours())),
        "outfit": sorted(p["outfits"])[rng.below(len(p["outfits"]))],
        "cloth_a": rng.below(len(cloth_colours())),
        "cloth_b": rng.below(len(cloth_colours())),
        "accessory": sorted(p["accessories"])[rng.below(len(p["accessories"]))],
    }


def persona_look(persona_id: str) -> dict[str, Any]:
    """A persona's seed, and its look: the seed's look with any record overrides applied."""
    rec = personas()[persona_id]
    look = look_from_seed(rec["seed"])
    if isinstance(rec.get("look"), dict):
        look.update(rec["look"])
    return {"persona": persona_id, "seed": rec["seed"], "look": look}


def _avatar_palette(look: dict[str, Any], base: str = "default") -> dict[str, str]:
    pal = palette(base)
    pal["skin"] = skin_tones()[look["skin"]]
    pal["hair"] = hair_colours()[look["hair_colour"]]
    pal["cloth_a"] = cloth_colours()[look["cloth_a"]]
    pal["cloth_b"] = (
        cloth_colours()[look["cloth_b"]] if look["outfit"] != "outfit_a" else pal["cloth_b"]
    )
    return pal


def look_problems(look: dict[str, Any]) -> list[str]:
    p = parts()
    out = [f"unknown_{k}" for k in LOOK_KEYS if k not in look]
    if look.get("body") not in p["bodies"]:
        out.append("unknown_body")
    if look.get("hair_style") not in p["hair_styles"]:
        out.append("unknown_hair_style")
    if look.get("outfit") not in p["outfits"]:
        out.append("unknown_outfit")
    if look.get("accessory") not in p["accessories"]:
        out.append("unknown_accessory")
    for key, n in (("skin", len(skin_tones())), ("hair_colour", len(hair_colours())),
                   ("cloth_a", len(cloth_colours())), ("cloth_b", len(cloth_colours()))):  # noqa: E501  # fmt: skip
        if not isinstance(look.get(key), int) or not 0 <= look[key] < n:
            out.append(f"bad_{key}")
    return out


def _group(cls: str, shapes: list[dict[str, Any]], pal: dict[str, str], extra: str = "") -> str:
    inner = "".join(part_markup(s, pal, "av") for s in shapes)
    return f'<g class="{cls}"{extra}>{inner}</g>'


def avatar_svg(
    look: dict[str, Any], expression: str = "neutral", mouth: str = "closed", base: str = "default"
) -> str:
    """One avatar. Both mouth frames are in the SVG; `mouth` says which one starts visible, and
    the page's CSS toggles them while audio plays."""
    bad = look_problems(look)
    if bad:
        raise ValueError(f"bad look: {bad}")
    reg = expressions()
    if expression not in reg["expressions"]:
        raise ValueError(f"unknown expression {expression!r}")
    face = reg["expressions"][expression]
    fp = reg["parts"]
    pal = _avatar_palette(look, base)
    p = parts()
    body = _group("body", p["bodies"][look["body"]] + p["outfits"][look["outfit"]], pal)
    head = _group(
        "head",
        p["head"] + p["hair_styles"][look["hair_style"]] + p["accessories"][look["accessory"]],
        pal,
    )
    eyes = _group("face", fp["eyes"][face["eyes"]] + fp["brows"][face["brows"]], pal)
    closed_vis = mouth == "closed"
    closed = _group("mouth mouth-closed", fp["mouth_closed"][face["mouth_closed"]], pal,
                    "" if closed_vis else ' opacity="0"')  # fmt: skip
    opened = _group("mouth mouth-open", fp["mouth_open"][face["mouth_open"]], pal,
                    ' opacity="0"' if closed_vis else "")  # fmt: skip
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 72" role="img" '
        f'data-alt="sprite.avatar.child" data-expression="{expression}">'
        f"{body}{head}{eyes}{closed}{opened}</svg>"
    )
    bad = validate_svg(svg)
    if bad:
        raise ValueError(f"avatar outside the grammar: {bad}")
    return svg


def seat_row(children: list[dict[str, Any]], base: str = "default") -> str:
    """The class on one strip: each child {look, expression, speaking}. 64 by 72 per seat."""
    n = len(children)
    inner = ""
    for i, c in enumerate(children):
        mouth = "open" if c.get("speaking") else "closed"
        svg = avatar_svg(c["look"], c.get("expression", "neutral"), mouth, base)
        body = svg[svg.index(">") + 1 : -len("</svg>")]
        box = 'width="64" height="72" viewBox="0 0 64 72"'
        inner += f'<svg class="seat" x="{i * 64}" y="0" {box}>{body}</svg>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {64 * n} 72" role="img" '
        f'data-alt="sprite.scene.seat_row">{inner}</svg>'
    )
