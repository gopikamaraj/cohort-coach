"""Counts-only class profiles and the simulated block summary.

A profile is what the phone's diagnosis produced for the whole class: how many children showed
each error. The schema forbids every other field, so a per-child array, a roll number or a name
is rejected with a 422 before anything is stored.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from functools import cache
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from engine.model import ErrorCode
from services.api.db import Base, ProfileSync, make_engine
from services.api.roles import require

router = APIRouter(prefix="/api", tags=["profiles"])

BLOCK_PATH = Path(__file__).resolve().parents[2] / "data" / "synthetic" / "block_T1T2.json"
# The id the phone makes: "c-" or "sim-" and 10 random hex digits. Nothing a person typed fits.
CLASS_ID = re.compile(r"^(c|sim)-[0-9a-f]{10}$")
ERROR_CODES = {c.value for c in ErrorCode}
UNTRACKED_KEYS = {"ADD-WHOLE-ONES"}


class ProfileIn(BaseModel):
    """Everything a class profile may carry. Any other field is rejected."""

    model_config = ConfigDict(extra="forbid")

    term: str = Field(pattern=r"^T[0-9]{1,2}$")
    form: Literal["A", "B"]
    children_checked: int = Field(ge=0, le=200)
    counts: dict[str, int]
    anchor_wrong_count: int = Field(ge=0, le=200)
    untracked: dict[str, int] = Field(default_factory=dict)
    simulated: bool = False

    @field_validator("counts")
    @classmethod
    def _counts_are_error_counts(cls, v: dict[str, int]) -> dict[str, int]:
        if set(v) - ERROR_CODES:
            raise ValueError("counts may only name the tracked error codes")
        if any(n < 0 or n > 200 for n in v.values()):
            raise ValueError("a count must be between 0 and 200")
        return v

    @field_validator("untracked")
    @classmethod
    def _untracked_names(cls, v: dict[str, int]) -> dict[str, int]:
        if set(v) - UNTRACKED_KEYS or any(n < 0 or n > 200 for n in v.values()):
            raise ValueError("untracked may only hold known pattern names and counts")
        return v

    @model_validator(mode="after")
    def _no_count_exceeds_the_class(self) -> ProfileIn:
        too_big = [c for c, n in self.counts.items() if n > self.children_checked]
        if too_big or self.anchor_wrong_count > self.children_checked:
            raise ValueError("a count cannot exceed the number of children checked")
        return self


@cache
def _factory() -> sessionmaker[Session]:
    engine = make_engine()
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    with _factory()() as s:
        yield s


SESSION = Depends(get_session)


@router.post("/classes/{class_id}/profile", dependencies=[Depends(require("profile.sync"))])
def post_profile(class_id: str, body: ProfileIn, db: Session = SESSION) -> dict[str, Any]:
    if not CLASS_ID.match(class_id):
        raise HTTPException(422, "The class id must be the random id the app made for this class.")
    row = db.execute(
        select(ProfileSync).where(ProfileSync.class_id == class_id, ProfileSync.term == body.term)
    ).scalar_one_or_none()
    values = {
        "form": body.form,
        "children_checked": body.children_checked,
        "counts": body.counts,
        "anchor_wrong_count": body.anchor_wrong_count,
        "untracked": body.untracked,
        "simulated": body.simulated,
    }
    if row is None:
        db.add(ProfileSync(class_id=class_id, term=body.term, **values))
    else:
        for k, v in values.items():
            setattr(row, k, v)
    db.commit()
    return {"stored": True, "class_id": class_id, "term": body.term}


@router.get("/demo/block")
def demo_block() -> dict[str, Any]:
    """A summary of the simulated block: counts per error, nothing about any child."""
    block = json.loads(BLOCK_PATH.read_text(encoding="utf-8"))
    terms: dict[str, Any] = {}
    for term, data in block["terms"].items():
        totals = {code: 0 for code in sorted(ERROR_CODES)}
        checked = 0
        for rec in data["classes"].values():
            checked += rec["children_checked"]
            for code, n in rec["counts"].items():
                totals[code] += n
        terms[term] = {
            "classes": len(data["classes"]),
            "children_checked": checked,
            "children_showing": totals,
            "form": data["form_label"],
        }
    return {
        "simulated": True,
        "label": block["label"],
        "block_id": block["block_id"],
        "grade": block["grade"],
        "schools": len(block["schools"]),
        "classes": len(block["classes"]),
        "terms": terms,
        "data_hash": block["data_hash"],
    }
