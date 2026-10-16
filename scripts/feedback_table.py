"""Render the "You said -> We changed" table from docs/feedback-log.md.

Usage: python scripts/feedback_table.py [path-to-log]
Reads the markdown table (columns: date, round, participant code, what they said or did,
what we changed, commit, status) and prints a two-column table of rows that changed something.
"""

from __future__ import annotations

import sys
from pathlib import Path

DEFAULT_LOG = Path(__file__).resolve().parent.parent / "docs" / "feedback-log.md"


def parse_rows(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 7 or cells[0].lower() == "date" or set(cells[0]) <= {"-", " ", ":"}:
            continue
        rows.append(cells)
    return rows


def render(text: str) -> str:
    out = ["| You said | We changed | Commit |", "| --- | --- | --- |"]
    for cells in parse_rows(text):
        said, changed, commit = cells[3], cells[4], cells[5]
        if said and changed:
            out.append(f"| {said} | {changed} | {commit} |")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else DEFAULT_LOG
    print(render(path.read_text(encoding="utf-8")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
