"""Layout engines: pure functions that place units exactly and report what they drew.

Every function takes an item spec (or none), a count, a palette and a seed and returns a `Scene`:
the SVG and a machine-readable report such as {"item_id": "ball", "count_drawn": 45}. Integer
arithmetic only, so the TypeScript port draws byte-identical SVG. A counted unit is any element
whose class holds the token `u`; tests parse the SVG and count them against the report.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isqrt
from typing import Any

from services.api.sprites.grammar import compile_item, validate_svg
from services.api.sprites.rng import Rng

W, H, PAD = 240, 160, 8
MAX_COUNT = 100


@dataclass(frozen=True)
class Scene:
    svg: str
    report: dict[str, Any]


class LayoutError(ValueError):
    pass


def _use(item_id: str, x: int, y: int, size: int, cls: str = "u") -> str:
    return (
        f'<use href="#i-{item_id}" x="{x}" y="{y}" width="{size}" height="{size}" class="{cls}"/>'
    )


def _line(x1: int, y1: int, x2: int, y2: int, stroke: str, sw: int = 1, cls: str = "") -> str:
    c = f' class="{cls}"' if cls else ""
    geo = f'x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"'
    return f'<line{c} {geo} fill="none" stroke="{stroke}" stroke-width="{sw}"/>'


def _rect(x: int, y: int, w: int, h: int, fill: str, stroke: str, sw: int, cls: str = "") -> str:
    c = f' class="{cls}"' if cls else ""
    geo = f'x="{x}" y="{y}" width="{w}" height="{h}"'
    return f'<rect{c} {geo} fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def assemble(
    layout: str, specs: list[dict[str, Any]], pal: dict[str, str], body: str, report: dict[str, Any]
) -> Scene:
    defs = "".join(compile_item(s, pal) for s in specs)
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" '
        f'data-alt="sprite.scene.{layout}" data-layout="{layout}" '
        f'data-item="{report["item_id"]}" data-count="{report["count_drawn"]}">'
    )
    bg = f'<rect x="0" y="0" width="{W}" height="{H}" fill="{pal["mat"]}"/>'
    svg = f"{head}<defs>{defs}</defs>{bg}{body}</svg>"
    bad = validate_svg(svg)
    if bad:  # a layout bug, never user input: fail loudly
        raise LayoutError(f"{layout} produced SVG outside the grammar: {bad}")
    return Scene(svg, {**report, "layout": layout})


def _check_count(n: int, lo: int = 0, hi: int = MAX_COUNT) -> None:
    if not isinstance(n, int) or isinstance(n, bool) or not lo <= n <= hi:
        raise LayoutError(f"count must be an integer from {lo} to {hi}")


# ---------------------------------------------------------------------------------- row, grid
def row(spec: dict[str, Any], n: int, pal: dict[str, str], seed: int = 0) -> Scene:
    _check_count(n)
    per_row = min(max(n, 1), 20)
    rows = -(-n // per_row) if n else 0
    cell = min(24, (W - 2 * PAD) // per_row, (H - 2 * PAD) // max(rows, 1))
    x0, y0 = (W - per_row * cell) // 2, (H - rows * cell) // 2
    body = "".join(
        _use(spec["id"], x0 + (i % per_row) * cell, y0 + (i // per_row) * cell, cell)
        for i in range(n)
    )
    return assemble("row", [spec], pal, body, {"item_id": spec["id"], "count_drawn": n})


def grid_array(spec: dict[str, Any], r: int, c: int, pal: dict[str, str], seed: int = 0) -> Scene:
    _check_count(r, 1, 20)
    _check_count(c, 1, 20)
    cell = min(24, (W - 2 * PAD) // c, (H - 2 * PAD) // r)
    x0, y0 = (W - c * cell) // 2, (H - r * cell) // 2
    body = "".join(
        _use(spec["id"], x0 + j * cell, y0 + i * cell, cell) for i in range(r) for j in range(c)
    )
    rep = {"item_id": spec["id"], "count_drawn": r * c, "rows": r, "cols": c}
    return assemble("grid_array", [spec], pal, body, rep)


# ------------------------------------------------------------------------------- ten frame
def ten_frame(spec: dict[str, Any], n: int, pal: dict[str, str], seed: int = 0) -> Scene:
    _check_count(n, 0, 20)
    ink = pal["ink"]
    frames = 1 if n <= 10 else 2
    fx = (W - 100) // 2
    top = (H - frames * 40 - (frames - 1) * 16) // 2
    body = ""
    for k in range(frames):
        fy = top + k * 56
        body += f'<g class="frame">{_rect(fx, fy, 100, 40, pal["mat"], ink, 2)}'
        body += "".join(_line(fx + 20 * i, fy, fx + 20 * i, fy + 40, ink) for i in (1, 2, 3, 4))
        body += _line(fx, fy + 20, fx + 100, fy + 20, ink) + "</g>"
    for i in range(n):
        k, j = divmod(i, 10)
        r, c = divmod(j, 5)
        body += _use(spec["id"], fx + c * 20 + 1, top + k * 56 + r * 20 + 1, 18)
    return assemble(
        "ten_frame", [spec], pal, body, {"item_id": spec["id"], "count_drawn": n, "frames": frames}
    )


# --------------------------------------------------------------------------------- bundles
def _bundle(item_id: str, x: int, y: int, cell: int, ink: str) -> str:
    """Exactly ten units in a 5 by 2 block, boxed (the shape that says bundle)."""
    units = "".join(_use(item_id, x + (i % 5) * cell, y + (i // 5) * cell, cell) for i in range(10))
    band = _rect(x - 1, y - 1, 5 * cell + 2, 2 * cell + 2, "none", ink, 1, "band")
    return f'<g class="bundle">{units}{band}</g>'


def bundle_group(spec: dict[str, Any], n: int, pal: dict[str, str], seed: int = 0) -> Scene:
    _check_count(n)
    t, o = divmod(n, 10)
    rows = -(-t // 5) if t else 0
    total = rows * 18 + max(rows - 1, 0) * 4 + (12 if (rows and o) else 0) + (16 if o else 0)
    y = (H - total) // 2
    body = ""
    for r in range(rows):
        k = min(5, t - r * 5)
        width = k * 40 + (k - 1) * 4
        x0 = (W - width) // 2
        for j in range(k):
            body += _bundle(spec["id"], x0 + j * 44, y + r * 22 + 1, 8, pal["ink"])
    if o:
        ly = y + (rows * 22 - 4 + 12 if rows else 0)
        lx = (W - o * 16) // 2
        body += "".join(_use(spec["id"], lx + i * 16, ly, 16) for i in range(o))
    rep = {"item_id": spec["id"], "count_drawn": n, "bundles": t, "loose": o}
    return assemble("bundle_group", [spec], pal, body, rep)


def place_value_mat(spec: dict[str, Any], n: int, pal: dict[str, str], seed: int = 0) -> Scene:
    _check_count(n, 0, 99)
    ink, mat = pal["ink"], pal["mat"]
    t, o = divmod(n, 10)
    body = _rect(8, 8, 112, 144, mat, ink, 2, "frame") + _rect(
        124, 8, 108, 144, mat, ink, 2, "frame"
    )
    body += (
        _rect(58, 14, 14, 8, "none", ink, 1, "tick")
        + f'<circle class="tick" cx="178" cy="18" r="4" fill="{ink}"/>'
    )
    for i in range(t):
        r, c = divmod(i, 3)
        body += _bundle(spec["id"], 14 + c * 36, 32 + r * 22, 6, ink)
    for i in range(o):
        r, c = divmod(i, 5)
        body += _use(spec["id"], 134 + c * 18, 40 + r * 22, 16)
    rep = {"item_id": spec["id"], "count_drawn": n, "tens": t, "ones": o}
    return assemble("place_value_mat", [spec], pal, body, rep)


# ----------------------------------------------------------------------- number line, bars
def number_line(lo: int, hi: int, marks: list[int], pal: dict[str, str], seed: int = 0) -> Scene:
    if not 1 <= hi - lo <= MAX_COUNT:
        raise LayoutError("the number line spans 1 to 100 steps")
    if any(m < lo or m > hi for m in marks):
        raise LayoutError("a mark lies outside the line")
    ink = pal["ink"]

    def x(v: int) -> int:
        return 12 + (v - lo) * 216 // (hi - lo)

    body = _line(12, 90, 228, 90, ink, 2)
    # one path per tick length (short, every 5, every 10): many ticks, a few bytes each
    for h, pick in (
        (6, lambda v: v % 5 != 0),
        (10, lambda v: v % 5 == 0 and v % 10 != 0),
        (14, lambda v: v % 10 == 0),
    ):
        d = "".join(f"M{x(v)} 90v{h}" for v in range(lo, hi + 1) if pick(v))
        if d:
            body += f'<path class="tick" d="{d}" fill="none" stroke="{ink}" stroke-width="1"/>'
    for m in sorted(marks):
        paint = f'fill="{pal["accent"]}" stroke="{ink}" stroke-width="1"'
        body += f'<circle class="u mk" cx="{x(m)}" cy="78" r="5" {paint}/>'
    rep = {"item_id": "number_line", "count_drawn": len(marks), "min": lo, "max": hi,
           "marks": sorted(marks), "ticks": hi - lo + 1}  # fmt: skip
    return assemble("number_line", [], pal, body, rep)


def bar_model(parts: list[int], pal: dict[str, str], seed: int = 0) -> Scene:
    if not parts or any(not isinstance(p, int) or p < 1 for p in parts) or sum(parts) > 200:
        raise LayoutError("a bar model needs 1 or more positive parts totalling at most 200")
    ink, total = pal["ink"], sum(parts)
    body, cum = "", 0
    for i, p in enumerate(parts):
        x1, x2 = 12 + cum * 216 // total, 12 + (cum + p) * 216 // total
        fill = pal["item_a"] if i % 2 == 0 else pal["item_b"]
        body += _rect(x1, 60, x2 - x1, 40, fill, ink, 1, "u")
        if i % 2 == 1:  # a pattern as well as a colour: the bar reads without colour
            body += "".join(_line(x, 60, x, 100, ink, 1) for x in range(x1 + 4, x2 - 2, 6))
        cum += p
    pts = 'points="12,52 12,46 228,46 228,52"'
    body += f'<polyline fill="none" stroke="{ink}" stroke-width="1" {pts}/>'
    rep = {"item_id": "bar_model", "count_drawn": len(parts), "parts": list(parts), "total": total}
    return assemble("bar_model", [], pal, body, rep)


# --------------------------------------------------------------------- subtraction and scatter
def cross_out(
    spec: dict[str, Any], total: int, marked: int, pal: dict[str, str], seed: int = 0
) -> Scene:
    _check_count(total, 1, MAX_COUNT)
    _check_count(marked, 0, total)
    cols = isqrt(total - 1) + 1
    rows = -(-total // cols)
    cell = min(24, (W - 2 * PAD) // cols, (H - 2 * PAD) // rows)
    x0, y0 = (W - cols * cell) // 2, (H - rows * cell) // 2
    body = ""
    for i in range(total):
        x, y = x0 + (i % cols) * cell, y0 + (i // cols) * cell
        if i < marked:
            body += _use(spec["id"], x, y, cell, "u x")
            body += (
                '<g class="mk">'
                + _line(x, y, x + cell, y + cell, pal["accent"], 2)
                + _line(x + cell, y, x, y + cell, pal["accent"], 2)
                + "</g>"
            )
        else:
            body += _use(spec["id"], x, y, cell)
    rep = {"item_id": spec["id"], "count_drawn": total, "marked": marked}
    return assemble("cross_out", [spec], pal, body, rep)


def _place(n: int, ox: int, oy: int, aw: int, ah: int, rng: Rng) -> list[tuple[int, int, int]]:
    """n non-overlapping (x, y, size) boxes in a region, seeded. Cells never overlap by design."""
    if n == 0:
        return []
    cell = 24
    while (aw // cell) * (ah // cell) < n:
        cell -= 1
        if cell < 8:
            raise LayoutError("too many items for the area")
    cols = aw // cell
    idx = rng.shuffle(list(range((aw // cell) * (ah // cell))))[:n]
    out = []
    for k in idx:
        jx, jy = rng.below(3), rng.below(3)
        out.append((ox + (k % cols) * cell + jx, oy + (k // cols) * cell + jy, cell - 2))
    return out


def scatter(spec: dict[str, Any], n: int, pal: dict[str, str], seed: int = 0) -> Scene:
    _check_count(n)
    boxes = _place(n, PAD, PAD, W - 2 * PAD, H - 2 * PAD, Rng(seed))
    body = "".join(_use(spec["id"], x, y, s) for x, y, s in boxes)
    return assemble("scatter", [spec], pal, body, {"item_id": spec["id"], "count_drawn": n})


def two_groups(spec: dict[str, Any], a: int, b: int, pal: dict[str, str], seed: int = 0) -> Scene:
    _check_count(a)
    _check_count(b)
    rng = Rng(seed)
    aw = (W - 2 * PAD - 8) // 2
    ga = "".join(_use(spec["id"], x, y, s) for x, y, s in _place(a, PAD, PAD, aw, H - 2 * PAD, rng))
    bx = PAD + aw + 8
    gb = "".join(_use(spec["id"], x, y, s) for x, y, s in _place(b, bx, PAD, aw, H - 2 * PAD, rng))
    frame = _rect(bx - 2, PAD - 2, aw + 4, H - 2 * PAD + 4, "none", pal["ink"], 2, "frame")
    body = f'<g class="ga">{ga}</g><g class="gb">{frame}{gb}</g>'
    rep = {"item_id": spec["id"], "count_drawn": a + b, "groups": [a, b]}
    return assemble("two_groups", [spec], pal, body, rep)
