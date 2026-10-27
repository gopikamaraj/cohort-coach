"""What the flows know about a teacher's class, computed by code from class-level counts.

The server holds counts only. For a judge (a demo teacher) the counts come from the simulated
block and every step built from them is labelled simulated. Numbers shown to a teacher are counts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from engine.diagnosis import profile_from_counts
from engine.model import ErrorCode
from services.api.db import ProfileSync, Teacher

BLOCK = Path(__file__).resolve().parents[3] / "data" / "synthetic" / "block_T1T2.json"


@dataclass(frozen=True)
class Summary:
    checked: int
    counts: dict[str, int]  # error code -> children showing it
    track: str | None
    simulated: bool


@cache
def _demo_counts() -> tuple[int, dict[str, int]]:
    block = json.loads(BLOCK.read_text(encoding="utf-8"))
    classes = block["terms"]["T1"]["classes"]
    best = max(classes, key=lambda c: (classes[c]["counts"].get("SUB-SFL", 0), c))
    rec = classes[best]
    return int(rec["children_checked"]), dict(rec["counts"])


def demo_change(error: str) -> tuple[str, int, int, int, int] | None:
    """The simulated demo class's counts for one error in term 1 and term 2, from the synthetic
    block (what a judge sees in My result). None if the block has no second term for that class."""
    block = json.loads(BLOCK.read_text(encoding="utf-8"))
    t1 = block["terms"]["T1"]["classes"]
    best = max(t1, key=lambda c: (t1[c]["counts"].get("SUB-SFL", 0), c))
    t2 = block["terms"].get("T2", {}).get("classes", {})
    if best not in t2:
        return None
    a, b = t1[best], t2[best]
    return (
        error,
        int(a["counts"].get(error, 0)),
        int(a["children_checked"]),
        int(b["counts"].get(error, 0)),
        int(b["children_checked"]),
    )


def summary(db: Session, teacher: Teacher) -> Summary | None:
    if teacher.judge:
        checked, counts = _demo_counts()
        simulated = True
    elif teacher.class_id:
        row = db.execute(
            select(ProfileSync)
            .where(ProfileSync.class_id == teacher.class_id)
            .order_by(ProfileSync.term.desc())
        ).scalars().first()  # fmt: skip
        if row is None:
            return None
        checked, counts, simulated = row.children_checked, dict(row.counts), row.simulated
    else:
        return None
    profile = profile_from_counts(
        checked, {ErrorCode(k): v for k, v in counts.items() if k in ErrorCode._value2member_map_}
    )
    return Summary(checked, counts, profile.track.value if profile.track else None, simulated)
