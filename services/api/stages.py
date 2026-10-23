"""Stage of breakdown for a class: counts per (error, stage), from reads held for this request only.

The phone sends one row of answers per child, with the teacher's tags. Nothing is stored or
logged: the rows are reduced to class counts by `engine.stages` and dropped. The response holds no
per-child data. A stage is always "most likely", and carries a one-minute probe.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from engine.forms import PILOT_FORMS
from engine.model import Reading
from engine.stages import StageResult, class_counts, classify_child
from services.api.roles import require
from services.api.strings import text
from services.practice.content import LANGS

router = APIRouter(
    prefix="/api", tags=["stages"], dependencies=[Depends(require("check.read_sheets"))]
)

MAX_CHILDREN = 300
PROBE_KEY = {
    "Core": "stage.probe.core",
    "Input (test)": "stage.probe.input_test",
    "Output": "stage.probe.output",
    "Input (teaching)": "stage.probe.input_teaching",
}


class ChildIn(BaseModel):
    answers: list[int | Literal["blank", "unreadable"]]
    missed_teaching: bool = False  # the whole sheet
    missed_concepts: list[Literal["place_value", "addition", "subtraction"]] = Field(
        default_factory=list
    )
    unreadable: int = Field(default=0, ge=0, le=10)
    two_answers: int = Field(default=0, ge=0, le=10)

    @field_validator("answers")
    @classmethod
    def _ten(cls, v: list[int | str]) -> list[int | str]:
        if len(v) != 10:
            raise ValueError("ten answers per child")
        if any(isinstance(a, int) and not 0 <= a <= 999_999 for a in v):
            raise ValueError("answer out of range")
        return v


class StagesIn(BaseModel):
    form: str
    language: str = "en"
    children: list[ChildIn] = Field(min_length=1, max_length=MAX_CHILDREN)


@router.post("/stages")
def post_stages(body: StagesIn) -> dict[str, Any]:
    form = PILOT_FORMS.get(body.form)
    if form is None:
        raise HTTPException(422, "The form must be A or B.")
    if body.language not in LANGS:
        raise HTTPException(422, f"language must be one of {', '.join(LANGS)}")
    results: list[StageResult] = []
    for child in body.children:
        readings: list[Reading] = list(child.answers)
        unreadable = child.unreadable + sum(1 for a in child.answers if a == "unreadable")
        results.append(
            classify_child(
                form,
                readings,
                missed_teaching=child.missed_teaching,
                missed_concepts=child.missed_concepts,
                unreadable=unreadable,
                two_answers=child.two_answers,
            )
        )
    counts = class_counts(results)
    by_signature = sorted(counts.by_signature.items(), key=lambda kv: (-kv[1], kv[0][0]))
    by_stage = sorted(counts.by_stage.items(), key=lambda kv: (-kv[1], kv[0].value))
    return {
        "checked": counts.checked,
        "missed_teaching": counts.missed_teaching,
        "missed_by_concept": counts.missed_by_concept,
        "not_attempted": counts.not_attempted,
        "by_signature": [
            {"code": code, "stage": stage.value, "n": n} for (code, stage), n in by_signature
        ],
        "by_stage": [{"stage": stage.value, "n": n} for stage, n in by_stage],
        "probes": {s.value: text(body.language, PROBE_KEY[s.value]) for s, _ in by_stage},
        "note": text(body.language, "stage.note"),
    }
