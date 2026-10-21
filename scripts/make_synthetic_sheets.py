"""Render the SYNTHETIC handwritten answer-sheet test set (coverage heroes and demo classes).

Usage: python scripts/make_synthetic_sheets.py [--out DIR] [--seed 2026] [--quick]

Everything is synthetic. Files start with SIM_, the manifest says synthetic=true, and nothing may
be shown as real pilot data or as real children's work: the "handwriting" is open-licence fonts
(plus a stroke skeleton for deliberately ambiguous glyphs) with random rotation, size, baseline,
stroke and pencil-grain variation, then a simulated phone photo (perspective, lighting, blur,
noise, crumple, finger, JPEG). The truth in the manifest is what the code drew.

Output (default data/synthetic_sheets/, git-ignored): SIM_*.jpg, manifest.json, manifest.csv,
contact_sheet.png, README.md and SIM_handwritten_sheets.zip. The self-check at the end
re-implements the scoring rule, recomputes every class prevalence from the generated truth and
asserts the targets (it exits non-zero if any fails).
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import random
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.ndimage import gaussian_filter, map_coordinates

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DPI = 150
W, H = 1240, 1754  # A4 at 150 dpi
FONT_BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
FONT_FILES = {
    "PatrickHand": "patrickhand/PatrickHand-Regular.ttf",
    "Kalam": "kalam/Kalam-Regular.ttf",
    "KalamLight": "kalam/Kalam-Light.ttf",
    "KalamBold": "kalam/Kalam-Bold.ttf",
    "IndieFlower": "indieflower/IndieFlower-Regular.ttf",
    "Caveat": "caveat/Caveat%5Bwght%5D.ttf",
    "Mukta": "mukta/Mukta-Regular.ttf",
    "MuktaBold": "mukta/Mukta-Bold.ttf",
}
DEVA_DIGITS = "०१२३४५६७८९"
TO_ASCII = {ord(d): str(i) for i, d in enumerate(DEVA_DIGITS)}
TO_DEVA = {str(i): d for i, d in enumerate(DEVA_DIGITS)}
JPEG_LIMIT = 390_000

# ---------------------------------------------------------------- the spec (from the brief) ----

KEY = {
    "A": [346, 728, 85, 74, 82, 35, 38, 26, 43, 54],
    "B": [264, 853, 75, 84, 72, 45, 48, 36, 53, 64],
}
OPERANDS = {
    "A": {
        3: (38, 47),
        4: (46, 28),
        5: (59, 23),
        6: (87, 52),
        7: (74, 36),
        8: (45, 19),
        9: (82, 39),
        10: (81, 27),
    },
    "B": {
        3: (29, 46),
        4: (35, 49),
        5: (18, 54),
        6: (86, 41),
        7: (83, 35),
        8: (64, 28),
        9: (71, 18),
        10: (93, 29),
    },
}
ERR: dict[str, dict[str, dict[int, list[int]]]] = {
    "A": {
        "PV-HEARD": {1: [3046, 30046, 300406], 2: [7028, 70028, 700208]},
        "PV-REVERSE": {1: [364], 2: [782]},
        "BOTH": {1: [3064, 30064, 300604], 2: [7082, 70082, 700802]},
        "ADD-NOCARRY": {3: [75], 4: [64], 5: [72]},
        "ADD-WHOLE-ONES": {3: [715], 4: [614], 5: [712]},
        "SUB-SFL": {7: [42], 8: [34], 9: [57], 10: [66]},
        "SUB-NODEC": {7: [48], 8: [36], 9: [53], 10: [64]},
    },
    "B": {
        "PV-HEARD": {1: [2064, 20064, 200604], 2: [8053, 80053, 800503]},
        "PV-REVERSE": {1: [246], 2: [835]},
        "BOTH": {1: [2046, 20046, 200406], 2: [8035, 80035, 800305]},
        "ADD-NOCARRY": {3: [65], 4: [74], 5: [62]},
        "ADD-WHOLE-ONES": {3: [615], 4: [714], 5: [612]},
        "SUB-SFL": {7: [52], 8: [44], 9: [67], 10: [76]},
        "SUB-NODEC": {7: [58], 8: [46], 9: [63], 10: [74]},
    },
}
SHOWN = ("PV-HEARD", "PV-REVERSE", "ADD-NOCARRY", "SUB-SFL", "SUB-NODEC")


def to_value(written: str) -> int | None:
    """The integer a written answer stands for (Devanagari digits equal ASCII); None if not one number."""
    text = written.strip().translate(TO_ASCII)
    return int(text) if text.isascii() and text.isdigit() else None


def label_of(form: str, item: int, value: int | None) -> str:
    if value is None:
        return "blank"
    if value == KEY[form][item - 1]:
        return "correct"
    codes: list[str] = []
    for code, per_item in ERR[form].items():
        if value in per_item.get(item, []):
            codes.append(code)
    if not codes:
        return "other"
    if "BOTH" in codes:
        return "PV-HEARD+PV-REVERSE"
    if codes == ["ADD-WHOLE-ONES"]:
        return "untracked"
    return codes[0]


def families(label: str) -> list[str]:
    return [c for c in label.split("+") if c in SHOWN]


def score(form: str, values: list[int | None]) -> dict[str, Any]:
    """The scoring rule, re-implemented from the brief (a crossed-out answer is already removed)."""
    labels = [label_of(form, i + 1, v) for i, v in enumerate(values)]
    hits: Counter[str] = Counter()
    for lab in labels:
        for fam in families(lab):
            hits[fam] += 1
    present = []
    if hits["PV-HEARD"] >= 2 and all("PV-HEARD" in families(labels[i]) for i in (0, 1)):
        present.append("PV-HEARD")
    if hits["PV-REVERSE"] >= 2 and all("PV-REVERSE" in families(labels[i]) for i in (0, 1)):
        present.append("PV-REVERSE")
    for fam, items in (
        ("ADD-NOCARRY", (3, 4, 5)),
        ("SUB-SFL", (7, 8, 9, 10)),
        ("SUB-NODEC", (7, 8, 9, 10)),
    ):
        if sum(1 for i in items if fam in families(labels[i - 1])) >= 2:
            present.append(fam)
    anchor_wrong = values[5] != KEY[form][5]
    one_hit_only = not present and any(hits[f] >= 1 for f in SHOWN)
    return {"labels": labels, "present": present, "anchor_wrong": anchor_wrong, "one_hit_only": one_hit_only,
            "all_correct": all(v == k for v, k in zip(values, KEY[form], strict=True))}  # fmt: skip


# --------------------------------------------------------------------------------- fonts ----


def ensure_fonts(out: Path) -> dict[str, str]:
    folder = out / "_fonts"
    folder.mkdir(parents=True, exist_ok=True)
    paths: dict[str, str] = {}
    for name, rel in FONT_FILES.items():
        target = folder / f"{name}.ttf"
        if not target.exists():
            try:
                r = httpx.get(FONT_BASE + rel, timeout=30, follow_redirects=True)
                r.raise_for_status()
                target.write_bytes(r.content)
            except Exception as exc:  # noqa: BLE001
                print(f"could not download {name}: {exc}")
                continue
        paths[name] = str(target)
    win = Path("C:/Windows/Fonts")
    for name, fn in (
        ("InkFree", "Inkfree.ttf"),
        ("SegoePrint", "segoepr.ttf"),
        ("Nirmala", "Nirmala.ttc"),
    ):
        if (win / fn).exists():
            paths[name] = str(win / fn)
    if "Mukta" not in paths and "Nirmala" in paths:
        paths["Mukta"] = paths["MuktaBold"] = paths["Nirmala"]
    if "Kalam" not in paths:
        raise SystemExit("no Devanagari handwriting font available (Kalam); cannot continue")
    return paths


# ------------------------------------------------------------------------------ the sheet ----


def make_template(
    form: str, fonts: dict[str, str]
) -> tuple[Image.Image, dict[Any, tuple[int, int, int, int]], dict[str, Any]]:
    """The printed sheet and the answer-box rectangles (item number -> box)."""
    img = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(img)
    f = lambda name, size: ImageFont.truetype(fonts[name], size)  # noqa: E731
    d.text(
        (W // 2, 62), "गणित जाँच · Maths check", font=f("MuktaBold", 56), fill="black", anchor="mm"
    )
    d.text(
        (W // 2, 124),
        f"कक्षा 3 · Class 3 · फ़ॉर्म {form} · Form {form}",
        font=f("Mukta", 32),
        fill="black",
        anchor="mm",
    )
    boxes: dict[Any, tuple[int, int, int, int]] = {}
    d.text((60, 172), "कक्षा कोड · Class code", font=f("Mukta", 24), fill="black", anchor="ls")
    d.text((660, 172), "रोल नंबर · Roll no.", font=f("Mukta", 24), fill="black", anchor="ls")
    boxes["class"] = (60, 182, 600, 246)
    boxes["roll"] = (660, 182, 1180, 246)
    for key in ("class", "roll"):
        d.rectangle(boxes[key], outline="black", width=3)
    d.text(
        (60, 282),
        "हर उत्तर उसके डिब्बे में लिखो। · Write each answer in its box.",
        font=f("Mukta", 26),
        fill="black",
        anchor="lm",
    )
    y = 322
    d.text(
        (60, y),
        "सुनो और लिखो · Listen and write",
        font=f("MuktaBold", 30),
        fill="black",
        anchor="lm",
    )
    y += 28
    for item, x0 in ((1, 60), (2, 640)):
        d.text((x0, y + 18), f"{item}", font=f("MuktaBold", 30), fill="black", anchor="lm")
        boxes[item] = (x0, y + 40, x0 + 540, y + 40 + 148)
        d.rectangle(boxes[item], outline="black", width=3)
    y = y + 40 + 148 + 46

    def sum_block(items: list[int], y0: int, cols: list[int], op: str) -> int:
        for item, x0 in zip(items, cols, strict=True):
            a, b = OPERANDS[form][item]
            d.text((x0, y0 + 14), f"{item}", font=f("MuktaBold", 30), fill="black", anchor="lm")
            right = x0 + 330
            d.text((right, y0 + 70), f"{a}", font=f("Mukta", 50), fill="black", anchor="rm")
            d.text((x0 + 20, y0 + 124), op, font=f("Mukta", 50), fill="black", anchor="lm")
            d.text((right, y0 + 124), f"{b}", font=f("Mukta", 50), fill="black", anchor="rm")
            d.line((x0 + 10, y0 + 158, right + 10, y0 + 158), fill="black", width=4)
            d.text((x0 + 14, y0 + 232), "=", font=f("Mukta", 50), fill="black", anchor="lm")
            boxes[item] = (x0 + 70, y0 + 170, right + 10, y0 + 170 + 148)
            d.rectangle(boxes[item], outline="black", width=3)
        return y0 + 170 + 148 + 44

    d.text((60, y), "जोड़ो · Add", font=f("MuktaBold", 30), fill="black", anchor="lm")
    y = sum_block([3, 4, 5], y + 24, [60, 450, 840], "+")
    d.text((60, y), "घटाओ · Subtract", font=f("MuktaBold", 30), fill="black", anchor="lm")
    y = sum_block([6, 7, 8], y + 24, [60, 450, 840], "−")
    y = sum_block([9, 10], y - 4, [60, 450], "−")
    meta = {"bottom_of_content": y}
    return img, boxes, meta


# ------------------------------------------------------------------------- handwriting ----

SKELETON: dict[str, list[list[tuple[float, float]]]] = {
    "0": [
        [
            (0.5, 0.0),
            (0.15, 0.2),
            (0.08, 0.6),
            (0.3, 0.95),
            (0.7, 0.97),
            (0.92, 0.6),
            (0.85, 0.2),
            (0.5, 0.0),
        ]
    ],
    "1": [[(0.25, 0.25), (0.55, 0.0), (0.55, 1.0)], [(0.3, 1.0), (0.8, 1.0)]],
    "2": [
        [(0.1, 0.25), (0.3, 0.03), (0.7, 0.03), (0.9, 0.28), (0.7, 0.55), (0.1, 1.0), (0.95, 1.0)]
    ],
    "3": [
        [(0.1, 0.1), (0.5, 0.0), (0.85, 0.2), (0.5, 0.48), (0.9, 0.72), (0.55, 1.0), (0.1, 0.92)]
    ],
    "4": [[(0.7, 1.0), (0.7, 0.0), (0.05, 0.68), (0.95, 0.68)]],
    "5": [
        [(0.85, 0.0), (0.2, 0.0), (0.15, 0.45), (0.6, 0.38), (0.9, 0.6), (0.75, 0.95), (0.1, 0.9)]
    ],
    "6": [
        [
            (0.8, 0.05),
            (0.35, 0.3),
            (0.12, 0.65),
            (0.3, 0.98),
            (0.7, 0.95),
            (0.85, 0.7),
            (0.55, 0.5),
            (0.2, 0.62),
        ]
    ],
    "7": [[(0.1, 0.0), (0.9, 0.0), (0.4, 1.0)]],
    "8": [
        [
            (0.5, 0.0),
            (0.2, 0.15),
            (0.5, 0.45),
            (0.85, 0.72),
            (0.5, 1.0),
            (0.15, 0.75),
            (0.5, 0.45),
            (0.8, 0.15),
            (0.5, 0.0),
        ]
    ],
    "9": [[(0.8, 0.3), (0.5, 0.0), (0.15, 0.25), (0.5, 0.5), (0.85, 0.3), (0.8, 0.6), (0.5, 1.0)]],
}
VARIANTS: dict[str, list[list[tuple[float, float]]]] = {
    # an open-top 4 that can be read as a 9
    "4_open": [[(0.15, 0.0), (0.08, 0.5), (0.92, 0.55)], [(0.8, 0.0), (0.8, 1.0)]],
    # a 7 with a bar through the stem
    "7_bar": [[(0.1, 0.0), (0.9, 0.0), (0.4, 1.0)], [(0.25, 0.5), (0.75, 0.5)]],
    # a 5 with a rounded top, close to a 3
    "5_as_3": [
        [(0.15, 0.12), (0.55, 0.0), (0.85, 0.18), (0.5, 0.45), (0.9, 0.7), (0.55, 1.0), (0.1, 0.9)]
    ],
    # a 6 whose stem has almost closed into a 0
    "6_as_0": [
        [(0.5, 0.0), (0.12, 0.3), (0.1, 0.75), (0.5, 1.0), (0.9, 0.75), (0.88, 0.3), (0.5, 0.0)],
        [(0.55, 0.0), (0.72, 0.06)],
    ],
    "7_nobar": [[(0.1, 0.0), (0.9, 0.0), (0.4, 1.0)]],
}


def _chaikin(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Corner cutting, so a polyline skeleton reads as a pencil curve rather than a polygon."""
    out = [pts[0]]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:], strict=False):
        out += [
            (0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1),
            (0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1),
        ]
    out.append(pts[-1])
    return out


