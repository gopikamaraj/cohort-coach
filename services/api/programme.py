"""My programme (where is my cohort, my mentor, my lessons) and the classroom-observation signal.

Counts and choices only: nothing here names another class, teacher or child. A real class that has
not been placed yet gets a plain "waiting" answer. A simulated class (id starts "sim-") is shown a
labelled example placement taken from the simulated block, so judges can see the screen working.
"""

from __future__ import annotations

import json
from collections import Counter
from functools import cache
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from services.api.db import SimObservation
from services.api.profiles import BLOCK_PATH, CLASS_ID, SESSION
from services.practice.content import LANGS

router = APIRouter(prefix="/api", tags=["programme"])

TRACKS = {"PV-HEARD", "ADD-NOCARRY", "SUB-SFL", "SUB-NODEC"}
MIN_FOR_SUMMARY = 5  # a figure covering fewer than 5 reports is hidden
DIFFERENCES = (
    "mistakes_differ",
    "too_easy",
    "too_hard",
    "quieter",
    "more_talkative",
    "explained_differently",
)


@cache
def _block() -> dict[str, Any]:
    return json.loads(BLOCK_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


@router.get("/programme/{class_id}")
def programme(class_id: str, track: str | None = Query(None)) -> dict[str, Any]:
    if not CLASS_ID.match(class_id):
        raise HTTPException(422, "Unknown class id.")
    if track is not None and track not in TRACKS:
        raise HTTPException(422, "Unknown track.")
    simulated = class_id.startswith("sim-")
    out: dict[str, Any] = {
        "class_id": class_id,
        "simulated": simulated,
        "placement": {"status": "waiting"},
        "cohort": None,
        # A mentor is chosen after the next check shows whose class fixed the error.
        "mentor": {"status": "after_next_check"},
        # Lessons and the model-lesson script appear once a reviewer has approved the track.
        "lessons": {"status": "not_published", "items": [], "script": None},
    }
    if not simulated:
        return out
    block = _block()
    wanted = [a for a in block["assignments"] if track is None or a["track"] == track]
    placed = {cid for c in block["cohorts"] for cid in c["class_ids"]}
    # prefer an example that really sits in a cohort, so the screen shows one
    pick = next((a for a in wanted if a["class_id"] in placed), wanted[0] if wanted else None)
    if pick is None:
        return out
    cohort = next((c for c in block["cohorts"] if pick["class_id"] in c["class_ids"]), None)
    out["placement"] = {
        "status": pick["arm"],  # this_term | next_term
        "track": pick["track"],
        "version": pick["version"],
        "reason": pick["reason"],
    }
    if cohort is not None:
        out["cohort"] = {
            "size": cohort["size"],
            "undersized": cohort["undersized"],
            "mentor_slot": cohort["mentor_slot"],
            "cross_block": cohort["cross_block"],
        }
    return out


class ObservationIn(BaseModel):
    """What a teacher may say about the simulation after trying it in class. Choices only."""

    model_config = ConfigDict(extra="forbid")

    scenario: Literal["PV-HEARD", "ADD-NOCARRY", "SUB-SFL", "SUB-NODEC"]
    language: Literal["en", "hi", "ta"]
    likeness: Literal["like", "some", "not_like"]
    differences: list[Literal[DIFFERENCES]] = Field(default_factory=list, max_length=6)  # type: ignore[valid-type]


@router.post("/practice/observations")
def add_observation(body: ObservationIn, db=SESSION) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    assert body.language in LANGS
    db.add(
        SimObservation(
            scenario=body.scenario,
            language=body.language,
            likeness=body.likeness,
            differences=sorted(set(body.differences)),
        )
    )
    db.commit()
    return {"stored": True}


@router.get("/practice/observations/summary")
def observation_summary(db=SESSION) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    rows = list(db.execute(select(SimObservation)).scalars())
    if len(rows) < MIN_FOR_SUMMARY:
        return {"hidden": True, "reason": f"fewer than {MIN_FOR_SUMMARY} reports"}
    likeness = Counter(r.likeness for r in rows)
    diffs: Counter[str] = Counter()
    for r in rows:
        diffs.update(r.differences)
    return {
        "hidden": False,
        "n": len(rows),
        "likeness": {k: likeness.get(k, 0) for k in ("like", "some", "not_like")},
        "differences": {k: diffs.get(k, 0) for k in DIFFERENCES},
    }
