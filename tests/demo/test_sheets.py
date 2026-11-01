"""Synthetic demo sheets: drawn into the real paper's layout map, named by class and roll number,
flagged as demo in the PNG and in a visible footer, and the same for the same seed."""

from __future__ import annotations

import io
from functools import cache
from pathlib import Path
from typing import Any

from PIL import Image

from services.demo import scenario, sheets
from services.papers import generator as g
from services.papers.rules import seed_rules

RULES = seed_rules()


@cache
def paper() -> dict[str, Any]:
    ref = g.CheckRef("demo:1", "pre", "A", "3A", 1)
    return g.pilot_paper(ref, RULES, 1, "A").to_dict()


def one(tmp: Path, roll: int) -> bytes:
    demo = scenario.build_class(scenario.load_scenario())
    child = demo.children[roll - 1]
    base, layout = sheets.template(paper(), RULES)
    img = sheets.photograph(
        sheets.draw_child(base, layout, paper(), child, demo.seed), child, demo.seed
    )
    img = sheets._footer(img, f"{sheets.FOOTER} · 3A roll {roll:02d}")
    return sheets.png_bytes(img, demo, child, paper()["check_code"], paper()["hash"])


def test_a_sheet_carries_the_demo_flag_roll_and_check_code_in_its_metadata(tmp_path: Path) -> None:
    data = one(tmp_path, 6)
    flag = sheets.demo_flag(data)
    assert flag is not None
    assert flag["demo-roll"] == "6" and flag["demo-class"] == "3A"
    assert flag["demo-check-code"] == "PRE · 3A · T1"
    assert "Not a real child" in flag["Comment"]


def test_the_footer_says_demo_sheet_in_the_bottom_corner(tmp_path: Path) -> None:
    img = Image.open(io.BytesIO(one(tmp_path, 1))).convert("L")
    w, h = img.size
    corner = img.crop((int(w * 0.6), int(h * 0.93), w, h))
    assert min(corner.getdata()) < 60 and max(corner.getdata()) > 240  # black text on white


def test_the_same_seed_draws_the_same_sheet(tmp_path: Path) -> None:
    assert one(tmp_path, 3) == one(tmp_path, 3)


def test_a_photo_that_is_not_a_demo_sheet_has_no_flag() -> None:
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), "white").save(buf, "PNG")
    assert sheets.demo_flag(buf.getvalue()) is None
    assert sheets.demo_flag(b"not an image") is None


def test_sheet_names_follow_class_code_and_roll_number() -> None:
    demo = scenario.build_class(scenario.load_scenario())
    assert [demo.sheet_name(c.roll) for c in demo.children][:3] == [
        "3A-roll01.png",
        "3A-roll02.png",
        "3A-roll03.png",
    ]


def test_the_zip_holds_every_sheet_the_answer_file_and_the_blank_paper(tmp_path: Path) -> None:
    import zipfile

    p = tmp_path / "3A-roll01.png"
    p.write_bytes(one(tmp_path, 1))
    data = sheets.zip_bytes([p], {"demo": True}, b"%PDF-1.7", "3A")
    names = zipfile.ZipFile(io.BytesIO(data)).namelist()
    assert names == ["3A-roll01.png", "reads.json", "3A-blank-paper.pdf", "README.txt"]
