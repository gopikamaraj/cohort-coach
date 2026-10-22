"""Draw the sprite contact sheet: what a coach looks at before approving a pack.

Writes docs/evidence/sprites/contact-sheet.png and contact-sheet.json (the same facts as data, plus
every validator failure; an empty list means none). Everything drawn comes from the renderer and
the content files: nothing here is hand-made. Run: python scripts/sprite_contact_sheet.py
"""

from __future__ import annotations

import io
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.api.sprites.avatar import (  # noqa: E402
    avatar_svg,
    expression_ids,
    persona_look,
    personas,
)
from services.api.sprites.grammar import validate_spec, validate_svg  # noqa: E402
from services.api.sprites.items import item_ids, load_item, load_pack, pack_ids  # noqa: E402
from services.api.sprites.layouts import bundle_group, number_line, place_value_mat, scatter  # noqa: E402
from services.api.sprites.packs import validate_pack  # noqa: E402
from services.api.sprites.palette import palette, palette_names  # noqa: E402
from services.api.sprites.png import svg_to_png  # noqa: E402

OUT = ROOT / "docs" / "evidence" / "sprites"
COUNTS = (1, 5, 10, 23, 45)
TILE_W, TILE_H = 160, 107
AV_W, AV_H = 80, 90
INK, PAPER = (20, 32, 31), (255, 255, 255)
FONT = ImageFont.load_default(size=13)
SMALL = ImageFont.load_default(size=10)
BIG = ImageFont.load_default(size=16)


def tile(svg: str, width: int) -> Image.Image:
    bad = validate_svg(svg)
    if bad:
        raise ValueError(bad)
    return Image.open(io.BytesIO(svg_to_png(svg, width=width, background="#ffffff"))).convert("RGB")


def tables() -> dict[str, dict[str, str]]:
    return {
        lang: json.loads((ROOT / "strings" / f"{lang}.json").read_text(encoding="utf-8"))
        for lang in ("en", "hi", "ta")
    }


