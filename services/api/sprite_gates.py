"""The gates a drafted sprite item passes before a coach ever sees it. All of them are code.

Call 11 drafts; these checks decide. Each returns a named `ValidatorResult` so a rejected draft can
tell the author exactly which rule failed (the client feeds the names and codes back on retry).
A draft that fails any of them is never shown to a teacher, a coach or a visitor.
"""

from __future__ import annotations

import io
import re
from typing import Any

from PIL import Image

from ai.schemas import SpriteItemDraft
from ai.validators import ValidatorResult, Violation
from ai.validators.check_items import check_items
from ai.validators.prefilter import check_prefilter
from services.api.sprites.grammar import VIEWBOX, compile_item, validate_spec, validate_svg
from services.api.sprites.items import item_ids
from services.api.sprites.layouts import LayoutError, row
from services.api.sprites.palette import palette, palette_names
from services.api.sprites.png import svg_to_png

PALETTE_CODES = ("paint_not_a_slot", "raw_colour")
SIZE_CODE = "over_budget"
TEXT_CODES = ("text_node", "forbidden_element")


def spec_from_draft(draft: SpriteItemDraft) -> dict[str, Any]:
    """The item spec the renderer reads. Unset fields are dropped; the id gives the alt key."""
    parts = [p.model_dump(exclude_none=True) for p in draft.parts]
    return {
        "id": draft.id,
        "version": 1,
        "status": "draft",
        "category": "item",
        "viewBox": list(VIEWBOX["item"]),
        "parts": parts,
        "count": {"mode": "single"},
        "alt": {"key": f"sprite.item.{draft.id}"},
        "topics": list(draft.topics),
    }


def _result(name: str, codes: list[str]) -> ValidatorResult:
    return ValidatorResult(name, tuple(Violation(c) for c in sorted(set(codes))))


def _contact_tile(spec: dict[str, Any]) -> list[str]:
    """The tile a coach would see: counts 1 and 5 in every palette, and as a PNG."""
    out: list[str] = []
    for name in palette_names():
        pal = palette(name)
        for n in (1, 5):
            try:
                scene = row(spec, n, pal)
            except (LayoutError, KeyError) as exc:
                out.append(f"render_failed:{name}:{type(exc).__name__}")
                continue
            if scene.report["count_drawn"] != n or scene.svg.count('class="u"') != n:
                out.append(f"count_mismatch:{name}:{n}")
    try:
        png = svg_to_png(row(spec, 1, palette("default")).svg, width=96)
        colours = Image.open(io.BytesIO(png)).convert("RGB").getcolors(maxcolors=4096) or []
        if len(colours) < 3:
            out.append("blank_tile")
    except Exception as exc:  # a PNG that will not render must stop the draft
        out.append(f"png_failed:{type(exc).__name__}")
    return out


def gate_draft(
    draft: SpriteItemDraft, *, existing: set[str] | None = None
) -> list[ValidatorResult]:
    """Gate 1 (code validators) and gate 1b (pre-filter) for a drafted item."""
    taken = set(item_ids()) if existing is None else existing
    spec = spec_from_draft(draft)
    grammar = validate_spec(spec, "item")
    id_codes = ["id_taken"] if draft.id in taken else []
    word_codes: list[str] = []
    if re.search(r"\d", draft.alt_en):
        word_codes.append("digit_in_alt")
    if re.search(r"[<>&{}]", draft.alt_en + "".join(draft.topics)):
        word_codes.append("markup_in_words")
    if not draft.topics:
        word_codes.append("topics_missing")

    svg = compile_item(spec, palette("default")) if not grammar else ""
    svg_codes = validate_svg(svg) if svg else []
    results = [
        _result("id", id_codes + [c for c in grammar if c in ("bad_id", "alt_key_format")]),
        _result(
            "grammar",
            [
                c
                for c in grammar
                if not c.startswith((SIZE_CODE, *PALETTE_CODES))
                and c not in ("bad_id", "alt_key_format")
            ],
        ),
        _result("size", [c.split(":")[0] for c in grammar if c.startswith(SIZE_CODE)]),
        _result("palette_slots", [c.split(":")[0] for c in grammar if c.startswith(PALETTE_CODES)]),
        _result("no_text", word_codes + [c for c in svg_codes if c.startswith(TEXT_CODES)]),
        _result("svg", [c for c in svg_codes if not c.startswith(TEXT_CODES)]),
    ]
    if not any(not r.ok for r in results):
        results.append(_result("contact_tile", _contact_tile(spec)))
    words = f"{draft.alt_en}. {', '.join(draft.topics)}"
    pre = check_prefilter(draft.alt_en, "en", max_chars=80)
    results.append(ValidatorResult("prefilter", tuple(pre)))
    results.append(ValidatorResult("check_items", tuple(check_items(words))))
    return results
