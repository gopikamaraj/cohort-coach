"""The pilot answer file (pilot_answers.json): the test, its questions, and every child's answers.

Same family as the Demo Studio's reads.json (`source` says which); the loader stays the demo's.
Every judgement here is the engine's: `classify` and `diagnose_child` mark each answer and apply
the 2-item rule, `class_profile` gives the class counts. No arithmetic is written here.
Child-level fields live only in this git-ignored file; the class summary is counts only.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, Field

from engine.bugs import classify, correct_answer, error_answers, probes
from engine.diagnosis import class_profile, diagnose_child
from engine.model import Form, ItemType, Mark, Reading
from engine.normalize import normalize_answer
from services.pilot_demo.config import PilotClass, PilotTest, read_form_for

CONFIDENCE_BAR = 0.8  # the bar call 8 uses
SKILLS = {
    ItemType.DICTATION: ("Place value", "Write a dictated number in digits"),
    ItemType.ADD_CARRY: ("Addition", "Add two-digit numbers with carrying"),
    ItemType.SUB_ANCHOR: ("Subtraction", "Subtract without borrowing"),
    ItemType.SUB_BORROW: ("Subtraction", "Subtract with borrowing"),
}
TYPE = {
    ItemType.DICTATION: "dictation",
    ItemType.ADD_CARRY: "add",
    ItemType.SUB_ANCHOR: "subtract",
    ItemType.SUB_BORROW: "subtract",
}


class Answer(BaseModel):
    q: int
    given: str  # digits as written; "" when blank or unreadable
    correct: bool | None  # None for a blank or unreadable box
    status: Literal["answered", "blank", "unreadable"]
    confidence: float = Field(ge=0, le=1)
    flag: Literal["smudged", "crossed_out"] | None = None
    matched_bug: str | None = None
    matched_bugs: list[str] = Field(default_factory=list)


class Summary(BaseModel):
    score: int
    flagged_errors: list[str]
    single_item_probes: list[str]


class Sheet(BaseModel):
    roll: int
    file: str | None
    status: Literal["entered", "absent", "no_sheet"]
    source: Literal["truth", "ai", "truth+ai"] | None = None
    verified: bool = False
    image_hash: str | None = None
    answers: list[Answer] = Field(default_factory=list)
    summary: Summary | None = None


class ClassSummary(BaseModel):
    counts: dict[str, int]
    children_paired: int
    absent: int
    no_sheet: int


class ClassOut(BaseModel):
    class_code: str
    teacher_label: str
    strength: int
    test_date: str
    sheets: list[Sheet]
    class_summary: ClassSummary


class AnswerFile(BaseModel):
    demo: bool = True  # lets the Demo Studio's loader accept it
    source: Literal["pilot"] = "pilot"
    label: str = "Pilot answer file: real sheets, roll numbers only. Never commit."
    test: dict[str, Any]
    classes: list[ClassOut]


def question(form: Form, n: int, variants: Mapping[str, int]) -> dict[str, Any]:
    item = form.items[n]
    competency, skill = SKILLS[item.type]
    prompt = f"Write the number {item.a}" if item.type is ItemType.DICTATION else _sum_text(item)
    return {
        "no": item.n,
        "text": prompt,
        "type": TYPE[item.type],
        "competency": competency,
        "skill": skill,
        "answer_format": "number",
        "correct_answer": correct_answer(item),
        "class_variants": dict(variants),
        "options": None,
        "error_probes": [c.value for c in probes(item)],
        "expected_wrong": {c.value: sorted(a) for c, a in error_answers(item).items()},
    }


def _sum_text(item: Any) -> str:
    sign = "+" if item.type is ItemType.ADD_CARRY else "-"
    return f"{item.a} {sign} {item.b}"


def build_test(
    classes: Sequence[PilotClass], test: PilotTest, name: str, date: str | None, version: str
) -> dict:
    base = read_form_for(classes[0], test)
    questions = []
    for n, item in enumerate(base.items):
        variants = {
            c.class_code: read_form_for(c, test).items[n].a
            for c in classes
            if item.type is ItemType.DICTATION
        }
        questions.append(question(base, n, variants))
    return {
        "name": name,
        "form": "A",
        "kind": "pre",
        "date": date,
        "paper_version": version,
        "competencies": sorted({q["competency"] for q in questions}),
        "questions": questions,
    }


def reading_of(given: str) -> Reading:
    return normalize_answer(given if given else None)


def mark_answers(
    form: Form, givens: Sequence[str], confidences: Sequence[float], flags: Sequence[str | None]
) -> list[Answer]:
    out: list[Answer] = []
    for item, given, conf, flag in zip(form.items, givens, confidences, flags, strict=True):
        reading = reading_of(given)
        mark = classify(item, reading)
        status: Literal["answered", "blank", "unreadable"] = (
            "blank"
            if mark.kind is Mark.BLANK
            else "unreadable"
            if mark.kind is Mark.UNREADABLE
            else "answered"
        )
        codes = sorted(c.value for c in mark.codes)
        out.append(
            Answer(
                q=item.n,
                given="" if status != "answered" else str(reading),
                correct=None if status != "answered" else mark.kind is Mark.CORRECT,
                status=status,
                confidence=conf,
                flag=flag,  # type: ignore[arg-type]
                matched_bug=codes[0] if codes else None,
                matched_bugs=codes,
            )
        )
    return out


def summarise(form: Form, answers: Sequence[Answer]) -> Summary:
    # the error finder and the 2-item rule use the ten check items only
    ten = answers[: len(form.items)]
    diag = diagnose_child(form, [reading_of(a.given) for a in ten])
    hits: Counter[str] = Counter()
    for a in answers:
        hits.update(a.matched_bugs)
    return Summary(
        score=sum(1 for a in answers if a.correct),
        flagged_errors=sorted(c.value for c in diag.shows),
        single_item_probes=sorted(c for c, n in hits.items() if n == 1),
    )


def class_out(c: PilotClass, sheets: Sequence[Sheet], form: Form) -> ClassOut:
    entered = [s for s in sheets if s.status == "entered"]
    profile = class_profile(
        [
            diagnose_child(form, [reading_of(a.given) for a in s.answers[: len(form.items)]])
            for s in entered
        ]
    )
    return ClassOut(
        class_code=c.class_code,
        teacher_label=c.teacher_label,
        strength=c.strength,
        test_date=c.test_date.isoformat(),
        sheets=list(sheets),
        class_summary=ClassSummary(
            counts={code.value: n for code, n in profile.counts.items()},
            children_paired=len(entered),
            absent=sum(1 for s in sheets if s.status == "absent"),
            no_sheet=sum(1 for s in sheets if s.status == "no_sheet" and s.file is None),
        ),
    )


def cells_of(sheet: Sheet) -> list[dict[str, Any]]:
    """The answers as the Demo Studio's review cells: text, status ok | check | blank."""
    out = []
    for a in sheet.answers:
        if a.status == "blank" and a.confidence >= CONFIDENCE_BAR:
            out.append({"text": "", "status": "blank", "confidence": a.confidence})
        elif a.status != "answered" or a.confidence < CONFIDENCE_BAR or a.flag:
            out.append({"text": a.given, "status": "check", "confidence": a.confidence})
        else:
            out.append({"text": a.given, "status": "ok", "confidence": a.confidence})
    return out