@dataclass
class Style:
    latin: str
    deva: str
    size: float
    rot: float
    baseline: float
    spacing: float
    stroke: int
    pressure: float
    grey: int
    shear: float
    smudge: float
    handed: str = "right"
    ident: str = ""


def make_style(
    rng: random.Random, fonts: dict[str, str], *, faint: bool = False, smudge: bool | None = None
) -> Style:
    latin = rng.choice(
        [
            n
            for n in ("PatrickHand", "Caveat", "IndieFlower", "Kalam", "InkFree", "SegoePrint")
            if n in fonts
        ]
    )
    handed = "left" if rng.random() < 0.2 else "right"
    return Style(
        latin=latin,
        deva=rng.choice(["Kalam", "KalamLight", "KalamBold"]),
        size=rng.uniform(112, 140),
        rot=rng.uniform(3, 8),
        baseline=rng.uniform(3, 12),
        spacing=rng.uniform(0.82, 1.1),
        stroke=rng.choice([0, 1, 1, 2]),
        pressure=(rng.uniform(0.35, 0.5) if faint else rng.uniform(0.62, 1.0)),
        grey=rng.randint(38, 85),
        shear=rng.uniform(-0.18, 0.18),
        smudge=(rng.uniform(0.6, 0.9) if smudge else 0.0)
        if smudge is not None
        else (rng.uniform(0.2, 0.5) if handed == "left" else 0.0),
        handed=handed,
        ident=f"{latin}/{handed}",
    )


def _glyph_mask(
    ch: str,
    style: Style,
    fonts: dict[str, str],
    size: float,
    rng: random.Random,
    variant: str | None,
) -> Image.Image:
    rot = rng.uniform(-style.rot, style.rot)
    shear = style.shear + rng.uniform(-0.05, 0.05)
    if variant:
        strokes = VARIANTS.get(variant or "", SKELETON.get(ch, SKELETON["0"]))
        gh = int(size * 0.72)
        gw = int(gh * 0.62)
        scale = 3
        m = Image.new("L", ((gw + 30) * scale, (gh + 30) * scale), 0)
        dm = ImageDraw.Draw(m)
        lw = max(3, int((5 + style.stroke * 2 + rng.uniform(-1, 1.5)) * scale))
        for stroke in strokes:
            stroke = _chaikin(_chaikin(stroke)) if len(stroke) > 2 else stroke
            pts = [
                (
                    (15 + (x + rng.uniform(-0.03, 0.03)) * gw) * scale,
                    (15 + (y + rng.uniform(-0.02, 0.02)) * gh) * scale,
                )
                for x, y in stroke
            ]
            dm.line(pts, fill=255, width=lw, joint="curve")
            for p in pts:
                dm.ellipse([p[0] - lw / 2, p[1] - lw / 2, p[0] + lw / 2, p[1] + lw / 2], fill=255)
        m = m.resize((gw + 30, gh + 30), Image.LANCZOS)
    else:
        font_name = style.deva if ch in DEVA_DIGITS else style.latin
        font = ImageFont.truetype(fonts[font_name], int(size))
        bbox = font.getbbox(ch, stroke_width=style.stroke)
        w, h = max(8, bbox[2] - bbox[0]), max(8, bbox[3] - bbox[1])
        m = Image.new("L", (w + 30, h + 30), 0)
        ImageDraw.Draw(m).text(
            (15 - bbox[0], 15 - bbox[1]), ch, font=font, fill=255, stroke_width=style.stroke
        )
    m = m.transform(
        m.size, Image.AFFINE, (1, shear, -shear * m.size[1] / 2, 0, 1, 0), resample=Image.BILINEAR
    )
    return m.rotate(rot, expand=True, resample=Image.BICUBIC)


