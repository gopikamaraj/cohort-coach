"""Synthetic photos of the filled demo paper. SIMULATED: no real child wrote any of them.

Each sheet starts from the real printed paper (Paper Studio's PDF at 150 dpi), and the child's
answers are written in handwriting-style fonts into the answer boxes from the paper's layout map,
with the roll number in its box, small carry and borrow marks for some children, and the hard cases
(a smudge, a crossed-out answer, an empty box). The page is then "photographed": rotation,
perspective, light, blur, noise and a background (the capture code of
scripts/make_synthetic_sheets.py).
Every image carries a "Demo sheet" footer and a demo flag in its PNG metadata, and is named
{class code}-roll{NN}.png.
"""

from __future__ import annotations

import io
import json
import random
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from PIL.PngImagePlugin import PngInfo

from scripts import make_synthetic_sheets as mss
from services.demo.scenario import DemoChild, DemoClass
from services.papers import render
from services.papers.rules import RuleSet

FONTS_DIR = Path(__file__).with_name("fonts")
FOOTER_FONT = Path(render.FONT_DIR) / "NotoSans-Bold.ttf"
DPI = 150
PX = DPI / 25.4  # pixels per millimetre
OUT_WIDTH = 1100  # final image width: readable, and a sheet stays near 1 MB
DEMO_KEY = "cohort-coach-demo"
FOOTER = "Demo sheet"


def fonts() -> dict[str, str]:
    """The bundled handwriting fonts only, so a sheet looks the same on every machine."""
    return {p.stem: str(p) for p in FONTS_DIR.glob("*.ttf")}


def template(
    paper: dict[str, Any], rules: RuleSet, lang: str = "en"
) -> tuple[Image.Image, dict[str, Any]]:
    """The printed paper as a 150 dpi image (A4: 1240 x 1754), and its layout map."""
    import pypdfium2 as pdfium

    pdf, layout = render.render_paper(paper, rules, lang)
    page = pdfium.PdfDocument(pdf)[0]
    img = page.render(scale=DPI / 72).to_pil().convert("RGB").resize((mss.W, mss.H))
    return img, layout


def _px(box: dict[str, Any]) -> tuple[int, int, int, int]:
    return (
        round(box["x"] * PX),
        round(box["y"] * PX),
        round((box["x"] + box["w"]) * PX),
        round((box["y"] + box["h"]) * PX),
    )


def _small(style: mss.Style) -> mss.Style:
    return mss.Style(**{**style.__dict__, "size": 34, "rot": 4})


def _marks(
    sheet: Image.Image,
    layout: dict[str, Any],
    paper: dict[str, Any],
    style: mss.Style,
    fs: dict[str, str],
    rng: random.Random,
) -> None:
    """Small working: a carried 1 over the tens of an addition, the borrow over a subtraction."""
    boxes = {b["id"]: b for b in layout["boxes"]}
    st = _small(style)
    for it in paper["items"]:
        top = boxes.get(f"top-{it['n']}")
        if top is None:
            continue
        x0, y0, x1, _ = _px(top)
        tens_x = x1 - int(9.5 * PX)
        if it["operation"] == "add" and it["a"] % 10 + it["b"] % 10 >= 10:
            mss.draw_written(
                sheet, "1", (tens_x - 26, y0 - 30, tens_x + 26, y0 - 2), st, fs, rng, max_width=90
            )
        elif it["operation"] == "subtract" and it["a"] % 10 < it["b"] % 10:
            mss.draw_written(
                sheet,
                str(it["a"] // 10 - 1),
                (tens_x - 26, y0 - 30, tens_x + 26, y0 - 2),
                st,
                fs,
                rng,
                max_width=90,
            )
            ones_x = x1 - int(3.5 * PX)
            mss.draw_written(
                sheet, "1", (ones_x - 40, y0 - 28, ones_x - 8, y0 - 2), st, fs, rng, max_width=90
            )


def _smudge(sheet: Image.Image, box: tuple[int, int, int, int], rng: random.Random) -> None:
    """A thumb smear over one answer: blurred ink and a grey cloud."""
    x0, y0, x1, y1 = (
        box[0] + 8,
        box[1] + 8,
        box[2] - 8,
        box[3] - 8,
    )  # the printed border stays sharp
    region = sheet.crop((x0, y0, x1, y1)).filter(ImageFilter.GaussianBlur(radius=rng.uniform(5, 7)))
    arr = np.asarray(region, dtype=np.float32)
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = rng.uniform(0.35, 0.65) * w, rng.uniform(0.35, 0.65) * h
    cloud = np.exp(-(((xx - cx) / (0.35 * w)) ** 2 + ((yy - cy) / (0.45 * h)) ** 2))
    arr = arr * (1 - 0.35 * cloud[..., None]) + 90 * 0.35 * cloud[..., None]
    sheet.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)), (x0, y0))


