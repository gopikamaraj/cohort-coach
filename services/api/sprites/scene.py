"""Scenes from a topic pack: the layout engines plus word-problem templates with number slots.

Numbers are filled by code. Every filled pair and every filled sentence goes through the
no-check-items validator, so a pack can never teach a Form A or Form B item.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ai.validators.check_items import check_items, check_pair
from services.api import strings
from services.api.sprites import layouts as L
from services.api.sprites.items import load_item, load_pack
from services.api.sprites.palette import palette

LAYOUTS = (
    "row", "grid_array", "ten_frame", "bundle_group", "place_value_mat", "number_line",
    "bar_model", "cross_out", "scatter", "two_groups",
)  # fmt: skip


class SceneError(ValueError):
    pass


@dataclass(frozen=True)
class TemplateScene:
    scene: L.Scene
    text: str  # the problem in her language, numbers filled by code
    alt_key: str
    slots: dict[str, int]


def render_layout(
    layout: str, item_id: str | None, args: dict[str, Any], pal: dict[str, str], seed: int = 0
) -> L.Scene:
    """One layout by name. `args` carries the layout's own numbers (n, r, c, total, marked, ...)."""
    spec = load_item(item_id) if item_id else {}
    match layout:
        case "row":
            return L.row(spec, args["n"], pal, seed)
        case "grid_array":
            return L.grid_array(spec, args["r"], args["c"], pal, seed)
        case "ten_frame":
            return L.ten_frame(spec, args["n"], pal, seed)
        case "bundle_group":
            return L.bundle_group(spec, args["n"], pal, seed)
        case "place_value_mat":
            return L.place_value_mat(spec, args["n"], pal, seed)
        case "number_line":
            return L.number_line(args["min"], args["max"], list(args["marks"]), pal, seed)
        case "bar_model":
            return L.bar_model(list(args["parts"]), pal, seed)
        case "cross_out":
            return L.cross_out(spec, args["total"], args["marked"], pal, seed)
        case "scatter":
            return L.scatter(spec, args["n"], pal, seed)
        case "two_groups":
            return L.two_groups(spec, args["a"], args["b"], pal, seed)
    raise SceneError(f"unknown layout {layout!r}")


def render_template(
    pack_id: str,
    template_id: str,
    a: int,
    b: int,
    *,
    lang: str = "en",
    pal: str = "default",
    seed: int = 0,
    allow_unapproved: bool = False,
) -> TemplateScene:
    """A word-problem scene: the picture and the sentence, from the template and two numbers."""
    pack = load_pack(pack_id)
    if pack["status"] != "enabled" and not allow_unapproved:
        raise SceneError(
            f"pack {pack_id} is {pack['status']}: only an enabled pack reaches a teacher"
        )
    tpl = next((t for t in pack["templates"] if t["id"] == template_id), None)
    if tpl is None:
        raise SceneError(f"pack {pack_id} has no template {template_id}")
    bad = check_pair(a, "op", b)
    if bad:
        raise SceneError(f"these numbers are a check item: {bad[0].detail}")
    text = strings.text(lang, tpl["text_key"], a=a, b=b)
    bad_text = check_items(text)
    if bad_text:
        raise SceneError(f"the sentence holds a check item: {bad_text[0].detail}")
    p = palette(pal)
    op = tpl["operation"]
    if op == "add":
        scene = render_layout(tpl["layout"], tpl["item"], {"a": a, "b": b}, p, seed)
    elif op == "sub":
        if b > a:
            raise SceneError("a subtraction scene needs the second number not above the first")
        scene = render_layout(tpl["layout"], tpl["item"], {"total": a, "marked": b}, p, seed)
    elif op == "parts":
        scene = render_layout(tpl["layout"], None, {"parts": [a, b]}, p, seed)
    else:
        raise SceneError(f"unknown operation {op!r}")
    return TemplateScene(scene, text, f"sprite.scene.{tpl['layout']}", {"a": a, "b": b})