def draw_written(
    sheet: Image.Image,
    text: str,
    box: tuple[int, int, int, int],
    style: Style,
    fonts: dict[str, str],
    rng: random.Random,
    *,
    variants: dict[int, str] | None = None,
    scale: float = 1.0,
    dx: int = 0,
    dy: int = 0,
    max_width: int | None = None,
    anchor: str = "center",
    overwrite: bool = False,
) -> tuple[int, int, int, int]:
    """Draw `text` in handwriting inside `box`; returns the ink bounds. Pencil grain, smudge, pressure."""
    x0, y0, x1, y1 = box
    avail = (max_width if max_width is not None else (x1 - x0)) - 28
    size = style.size * scale * (0.9 if len(text) <= 3 else 0.78)
    for _ in range(8):
        masks = [
            _glyph_mask(
                c, style, fonts, size * rng.uniform(0.87, 1.13), rng, (variants or {}).get(i)
            )
            if c != " "
            else Image.new("L", (int(size * 0.55), 8), 0)
            for i, c in enumerate(text)
        ]
        adv = [
            m.size[0] * (1.0 if text[i] == " " else 0.78) * style.spacing
            for i, m in enumerate(masks)
        ]
        total = sum(adv) + masks[-1].size[0] * 0.25 if masks else 0
        if total <= avail or not masks:
            break
        size *= avail / total * 0.97
    cx = (x0 + x1) // 2 + dx if anchor == "center" else x0 + 14 + dx
    cy = (y0 + y1) // 2 + dy
    start = cx - total / 2 if anchor == "center" else cx
    pad = 40
    rx0, ry0, rx1, ry1 = (
        int(x0 - pad + dx),
        int(y0 - pad + dy),
        int(x1 + pad + dx),
        int(y1 + pad + dy),
    )
    rx0, ry0, rx1, ry1 = max(0, rx0), max(0, ry0), min(W, rx1), min(H, ry1)
    alpha = np.zeros((ry1 - ry0, rx1 - rx0), dtype=np.float32)
    x = start
    bounds = [10**6, 10**6, 0, 0]
    for m, a in zip(masks, adv, strict=True):
        gx = int(x - 0 - rx0)
        gy = int(cy - m.size[1] / 2 + rng.uniform(-style.baseline, style.baseline) - ry0)
        arr = np.asarray(m, dtype=np.float32) / 255.0
        ax0, ay0 = max(0, gx), max(0, gy)
        ax1, ay1 = min(alpha.shape[1], gx + arr.shape[1]), min(alpha.shape[0], gy + arr.shape[0])
        if ax1 > ax0 and ay1 > ay0:
            sub = arr[ay0 - gy : ay1 - gy, ax0 - gx : ax1 - gx]
            alpha[ay0:ay1, ax0:ax1] = np.maximum(alpha[ay0:ay1, ax0:ax1], sub)
            bounds = [
                min(bounds[0], ax0 + rx0),
                min(bounds[1], ay0 + ry0),
                max(bounds[2], ax1 + rx0),
                max(bounds[3], ay1 + ry0),
            ]
        x += a
    if overwrite and masks:  # a second digit written over the last one
        m2 = _glyph_mask(rng.choice("0123456789"), style, fonts, size, rng, None)
        arr = np.asarray(m2, dtype=np.float32) / 255.0
        gx = int(x - adv[-1] - rx0 + 6)
        gy = int(cy - m2.size[1] / 2 - ry0)
        ax0, ay0 = max(0, gx), max(0, gy)
        ax1, ay1 = min(alpha.shape[1], gx + arr.shape[1]), min(alpha.shape[0], gy + arr.shape[0])
        sub = arr[ay0 - gy : ay1 - gy, ax0 - gx : ax1 - gx]
        alpha[ay0:ay1, ax0:ax1] = np.maximum(alpha[ay0:ay1, ax0:ax1], sub * 0.9)
    _composite_ink(sheet, alpha, (rx0, ry0), style, rng)
    return (bounds[0], bounds[1], bounds[2], bounds[3])


def _composite_ink(
    sheet: Image.Image, alpha: np.ndarray, origin: tuple[int, int], style: Style, rng: random.Random
) -> None:
    grain = gaussian_filter(
        np.random.default_rng(rng.randrange(10**9)).random(alpha.shape).astype(np.float32), 0.9
    )
    grain = (grain - grain.min()) / (np.ptp(grain) + 1e-6)
    a = gaussian_filter(alpha, 0.6) * style.pressure * (0.55 + 0.45 * grain)
    if style.smudge > 0:  # a left-hander's hand drags the graphite to the right
        smear = gaussian_filter(alpha, (2.0, 9.0))
        smear = np.roll(smear, 10, axis=1) * 0.35 * style.smudge
        a = np.clip(a + smear * (0.4 + 0.6 * grain), 0, 1)
    a = np.clip(a, 0, 1)
    ox, oy = origin
    region = np.asarray(sheet.crop((ox, oy, ox + a.shape[1], oy + a.shape[0])), dtype=np.float32)
    ink = np.array([style.grey, style.grey, style.grey + 6], dtype=np.float32)
    region = region * (1 - a[..., None]) + ink * a[..., None]
    sheet.paste(Image.fromarray(region.clip(0, 255).astype(np.uint8)), (ox, oy))


def strike(
    sheet: Image.Image,
    bounds: tuple[int, int, int, int],
    style: Style,
    rng: random.Random,
    scribble: bool,
) -> None:
    x0, y0, x1, y1 = bounds
    alpha = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(alpha)
    cy = (y0 + y1) // 2
    if scribble:
        pts = []
        n = 9
        for i in range(n):
            pts.append(
                (
                    x0 - 8 + (x1 - x0 + 16) * i / (n - 1),
                    cy + (-1) ** i * (y1 - y0) * 0.35 + rng.uniform(-6, 6),
                )
            )
        d.line(pts, fill=255, width=5, joint="curve")
    else:
        d.line(
            [(x0 - 10, cy + rng.uniform(-8, 8)), (x1 + 10, cy + rng.uniform(-8, 8))],
            fill=255,
            width=5,
        )
    arr = np.asarray(alpha, dtype=np.float32) / 255.0
    _composite_ink(sheet, arr, (0, 0), style, rng)


def small_marks(
    sheet: Image.Image,
    boxes: dict[Any, tuple[int, int, int, int]],
    style: Style,
    fonts: dict[str, str],
    rng: random.Random,
    form: str,
) -> None:
    """Carry and borrow marks on the sums and a bit of working in the margin (H18)."""
    st = Style(
        **{**style.__dict__, "size": 50, "pressure": min(1.0, style.pressure * 0.95), "rot": 5}
    )
    for item in (3, 4, 5):  # a carried 1 above the tens digit of the top number
        x0, y0, x1, y1 = boxes[item]
        right, ytop = x1 - 10, y0 - 100
        draw_written(
            sheet, "1", (right - 70, ytop - 70, right - 14, ytop - 24), st, fonts, rng, max_width=90
        )
    for item in (
        7,
        8,
        9,
        10,
    ):  # borrow: the tens digit struck out, one less written above, a small 1 by the units
        x0, y0, x1, y1 = boxes[item]
        right, ytop = x1 - 10, y0 - 100
        tens = OPERANDS[form][item][0] // 10
        bnd = (right - 58, ytop - 22, right - 30, ytop + 22)
        strike(sheet, bnd, st, rng, False)
        draw_written(
            sheet,
            str(tens - 1),
            (right - 70, ytop - 74, right - 14, ytop - 28),
            st,
            fonts,
            rng,
            max_width=90,
        )
        draw_written(
            sheet, "1", (right - 36, ytop - 56, right + 6, ytop - 14), st, fonts, rng, max_width=70
        )
    for k, line in enumerate(("8 + 7 = 15", "70 - 30 = 40", "4 tens")):
        draw_written(
            sheet,
            line,
            (820, 1590 + k * 56, 1210, 1646 + k * 56),
            st,
            fonts,
            rng,
            anchor="left",
            max_width=380,
        )


# --------------------------------------------------------------------------- the photo ----


def _persp_coeffs(dst: list[tuple[float, float]], src: list[tuple[float, float]]) -> list[float]:
    rows, rhs = [], []
    for (x, y), (u, v) in zip(dst, src, strict=True):
        rows.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        rows.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        rhs.extend([u, v])
    return list(np.linalg.solve(np.array(rows, dtype=np.float64), np.array(rhs, dtype=np.float64)))


def _noise_field(
    rng: np.random.Generator, shape: tuple[int, int], grid: int, amp: float
) -> np.ndarray:
    small = rng.standard_normal((grid, max(2, int(grid * shape[1] / shape[0]))))
    big = np.asarray(
        Image.fromarray(small.astype(np.float32)).resize((shape[1], shape[0]), Image.BICUBIC),
        dtype=np.float32,
    )
    return big * amp


