"""The design system's contrast figures are computed from the CSS tokens, not typed.

docs/design-system.md quotes WCAG contrast ratios; this test recomputes them from the tokens in
apps/pwa/src/theme.css (the one place that holds the look) and fails if the doc, the tokens or the
4.5:1 floor drift apart. It also keeps the look configurable: no colour literal in styles.css, every
token that a stylesheet uses is defined, and the colours that sit outside CSS match the tokens.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THEME = (ROOT / "apps/pwa/src/theme.css").read_text(encoding="utf-8")
CSS = (ROOT / "apps/pwa/src/styles.css").read_text(encoding="utf-8")
DOC = (ROOT / "docs/design-system.md").read_text(encoding="utf-8")


def token(name: str) -> str:
    m = re.search(rf"--{name}:\s*(#[0-9a-fA-F]{{6}})", THEME)
    assert m, name
    return m.group(1)


def luminance(hex_colour: str) -> float:
    r, g, b = (int(hex_colour[i : i + 2], 16) / 255 for i in (1, 3, 5))

    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(fg: str, bg: str) -> float:
    hi, lo = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_tokens_in_the_doc_match_the_css() -> None:
    for name in ("paper", "ink", "muted", "pen", "margin", "stick", "slate", "rule"):
        assert token(name).lower() in DOC.lower(), name


def test_every_text_pair_meets_the_floor_and_body_text_meets_7() -> None:
    paper = token("paper")
    assert contrast(token("ink"), paper) >= 7 and contrast(token("muted"), paper) >= 7
    for fg, bg in (
        ("pen", "paper"),
        ("margin", "paper"),
        ("ink", "stick"),
        ("chalk", "slate"),
    ):
        assert contrast(token(fg), token(bg)) >= 4.5, (fg, bg)
    assert contrast("#FFFFFF", token("pen")) >= 4.5
    assert contrast("#FFFFFF", token("margin")) >= 4.5


def test_the_ratios_quoted_in_the_doc_are_the_computed_ones() -> None:
    paper = token("paper")
    quoted = {
        "ink": contrast(token("ink"), paper),
        "muted": contrast(token("muted"), paper),
        "pen": contrast(token("pen"), paper),
        "margin": contrast(token("margin"), paper),
        "rule": contrast(token("rule"), paper),
    }
    for name, ratio in quoted.items():
        row = next(line for line in DOC.splitlines() if line.startswith(f"| `{name}`"))
        assert f"{ratio:.1f}" in row, (name, f"{ratio:.1f}", row)
    assert f"{contrast('#FFFFFF', token('pen')):.1f}" in DOC
    assert f"{contrast('#FFFFFF', token('margin')):.1f}" in DOC
    assert f"{contrast(token('ink'), token('stick')):.1f}" in DOC
    assert f"{contrast(token('chalk'), token('slate')):.1f}" in DOC


def test_the_tap_target_and_font_floors_are_in_the_css() -> None:
    assert "min-height: 48px" in CSS and "min-height: 56px" in CSS
    sizes = [int(s) for s in re.findall(r"font-size:\s*(\d+)px", CSS)]
    assert min(sizes) >= 16  # the design system's floor for any text


COLOUR_LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?)\(")


def test_styles_hold_no_colour_literal_so_the_look_changes_in_one_file() -> None:
    found = COLOUR_LITERAL.findall(CSS)
    assert not found, f"colour literals in styles.css (move them to theme.css): {found[:5]}"


def test_every_token_a_stylesheet_uses_is_defined() -> None:
    sheets = THEME + CSS
    defined = set(re.findall(r"(--[a-z0-9-]+)\s*:", sheets))
    used = set(re.findall(r"var\((--[a-z0-9-]+)\s*\)", sheets))  # a var() with a fallback is exempt
    assert not (used - defined), f"tokens used but not defined: {sorted(used - defined)}"


def test_the_classic_theme_only_overrides_tokens_that_exist() -> None:
    root = re.search(r":root \{(.*?)\n\}", THEME, re.S)
    classic = re.search(r'\[data-theme="classic"\] \{(.*?)\n\}', THEME, re.S)
    assert root and classic
    base = set(re.findall(r"(--[a-z0-9-]+)\s*:", root.group(1)))
    over = set(re.findall(r"(--[a-z0-9-]+)\s*:", classic.group(1)))
    assert over <= base, sorted(over - base)


def test_colours_outside_css_match_the_tokens() -> None:
    vite = (ROOT / "apps/pwa/vite.config.ts").read_text(encoding="utf-8")
    html = (ROOT / "apps/pwa/index.html").read_text(encoding="utf-8")
    icon_script = (ROOT / "scripts/make_icons.py").read_text(encoding="utf-8")
    svg = (ROOT / "apps/pwa/public/icon.svg").read_text(encoding="utf-8")
    pen, paper = token("pen").lower(), token("paper").lower()
    assert f'theme_color: "{pen}"' in vite and f'background_color: "{paper}"' in vite
    assert f'<meta name="theme-color" content="{pen}"' in html
    assert pen in svg.lower()
    for name in ("slate", "paper", "stick", "ink"):
        assert token(name).upper() in icon_script.upper(), name


HEAT = ("heat-ph", "heat-pr", "heat-ac", "heat-sf", "heat-sn")

# Colour-blind simulation matrices (Machado et al. 2009, full severity), applied in linear RGB.
_SIM = {
    "protan": [
        [0.152286, 1.052583, -0.204868],
        [0.114503, 0.786281, 0.099216],
        [-0.003882, -0.048116, 1.051998],
    ],  # noqa: E501
    "deutan": [
        [0.367322, 0.860646, -0.227968],
        [0.280085, 0.672501, 0.047413],
        [-0.011820, 0.042940, 0.968881],
    ],  # noqa: E501
    "tritan": [
        [1.255528, -0.076749, -0.178779],
        [-0.078411, 0.930809, 0.147602],
        [0.004733, 0.691367, 0.303900],
    ],  # noqa: E501
}  # noqa: E501


def _lin(c: int) -> float:
    x = c / 255
    return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4


def _lab(rgb: list[float]) -> tuple[float, float, float]:
    r, g, b = rgb
    x = 0.4124 * r + 0.3576 * g + 0.1805 * b
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = 0.0193 * r + 0.1192 * g + 0.9505 * b

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    fx, fy, fz = f(x / 0.95047), f(y), f(z / 1.08883)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def _seen(hex_colour: str, kind: str) -> tuple[float, float, float]:
    rgb = [_lin(int(hex_colour[i : i + 2], 16)) for i in (1, 3, 5)]
    m = _SIM[kind]
    sim = [max(0.0, min(1.0, sum(m[i][j] * rgb[j] for j in range(3)))) for i in range(3)]
    return _lab(sim)


def test_the_answer_map_colours_have_contrast_with_ink_and_are_told_apart_by_colour_blind_eyes() -> (  # noqa: E501
    None
):
    from itertools import combinations
    from math import dist

    for name in HEAT:
        assert contrast(token("ink"), token(name)) >= 4.5, name
    for kind in _SIM:
        for a, b in combinations(HEAT, 2):
            assert dist(_seen(token(a), kind), _seen(token(b), kind)) >= 15, (kind, a, b)


def test_every_mistake_in_the_answer_map_has_its_own_pattern_and_letters() -> None:
    """Colour is never the only signal: a pattern per mistake in the CSS, two letters per mistake in code."""  # noqa: E501
    for cls in (
        "amap-pv-heard",
        "amap-pv-reverse",
        "amap-add-nocarry",
        "amap-sub-sfl",
        "amap-sub-nodec",
    ):
        block = re.search(rf"\.{cls} \{{(.*?)\}}", CSS, re.S)
        assert block and "--pat:" in block.group(1) and "--heat:" in block.group(1), cls
    patterns = re.findall(r"--pat:\s*([^;]+);", CSS)
    assert len(patterns) == len(set(patterns)) == 5
    ts = (ROOT / "apps/pwa/src/lib/results.ts").read_text(encoding="utf-8")
    letters = re.findall(r'"[A-Z-]+": "([A-Z]{2})"', ts)
    assert len(letters) == len(set(letters)) == 5
