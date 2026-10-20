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