def background(rng: np.random.Generator, size: tuple[int, int], kind: str) -> np.ndarray:
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    if kind == "desk":
        base = np.array([150, 108, 70], dtype=np.float32) * rng.uniform(0.8, 1.15)
        grain = (
            np.sin(yy * rng.uniform(0.05, 0.09) + _noise_field(rng, (h, w), 6, 6.0)) * 0.08
            + gaussian_filter(rng.standard_normal((h, w)).astype(np.float32), 1.5) * 0.04
        )
        img = base[None, None, :] * (1 + grain[..., None])
    elif kind == "floor":
        base = np.array([172, 168, 160], dtype=np.float32) * rng.uniform(0.85, 1.1)
        tiles = ((np.floor(xx / 380) + np.floor(yy / 380)) % 2) * 0.05
        lines = ((xx % 380 < 4) | (yy % 380 < 4)).astype(np.float32) * -0.18
        img = base[None, None, :] * (
            1
            + tiles[..., None]
            + lines[..., None]
            + gaussian_filter(rng.standard_normal((h, w)).astype(np.float32), 2.0)[..., None] * 0.05
        )
    else:  # table
        base = np.array([196, 190, 178], dtype=np.float32) * rng.uniform(0.85, 1.05)
        img = base[None, None, :] * (1 + _noise_field(rng, (h, w), 5, 0.03)[..., None])
    return img


CLEAN = {
    "tilt": 2.0,
    "persp": 0.012,
    "light": "mild",
    "blur": 0.5,
    "noise": 2.5,
    "crumple": False,
    "finger": False,
    "crop": False,
    "mp": (1.6, 2.0),
    "q": (55, 60),
    "fill": (0.74, 0.86),
    "rot180": False,
    "faint": False,
    "label": ["clean"],
}


def pick_conditions(rng: random.Random, kind: str) -> dict[str, Any]:
    c = dict(CLEAN)
    if kind == "clean":
        c["tilt"] = rng.uniform(0.5, 3.0)
        c["light"] = rng.choice(["mild", "mild", "bright"])
        c["label"] = ["clean"]
    elif kind == "fair":
        c.update(
            tilt=rng.uniform(3, 8),
            persp=rng.uniform(0.02, 0.05),
            blur=rng.uniform(0.6, 1.3),
            noise=rng.uniform(3, 5),
            mp=(1.2, 1.7),
            q=(40, 55),
            fill=(0.66, 0.82),
        )
        c["light"] = rng.choice(["shadow", "warm", "cool", "mild"])
        c["label"] = [f"tilt_{int(c['tilt'])}deg", f"{c['light']}_light", "slight_blur"]
    else:  # bad
        c.update(
            tilt=rng.uniform(8, 16),
            persp=rng.uniform(0.04, 0.08),
            blur=rng.uniform(1.4, 2.4),
            noise=rng.uniform(5, 8),
            crumple=rng.random() < 0.7,
            finger=rng.random() < 0.7,
            crop=rng.random() < 0.4,
            mp=(1.0, 1.25),
            q=(25, 38),
            fill=(0.62, 0.78),
        )
        c["light"] = rng.choice(["dim", "shadow", "dim"])
        c["label"] = (
            ["bad_capture", f"tilt_{int(c['tilt'])}deg", f"{c['light']}_light", "low_resolution"]
            + (["crumpled"] if c["crumple"] else [])
            + (["finger_over_corner"] if c["finger"] else [])
            + (["cropped_corner"] if c["crop"] else [])
        )
    return c


def capture(
    sheet: Image.Image, cond: dict[str, Any], rng: random.Random, bg_kind: str
) -> tuple[bytes, tuple[int, int]]:
    nrng = np.random.default_rng(rng.randrange(10**9))
    if cond["rot180"]:
        sheet = sheet.rotate(180)
    cw, ch = 1800, 2400
    frac = rng.uniform(*cond["fill"])
    sw = math.sqrt(frac * cw * ch / 1.414)
    sh = sw * 1.414
    cx = cw / 2 + rng.uniform(-0.03, 0.03) * cw - (0.05 * cw if cond["crop"] else 0)
    cy = ch / 2 + rng.uniform(-0.03, 0.03) * ch - (0.04 * ch if cond["crop"] else 0)
    ang = math.radians(cond["tilt"] * rng.choice([-1, 1]))
    quad = []
    for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        px, py = sx * sw / 2, sy * sh / 2
        rx, ry = px * math.cos(ang) - py * math.sin(ang), px * math.sin(ang) + py * math.cos(ang)
        quad.append(
            (
                cx + rx + rng.uniform(-1, 1) * cond["persp"] * sw,
                cy + ry + rng.uniform(-1, 1) * cond["persp"] * sw,
            )
        )
    src = [(0.0, 0.0), (float(W), 0.0), (float(W), float(H)), (0.0, float(H))]
    coeffs = _persp_coeffs(quad, src)
    rgba = sheet.convert("RGBA")
    rgba.putalpha(Image.new("L", sheet.size, 255))
    warped = rgba.transform((cw, ch), Image.PERSPECTIVE, coeffs, resample=Image.BICUBIC)
    arr = np.asarray(warped, dtype=np.float32)
    if cond["crumple"]:
        gy, gx = np.mgrid[0:ch, 0:cw].astype(np.float32)
        dx, dy = _noise_field(nrng, (ch, cw), 9, 9.0), _noise_field(nrng, (ch, cw), 9, 9.0)
        shade = np.gradient(dx, axis=1) * 6 + np.gradient(dy, axis=0) * 6
        for c in range(4):
            arr[..., c] = map_coordinates(arr[..., c], [gy + dy, gx + dx], order=1, mode="nearest")
        arr[..., :3] *= (1 + np.clip(shade, -0.25, 0.25))[..., None]
    mask = arr[..., 3:4] / 255.0
    bg = background(nrng, (cw, ch), bg_kind)
    shadow = gaussian_filter(np.roll(np.roll(mask[..., 0], 14, axis=0), 10, axis=1), 14) * 0.45
    bg = bg * (1 - shadow[..., None])
    out = bg * (1 - mask) + arr[..., :3] * mask
    # lighting
    ys, xs = np.mgrid[0:ch, 0:cw].astype(np.float32)
    theta = rng.uniform(0, 2 * math.pi)
    grad = ((xs / cw - 0.5) * math.cos(theta) + (ys / ch - 0.5) * math.sin(theta)) * rng.uniform(
        0.08, 0.22
    )
    field = 1 + grad + _noise_field(nrng, (ch, cw), 4, 0.025)
    tint = np.ones(3, dtype=np.float32)
    light = cond["light"]
    if light == "bright":
        field *= 1.08
    elif light == "warm":
        tint = np.array([1.06, 0.96, 0.78], dtype=np.float32)
        r = np.sqrt(((xs - cw / 2) / cw) ** 2 + ((ys - ch / 2) / ch) ** 2)
        field *= 1.05 - 0.45 * r
    elif light == "cool":
        tint = np.array([0.9, 0.99, 1.08], dtype=np.float32)
    elif light in ("shadow", "dim"):
        band_c = rng.uniform(0.3, 0.7)
        phase = (xs / cw * 0.8 + ys / ch * 0.6) - band_c
        band = 1 - 0.36 * np.exp(-((phase / 0.16) ** 2))
        field *= band
        if light == "dim":
            field *= 0.62
            tint = np.array([0.98, 0.97, 1.0], dtype=np.float32)
    out = out * field[..., None] * tint[None, None, :]
    if cond["finger"]:
        fimg = Image.new("L", (cw, ch), 0)
        fd = ImageDraw.Draw(fimg)
        fx, fy = quad[2][0] - 70, quad[2][1] - 130  # bottom-right corner, over the empty margin
        fd.ellipse([fx - 90, fy - 20, fx + 160, fy + 330], fill=255)
        fd.ellipse([fx - 50, fy - 150, fx + 100, fy + 120], fill=255)
        fm = (
            np.asarray(fimg.filter(ImageFilter.GaussianBlur(8)), dtype=np.float32)[..., None]
            / 255.0
        )
        skin = (
            np.array([214, 160, 128], dtype=np.float32)
            * (1 + _noise_field(nrng, (ch, cw), 6, 0.05))[..., None]
        )
        out = out * (1 - fm) + skin * fm
    out = np.clip(out, 0, 255).astype(np.uint8)
    img = Image.fromarray(out)
    if cond["blur"] > 0:
        img = img.filter(ImageFilter.GaussianBlur(cond["blur"] * 1.5))
    mp = rng.uniform(*cond["mp"])
    sc = math.sqrt(mp * 1e6 / (cw * ch))
    img = img.resize((int(cw * sc), int(ch * sc)), Image.LANCZOS)
    n = np.asarray(img, dtype=np.float32)
    n = (
        n
        + nrng.standard_normal(n.shape).astype(np.float32) * cond["noise"]
        + nrng.standard_normal(n.shape[:2]).astype(np.float32)[..., None] * cond["noise"] * 0.6
    )
    img = Image.fromarray(np.clip(n, 0, 255).astype(np.uint8))
    q = rng.randint(*cond["q"])
    while True:
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=q)
        if len(buf.getvalue()) <= JPEG_LIMIT:
            break
        if q > 25:
            q = max(25, q - 5)
        else:
            img = img.resize((int(img.width * 0.92), int(img.height * 0.92)), Image.LANCZOS)
    return buf.getvalue(), img.size


