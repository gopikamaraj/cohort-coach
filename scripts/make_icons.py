"""Draw the app icons (a bundle of ten sticks tied with a band) as PNGs for the PWA manifest.

Usage: python scripts/make_icons.py
Writes apps/pwa/public/icon-192.png, icon-512.png and icon-maskable-512.png. Pillow only; the
colours are the design tokens in docs/design-system.md.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "apps" / "pwa" / "public"
SLATE, PAPER, STICK, INK = "#1F3A33", "#FBFCFD", "#E8B93C", "#14201F"


def draw(size: int, safe: float) -> Image.Image:
    """`safe` is the share of the canvas the drawing may use (smaller for a maskable icon)."""
    img = Image.new("RGB", (size, size), SLATE)
    d = ImageDraw.Draw(img)
    box = size * safe
    left = (size - box) / 2
    top = (size - box) / 2
    stick_w = box / 14
    gap = box / 40
    total = 10 * stick_w + 9 * gap
    x = left + (box - total) / 2
    for _ in range(10):
        d.rectangle(
            [x, top + box * 0.12, x + stick_w, top + box * 0.88],
            fill=STICK,
            outline=INK,
            width=max(1, size // 160),
        )
        x += stick_w + gap
    band_y = top + box / 2
    d.rectangle(
        [left + box * 0.08, band_y - box * 0.04, left + box * 0.92, band_y + box * 0.04],
        fill=PAPER,
        outline=INK,
        width=max(1, size // 160),
    )
    return img


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    draw(192, 0.8).save(OUT / "icon-192.png", optimize=True)
    draw(512, 0.8).save(OUT / "icon-512.png", optimize=True)
    draw(512, 0.6).save(OUT / "icon-maskable-512.png", optimize=True)
    print("wrote icon-192.png, icon-512.png, icon-maskable-512.png")


if __name__ == "__main__":
    main()
