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


class TrackPart(BaseModel):
    """Call 5, one request: one voice lesson (day 1 to 6) or the model-lesson script (day 0).
    The script holds slots and child-mistake tags; code fills and checks them."""

    kind: Literal["lesson", "model_lesson"]
    day: int = Field(ge=0, le=6)
    script: str = Field(min_length=1, max_length=12000)


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


class SheetHeader(BaseModel):
    """What is printed or written in the sheet's header: the class code and the roll number."""

    class_code: str | None = None
    roll_number: int | None = None
    confidence: float = 0.0


class SheetRead(BaseModel):
    """Call 8: digits a child wrote. Never told the expected answers."""

    reads: list[str]
    confidences: list[float]
    header: SheetHeader | None = None


class PilotSheetScan(BaseModel):
    """Call 15 (offline, pilot demo ingest): the printed header, and where a person's name is."""

    class_code: str | None = None
    roll: int | None = None
    name_present: bool
    box1_words: str | None = None  # number words a child wrote in dictation box 1
    box2_words: str | None = None
    name_boxes: list[list[float]] = []  # [x0, y0, x1, y1] as fractions of the image, 0 to 1


class ReadPaperItem(BaseModel):
    """One printed question, as printed. No handwriting, no name."""

    n: int
    operation: Literal["dictate", "add", "subtract", "other"]
    a: int | None = None  # first number printed (None for a dictated item: the number is spoken)
    b: int | None = None
    prompt_text: str = ""
    box_pct: list[float] = []  # answer box [x, y, w, h] as a percentage of the page
    printed_answer: str | None = None  # only if the sheet prints a key; never handwriting
    unsure: bool = False


class PaperRead(BaseModel):
    """Call 16 (Papers page): what is printed on a paper, read from a blank paper, a key or an
    answered sheet. The caller computes every answer; this never carries one it worked out."""

    form_letter: str | None = None
    check_code: str | None = None
    class_code: str | None = None
    language: Literal["en", "hi", "ta", "other"] = "en"
    contains_handwritten_answers: bool = False
    items: list[ReadPaperItem] = []


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


ChatClassLabel = Literal[
    "content_question",
    "child_specific",
    "safety_or_welfare",
    "discipline_or_personal",
    "off_topic",
    "unclear",
]


class ChatClass(BaseModel):
    """Call 12: what kind of question a teacher asked her mentor. Low confidence means unclear."""

    label: ChatClassLabel
    confidence: float = Field(ge=0.0, le=1.0)


class ChatCitation(BaseModel):
    source_id: str = Field(max_length=40)
    quote: str = Field(max_length=300)  # a verbatim sentence or phrase from that source


class ChatReply(BaseModel):
    """Call 13: a short reply from approved sources only, or no answer and why."""

    answer: str | None = Field(default=None, max_length=1500)
    no_answer_reason: str | None = Field(default=None, max_length=200)
    citations: list[ChatCitation] = Field(default_factory=list, max_length=6)


class AssistantCitation(BaseModel):
    # S1, S2 ... for a document passage; R:<id> for a rubric row
    source_id: str = Field(max_length=12)
    quote: str = Field(max_length=300)  # a verbatim sentence or phrase from that source


class AssistantAnswer(BaseModel):
    """Call 14: an answer from the offered sources only, or no answer and why. The model writes the
    answer and chooses which rubric rows it rests on; code derives every status label, the
    how-to-check line and the limits from those rows."""

    answer: str | None = Field(default=None, max_length=1200)
    rubric_rows: list[str] = Field(default_factory=list, max_length=4)
    citations: list[AssistantCitation] = Field(default_factory=list, max_length=6)
    no_answer_reason: str | None = Field(default=None, max_length=200)
    follow_ups: list[str] = Field(
        default_factory=list, max_length=3
    )  # short next questions the pages could answer
