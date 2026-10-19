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
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from ai.calls.c08_answer_reading import read_sheet
from ai.client import BudgetExceeded, CallContext
from engine.forms import PILOT_FORMS
from services.api.practice import AI_CONTEXT

router = APIRouter(prefix="/api/sheets", tags=["sheets"])

MAX_IMAGE_BYTES = 800_000  # a downscaled sheet is about 80 KB; stays under the 1 MB spool limit
_MAGIC = ((b"\xff\xd8\xff", "image/jpeg"), (b"\x89PNG\r\n\x1a\n", "image/png"))


def _media_type(data: bytes) -> str | None:
    for magic, media in _MAGIC:
        if data.startswith(magic):
            return media
    return None


@router.post("/read")
def read(
    request: Request,
    image: UploadFile = File(...),  # noqa: B008
    form: str = Form("A"),
    ctx: CallContext = AI_CONTEXT,
) -> dict[str, Any]:
    if form not in PILOT_FORMS:
        raise HTTPException(422, "Unknown form.")
    if int(request.headers.get("content-length") or 0) > MAX_IMAGE_BYTES + 50_000:
        raise HTTPException(413, "That photo is too large. Take it again.")
    data = image.file.read(MAX_IMAGE_BYTES + 1)
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, "That photo was empty or too large. Take it again.")
    media = _media_type(data)
    if media is None:
        raise HTTPException(422, "That file is not a photo (JPEG or PNG).")
    try:
        outcome = read_sheet(base64.b64encode(data).decode(), media, PILOT_FORMS[form], context=ctx)
    except BudgetExceeded as exc:
        raise HTTPException(503, {"needs_typing": True, "message": "Reading is paused."}) from exc
    finally:
        del data
    if outcome is None:
        raise HTTPException(503, {"needs_typing": True, "message": "Could not read this sheet."})
    return {
        "form": form,
        "retried": outcome.retried,
        "cells": [{"text": c.text, "status": c.status} for c in outcome.cells],
    }
