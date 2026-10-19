"""Call 8, answer reading: a vision model transcribes the digits a child wrote, blind.

The model is told only how many boxes there are: never the questions, the operands or the
expected answers. Code then does the judging: digits are normalised (Devanagari and Tamil
digits), a read is "ok" only if it is confident and is one of the answers the item recognises
(the correct one, a known error answer or a known untracked pattern); everything else is marked
"check" for the teacher. A read the code cannot trust is never filled in silently. If the first
try breaks the format a stronger model tries once; if that fails too the caller is told to type.

The photo is held in memory for this call only and is never stored or logged.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from ai import config
from ai.client import CallContext, CallInput, CallResult, run_call
from ai.schemas import SheetRead
from ai.validators import ValidatorResult, Violation
from engine.bugs import answer_codes, correct_answer, untracked_signatures
from engine.model import Form
from engine.normalize import normalize_answer

CONFIDENCE_BAR = 0.8
MAX_READ_CHARS = 12
Status = Literal["ok", "check", "blank"]


@dataclass(frozen=True)
class Cell:
    text: str  # digits as the teacher would type them; "" when nothing usable was read
    confidence: float
    status: Status


@dataclass(frozen=True)
class SheetOutcome:
    cells: list[Cell]
    retried: bool
    runs: list[CallResult]


def plausible_answers(form: Form, n: int) -> set[str]:
    """What item n can legitimately be answered with: correct, known error, known untracked."""
    item = form.items[n]
    answers = {correct_answer(item), *answer_codes(item)}
    for numbers in untracked_signatures(item).values():
        answers |= set(numbers)
    return {str(a) for a in answers}


def classify(form: Form, reads: list[str], confidences: list[float]) -> list[Cell]:
    cells: list[Cell] = []
    for i, (raw, conf) in enumerate(zip(reads, confidences, strict=True)):
        reading = normalize_answer(raw)
        conf = max(0.0, min(1.0, conf))
        if reading == "blank":
            cells.append(Cell("", conf, "blank" if conf >= CONFIDENCE_BAR else "check"))
        elif reading == "unreadable":
            cells.append(Cell("", conf, "check"))
        else:
            text = str(reading)
            ok = conf >= CONFIDENCE_BAR and text in plausible_answers(form, i)
            cells.append(Cell(text, conf, "ok" if ok else "check"))
    return cells


def _validators(n: int):  # type: ignore[no-untyped-def]
    def check(out: object) -> list[ValidatorResult]:
        assert isinstance(out, SheetRead)
        problems: list[Violation] = []
        if len(out.reads) != n or len(out.confidences) != n:
            problems.append(Violation("wrong_box_count"))
        if any(len(r) > MAX_READ_CHARS for r in out.reads):
            problems.append(Violation("read_too_long"))
        if any(not 0.0 <= c <= 1.0 for c in out.confidences):
            problems.append(Violation("confidence_out_of_range"))
        return [ValidatorResult("sheet_shape", tuple(problems))]

    return check


def _empty(n: int) -> SheetRead:
    return SheetRead(reads=[""] * n, confidences=[0.0] * n)


def read_sheet(
    image_b64: str,
    media_type: str,
    form: Form,
    *,
    context: CallContext | None = None,
) -> SheetOutcome | None:
    """Read one sheet. Returns None when neither model gave a usable answer (she types)."""
    n = len(form.items)
    base = context or CallContext()
    payload = CallInput(trusted={"boxes": n}, images=[(media_type, image_b64)])
    runs: list[CallResult] = []
    for retried, model in ((False, base.model), (True, config.model_for("MODEL_READ_RETRY"))):
        ctx = replace(base, validators=_validators(n), fallback=lambda: _empty(n), model=model)
        run = run_call(8, payload, context=ctx)
        runs.append(run)
        if run.ok and isinstance(run.output, SheetRead):
            return SheetOutcome(
                classify(form, run.output.reads, run.output.confidences), retried, runs
            )
    return None