def not_a_sheet(fonts: dict[str, str], rng: random.Random) -> Image.Image:
    """H25: a notebook page with different content (lines, a margin, handwriting, a drawing)."""
    page = Image.new("RGB", (W, H), (250, 249, 240))
    d = ImageDraw.Draw(page)
    for y in range(120, H - 60, 56):
        d.line((0, y, W, y), fill=(165, 190, 225), width=2)
    d.line((150, 0, 150, H), fill=(214, 120, 120), width=3)
    style = make_style(rng, fonts)
    st = Style(**{**style.__dict__, "size": 62, "pressure": 0.9})
    lines = [
        "Science: plants need",
        "water, light and air",
        "1. Roots take water",
        "2. Leaves make food",
        "Homework: draw a leaf",
    ]
    for i, t in enumerate(lines):
        draw_written(
            page, t, (180, 100 + i * 112, 1180, 160 + i * 112), st, fonts, rng, anchor="left"
        )
    d.ellipse([700, 900, 1000, 1150], outline=(60, 60, 70), width=4)
    d.line((850, 1150, 850, 1400), fill=(60, 60, 70), width=4)
    return page


# ---------------------------------------------------------------------------------- sets ----


@dataclass
class SheetSpec:
    set_name: str
    sheet_id: str
    hero_id: str | None
    form: str
    class_code: str
    roll_no: int | None
    texts: list[str]  # written text per item ("" = blank)
    crossed: dict[int, list[str]] = field(default_factory=dict)
    notes: dict[int, str] = field(default_factory=dict)
    ambiguous_items: dict[int, dict[int, str]] = field(
        default_factory=dict
    )  # item -> {glyph index: variant}
    flags: dict[str, Any] = field(default_factory=dict)
    covered: str = "Y"
    cond_kind: str = "clean"
    cond_override: dict[str, Any] = field(default_factory=dict)
    cond_notes: list[str] = field(default_factory=list)
    expected_errors: list[str] | None = None
    expected_stages: list[str] | None = (
        None  # most-likely stages (addendum v3.1 F); None = not asserted
    )
    is_sheet: bool = True
    header_name: str | None = None
    selected_form: str | None = None


def texts_for(form: str, ints: list[str]) -> list[str]:
    return ints


# Expected stages for the hero sheets (docs/build/synthetic-sheets-stage-addendum.md). "not attempted"
# means no stage and the not-attempted line; [] means no stage at all.
HERO_STAGES: dict[str, list[str]] = {
    "H02": ["Core"], "H03": ["Input (test)"], "H04": ["Core", "Input (test)"],
    "H05": ["Core"], "H06": ["Core"], "H07": ["Core"], "H08": ["Core"], "H09": [],
    "H10": ["Core"], "H11": ["Core"], "H12": [], "H13": ["not attempted"], "H14": [],
    "H15": ["Core"], "H20": ["Core"], "H26": ["Core"],
}  # fmt: skip

# Seven Form A rows that exercise the stage signatures (the same rows as the addendum's table).
STAGE_ROWS: list[tuple[str, str, list[str]]] = [
    ("S01", "346,728,85,74,82,35,110,26,121,54", ["Input (test)"]),
    ("S02", "346,728,9,18,36,35,38,26,43,54", ["Input (test)"]),
    ("S03", "346,728,130,92,118,35,38,26,43,54", ["Input (test)"]),
    ("S04", "346,728,58,47,28,35,83,62,43,54", ["Output"]),
    ("S05", "347,738,85,74,82,35,38,26,43,54", ["Input (test)"]),
    ("S06", "346,728,84,73,83,35,39,26,43,54", ["Core"]),
    ("S07", "364,782,58,47,28,35,42,34,57,66", ["Core", "Output"]),
]


def stage_specs() -> list[SheetSpec]:
    return [
        SheetSpec("STG", sid, sid, "A", "S0-3A", None, row.split(","), expected_stages=stages)
        for sid, row, stages in STAGE_ROWS
    ]


def hero_specs() -> list[SheetSpec]:
    A = lambda s: s.split(",")  # noqa: E731
    h: list[SheetSpec] = []

    def add(hid: str, form: str, written: str, **kw: Any) -> SheetSpec:
        spec = SheetSpec("COV", hid, hid, form, "S0-3A", None, A(written), **kw)
        h.append(spec)
        return spec

    ok = "346,728,85,74,82,35,38,26,43,54"
    add(
        "H01",
        "A",
        ok,
        expected_errors=[],
        cond_override={"light": "bright", "tilt": 1.0, "persp": 0.006},
        cond_notes=["clean", "top_down", "bright"],
    )
    add("H02", "A", "300406,700208,85,74,82,35,38,26,43,54", expected_errors=["PV-HEARD"])
    add(
        "H03",
        "A",
        "364,782,85,74,82,35,38,26,43,54",
        expected_errors=["PV-REVERSE"],
        cond_override={"blur": 1.6},
        cond_notes=["slight_blur"],
    )
    add(
        "H04",
        "A",
        "300604,700802,85,74,82,35,38,26,43,54",
        expected_errors=["PV-HEARD", "PV-REVERSE"],
        cond_override={"light": "shadow"},
        cond_notes=["soft_shadow"],
    )
    add(
        "H05",
        "A",
        "346,728,75,64,72,35,38,26,43,54",
        expected_errors=["ADD-NOCARRY"],
        cond_override={"tilt": 10.0},
        cond_notes=["tilted_10deg"],
    )
    add("H06", "A", "346,728,85,74,82,35,42,34,57,66", expected_errors=["SUB-SFL"])
    add(
        "H07",
        "A",
        "346,728,85,74,82,35,48,36,53,64",
        expected_errors=["SUB-NODEC"],
        cond_override={"light": "warm"},
        cond_notes=["warm_lamp_light"],
    )
    add("H08", "A", "346,728,85,74,82,35,42,34,43,54", expected_errors=["SUB-SFL"])
    add("H09", "A", "346,728,85,74,82,35,42,26,43,54", expected_errors=[])
    add(
        "H10",
        "A",
        "346,728,75,64,72,25,42,34,57,66",
        expected_errors=["ADD-NOCARRY", "SUB-SFL"],
        cond_override={"blur": 1.6},
        cond_notes=["slight_blur"],
    )
    add("H11", "A", "346,728,715,614,712,35,38,26,43,54", expected_errors=[], covered="Edge")
    add("H12", "A", "346,728,95,70,82,35,39,26,41,54", expected_errors=[])
    add("H13", "A", "346,728,85,74,82,35,38,,,", expected_errors=[])
    add(
        "H14",
        "A",
        "346,728,85,74,82,35,38,26,57,54",
        crossed={7: ["42"], 9: ["43"]},
        expected_errors=[],
        flags={"scribble": {9: True}},
    )
    add(
        "H15",
        "A",
        "३४६,७२८,८५,७४,८२,३५,४२,३४,५७,६६",
        expected_errors=["SUB-SFL"],
        flags={"deva": True},
    )
    s16 = add(
        "H16",
        "A",
        ok,
        expected_errors=[],
        covered="Edge",
        cond_override={"faint": True},
        cond_notes=["faint_pencil", "smudged"],
        flags={"faint": True, "smudge": True},
    )
    s16.ambiguous_items = {
        1: {1: "4_open"},
        2: {0: "7_bar"},
        3: {1: "5_as_3"},
        4: {0: "7_nobar"},
        6: {1: "5_as_3"},
        8: {1: "6_as_0"},
        10: {1: "4_open"},
    }
    s17 = add("H17", "A", ok, expected_errors=[], covered="N")
    s17.header_name = "Rohan"
    add(
        "H18",
        "A",
        ok,
        expected_errors=[],
        covered="Edge",
        flags={"marks": True},
        cond_notes=["carry_and_borrow_marks", "working_in_margin"],
    )
    s19 = add(
        "H19",
        "A",
        "346,728,85,74,82 72,35,38,26,43,54",
        expected_errors=[],
        covered="N",
        flags={"overwrite": {8: True}, "outside": {10: True}},
    )
    add(
        "H20",
        "A",
        "346,728,85,74,82,35,42,34,57,66",
        expected_errors=["SUB-SFL"],
        covered="Edge",
        cond_kind="bad",
        cond_override={
            "tilt": 15.0,
            "crumple": True,
            "finger": True,
            "light": "dim",
            "mp": (1.0, 1.05),
            "q": (28, 34),
            "blur": 1.8,
        },
        cond_notes=[
            "bad_capture",
            "crumpled",
            "finger_over_corner",
            "rotated_15deg",
            "dim",
            "downscaled_1MP",
        ],
    )
    add("H21", "B", "264,853,75,84,72,45,48,36,53,64", expected_errors=[])
    add("H22", "B", "264,853,75,84,72,45,52,36,53,64", expected_errors=[])
    s23 = add("H23", "B", "264,853,75,84,72,45,48,36,53,64", expected_errors=[], covered="N")
    s23.selected_form = "A"
    add("H24", "A", ",,,,,,,,,", expected_errors=[], covered="Edge")
    h.append(
        SheetSpec(
            "COV",
            "H25",
            "H25",
            "none",
            "",
            None,
            [],
            covered="N",
            expected_errors=None,
            is_sheet=False,
        )
    )
    add(
        "H26",
        "A",
        "346,728,85,74,82,35,48,36,53,64",
        expected_errors=["SUB-NODEC"],
        covered="Edge",
        cond_override={"rot180": True},
        cond_notes=["upside_down_180deg"],
    )
    del s19
    for spec in h:
        if spec.hero_id in HERO_STAGES:
            spec.expected_stages = HERO_STAGES[spec.hero_id]
    return h


