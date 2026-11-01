"""The pilot class's sheets, entered in Enter check: the first sheet read by call 8, the rest filled
from the answer file. Every route answers 404 unless ALL of these hold: PILOT_DEMO=1 on this
machine, the folder and manifest exist with a confirmed consent note, and the answer file is made.
A deployment without that folder (the hosted app) therefore has nothing here, and the screen shows
nothing.

Nothing here is cached: images and answers go out with `Cache-Control: no-store`. The only
network call is call 8, for the one sheet the teacher selects (the same call the product makes).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ai.calls.c08_answer_reading import read_sheet
from ai.client import BudgetExceeded, CallContext
from services.api.practice import AI_CONTEXT
from services.api.profiles import SESSION
from services.demo.api import MAX_UPLOAD, _model_image, ai_reads_cap
from services.papers import keys
from services.papers.models import PaperRow
from services.pilot_demo import answers as ans
from services.pilot_demo import config as cfg

NO_STORE = {
    "Cache-Control": "no-store, max-age=0",
    "Pragma": "no-cache",
    "X-Content-Type-Options": "nosniff",
}


_reads = {"n": 0}  # call 8 reads made by this server process: the cap is per run, not per person


def _gate() -> None:
    st = cfg.status()
    if not st.enabled:
        detail: dict[str, Any] = {
            "pilot": False,
            "show": st.show,
            "reason": st.reason if st.show else "",
        }
        raise HTTPException(404, detail)


router = APIRouter(prefix="/api/pilot-data", tags=["pilot-data"])


def _doc() -> ans.AnswerFile:
    return ans.AnswerFile.model_validate_json(
        (cfg.folder() / "pilot_answers.json").read_text(encoding="utf-8")
    )


def _klass(doc: ans.AnswerFile, code: str) -> ans.ClassOut:
    out = next((c for c in doc.classes if c.class_code == code), None)
    if out is None or not cfg.CLASS_RE.match(code):
        raise HTTPException(404, "No such class.")
    return out


def _sheet_path(code: str, roll: int) -> Path:
    base = (cfg.folder() / "sheets").resolve()
    path = (base / f"{code}-roll{roll:02d}.jpg").resolve()
    if base not in path.parents or not path.is_file():
        raise HTTPException(404, "No such sheet.")
    return path


@router.get("/manifest")
def manifest(_: None = Depends(_gate)) -> Response:  # noqa: B008
    doc = _doc()
    mf = cfg.load_manifest()
    classes = []
    for c in doc.classes:
        rolls = []
        for s in c.sheets:
            has_image = s.file is not None and (cfg.folder() / "sheets" / s.file).is_file()
            rolls.append(
                {
                    "roll": s.roll,
                    "status": s.status,
                    "has_image": has_image,
                    "in_answer_file": s.status == "entered",
                }
            )
        classes.append(
            {
                "class_code": c.class_code,
                "teacher_label": c.teacher_label,
                "strength": c.strength,
                "test_date": c.test_date,
                "rolls": rolls,
                # the on-phone error finder knows the printed dictation numbers only
                "dictation_override": bool((mf.klass(c.class_code) or mf.classes[0]).dictation),
            }
        )
    body = {
        "pilot": True,
        "banner": cfg.BANNER,
        "test": {k: doc.test[k] for k in ("name", "form", "kind", "date", "paper_version")},
        "classes": classes,
        "ai_reads": _reads["n"],
        "ai_reads_cap": ai_reads_cap(),
    }
    return Response(_json(body), media_type="application/json", headers=NO_STORE)


@router.get("/sheet/{class_code}/{roll}")
def sheet(class_code: str, roll: int, _: None = Depends(_gate)) -> Response:  # noqa: B008
    if not cfg.CLASS_RE.match(class_code) or not 1 <= roll <= 99:
        raise HTTPException(404, "No such sheet.")
    path = _sheet_path(class_code, roll)
    return Response(path.read_bytes(), media_type="image/jpeg", headers=NO_STORE)


@router.post("/read")
def read(
    class_code: str = Form(...),
    roll: int = Form(..., ge=1, le=99),
    image: UploadFile | None = File(default=None),  # noqa: B008
    paper_id: str | None = Form(default=None, pattern=r"^P-[0-9a-f]{12}$"),
    _: None = Depends(_gate),  # noqa: B008
    db: Session = SESSION,
    ctx: CallContext = AI_CONTEXT,
) -> Response:
    """Read ONE sheet with call 8: the picture she picked from the folder, or one she uploads."""
    doc = _doc()
    out = _klass(doc, class_code)
    if image is not None:
        data = image.file.read(MAX_UPLOAD + 1)
        if not data or len(data) > MAX_UPLOAD:
            raise HTTPException(413, "That image was empty or too large.")
    else:
        data = _sheet_path(class_code, roll).read_bytes()
    if _reads["n"] >= ai_reads_cap():
        raise HTTPException(
            429, {"message": f"This demo has used its {ai_reads_cap()} AI reads. Use Auto-fill."}
        )
    # read with the key of the paper chosen in Enter check; the folder's own form only without one
    row = db.get(PaperRow, paper_id) if paper_id else None
    if paper_id and row is None:
        raise HTTPException(404, "No such paper.")
    if row is not None:
        form = keys.form_of(row.body, row.check_code)
    else:
        klass = cfg.load_manifest().klass(class_code)
        assert klass is not None
        form = cfg.read_form_for(klass, cfg.load_manifest().test)
    b64, media = _model_image(data)
    try:
        outcome = read_sheet(b64, media, form, context=ctx)
    except BudgetExceeded as exc:
        raise HTTPException(503, {"message": "AI reading is paused. Type the answers."}) from exc
    if outcome is None:
        raise HTTPException(503, {"message": "Could not read this sheet. Type the answers."})
    _reads["n"] += 1
    body = {
        "source": "ai",
        "label": cfg.LABEL_AI,
        "banner": cfg.BANNER,
        "class_code": out.class_code,
        "roll": roll,
        "cells": [
            {"text": c.text, "status": c.status, "confidence": c.confidence} for c in outcome.cells
        ],
        "ai_reads": _reads["n"],
        "ai_reads_cap": ai_reads_cap(),
    }
    return Response(_json(body), media_type="application/json", headers=NO_STORE)


class AutofillIn(BaseModel):
    class_code: str = Field(pattern=r"^[A-Za-z0-9]{1,8}$")
    skip: list[int] = Field(default_factory=list, max_length=100)


@router.post("/autofill")
def autofill(body: AutofillIn, _: None = Depends(_gate)) -> Response:  # noqa: B008
    """Every other roll number's data from the answer file. No AI call, nothing fake."""
    out = _klass(_doc(), body.class_code)
    skip = set(body.skip)
    sheets = [
        {
            "roll": s.roll,
            "cells": ans.cells_of(s),
            "verified": s.verified,
            "source": s.source,
            "label": cfg.LABEL_FILE,
            "has_image": s.file is not None,
        }
        for s in out.sheets
        if s.status == "entered" and s.roll not in skip
    ]
    payload = {
        "class_code": out.class_code,
        "label": cfg.LABEL_FILE,
        "banner": cfg.BANNER,
        "sheets": sheets,
        "no_sheet": [s.roll for s in out.sheets if s.status == "no_sheet" and s.file is None],
        "unread": [s.roll for s in out.sheets if s.status == "no_sheet" and s.file is not None],
        "absent": [s.roll for s in out.sheets if s.status == "absent"],
    }
    return Response(_json(payload), media_type="application/json", headers=NO_STORE)


def _json(obj: Any) -> bytes:
    import json

    return json.dumps(obj).encode("utf-8")
