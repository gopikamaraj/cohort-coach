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