def main() -> int:
    failures: list[str] = []
    strings = tables()
    packs = {p: load_pack(p) for p in pack_ids()}
    enabled = [p for p, d in packs.items() if d.get("status") == "enabled"]
    skipped = {p: d.get("status") for p, d in packs.items() if p not in enabled}
    for pid, pack in packs.items():
        failures += [f"pack {pid}: {f}" for f in validate_pack(pack, strings)]
    for iid in item_ids():
        failures += [f"item {iid}: {f}" for f in validate_spec(load_item(iid))]

    sections: list[tuple[str, Image.Image]] = []
    pal = palette("default")

    # items at counts 1, 5, 10, 23, 45 for every item of every enabled pack
    rows: list[tuple[str, list[Image.Image]]] = []
    for pid in enabled:
        for iid in packs[pid]["items"]:
            spec = load_item(iid)
            tiles = []
            for n in COUNTS:
                scene = scatter(spec, n, pal, seed=n) if iid != "ten_frame" else None
                if scene is None:  # a ten-frame is one frame; show 7 and 15 counters
                    from services.api.sprites.layouts import ten_frame

                    scene = ten_frame(load_item("counter"), min(n, 20), pal)
                if scene.report["count_drawn"] != min(n, 20 if iid == "ten_frame" else n):
                    failures.append(f"count mismatch: {iid} {n}")
                tiles.append(tile(scene.svg, TILE_W))
            rows.append((f"{pid} / {iid}", tiles))
    h = sum(TILE_H + 22 for _ in rows)
    items_img = Image.new("RGB", (TILE_W * len(COUNTS) + 8 * (len(COUNTS) + 1), h + 30), PAPER)
    d = ImageDraw.Draw(items_img)
    d.text(
        (8, 6),
        f"Items at counts {', '.join(map(str, COUNTS))} (scatter, seeded)",
        font=BIG,
        fill=INK,
    )
    y = 30
    for label, tiles in rows:
        d.text((8, y), label, font=FONT, fill=INK)
        for i, t in enumerate(tiles):
            items_img.paste(t, (8 + i * (TILE_W + 8), y + 18))
        y += TILE_H + 22
    sections.append(("items", items_img))

    # the same item in every palette
    pal_tiles = [
        (name, tile(scatter(load_item("ball"), 12, palette(name), seed=2).svg, TILE_W))
        for name in palette_names()
    ]
    pal_img = Image.new("RGB", (items_img.width, TILE_H + 56), PAPER)
    d = ImageDraw.Draw(pal_img)
    d.text(
        (8, 6), "Palettes (the high-contrast one reads by outline and shape)", font=BIG, fill=INK
    )
    for i, (name, t) in enumerate(pal_tiles):
        d.text((8 + i * (TILE_W + 8), 30), name, font=FONT, fill=INK)
        pal_img.paste(t, (8 + i * (TILE_W + 8), 48))
    sections.append(("palettes", pal_img))

    # the two mats
    mats = [
        ("place_value_mat, 47", tile(place_value_mat(load_item("stick"), 47, pal).svg, 320)),
        (
            "number_line 0 to 100, marks 3 50 99",
            tile(number_line(0, 100, [3, 50, 99], pal).svg, 320),
        ),
        ("bundle_group, 45", tile(bundle_group(load_item("ball"), 45, pal).svg, 320)),
    ]
    mat_img = Image.new("RGB", (items_img.width, 213 + 56), PAPER)
    d = ImageDraw.Draw(mat_img)
    d.text((8, 6), "Mats and groups", font=BIG, fill=INK)
    for i, (name, t) in enumerate(mats[:2]):
        d.text((8 + i * 336, 30), name, font=FONT, fill=INK)
        mat_img.paste(t, (8 + i * 336, 48))
    sections.append(("mats", mat_img))
    group_img = Image.new("RGB", (items_img.width, 213 + 30), PAPER)
    ImageDraw.Draw(group_img).text((8, 6), mats[2][0], font=FONT, fill=INK)
    group_img.paste(mats[2][1], (8, 24))
    sections.append(("groups", group_img))

    # every persona with every expression
    exprs = expression_ids()
    ids = list(personas())
    av_img = Image.new("RGB", (items_img.width, (AV_H + 6) * len(ids) + 56), PAPER)
    d = ImageDraw.Draw(av_img)
    d.text((8, 6), "Children: every persona with every expression (calm mouth)", font=BIG, fill=INK)
    for c, e in enumerate(exprs):
        d.text((70 + c * (AV_W + 4), 30), e, font=SMALL, fill=INK)
    for r, pid in enumerate(ids):
        d.text((8, 56 + r * (AV_H + 6) + 34), pid, font=FONT, fill=INK)
        look = persona_look(pid)["look"]
        for c, e in enumerate(exprs):
            av_img.paste(
                tile(avatar_svg(look, e, "closed"), AV_W),
                (70 + c * (AV_W + 4), 50 + r * (AV_H + 6)),
            )
    sections.append(("avatars", av_img))

    sheet = Image.new(
        "RGB", (items_img.width, sum(i.height + 12 for _, i in sections) + 150), PAPER
    )
    d = ImageDraw.Draw(sheet)
    d.text(
        (8, 8),
        "Sprite contact sheet (generated by scripts/sprite_contact_sheet.py)",
        font=BIG,
        fill=INK,
    )
    d.text((8, 32), f"Enabled packs: {', '.join(enabled) or 'none'}", font=FONT, fill=INK)
    d.text((8, 50), f"Not enabled (not drawn): {json.dumps(skipped)}", font=FONT, fill=INK)
    d.text(
        (8, 68),
        f"Validator failures: {len(failures)}",
        font=FONT,
        fill=(150, 0, 0) if failures else INK,
    )
    for k, f in enumerate(failures[:3]):
        d.text((8, 86 + 16 * k), f[:110], font=FONT, fill=(150, 0, 0))
    y = 140
    for _, img in sections:
        sheet.paste(img, (0, y))
        y += img.height + 12
    OUT.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT / "contact-sheet.png", optimize=True)
    (OUT / "contact-sheet.json").write_text(
        json.dumps(
            {
                "generated": datetime.now(UTC).strftime("%Y-%m-%d"),
                "source": "scripts/sprite_contact_sheet.py",
                "enabled_packs": enabled,
                "not_enabled": skipped,
                "items": item_ids(),
                "counts": list(COUNTS),
                "personas": ids,
                "expressions": exprs,
                "validator_failures": failures,
            },
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"wrote {OUT / 'contact-sheet.png'} ({sheet.width}x{sheet.height}); "
        f"failures: {len(failures)}"
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
