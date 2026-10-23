"""Check the Stitch prompts in docs/design/stitch/.

Fails loudly unless:
- every ID in INVENTORY.md has exactly one prompt file, and no prompt file has an ID the inventory
  does not list;
- every prompt contains the shared header (_header.md, at most 250 words) between its markers;
- no emoji (or emoji-capable symbol) appears in any file under prompts/ or in _header.md;
- no child name from the dataset (content/personas/children.v1.yaml) appears outside the Practice
  Class prompts;
- teacher-facing prompts (role Teacher or Mentor) contain no percent sign;
- every prompt is between 600 and 1,500 words.

Run: python scripts/check_stitch_prompts.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
STITCH = ROOT / "docs" / "design" / "stitch"
CHILDREN = ROOT / "content" / "personas" / "children.v1.yaml"

MIN_WORDS, MAX_WORDS, MAX_HEADER_WORDS = 600, 1500, 250
# Prompts that show the simulated Practice Class children and so may use their names.
PRACTICE_CLASS_IDS = frozenset({"T5", "X3"})
TEACHER_FACING_ROLES = ("Teacher", "Mentor")

EMOJI = re.compile(
    "["
    "\U0001f000-\U0001faff"  # pictographs, emoticons, transport, symbols
    "←-⇿"  # arrows (several are emoji)
    "⌀-⏿"  # technical (hourglass, watch)
    "■-◿"  # geometric shapes (play triangle)
    "☀-➿"  # miscellaneous symbols and dingbats (check marks, crosses, stars)
    "⬀-⯿"  # arrows and stars
    "‍️"  # joiner and emoji variation selector
    "〰〽㊗㊙"
    "]"
)
ID_ROW = re.compile(r"^\|\s*([A-Z]{1,2}\d+)\s*\|", re.M)
HEADER_START, HEADER_END = "<!-- stitch-header:start -->", "<!-- stitch-header:end -->"


def words(text: str) -> int:
    return len(re.findall(r"\S+", text))


def squash(text: str) -> str:
    return " ".join(text.split())


def inventory(stitch: Path = STITCH) -> dict[str, str]:
    """ID -> role, from the inventory table (columns: ID, name, role, ...)."""
    out: dict[str, str] = {}
    for line in (stitch / "INVENTORY.md").read_text(encoding="utf-8").splitlines():
        if ID_ROW.match(line):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            out[cells[0]] = cells[2]
    return out


def child_names(path: Path = CHILDREN) -> list[str]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return sorted({n for kid in data["children"] for n in kid["names"].values()})


def name_pattern(name: str) -> re.Pattern[str]:
    if name.isascii():  # a whole word, so "Mani" does not match inside "Manifest"
        return re.compile(rf"(?<![A-Za-z]){re.escape(name)}(?![A-Za-z])")
    return re.compile(re.escape(name))


def check(stitch: Path = STITCH, names: list[str] | None = None) -> list[str]:
    problems: list[str] = []
    roles = inventory(stitch)
    header_path = stitch / "_header.md"
    if not header_path.exists():
        return ["_header.md is missing"]
    header_text = header_path.read_text(encoding="utf-8")
    header = squash(header_text)
    if words(header_text) > MAX_HEADER_WORDS:
        problems.append(f"_header.md has {words(header_text)} words (max {MAX_HEADER_WORDS})")
    if EMOJI.search(header_text):
        problems.append("_header.md contains an emoji or emoji-capable symbol")

    prompts = {p.name.split("-", 1)[0]: p for p in sorted((stitch / "prompts").glob("*.md"))}
    for pid in roles:
        if pid not in prompts:
            problems.append(f"{pid}: no prompt file in prompts/")
    for pid in prompts:
        if pid not in roles:
            problems.append(f"{pid}: prompt file has no row in INVENTORY.md")

    patterns = [(n, name_pattern(n)) for n in (child_names() if names is None else names)]
    for pid, path in prompts.items():
        text = path.read_text(encoding="utf-8")
        label = f"{pid} ({path.name})"
        count = words(text)
        if not MIN_WORDS <= count <= MAX_WORDS:
            problems.append(f"{label}: {count} words (need {MIN_WORDS} to {MAX_WORDS})")
        start, end = text.find(HEADER_START), text.find(HEADER_END)
        if start < 0 or end < start or squash(text[start + len(HEADER_START) : end]) != header:
            problems.append(f"{label}: the shared header is missing or was edited")
        if EMOJI.search(text):
            problems.append(f"{label}: contains an emoji or emoji-capable symbol")
        if pid not in PRACTICE_CLASS_IDS:
            for name, pat in patterns:
                if pat.search(text):
                    problems.append(f"{label}: child name {name!r} outside the Practice Class")
        if roles.get(pid, "").startswith(TEACHER_FACING_ROLES) and "%" in text:
            problems.append(f"{label}: percent sign in a teacher-facing prompt")
    return problems


def main() -> int:
    problems = check()
    ids = inventory()
    if problems:
        print(f"FAIL: {len(problems)} problem(s) in the Stitch prompts")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"OK: {len(ids)} prompts, header shared, no emoji, no child names outside Practice Class")
    return 0


if __name__ == "__main__":
    sys.exit(main())
