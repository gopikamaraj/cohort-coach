"""The design system's contrast figures are computed from the CSS tokens, not typed.

docs/design-system.md quotes WCAG contrast ratios; this test recomputes them from
apps/pwa/src/styles.css and fails if the doc, the CSS or the 4.5:1 floor drift apart.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "apps/pwa/src/styles.css").read_text(encoding="utf-8")
DOC = (ROOT / "docs/design-system.md").read_text(encoding="utf-8")


def token(name: str) -> str:
    m = re.search(rf"--{name}:\s*(#[0-9a-fA-F]{{6}})", CSS)
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
