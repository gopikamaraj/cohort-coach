"""Pydantic output models for the 8 calls. Minimal in P03; each call grows its own in its phase."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Language = Literal["en", "hi", "ta"]


class ChildLine(BaseModel):
    """Call 1: what a simulated child says. The number comes from the engine, never from Claude."""

    text: str = Field(max_length=400)


class MoveLabel(BaseModel):
    """Call 2: one label from the technique's fixed move list."""

    label: str
    confidence: float = Field(ge=0, le=1)


class Quoted(BaseModel):
    point: str
    quote: str


class Feedback(BaseModel):
    """Call 3: two strengths and one thing to try, each quoting her words. No score."""

    strengths: list[Quoted] = Field(min_length=2, max_length=2)
    try_next: Quoted


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