@dataclass
class Profile:
    sfl: int = 0
    nodec: int = 0
    add: int = 0
    heard: bool = False
    reverse: bool = False
    both: bool = False
    anchor_wrong: bool = False
    one_hit: str | None = None
    noise: int = 0
    tag: str = ""


def answers_for(form: str, p: Profile, rng: random.Random) -> list[int | None]:
    v: list[int | None] = list(KEY[form])
    e = ERR[form]
    if p.both:
        v[0], v[1] = rng.choice(e["BOTH"][1]), rng.choice(e["BOTH"][2])
    elif p.heard:
        v[0], v[1] = rng.choice(e["PV-HEARD"][1]), rng.choice(e["PV-HEARD"][2])
    elif p.reverse:
        v[0], v[1] = rng.choice(e["PV-REVERSE"][1]), rng.choice(e["PV-REVERSE"][2])
    if p.add:
        for it in rng.sample([3, 4, 5], p.add):
            v[it - 1] = rng.choice(e["ADD-NOCARRY"][it])
    if p.sfl:
        for it in rng.sample([7, 8, 9, 10], p.sfl):
            v[it - 1] = rng.choice(e["SUB-SFL"][it])
    if p.nodec:
        for it in rng.sample([7, 8, 9, 10], p.nodec):
            v[it - 1] = rng.choice(e["SUB-NODEC"][it])
    if p.one_hit == "SUB-SFL":
        it = rng.choice([7, 8, 9, 10])
        v[it - 1] = rng.choice(e["SUB-SFL"][it])  # noqa: E702
    elif p.one_hit == "ADD-NOCARRY":
        it = rng.choice([3, 4, 5])
        v[it - 1] = rng.choice(e["ADD-NOCARRY"][it])  # noqa: E702
    elif p.one_hit == "PV-HEARD":
        v[0] = rng.choice(e["PV-HEARD"][1])
    if p.anchor_wrong:
        v[5] = KEY[form][5] - 10
    if p.noise:
        free = [i for i in (3, 4, 5, 7, 8, 9, 10) if v[i - 1] == KEY[form][i - 1]]
        for it in rng.sample(free, min(p.noise, len(free))):
            if rng.random() < 0.3:
                v[it - 1] = None
            else:
                bad = {x for lst in (e[c].get(it, []) for c in e) for x in lst} | {
                    KEY[form][it - 1]
                }
                while True:
                    cand = KEY[form][it - 1] + rng.choice([-11, -9, -2, -1, 1, 2, 9, 11, 20, -20])
                    if cand > 0 and cand not in bad:
                        v[it - 1] = cand
                        break
    return v


def class_profiles(kind: str, rng: random.Random) -> list[Profile]:
    if kind == "S1":
        ps = [Profile(tag="correct") for _ in range(3)]
        ps += [Profile(one_hit=c, tag="one_hit") for c in ("SUB-SFL", "ADD-NOCARRY", "PV-HEARD")]
        ps += [
            Profile(sfl=rng.choice([2, 3, 4]), add=rng.choice([2, 3]), tag="sfl+add")
            for _ in range(3)
        ]
        ps += [
            Profile(sfl=rng.choice([2, 3]), heard=True, tag="sfl+heard"),
            Profile(sfl=rng.choice([2, 3]), reverse=True, tag="sfl+reverse"),
        ]
        ps += [Profile(sfl=rng.choice([2, 3, 4]), tag="sfl") for _ in range(6)]
        ps += [Profile(nodec=rng.choice([2, 3]), add=2, tag="nodec+add")] + [
            Profile(nodec=rng.choice([2, 3, 4]), tag="nodec") for _ in range(2)
        ]
        ps += [Profile(heard=True, tag="heard") for _ in range(4)] + [
            Profile(reverse=True, tag="reverse"),
            Profile(both=True, tag="both"),
        ]
        ps += [Profile(noise=rng.choice([1, 2]), tag="noise") for _ in range(2)]
        # two children also have a wrong anchor
        ps[[i for i, p in enumerate(ps) if p.tag == "sfl+add"][0]].anchor_wrong = True
        ps[[i for i, p in enumerate(ps) if p.tag == "heard"][0]].anchor_wrong = True
    else:  # S2
        ps = [Profile(tag="correct") for _ in range(4)]
        ps += [Profile(one_hit=c, tag="one_hit") for c in ("SUB-SFL", "PV-HEARD")]
        ps += [Profile(sfl=rng.choice([2, 3]), add=2, tag="sfl+add") for _ in range(2)]
        ps += [Profile(sfl=rng.choice([2, 3, 4]), tag="sfl") for _ in range(7)]
        ps += [Profile(heard=True, tag="heard") for _ in range(3)] + [
            Profile(nodec=2, tag="nodec") for _ in range(2)
        ]
        ps += [Profile(noise=rng.choice([1, 2]), tag="noise") for _ in range(26 - len(ps))]
    assert len(ps) == (28 if kind == "S1" else 26), len(ps)
    return ps


def post_profiles(kind: str, pre: list[Profile], rng: random.Random) -> list[Profile]:
    post = [Profile(**p.__dict__) for p in pre]
    sfl_idx = [i for i, p in enumerate(post) if p.sfl]
    fixed_n, still_n = (8, 3) if kind == "S1" else (2, len(sfl_idx) - 2)
    rng.shuffle(sfl_idx)
    for i in sfl_idx[:fixed_n]:
        post[i].sfl = 0
    for i in sfl_idx[fixed_n:]:
        post[i].sfl = rng.choice([2, 3])
    clean = [i for i, p in enumerate(post) if p.tag == "correct"]
    new = clean[0]
    post[new].sfl = 2  # a child who did not have it before now does
    for p in post:  # anything else that was only a one-off stays as it was; noise is re-drawn
        p.anchor_wrong = False
        p.noise = p.noise
    if kind == "S1":  # other errors drift by at most one child
        add_idx = [i for i, p in enumerate(post) if p.add and not p.sfl]
        post[
            add_idx[0] if add_idx else [i for i, p in enumerate(post) if p.add][0]
        ].add = 0  # ADD-NOCARRY -1
        one = [i for i, p in enumerate(post) if p.one_hit == "SUB-SFL"][0]
        post[one].one_hit = None
        post[one].nodec = 2  # SUB-NODEC +1
        post[one].sfl = 0
    return post


def build_class(
    set_name: str, kind: str, class_code: str, n: int, rng: random.Random
) -> list[SheetSpec]:
    pre = class_profiles(kind, rng)
    order = list(range(n))
    rng.shuffle(order)  # who gets which roll number
    post = post_profiles(kind, pre, rng)
    specs: list[SheetSpec] = []
    for phase, form, profs in (("PRE", "A", pre), ("POST", "B", post)):
        for child, roll in enumerate(order, start=1):
            vals = answers_for(form, profs[child - 1], rng)
            roll_no = roll + 1
            specs.append(
                SheetSpec(f"{set_name}-{phase}", f"R{roll_no:02d}", None, form, class_code, roll_no,
                          ["" if v is None else str(v) for v in vals], cond_kind=rng.choices(["clean", "fair", "bad"], [0.55, 0.35, 0.10])[0],
                          expected_errors=None, flags={"child": child, "profile": profs[child - 1].tag}))  # fmt: skip
    return specs


# ------------------------------------------------------------------------------- render ----


