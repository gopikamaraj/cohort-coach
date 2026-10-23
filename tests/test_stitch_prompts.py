"""The Stitch prompt checker: the real files pass, and each rule fails loudly when broken."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_stitch_prompts as chk  # noqa: E402


@pytest.fixture
def stitch(tmp_path: Path) -> Path:
    dest = tmp_path / "stitch"
    shutil.copytree(chk.STITCH, dest, ignore=shutil.ignore_patterns("exports"))
    return dest


def prompt(stitch: Path, pid: str) -> Path:
    return next((stitch / "prompts").glob(f"{pid}-*.md"))


def test_the_real_prompts_pass() -> None:
    assert chk.check() == []


def test_the_inventory_lists_every_design_doc_screen_and_the_added_ones() -> None:
    ids = set(chk.inventory())
    assert {"T1", "T2", "T3", "T4", "T5", "T6", "M1", "M2", "P1", "P2", "P3", "P4", "J1"} <= ids
    assert {"X1", "X2", "X3"} <= ids and any(i.startswith("R") for i in ids)


def test_a_screen_with_no_prompt_file_fails(stitch: Path) -> None:
    prompt(stitch, "T3").unlink()
    assert any(p.startswith("T3: no prompt file") for p in chk.check(stitch))


def test_a_prompt_with_no_inventory_row_fails(stitch: Path) -> None:
    (stitch / "prompts" / "Z9-extra.md").write_text("# Z9", encoding="utf-8")
    assert any(p.startswith("Z9: prompt file has no row") for p in chk.check(stitch))


def test_a_prompt_without_the_shared_header_fails(stitch: Path) -> None:
    path = prompt(stitch, "T1")
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("primary #0B6B6B", "primary #123456"), encoding="utf-8")
    assert any("T1" in p and "header" in p for p in chk.check(stitch))


def test_an_emoji_fails(stitch: Path) -> None:
    path = prompt(stitch, "P1")
    path.write_text(path.read_text(encoding="utf-8") + "\nGood \U0001f600\n", encoding="utf-8")
    assert any("P1" in p and "emoji" in p for p in chk.check(stitch))


@pytest.mark.parametrize("symbol", ["✓", "▶", "→"])
def test_emoji_capable_symbols_fail_too(stitch: Path, symbol: str) -> None:
    path = prompt(stitch, "T2")
    path.write_text(path.read_text(encoding="utf-8") + f"\nChecked {symbol}\n", encoding="utf-8")
    assert any("T2" in p and "emoji" in p for p in chk.check(stitch))


def test_a_child_name_outside_the_practice_class_fails_but_inside_it_passes(stitch: Path) -> None:
    names = chk.child_names()
    assert "Meena" in names
    path = prompt(stitch, "T3")
    path.write_text(path.read_text(encoding="utf-8") + "\nMeena got it.\n", encoding="utf-8")
    assert any("T3" in p and "'Meena'" in p for p in chk.check(stitch))
    inside = prompt(stitch, "T5")
    inside.write_text(inside.read_text(encoding="utf-8") + "\nMeena got it.\n", encoding="utf-8")
    assert not any("T5" in p and "child name" in p for p in chk.check(stitch))


def test_a_hindi_child_name_also_fails(stitch: Path) -> None:
    path = prompt(stitch, "M2")
    path.write_text(path.read_text(encoding="utf-8") + "\nमीना\n", encoding="utf-8")
    assert any("M2" in p and "child name" in p for p in chk.check(stitch))


def test_a_percent_sign_fails_in_a_teacher_prompt_but_not_an_officer_one(stitch: Path) -> None:
    for pid in ("T3", "M1"):
        path = prompt(stitch, pid)
        path.write_text(path.read_text(encoding="utf-8") + "\n40%\n", encoding="utf-8")
    problems = chk.check(stitch)
    assert any("T3" in p and "percent sign" in p for p in problems)
    assert any("M1" in p and "percent sign" in p for p in problems)
    officer = prompt(stitch, "P1")
    officer.write_text(officer.read_text(encoding="utf-8") + "\n40%\n", encoding="utf-8")
    assert not any("P1" in p and "percent sign" in p for p in chk.check(stitch))


def test_word_limits_are_enforced(stitch: Path) -> None:
    short = prompt(stitch, "T4")
    text = short.read_text(encoding="utf-8")
    short.write_text(text[: len(text) // 4], encoding="utf-8")
    long_ = prompt(stitch, "T6")
    long_.write_text(long_.read_text(encoding="utf-8") + "word " * 1600, encoding="utf-8")
    problems = chk.check(stitch)
    assert any("T4" in p and "words" in p for p in problems)
    assert any("T6" in p and "words" in p for p in problems)


def test_the_header_itself_is_within_its_limit(stitch: Path) -> None:
    header = stitch / "_header.md"
    header.write_text(header.read_text(encoding="utf-8") + "extra " * 40, encoding="utf-8")
    assert any("_header.md has" in p for p in chk.check(stitch))


def test_a_missing_header_file_fails(stitch: Path) -> None:
    (stitch / "_header.md").unlink()
    assert chk.check(stitch) == ["_header.md is missing"]


def test_no_secret_or_stitch_bug_is_copied_into_a_prompt() -> None:
    for path in (chk.STITCH / "prompts").glob("*.md"):
        text = path.read_text(encoding="utf-8")
        assert "fonts.googleapis" not in text and "cdn.tailwindcss" not in text, path.name
