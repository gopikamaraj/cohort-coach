"""SVG to PNG on the server, for Telegram and WhatsApp (and the PWA's fallback sprite sheet).

Library: `resvg-py` (the resvg Rust renderer in a wheel: no Cairo or system libraries, so it works
on Windows, Linux and the hosts we use). Chosen over CairoSVG, which needs the native Cairo
library. Only SVG that passes the sprite grammar is ever rendered, and no font is loaded because
the grammar has no text.
"""

from __future__ import annotations

import resvg_py

from services.api.sprites.grammar import validate_svg


def svg_to_png(svg: str, width: int = 480, background: str | None = None) -> bytes:
    bad = validate_svg(svg)
    if bad:
        raise ValueError(f"refusing to render SVG outside the grammar: {bad}")
    return bytes(
        resvg_py.svg_to_bytes(
            svg_string=svg, width=width, background=background, skip_system_fonts=True
        )  # fmt: skip
    )