def render_spec(spec: SheetSpec, fonts: dict[str, str], seed: int, out: Path) -> dict[str, Any]:
    rng = random.Random(f"{seed}:{spec.set_name}:{spec.sheet_id}")
    fname = f"SIM_{spec.set_name}_{spec.sheet_id}.jpg"
    bg_kind = rng.choice(["desk", "floor", "table"])
    cond = pick_conditions(rng, spec.cond_kind)
    cond.update(spec.cond_override)
    notes = list(spec.cond_notes) if spec.cond_notes else list(cond["label"])
    if not spec.is_sheet:
        page = not_a_sheet(fonts, rng)
        data, size = capture(page, cond, rng, "desk")
        (out / fname).write_bytes(data)
        return {
            "file": fname,
            "sheet_id": spec.sheet_id,
            "synthetic": True,
            "set": spec.set_name,
            "form": "none",
            "class_code": None,
            "roll_no": None,
            "is_answer_sheet": False,
            "answers": [],
            "errors_present_by_scoring_rule": [],
            "hero_id": spec.hero_id,
            "capture_conditions": notes + ["not_an_answer_sheet", "notebook_page_on_desk"],
            "covered": spec.covered,
            "truth_source": "rendered_by_code",
            "image_size": list(size),
            "bytes": len(data),
        }
    sheet, boxes, _ = make_template(spec.form, fonts)
    style = make_style(
        rng,
        fonts,
        faint=bool(spec.flags.get("faint")),
        smudge=True if spec.flags.get("smudge") else None,
    )
    teacher = make_style(random.Random(f"teacher:{spec.class_code}"), fonts)
    teacher.size, teacher.rot, teacher.pressure, teacher.smudge = 80, 3, 0.85, 0.0
    if spec.class_code:
        draw_written(sheet, spec.class_code, boxes["class"], teacher, fonts, rng)
    if spec.roll_no is not None or spec.hero_id:
        roll = spec.roll_no if spec.roll_no is not None else rng.randint(1, 28)
        spec.roll_no = roll
        draw_written(sheet, str(roll), boxes["roll"], teacher, fonts, rng)
    if spec.header_name:
        draw_written(
            sheet, spec.header_name, (60, 4, 420, 70), style, fonts, rng, anchor="left", scale=0.5
        )
    if spec.flags.get("marks"):
        small_marks(sheet, boxes, style, fonts, rng, spec.form)
    answers = []
    values: list[int | None] = []
    for item in range(1, 11):
        text = spec.texts[item - 1]
        box = boxes[item]
        crossed = spec.crossed.get(item, [])
        dxo = 0
        if crossed:
            half = (box[2] - box[0]) // 2
            b1 = (box[0], box[1], box[0] + half, box[3])
            b2 = (box[0] + half - 10, box[1], box[2], box[3])
            for c in crossed:
                bnd = draw_written(sheet, c, b1, style, fonts, rng, scale=0.7)
                strike(sheet, bnd, style, rng, bool(spec.flags.get("scribble", {}).get(item)))
            draw_written(sheet, text, b2, style, fonts, rng, scale=0.9)
        elif text:
            if spec.flags.get("outside", {}).get(item):
                dxo = (box[2] - box[0]) // 2 - 10
            variants = spec.ambiguous_items.get(item)
            draw_written(
                sheet,
                text,
                box,
                style,
                fonts,
                rng,
                variants=variants,
                dx=dxo,
                overwrite=bool(spec.flags.get("overwrite", {}).get(item)),
            )
        value = None if (" " in text.strip()) else to_value(text)
        label = label_of(spec.form, item, value)
        note = None
        if spec.ambiguous_items.get(item):
            label, note = "ambiguous", "glyphs deliberately ambiguous (value = the intended digits)"
        if " " in text.strip():
            label, note = (
                "ambiguous",
                "two different answers written in one box, neither crossed out",
            )
        if spec.flags.get("overwrite", {}).get(item):
            label, note = "ambiguous", "last digit written over another digit"
        if spec.flags.get("outside", {}).get(item):
            note = "answer written half outside the box"
        values.append(value if label not in ("ambiguous",) or value is not None else None)
        rec: dict[str, Any] = {
            "item": item,
            "written": text,
            "value": value,
            "crossed_out_first_attempts": crossed,
            "label": label,
        }
        if note:
            rec["note"] = note
        answers.append(rec)
    # the scoring rule runs on intended values; two answers in one box has no single value
    score_vals = [a["value"] for a in answers]
    sc = score(spec.form, score_vals)
    if "82 72" in " ".join(spec.texts):
        pass
    data, size = capture(sheet, cond, rng, bg_kind)
    (out / fname).write_bytes(data)
    conds = notes if notes else cond["label"]
    rec = {
        "file": fname,
        "sheet_id": spec.sheet_id,
        "synthetic": True,
        "set": spec.set_name,
        "form": spec.form,
        "class_code": spec.class_code,
        "roll_no": spec.roll_no,
        "answers": answers,
        "errors_present_by_scoring_rule": sc["present"],
        "hero_id": spec.hero_id,
        "capture_conditions": conds,
        "covered": spec.covered,
        "truth_source": "rendered_by_code",
        "is_answer_sheet": True,
        "anchor_wrong": sc["anchor_wrong"],
        "handwriting_style": style.ident,
        "background": bg_kind,
        "image_size": list(size),
        "bytes": len(data),
        "expected_stages": spec.expected_stages,
    }
    if spec.header_name:
        rec["header_name_written"] = f"{spec.header_name} (made up)"
    if spec.selected_form:
        rec["selected_form_in_app"] = spec.selected_form
    if spec.flags.get("profile"):
        rec["profile"] = spec.flags["profile"]
    return rec


# ---------------------------------------------------------------------------- self-check ----


def stage_check(manifest: list[dict[str, Any]], chk: Any) -> None:
    """The engine's stage for each sheet that has an expected stage (addendum v3.1 F)."""
    from engine.forms import PILOT_FORMS
    from engine.stages import classify_child

    for r in manifest:
        want = r.get("expected_stages")
        if want is None or not r.get("is_answer_sheet", True):
            continue
        readings = ["blank" if a["value"] is None else a["value"] for a in r["answers"]]
        res = classify_child(PILOT_FORMS[r["form"]], readings)
        got = (
            ["not attempted"]
            if res.not_attempted and not res.stages
            else sorted(s.value for s in res.stages)
        )
        chk(f"{r['sheet_id']} stages", got, sorted(want))


def mcnemar_exact(fixed: int, new: int) -> float:
    n = fixed + new
    k = min(fixed, new)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2**n * 2
    return min(1.0, p)


def prevalence(records: list[dict[str, Any]]) -> dict[str, int]:
    c: Counter[str] = Counter()
    for r in records:
        vals = [a["value"] for a in r["answers"]]
        sc = score(r["form"], vals)
        for p in sc["present"]:
            c[p] += 1
        c["anchor_wrong"] += int(sc["anchor_wrong"])
        c["one_hit_only"] += int(sc["one_hit_only"])
        c["all_correct"] += int(sc["all_correct"])
        c["PV-BOTH"] += int("PV-HEARD" in sc["present"] and "PV-REVERSE" in sc["present"])
    return dict(c)


def self_check(manifest: list[dict[str, Any]]) -> bool:
    ok = True

    def chk(name: str, got: Any, want: Any) -> None:
        nonlocal ok
        good = got == want
        ok &= good
        print(f"  {'PASS' if good else 'FAIL'}  {name}: got {got}, target {want}")

    print(
        "\nSelf-check: scoring rule re-implemented, prevalence recomputed from the generated truth"
    )
    heroes = {r["hero_id"]: r for r in manifest if r["set"] == "COV"}
    exp = {s.hero_id: s.expected_errors for s in hero_specs() if s.expected_errors is not None}
    for hid, want in exp.items():
        got = sorted(heroes[hid]["errors_present_by_scoring_rule"])
        chk(f"{hid} errors by rule", got, sorted(want))
    stage_check(manifest, chk)
    h10 = heroes["H10"]
    chk("H10 wrong anchor", h10["anchor_wrong"], True)
    for name, targets in (
        (
            "S1-3A-PRE",
            {
                "SUB-SFL": 11,
                "SUB-NODEC": 3,
                "PV-HEARD": 6,
                "PV-REVERSE": 3,
                "PV-BOTH": 1,
                "ADD-NOCARRY": 4,
                "anchor_wrong": 2,
                "one_hit_only": 3,
                "all_correct": 3,
            },
        ),
    ):
        recs = [r for r in manifest if r["set"] == name]
        pv = prevalence(recs)
        print(f"\n{name}: {len(recs)} sheets")
        chk("children", len(recs), 28)
        for k, t in targets.items():
            chk(k, pv.get(k, 0), t)
    pre = {r["roll_no"]: r for r in manifest if r["set"] == "S1-3A-PRE"}
    post = {r["roll_no"]: r for r in manifest if r["set"] == "S1-3A-POST"}
    chk("S1 post children", len(post), 28)
    shows = lambda r, e: e in score(r["form"], [a["value"] for a in r["answers"]])["present"]  # noqa: E731
    sfl_pre = [k for k, r in pre.items() if shows(r, "SUB-SFL")]
    fixed = sum(1 for k in sfl_pre if not shows(post[k], "SUB-SFL"))
    still = sum(1 for k in sfl_pre if shows(post[k], "SUB-SFL"))
    new = sum(1 for k, r in post.items() if shows(r, "SUB-SFL") and k not in sfl_pre)
    chk("S1 SUB-SFL fixed", fixed, 8)
    chk("S1 SUB-SFL still", still, 3)
    chk("S1 SUB-SFL new", new, 1)
    p_pre, p_post = prevalence(list(pre.values())), prevalence(list(post.values()))
    print("\nS1 other errors, pre -> post (each may drift by at most 1 child):")
    for e in ("SUB-NODEC", "PV-HEARD", "PV-REVERSE", "ADD-NOCARRY"):
        d = p_post.get(e, 0) - p_pre.get(e, 0)
        chk(f"{e} {p_pre.get(e, 0)} -> {p_post.get(e, 0)} (|drift| <= 1)", abs(d) <= 1, True)
    p = mcnemar_exact(fixed, new)
    print(
        f"\nExact McNemar for S1 SUB-SFL (Fixed {fixed}, New {new}, two-sided exact binomial): p = {p:.6f}"
    )
    chk("McNemar p (20/512)", round(p, 7), round(20 / 512, 7))
    s2pre = [r for r in manifest if r["set"] == "S2-3B-PRE"]
    s2post = [r for r in manifest if r["set"] == "S2-3B-POST"]
    a = {r["roll_no"]: r for r in s2pre}
    b = {r["roll_no"]: r for r in s2post}
    spre = [k for k, r in a.items() if shows(r, "SUB-SFL")]
    chk("S2 SUB-SFL pre", len(spre), 9)
    chk("S2 SUB-SFL post", sum(1 for r in b.values() if shows(r, "SUB-SFL")), 8)
    chk("S2 fixed", sum(1 for k in spre if not shows(b[k], "SUB-SFL")), 2)
    chk("S2 new", sum(1 for k, r in b.items() if shows(r, "SUB-SFL") and k not in spre), 1)
    try:  # a third, independent implementation: the project's own engine
        from engine.diagnosis import diagnose_child
        from engine.forms import PILOT_FORMS

        compared = bad = 0
        for r in manifest:
            if not r["is_answer_sheet"] or any(
                a["value"] is None and a["label"] == "ambiguous" for a in r["answers"]
            ):
                continue
            vals = [a["value"] if a["value"] is not None else "blank" for a in r["answers"]]
            shown = sorted(c.value for c in diagnose_child(PILOT_FORMS[r["form"]], vals).shows)
            compared += 1
            bad += shown != sorted(r["errors_present_by_scoring_rule"])
        chk(
            f"engine.diagnosis agrees with the scoring rule on {compared} sheets (mismatches)",
            bad,
            0,
        )
    except ImportError:
        print("  (engine not importable: cross-check skipped)")
    print("\nPrevalence table (children showing each error by the scoring rule):")
    print(
        f"{'set':<12}"
        + "".join(
            f"{c:>13}"
            for c in (
                "SUB-SFL",
                "SUB-NODEC",
                "PV-HEARD",
                "PV-REVERSE",
                "ADD-NOCARRY",
                "anchor_wrong",
                "one_hit_only",
                "all_correct",
            )
        )
    )
    for nm in ("S1-3A-PRE", "S1-3A-POST", "S2-3B-PRE", "S2-3B-POST"):
        pv = prevalence([r for r in manifest if r["set"] == nm])
        print(
            f"{nm:<12}"
            + "".join(
                f"{pv.get(c, 0):>13}"
                for c in (
                    "SUB-SFL",
                    "SUB-NODEC",
                    "PV-HEARD",
                    "PV-REVERSE",
                    "ADD-NOCARRY",
                    "anchor_wrong",
                    "one_hit_only",
                    "all_correct",
                )
            )
        )
    return ok


