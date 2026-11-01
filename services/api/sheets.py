"""Read an answer-sheet photo (call 8) and hand the reads back to the teacher's phone.

The photo is read into memory, sent to the model, and dropped: it is never written to disk (the
size cap sits below the 1 MB at which the framework would spool an upload to a temporary file),
never logged, never returned. Nothing about the reads is stored here either: they go back to
the phone, where the teacher reviews and corrects them. The audit row for the call holds
metadata only. Expected answers are used after reading, to decide what needs a second look;
the model never sees them.
"""

from __future__ import annotations

import base64
import re
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from ai.calls.c08_answer_reading import read_sheet
from ai.client import BudgetExceeded, CallContext
from engine.forms import PILOT_FORMS
from services.api.practice import AI_CONTEXT
from services.api.profiles import SESSION
from services.api.ratelimit import RateLimiter
from services.api.roles import require
from services.papers import keys
from services.papers.models import PaperRow

router = APIRouter(
    prefix="/api/sheets",
    tags=["sheets"],
    dependencies=[Depends(require("check.read_sheets"))],
)

MAX_IMAGE_BYTES = 800_000  # a downscaled sheet is about 80 KB; stays under the 1 MB spool limit
_MAGIC = ((b"\xff\xd8\xff", "image/jpeg"), (b"\x89PNG\r\n\x1a\n", "image/png"))


def _media_type(data: bytes) -> str | None:
    for magic, media in _MAGIC:
        if data.startswith(magic):
            return media
    return None


_LIMIT_READ = RateLimiter("sheets_read", 30)  # each call reads one photo with a paid model


@router.post("/read", dependencies=[Depends(_LIMIT_READ)])
def read(
    request: Request,
    image: UploadFile = File(...),  # noqa: B008
    form: str = Form("A"),
    sha256: str = Form(""),
    db: Session = SESSION,
    ctx: CallContext = AI_CONTEXT,
) -> dict[str, Any]:
    # `form` is a paper id (P-...), or one of the built-in forms the older checks used
    if form in PILOT_FORMS:
        the_form = PILOT_FORMS[form]
    else:
        row = db.get(PaperRow, form) if re.fullmatch(r"P-[0-9a-f]{12}", form) else None
        if row is None:
            raise HTTPException(422, "Unknown paper.")
        the_form = keys.form_of(row.body, row.check_code)
    file_hash = sha256.lower() if re.fullmatch(r"[0-9a-fA-F]{64}", sha256) else None
    if int(request.headers.get("content-length") or 0) > MAX_IMAGE_BYTES + 50_000:
        raise HTTPException(413, "That photo is too large. Take it again.")
    data = image.file.read(MAX_IMAGE_BYTES + 1)
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "That photo was empty or too large. Take it again.")
    media = _media_type(data)
    if media is None:
        raise HTTPException(422, "That file is not a photo (JPEG or PNG).")
    try:
        outcome = read_sheet(
            base64.b64encode(data).decode(), media, the_form, context=ctx, file_sha256=file_hash
        )
    except BudgetExceeded as exc:
        raise HTTPException(503, {"needs_typing": True, "message": "Reading is paused."}) from exc
    finally:
        del data
    if outcome is None:
        raise HTTPException(503, {"needs_typing": True, "message": "Could not read this sheet."})
    return {
        "form": form,
        "retried": outcome.retried,
        "header": outcome.header.model_dump() if outcome.header else None,
        "cells": [{"text": c.text, "status": c.status} for c in outcome.cells],
    }