def draw_child(
    base: Image.Image, layout: dict[str, Any], paper: dict[str, Any], child: DemoChild, seed: int
) -> Image.Image:
    """The paper as this child filled it in (before the photo is taken)."""
    rng = random.Random(f"{seed}|sheet|{child.roll}")
    fs = fonts()
    sheet = base.copy()
    style = mss.make_style(rng, fs)
    roll = next(b for b in layout["boxes"] if b["kind"] == "roll")
    mss.draw_written(sheet, str(child.roll), _px(roll), style, fs, rng)
    answer = layout["answer_boxes"]
    for i, text in enumerate(child.answers):
        box = _px(answer[str(i + 1)])
        if text == "":
            continue
        if child.hard == "crossed" and i == child.hard_item:
            x0, y0, x1, y1 = box
            mid = (x0 + x1) // 2
            first = str(int(text) + rng.choice([-10, 10, 1]))
            # the first try, crossed out, then the answer written again beside it
            bounds = mss.draw_written(
                sheet,
                first,
                (x0, y0, mid + 10, y1),
                style,
                fs,
                rng,
                max_width=mid - x0 + 60,
                scale=0.8,
            )
            mss.strike(sheet, bounds, style, rng, scribble=False)
            mss.draw_written(
                sheet,
                text,
                (mid - 4, y0, x1, y1),
                style,
                fs,
                rng,
                max_width=x1 - mid + 60,
                scale=0.85,
            )
            continue
        mss.draw_written(sheet, text, box, style, fs, rng)
        if child.hard == "smudge" and i == child.hard_item:
            _smudge(sheet, box, rng)
    if child.marks:
        _marks(sheet, layout, paper, style, fs, rng)
    return sheet


def _footer(img: Image.Image, text: str) -> Image.Image:
    """A small band at the foot of the photo: "Demo sheet" and the roll number."""
    out = img.copy()
    d = ImageDraw.Draw(out)
    size = max(18, img.width // 45)
    font = ImageFont.truetype(str(FOOTER_FONT), size)
    bbox = d.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = size // 2
    x, y = img.width - w - 3 * pad, img.height - h - 3 * pad
    d.rectangle(
        (x - pad, y - pad, x + w + pad, y + h + pad), fill=(255, 255, 255), outline=(0, 0, 0)
    )
    d.text((x - bbox[0], y - bbox[1]), text, fill=(0, 0, 0), font=font)
    return out


def photograph(sheet: Image.Image, child: DemoChild, seed: int) -> Image.Image:
    rng = random.Random(f"{seed}|photo|{child.roll}")
    kind = "fair" if child.hard or rng.random() < 0.35 else "clean"
    cond = mss.pick_conditions(rng, kind)
    cond["rot180"] = False
    cond["crop"] = False  # the corners and the code stay in view
    jpeg, _ = mss.capture(sheet, cond, rng, rng.choice(["desk", "table", "floor"]))
    img = Image.open(io.BytesIO(jpeg)).convert("RGB")
    if img.width > OUT_WIDTH:
        img = img.resize((OUT_WIDTH, round(img.height * OUT_WIDTH / img.width)), Image.LANCZOS)
    return img


def png_bytes(
    img: Image.Image, demo: DemoClass, child: DemoChild, check_code: str, paper_hash: str
) -> bytes:
    info = PngInfo()
    info.add_text(DEMO_KEY, "1")
    info.add_text("demo-roll", str(child.roll))
    info.add_text("demo-class", demo.class_code)
    info.add_text("demo-check-code", check_code)
    info.add_text("demo-paper-hash", paper_hash)
    info.add_text("demo-seed", str(demo.seed))
    info.add_text("Comment", "Demo sheet: synthetic, made by code. Not a real child's work.")
    buf = io.BytesIO()
    img.save(buf, "PNG", pnginfo=info, optimize=True)
    return buf.getvalue()


def demo_flag(data: bytes) -> dict[str, str] | None:
    """The demo text chunks of a PNG, or None if it is not a demo sheet."""
    try:
        img = Image.open(io.BytesIO(data))
    except Exception:  # noqa: BLE001
        return None
    text = getattr(img, "text", {}) or {}
    return dict(text) if text.get(DEMO_KEY) == "1" else None


def render_sheets(demo: DemoClass, paper: dict[str, Any], rules: RuleSet, out: Path) -> list[Path]:
    """Every child's sheet as a PNG in `out` (kept if already made for this seed and paper)."""
    out.mkdir(parents=True, exist_ok=True)
    base, layout = template(paper, rules)
    paths = []
    for child in demo.children:
        path = out / demo.sheet_name(child.roll)
        if not path.exists():
            img = photograph(draw_child(base, layout, paper, child, demo.seed), child, demo.seed)
            img = _footer(img, f"{FOOTER} · {demo.class_code} roll {child.roll:02d}")
            path.write_bytes(png_bytes(img, demo, child, paper["check_code"], paper["hash"]))
        paths.append(path)
    return paths


def zip_bytes(paths: list[Path], reads: dict[str, Any], blank_pdf: bytes, class_code: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:  # PNGs are already compressed
        for p in paths:
            z.write(p, p.name)
        z.writestr("reads.json", json.dumps(reads, indent=1, ensure_ascii=False))
        z.writestr(f"{class_code}-blank-paper.pdf", blank_pdf)
        z.writestr(
            "README.txt",
            "Demo sheets: synthetic, made by code for the Cohort Coach judge demo. No real child "
            "wrote them. reads.json is the demo answer file: what a reader would return for each "
            "sheet.\n",
        )
    return buf.getvalue()