def write_outputs(
    out: Path, manifest: list[dict[str, Any]], seed: int, fonts: dict[str, str]
) -> None:
    (out / "manifest.json").write_text(
        json.dumps(
            {
                "synthetic": True,
                "seed": seed,
                "note": "SYNTHETIC test set. Not pilot data. Not real children's work.",
                "sheets": manifest,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    with (out / "manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "file",
                "sheet_id",
                "set",
                "hero_id",
                "synthetic",
                "form",
                "class_code",
                "roll_no",
                *[f"a{i}" for i in range(1, 11)],
                "errors_present",
                "covered",
                "capture_conditions",
                "truth_source",
            ]
        )
        for r in manifest:
            ans = [a["written"] for a in r["answers"]] if r["answers"] else [""] * 10
            w.writerow(
                [
                    r["file"],
                    r["sheet_id"],
                    r["set"],
                    r["hero_id"] or "",
                    "true",
                    r["form"],
                    r["class_code"] or "",
                    r["roll_no"] or "",
                    *ans,
                    ";".join(r["errors_present_by_scoring_rule"]),
                    r["covered"],
                    ";".join(r["capture_conditions"]),
                    r["truth_source"],
                ]
            )
    used = sorted({Path(p).name for p in fonts.values()})
    (out / "README.md").write_text(
        "# SIM handwritten answer sheets (SYNTHETIC backup set)\n\n"
        "**This is synthetic data.** It is not pilot data and not any real child's work. Every file name starts with `SIM_` and `manifest.json` says `synthetic: true`. "
        "The handwriting is open-licence handwriting fonts (and a stroke skeleton for deliberately ambiguous glyphs) with random rotation, size, baseline, stroke and pencil-grain variation; "
        "the photo effects (perspective, lighting, blur, noise, crumple, finger, JPEG) are simulated. It does not stand in for real children's handwriting and says nothing about reader accuracy on real sheets.\n\n"
        "## What is here\n\n"
        "- `SIM_COV_H01.jpg` to `SIM_COV_H26.jpg`: 26 coverage sheets (set `COV`, class code S0-3A), one per row of the coverage table.\n"
        "- `SIM_STG_S01.jpg` to `SIM_STG_S07.jpg`: seven Form A sheets that exercise the stage signatures (set `STG`); `expected_stages` in the manifest is what the engine must report. Robustness only, never eval 9 accuracy.\n"
        "- `SIM_S1-3A-PRE_Rnn.jpg` and `SIM_S1-3A-POST_Rnn.jpg`: the demo class S1-3A, 28 children (roll 1 to 28), Form A pre-test then Form B post-test.\n"
        "- `SIM_S2-3B-PRE_Rnn.jpg` and `SIM_S2-3B-POST_Rnn.jpg`: the untrained comparison class S2-3B, 26 children.\n"
        "- `manifest.json` and `manifest.csv`: the truth, one record per image: what is written (Devanagari kept), its value, crossed-out first attempts, a label per answer, the errors by the scoring rule, the capture conditions, whether the current reader is expected to handle it (`covered`: Y, Edge, N) and `truth_source` (`rendered_by_code`: the truth is what the code drew; nothing was read back by a person).\n"
        "- `contact_sheet.png`: 12 thumbnails for a quick visual check.\n\n"
        "## Honest limits\n\n"
        "- Fonts differ in look from a child's pencil work; digits are cleaner than real ones. A few glyphs are drawn from a stroke skeleton on purpose (H16).\n"
        "- H16 cannot include a 1 that looks like a 7 because none of the Form A answers contains a 1.\n"
        "- A wrong answer on item 6 is recorded (`anchor_wrong`) but items 7 to 10 are still scored.\n"
        f"- Seed {seed}. Fonts used: {', '.join(used)} (open-licence Google Fonts and Windows system fonts).\n",
        encoding="utf-8",
    )


def contact_sheet(out: Path, manifest: list[dict[str, Any]]) -> None:
    pick = ["H01", "H04", "H07", "H14", "H15", "H16", "H19", "H20", "H24", "H25", "H26", "H18"]
    files = [next(r["file"] for r in manifest if r["hero_id"] == h) for h in pick]
    tw, th = 300, 420
    sheet = Image.new("RGB", (tw * 4, th * 3 + 30), (255, 255, 255))
    d = ImageDraw.Draw(sheet)
    for i, fn in enumerate(files):
        im = Image.open(out / fn).convert("RGB")
        im.thumbnail((tw - 8, th - 28))
        x, y = (i % 4) * tw + 4, (i // 4) * th + 26
        sheet.paste(im, (x, y))
        d.text((x, y - 18), f"{pick[i]}  {fn}", fill="black")
    d.text((4, 4), "SYNTHETIC test set (SIM_): contact sheet", fill="black")
    sheet.save(out / "contact_sheet.png")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "data" / "synthetic_sheets"))
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--quick", action="store_true", help="coverage set only")
    ap.add_argument(
        "--check-only",
        action="store_true",
        help="re-run the self-check on the existing manifest.json",
    )
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.check_only:
        return (
            0
            if self_check(json.loads((out / "manifest.json").read_text(encoding="utf-8"))["sheets"])
            else 1
        )
    fonts = ensure_fonts(out)
    print("fonts:", ", ".join(f"{k}={Path(v).name}" for k, v in fonts.items()))
    rng = random.Random(args.seed)
    specs = hero_specs() + stage_specs()
    if not args.quick:
        specs += build_class("S1-3A", "S1", "S1-3A", 28, rng)
        specs += build_class("S2-3B", "S2", "S2-3B", 26, rng)
    manifest = []
    for i, spec in enumerate(specs, 1):
        manifest.append(render_spec(spec, fonts, args.seed, out))
        if i % 10 == 0 or i == len(specs):
            print(f"rendered {i}/{len(specs)}")
    contact_sheet(out, manifest)
    write_outputs(out, manifest, args.seed, fonts)
    ok = self_check(manifest) if not args.quick else True
    big = [m["file"] for m in manifest if m["bytes"] > 400_000]
    print(
        f"\nlargest JPEG: {max(m['bytes'] for m in manifest):,} bytes; over 400 KB: {big or 'none'}"
    )
    zpath = out / "SIM_handwritten_sheets.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.iterdir()):
            if p.suffix.lower() in (".jpg", ".png", ".json", ".csv", ".md"):
                z.write(p, p.name)
    print(
        f"wrote {len(manifest)} images, manifest.json, manifest.csv, contact_sheet.png, README.md and {zpath.name} in {out}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
