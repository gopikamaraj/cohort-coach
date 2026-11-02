"""The printed paper: four layouts render, fonts are embedded, every glyph is covered, nothing
overflows, and the layout map matches the rendered boxes (checked by sampling pixels)."""

from __future__ import annotations

import ctypes
from functools import cache
from typing import Any

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c
import pytest

from services.papers import generator as g
from services.papers import render as r
from services.papers import verifier as v
from services.papers.rules import LAYOUTS, seed_rules

RULES = seed_rules()
DPI = 100


@cache
def paper(blueprint: str = "standard_10_5") -> dict[str, Any]:
    check = g.CheckRef(id="c-1:1", kind="pre", form="A", class_label="3A", term=1)
    prof = g.profile_from_counts({"SUB-SFL": 9, "ADD-NOCARRY": 3}, 18, "en")
    return g.generate_paper(check, prof, RULES, blueprint, 1, 7).to_dict()


@cache
def rendered(lang: str, blueprint: str = "standard_10_5") -> tuple[bytes, dict[str, Any]]:
    return r.render_paper(paper(blueprint), RULES, lang)


def test_weasyprint_is_available() -> None:
    assert r.weasyprint_available()


@pytest.mark.parametrize("lang", LAYOUTS)
def test_every_layout_renders_with_nothing_overflowing_or_overlapping(lang: str) -> None:
    pdf, layout = rendered(lang)
    assert pdf.startswith(b"%PDF")
    assert layout["overflow"] == []
    assert v.verify_layout(layout) == []
    assert len(pdfium.PdfDocument(pdf)) == layout["pages"]


def test_the_pilot_shaped_paper_fits_on_one_page_in_every_layout() -> None:
    for lang in LAYOUTS:
        assert rendered(lang, "baseline_10")[1]["pages"] == 1


def embedded_fonts(pdf: bytes) -> dict[str, bool]:
    """Font name (subset prefix removed) -> embedded, for every text object in the PDF."""
    out: dict[str, bool] = {}
    for page in pdfium.PdfDocument(pdf):
        for obj in page.get_objects(filter=[pdfium_c.FPDF_PAGEOBJ_TEXT]):
            font = pdfium_c.FPDFTextObj_GetFont(obj.raw)
            n = pdfium_c.FPDFFont_GetBaseFontName(font, None, 0)
            buf = ctypes.create_string_buffer(n)
            pdfium_c.FPDFFont_GetBaseFontName(font, buf, n)
            name = buf.value.decode().split("+", 1)[-1]
            out[name] = bool(pdfium_c.FPDFFont_GetIsEmbedded(font))
    return out


@pytest.mark.parametrize(
    ("lang", "font"),
    [
        ("en", "Noto-Sans"),
        ("hi", "Noto-Sans-Devanagari"),
        ("ta", "Noto-Sans-Tamil"),
        ("en_hi", "Noto-Sans-Devanagari"),
    ],
)
def test_fonts_are_embedded(lang: str, font: str) -> None:
    fonts = embedded_fonts(rendered(lang)[0])
    assert font in fonts and all(fonts.values()), fonts


def test_every_glyph_in_every_string_pack_is_in_the_embedded_fonts() -> None:
    packs = {p.lang: p.strings for p in RULES.string_packs}
    assert v.verify_strings(packs, v.FONTS) == []


def _image(pdf: bytes, page: int) -> Any:
    return pdfium.PdfDocument(pdf)[page - 1].render(scale=DPI / 72).to_pil().convert("L")


def _px(mm: float) -> int:
    return round(mm / 25.4 * DPI)


@pytest.mark.parametrize("lang", LAYOUTS)
def test_the_layout_map_matches_the_printed_boxes(lang: str) -> None:
    pdf, layout = rendered(lang)
    images = {p: _image(pdf, p) for p in range(1, layout["pages"] + 1)}
    boxes = [b for b in layout["boxes"] if b["kind"] in ("answer", "roll", "form")]
    assert len(layout["answer_boxes"]) == len(paper()["items"])
    for b in boxes:
        img = images[b["page"]]
        edge = img.getpixel((_px(b["x"] + b["w"] / 2), _px(b["y"] + 0.25)))
        left = img.getpixel((_px(b["x"] + 0.25), _px(b["y"] + b["h"] / 2)))
        assert edge < 100 and left < 100, (b["id"], edge, left)
        if b["kind"] != "form":  # the form box holds its letter
            middle = img.getpixel((_px(b["x"] + b["w"] / 2), _px(b["y"] + b["h"] / 2)))
            assert middle > 200, (b["id"], middle)
    for m in layout["marks"]:
        img = images[m["page"]]
        assert img.getpixel((_px(m["x"] + m["w"] / 2), _px(m["y"] + m["h"] / 2))) < 60


def test_every_page_has_four_corner_marks() -> None:
    _, layout = rendered("hi")
    for p in range(1, layout["pages"] + 1):
        assert len([m for m in layout["marks"] if m["page"] == p]) == 4


def test_the_childs_paper_has_a_roll_box_no_name_field_and_never_says_cohort_coach() -> None:
    for lang in LAYOUTS:
        pdf, layout = rendered(lang)
        text = "".join(page.get_textpage().get_text_range() for page in pdfium.PdfDocument(pdf))
        assert "Cohort" not in text and "Coach" not in text
        assert paper()["check_code"].replace(" ", "") in text.replace(" ", "").replace("\r\n", "")
        kinds = {b["kind"] for b in layout["boxes"]}
        assert "roll" in kinds and not any(
            "name" in b["id"] and b["kind"] != "text" for b in layout["boxes"]
        )


def test_the_answer_key_lists_the_key_and_the_wrong_answers() -> None:
    p = paper()
    pdf = r.render_key(p, RULES, "en")
    text = "".join(page.get_textpage().get_text_range() for page in pdfium.PdfDocument(pdf))
    for it in p["items"]:
        assert str(it["correct"]) in text
    assert "SUB-SFL" in text and "ADD-NOCARRY" in text
    assert "Noto-Sans-Tamil" in embedded_fonts(r.render_key(p, RULES, "ta"))


def test_any_two_languages_make_a_layout_first_language_first() -> None:
    from services.papers.rules import layout_langs

    assert layout_langs("ta_hi") == ("ta", "hi") and layout_langs("en") == ("en",)
    assert len(LAYOUTS) == 9
    with pytest.raises(ValueError):
        layout_langs("hi_hi")


def test_the_key_says_why_item_6_has_no_wrong_answers_and_explains_its_header() -> None:
    from services.papers import generator as gen

    check = gen.CheckRef("c-1:1", "pre", "A", "3A", 1)
    p = gen.pilot_paper(check, RULES, 1, "A").to_dict()
    text = "".join(
        page.get_textpage().get_text_range()
        for page in pdfium.PdfDocument(r.render_key(p, RULES, "en"))
    ).replace("\r\n", " ")
    assert "whether the child can take away at all" in text
    assert "Made by code, not AI" in text and "10 questions, the same skills as the pilot" in text
    assert "baseline_10" not in text
