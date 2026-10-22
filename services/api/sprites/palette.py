"""Palette slots: specs name a slot, never a colour. Also the contrast and colour-blind checks."""

from __future__ import annotations

import json
from functools import cache
from pathlib import Path
from typing import Any

SPRITES = Path(__file__).resolve().parents[3] / "content" / "sprites"
SLOTS = ("skin", "hair", "cloth_a", "cloth_b", "accent", "item_a", "item_b", "mat", "ink")


@cache
def _file() -> dict[str, Any]:
    return json.loads((SPRITES / "palettes.v1.json").read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def palette(name: str = "default") -> dict[str, str]:
    p = _file()["palettes"][name]
    assert set(p) == set(SLOTS), name
    return dict(p)


def palette_names() -> list[str]:
    return list(_file()["palettes"])


def skin_tones() -> list[str]:
    return list(_file()["skin_tones"])


def hair_colours() -> list[str]:
    return list(_file()["hair_colours"])


def cloth_colours() -> list[str]:
    return list(_file()["cloth_colours"])


# --- documented colour-blind simulation -------------------------------------------------------
# Machado, Oliveira and Fernandes (2009), "A Physiologically-based Model for Simulation of Color
# Vision Deficiency", IEEE TVCG 15(6): matrices for severity 1.0, applied to linear sRGB.
CVD: dict[str, tuple[tuple[float, float, float], ...]] = {
    "protanopia": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    "deuteranopia": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
    "tritanopia": (
        (1.255528, -0.076749, -0.178779),
        (-0.078411, 0.930809, 0.147602),
        (0.004733, 0.691367, 0.303900),
    ),
}


def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _gam(c: float) -> float:
    c = min(1.0, max(0.0, c))
    return c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def rgb(hex_colour: str) -> tuple[float, float, float]:
    h = hex_colour.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def simulate(hex_colour: str, kind: str) -> tuple[float, float, float]:
    lin = [_lin(c) for c in rgb(hex_colour)]
    m = CVD[kind]
    out = [sum(m[r][c] * lin[c] for c in range(3)) for r in range(3)]
    return tuple(_gam(v) for v in out)  # type: ignore[return-value]


def luminance(c: tuple[float, float, float]) -> float:
    r, g, b = (_lin(v) for v in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)
