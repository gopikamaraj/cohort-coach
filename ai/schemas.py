"""Pydantic output models for the 8 calls. Minimal in P03; each call grows its own in its phase."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Language = Literal["en", "hi", "ta"]


class ChildLine(BaseModel):
    """Call 1: what a simulated child says. The number comes from the engine, never from Claude.

    `english` is the subtitle: the same line in English with the same digits (prompt v3).
    """

    text: str = Field(max_length=400)
    english: str = Field(default="", max_length=400)


class PosedProblem(BaseModel):
    """A sum or dictation the teacher poses. Numbers are digits taken from her line."""

    a: int
    op: Literal["-", "+", "dictate"]
    b: int | None = None


class MoveLabel(BaseModel):
    """Call 2: one move from the technique's fixed list (the run narrows move_id to that list)."""

    move_id: str
    addressed_child: str
    posed_problem: PosedProblem | None = None
    confidence: float = Field(ge=0, le=1)


class DemoTeacherTurn(BaseModel):
    """Call 10 (judge mode only): the AI teacher's next move and line in a Watch run."""

    move_id: str
    addressed_child: str
    line: str = Field(max_length=300)


class FeedbackPoint(BaseModel):
    rubric_point: str
    turn_id: int
    quote: str
    comment: str


class TryNext(BaseModel):
    rubric_point: str
    suggestion: str
    quote: str | None = None
    turn_id: int | None = None


class Feedback(BaseModel):
    """Call 3: strengths and one thing to try, each quoting her words. No score."""

    strengths: list[FeedbackPoint] = Field(min_length=1, max_length=2)
    try_next: TryNext


class MethodStep(BaseModel):
    text: str
    sentence_ids: list[int] = Field(min_length=1)


class MethodCard(BaseModel):
    """Call 4: a mentor's method, every step citing sentences she said."""

    title: str
    steps: list[MethodStep] = Field(min_length=1)


class TrackLesson(BaseModel):
    day: int
    script: str
    slots: dict[str, str] = Field(default_factory=dict)


class TrackDraft(BaseModel):
    """Call 5: six lessons and one model-lesson script. Class numbers are slots filled by code."""

    error: str
    language: Language
    lessons: list[TrackLesson]
    model_lesson: str


class Digest(BaseModel):
    """Call 6: themes only; code counts them."""

    themes: list[str]
    assignments: list[int]


class Verdict(BaseModel):
    """Call 7: the output checker's structured verdict."""

    passed: bool
    failed_items: list[str] = Field(default_factory=list)
    reason_short: str
    reason_for_user: str


class SheetRead(BaseModel):
    """Call 8: digits a child wrote. Never told the expected answers."""

    reads: list[str]
    confidences: list[float]


SpriteSlot = Literal[
    "skin", "hair", "cloth_a", "cloth_b", "accent", "item_a", "item_b", "mat", "ink", "none"
]


class SpritePart(BaseModel):
    """One shape of an item. Integers only; colours are palette slot names, never hex."""

    shape: Literal["circle", "ellipse", "rect", "line", "polyline", "polygon", "path"]
    cx: int | None = None
    cy: int | None = None
    r: int | None = None
    rx: int | None = None
    ry: int | None = None
    x: int | None = None
    y: int | None = None
    width: int | None = None
    height: int | None = None
    x1: int | None = None
    y1: int | None = None
    x2: int | None = None
    y2: int | None = None
    points: str | None = Field(default=None, max_length=200)
    d: str | None = Field(default=None, max_length=400)
    fill: SpriteSlot | None = None
    stroke: SpriteSlot | None = None
    stroke_width: int | None = None
    transform: str | None = Field(default=None, max_length=80)


class SpriteItemDraft(BaseModel):
    """Call 11 (offline authoring): a draft item spec. Never shown to a teacher before the gates,
    a coach and an officer."""

    id: str = Field(max_length=32)
    alt_en: str = Field(max_length=60)
    topics: list[str] = Field(max_length=6)
    parts: list[SpritePart] = Field(max_length=14)
    note: str = Field(default="", max_length=200)
