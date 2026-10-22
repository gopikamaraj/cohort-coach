"""The sprite grammar: what an item spec and a rendered SVG may contain, and the compiler for specs.

Specs are data (JSON); only a whitelist of shapes and attributes is allowed, colours are palette
slot names (never hex), numbers are integers. The same rules run on every rendered SVG, so a
scene can never carry a script, text, an animation or an external reference.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

from services.api.sprites.palette import SLOTS

ALLOWED_TAGS = frozenset(
    "svg g circle ellipse rect line polyline polygon path defs linearGradient radialGradient stop "
    "clipPath use".split()
)
FORBIDDEN_TAGS = frozenset(
    "script foreignObject image text tspan title desc style a animate animateTransform set".split()
)
ALLOWED_ATTRS = frozenset(
    "xmlns viewBox role class id x y width height cx cy r rx ry x1 y1 x2 y2 points d fill stroke "
    "stroke-width opacity transform href offset stop-color gradientUnits clip-path".split()
)
ALLOWED_CLASSES = frozenset(
    "u x mk bundle band ga gb frame mouth mouth-open mouth-closed body head face seat tick".split()
)

SPEC_SHAPES: dict[str, tuple[str, ...]] = {
    "circle": ("cx", "cy", "r"),
    "ellipse": ("cx", "cy", "rx", "ry"),
    "rect": ("x", "y", "width", "height", "rx"),
    "line": ("x1", "y1", "x2", "y2"),
    "polyline": ("points",),
    "polygon": ("points",),
    "path": ("d",),
}
REQUIRED = {
    "circle": ("cx", "cy", "r"),
    "ellipse": ("cx", "cy", "rx", "ry"),
    "rect": ("x", "y", "width", "height"),
    "line": ("x1", "y1", "x2", "y2"),
    "polyline": ("points",),
    "polygon": ("points",),
    "path": ("d",),
}
STYLE_KEYS = ("fill", "stroke", "stroke_width", "transform")
VIEWBOX = {
    "item": (0, 0, 24, 24),
    "avatar": (0, 0, 64, 72),
    "mat": (0, 0, 240, 160),
    "scene": (0, 0, 240, 160),
}
BUDGET = {"item": 2048, "avatar": 12288, "mat": 6144}

_ID = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
_PATH = re.compile(r"^[MmLlHhVvCcSsQqTtAaZz0-9\s,.\-]+$")
_POINTS = re.compile(r"^[0-9\s,\-]+$")
_NUM = r"-?\d+( -?\d+){0,2}"
_TRANSFORM = re.compile(
    rf"^(translate|rotate|scale)\({_NUM}\)( (translate|rotate|scale)\({_NUM}\))*$"
)
_HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")
_CLASS = re.compile(r"^[a-z0-9 _-]+$")


def validate_svg(svg: str) -> list[str]:
    """Rule ids broken by this SVG; empty when it is within the grammar."""
    try:
        root = ET.fromstring(svg)
    except ET.ParseError:
        return ["not_well_formed"]
    out: list[str] = []
    for el in root.iter():
        tag = el.tag.split("}")[-1] if isinstance(el.tag, str) else ""
        if tag in FORBIDDEN_TAGS:
            out.append(f"forbidden_element:{tag}")
        elif tag not in ALLOWED_TAGS:
            out.append(f"element_not_allowed:{tag}")
        if (el.text or "").strip() or (el.tail or "").strip():
            out.append("text_node")
        for name, value in el.attrib.items():
            if (
                "}" in name
            ):  # a namespaced attribute (xlink:href and the like) is not in the grammar
                out.append(f"attribute_not_allowed:{name.split('}')[-1]}")
                continue
            if name.lower().startswith("on"):
                out.append(f"event_attribute:{name}")
            elif name == "style":
                out.append("style_attribute")
            elif name == "href":
                if not value.startswith("#"):
                    out.append("external_href")
            elif name == "class":
                if not _CLASS.match(value) or not set(value.split()) <= ALLOWED_CLASSES:
                    out.append(f"class_not_allowed:{value}")
            elif name.startswith("data-"):
                if not re.match(r"^[a-zA-Z0-9_ .:/-]*$", value):
                    out.append(f"data_value:{name}")
            elif name not in ALLOWED_ATTRS:
                out.append(f"attribute_not_allowed:{name}")
    return sorted(set(out))


def validate_spec(spec: dict[str, Any], kind: str = "item") -> list[str]:
    """Rule ids broken by an item, avatar-part or mat spec. Empty when it is valid."""
    out: list[str] = []
    if not _ID.match(str(spec.get("id", ""))):
        out.append("bad_id")
    if spec.get("category", kind) != kind:
        out.append("category_mismatch")
    if tuple(spec.get("viewBox", VIEWBOX[kind])) != VIEWBOX[kind]:
        out.append("viewbox_not_fixed")
    if not _int(spec.get("version")):
        out.append("bad_version")
    alt = spec.get("alt", {}).get("key", "")
    if not re.match(rf"^sprite\.{kind}\.[a-z0-9_]+$", alt):
        out.append("alt_key_format")
    if not spec.get("topics"):
        out.append("topics_missing")
    if _HEX.search(repr(spec)):
        out.append("raw_colour")
    gradients = {g.get("id") for g in spec.get("defs", [])}
    allowed_paint = {*SLOTS, "none", *(f"grad:{g}" for g in gradients)}
    parts = spec.get("parts", [])
    if not parts:
        out.append("no_parts")
    for part in parts:
        out += _part_rules(part, allowed_paint)
    for g in spec.get("defs", []):
        out += _gradient_rules(g)
    if not out:
        out += _budget_rules(spec, kind)
    return sorted(set(out))


def _int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _part_rules(part: dict[str, Any], allowed_paint: set[str]) -> list[str]:
    out: list[str] = []
    shape = part.get("shape")
    if shape not in SPEC_SHAPES:
        return [f"shape_not_allowed:{shape}"]
    known = {"shape", *SPEC_SHAPES[shape], *STYLE_KEYS}
    for key in part:
        if key not in known:
            out.append(f"attribute_not_allowed:{key}")
    for key in REQUIRED[shape]:
        if key not in part:
            out.append(f"missing:{key}")
    for key in SPEC_SHAPES[shape]:
        v = part.get(key)
        if v is None:
            continue
        if key == "d":
            if not isinstance(v, str) or not _PATH.match(v):
                out.append("bad_path_data")
        elif key == "points":
            if not isinstance(v, str) or not _POINTS.match(v):
                out.append("bad_points")
        elif not _int(v):
            out.append("number_not_integer")
    for key in ("fill", "stroke"):
        v = part.get(key)
        if v is not None and v not in allowed_paint:
            out.append(f"paint_not_a_slot:{key}")
    if "stroke_width" in part and not _int(part["stroke_width"]):
        out.append("number_not_integer")
    if "transform" in part and not _TRANSFORM.match(str(part["transform"])):
        out.append("bad_transform")
    return out


def _gradient_rules(g: dict[str, Any]) -> list[str]:
    out: list[str] = []
    if g.get("type") not in ("radialGradient", "linearGradient"):
        return ["gradient_type"]
    if not _ID.match(str(g.get("id", ""))):
        out.append("bad_id")
    keys = ("cx", "cy", "r") if g["type"] == "radialGradient" else ("x1", "y1", "x2", "y2")
    if any(not _int(g.get(k)) for k in keys):
        out.append("number_not_integer")
    for s in g.get("stops", []):
        if s.get("color") not in SLOTS or not _int(s.get("offset")):
            out.append("gradient_stop")
    if len(g.get("stops", [])) < 2:
        out.append("gradient_stop")
    return out


def _budget_rules(spec: dict[str, Any], kind: str) -> list[str]:
    from services.api.sprites.palette import palette

    size = len(compile_item(spec, palette("default")).encode("utf-8"))
    return [f"over_budget:{size}>{BUDGET[kind]}"] if size > BUDGET[kind] else []


# ------------------------------------------------------------------------------------ compiler
def part_markup(part: dict[str, Any], pal: dict[str, str], scope: str) -> str:
    shape = part["shape"]
    attrs = [f'{k}="{part[k]}"' for k in SPEC_SHAPES[shape] if k in part]
    attrs.append(f'fill="{_paint(part.get("fill", "none"), pal, scope)}"')
    if "stroke" in part:
        attrs.append(f'stroke="{_paint(part["stroke"], pal, scope)}"')
        attrs.append(f'stroke-width="{part.get("stroke_width", 1)}"')
    if "transform" in part:
        attrs.append(f'transform="{part["transform"]}"')
    return f"<{shape} {' '.join(attrs)}/>"


def _paint(value: str, pal: dict[str, str], scope: str) -> str:
    if value == "none":
        return "none"
    if value.startswith("grad:"):
        return f"url(#{scope}-{value[5:]})"
    return pal[value]


def gradient_markup(g: dict[str, Any], pal: dict[str, str], scope: str) -> str:
    keys = ("cx", "cy", "r") if g["type"] == "radialGradient" else ("x1", "y1", "x2", "y2")
    geo = " ".join(f'{k}="{g[k]}"' for k in keys)
    stops = "".join(
        f'<stop offset="{s["offset"]}%" stop-color="{pal[s["color"]]}"/>' for s in g["stops"]
    )
    tag = g["type"]
    return f'<{tag} id="{scope}-{g["id"]}" gradientUnits="userSpaceOnUse" {geo}>{stops}</{tag}>'


def compile_item(spec: dict[str, Any], pal: dict[str, str]) -> str:
    """The reusable definition of one item: a nested `svg` that scenes instance with `use`."""
    scope = f"i-{spec['id']}"
    vb = " ".join(str(v) for v in spec.get("viewBox", VIEWBOX["item"]))
    inner = "".join(gradient_markup(g, pal, scope) for g in spec.get("defs", []))
    if inner:
        inner = f"<defs>{inner}</defs>"
    inner += "".join(part_markup(p, pal, scope) for p in spec["parts"])
    return f'<svg id="{scope}" viewBox="{vb}">{inner}</svg>'
