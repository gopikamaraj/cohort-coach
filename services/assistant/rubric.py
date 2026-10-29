"""docs/RUBRIC_MAP.md as data: one Row per claim, with its honest status.

The assistant never states a status stronger than the row's. When the deck or the video script uses a
stronger word for the same row, the stricter status wins and the answer says the deck or video
differs (claims.py).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUBRIC_MAP = ROOT / "docs" / "RUBRIC_MAP.md"

STATUSES = ("Built", "Partly built", "Simulated", "Mock", "Roadmap")  # strongest first
RANK = {s: len(STATUSES) - i for i, s in enumerate(STATUSES)}  # Built 5 ... Roadmap 1
COLUMNS = (
    "Id",
    "Bullet",
    "Claim",
    "Status",
    "Feature",
    "Code",
    "Test or eval",
    "Demo",
    "Known limit",
    "Slide",
    "Video",
)
CRITERIA = {
    "Efficacy and user centricity": (
        "Impact potential",
        "An intuitive interface",
        "User constraints",
        "Proof of testing and refinement",
    ),
    "Innovation": ("A novel AI-centred approach", "Differentiation"),
    "Effective AI use and technical strength": (
        "Effective LLM use",
        "Technical depth and guardrails",
        "Working in real scenarios",
    ),
    "Future roadmap": ("Future roadmap",),
}


@dataclass(frozen=True)
class Row:
    id: str
    criterion: str
    bullet: str
    claim: str
    status: str
    feature: str
    code: tuple[str, ...]
    tests: tuple[str, ...]
    demo: str
    limit: str
    slides: tuple[int, ...]
    video: tuple[str, ...]  # "mm:ss" segment starts

    def to_dict(self) -> dict[str, object]:
        return {k: list(v) if isinstance(v, tuple) else v for k, v in self.__dict__.items()}


class RubricError(Exception):
    pass


def _paths(cell: str) -> tuple[str, ...]:
    return tuple(re.findall(r"`([^`]+)`", cell))


def parse(text: str) -> list[Row]:
    rows: list[Row] = []
    criterion = ""
    in_table = False
    for n, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            criterion = re.sub(r"\s*\(\d+ percent\)\s*$", "", line[3:]).strip()
            in_table = False
            continue
        if not line.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if tuple(cells) == COLUMNS:
            in_table = True
            continue
        if not in_table or set("".join(cells)) <= set("-: "):
            continue
        if len(cells) != len(COLUMNS):
            raise RubricError(f"line {n}: {len(cells)} cells, expected {len(COLUMNS)}")
        rid, bullet, claim, status, feature, code, tests, demo, limit, slide, video = cells
        if status not in STATUSES:
            raise RubricError(f"line {n}: status {status!r} is not one of {STATUSES}")
        rows.append(
            Row(
                id=rid,
                criterion=criterion,
                bullet=bullet,
                claim=claim,
                status=status,
                feature=feature,
                code=_paths(code),
                tests=_paths(tests),
                demo=demo,
                limit=limit,
                slides=tuple(int(x) for x in re.findall(r"\d+", slide)),
                video=tuple(re.findall(r"\d{2}:\d{2}", video)),
            )
        )
    ids = [r.id for r in rows]
    if len(ids) != len(set(ids)):
        raise RubricError("row ids must be unique")
    return rows


def load(path: Path = RUBRIC_MAP) -> list[Row]:
    return parse(path.read_text(encoding="utf-8"))


def stricter(a: str, b: str) -> str:
    """The weaker of two statuses: what may honestly be claimed when two sources disagree."""
    return a if RANK[a] <= RANK[b] else b
