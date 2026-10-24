"""Pre-test answer sheets: consent gate, signed upload, duplicate skip, reading, retention.

A sheet photo goes from the coordinator's phone straight to the private sheets bucket by a
short-lived signed URL; the API never holds the file while it is uploaded. After it is stored, the
existing call 8 reads it blind. What the read adds up to is kept as class-level counts only; the
per-box reads are dropped. A sheet with any unsure box, or in a format call 8 cannot take (HEIC,
PDF), is marked "needs a second look" and adds nothing to the counts: pilot mode has no page for
fixing reads, so those sheets wait for hand-keying with scripts/pilot_import.
"""

from __future__ import annotations

import base64
import uuid
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ai.calls.c08_answer_reading import read_sheet
from ai.client import BudgetExceeded, CallContext
from engine.diagnosis import diagnose_child
from engine.forms import FORM_A
from engine.normalize import normalize_answer
from services.api.db import PilotClassCount, PilotSheet
from services.pilot.common import (
    CLASS_CODE,
    CODE,
    CONSENT_REF,
    audit,
    check_code,
    retention_days,
)
from services.pilot.storage import BlobStore

MIME_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/heic": "heic",
    "image/heif": "heic",
    "application/pdf": "pdf",
}
READABLE = {"image/jpeg", "image/png"}  # what call 8 takes; the rest need a second look
MAX_UPLOAD_BYTES = 8_000_000
MAX_READ_BYTES = 4_500_000  # the model's image limit is 5 MB
PUT_EXPIRES_S = 300
GET_EXPIRES_S = 120
DONE = ("stored", "read", "needs_look")


class InitIn(BaseModel):
    model_config = ConfigDict(extra="forbid")  # a stray "child_name" field is refused, not stored

    school_code: str = Field(max_length=24)
    class_code: str = Field(max_length=12)
    teacher_ref: str = Field(max_length=24)
    consent_confirmed: bool = False
    consent_ref: str = Field(default="", max_length=60)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bytes: int = Field(ge=1, le=MAX_UPLOAD_BYTES)
    mime: str = Field(max_length=40)


def init_upload(
    db: Session, store: BlobStore, actor: str, body: InitIn, *, now: datetime | None = None
) -> dict[str, Any]:
    """Check the gate, then either say "already stored" or hand back a signed upload URL."""
    if not body.consent_confirmed or not CONSENT_REF.match(body.consent_ref.strip()):
        raise HTTPException(403, "Confirm that school consent is on file and enter its reference.")
    school = check_code(body.school_code, "school code", CODE)
    klass = check_code(body.class_code, "class", CLASS_CODE)
    teacher = check_code(body.teacher_ref, "teacher code", CODE)
    if body.mime not in MIME_EXT:
        raise HTTPException(422, "Send a JPG, PNG, HEIC or PDF file.")
    purge_expired(db, store, now=now)

    existing = db.execute(
        select(PilotSheet).where(PilotSheet.school_code == school, PilotSheet.sha256 == body.sha256)
    ).scalar_one_or_none()
    if existing is not None and existing.status in DONE:
        return {"duplicate": True, "id": existing.id, "status": existing.status}
    if existing is None:
        sheet_id = uuid.uuid4().hex
        existing = PilotSheet(
            id=sheet_id,
            school_code=school,
            class_code=klass,
            teacher_ref=teacher,
            test_phase="pre",
            object_key=f"sheets/{sheet_id}.{MIME_EXT[body.mime]}",
            sha256=body.sha256,
            bytes=body.bytes,
            mime=body.mime,
            consent_ref=body.consent_ref.strip(),
            uploaded_by=actor,
            status="pending",
        )
        db.add(existing)
    else:  # a retry of an upload that never finished (pending or failed): same row, fresh URL
        existing.status = "pending"
        existing.note = None
        existing.consent_ref = body.consent_ref.strip()
    db.commit()
    signed = store.presign_put(existing.object_key, existing.mime, PUT_EXPIRES_S)
    return {
        "duplicate": False,
        "id": existing.id,
        "upload": {"url": signed.url, "headers": signed.headers, "expires_in": signed.expires_in},
    }


def complete_upload(db: Session, store: BlobStore, actor: str, sheet_id: str) -> PilotSheet:
    """Mark a sheet stored once the object is really in the bucket at the size the phone said."""
    sheet = db.get(PilotSheet, sheet_id)
    if sheet is None:
        raise HTTPException(404, "That sheet is not known.")
    if sheet.status in DONE:
        return sheet
    if store.size(sheet.object_key) != sheet.bytes:
        sheet.status = "failed"
        sheet.note = "not_stored"
        db.commit()
        try:
            store.delete(sheet.object_key)  # a short or oversized object is not kept
        except Exception:
            pass
        raise HTTPException(409, "The file did not arrive in full. Try this sheet again.")
    sheet.status = "stored"
    sheet.uploaded_at = datetime.now(UTC)
    db.commit()
    audit(db, actor, "sheet.stored", sheet.id, bytes=sheet.bytes)
    return sheet


def _count_read(db: Session, sheet: PilotSheet, cells: list[str]) -> None:
    diag = diagnose_child(FORM_A, [normalize_answer(c) for c in cells])
    row = db.execute(
        select(PilotClassCount).where(
            PilotClassCount.school_code == sheet.school_code,
            PilotClassCount.class_code == sheet.class_code,
        )
    ).scalar_one_or_none()
    if row is None:
        row = PilotClassCount(
            school_code=sheet.school_code,
            class_code=sheet.class_code,
            teacher_ref=sheet.teacher_ref,
            children_checked=0,
            counts={},
            anchor_wrong_count=0,
            untracked={},
        )
        db.add(row)
    counts = Counter(row.counts or {})
    counts.update(code.value for code in diag.shows)
    untracked = Counter(row.untracked or {})
    untracked.update(diag.untracked)
    row.children_checked += 1
    row.counts = dict(counts)
    row.anchor_wrong_count += int(diag.anchor_wrong)
    row.untracked = dict(untracked)
    row.teacher_ref = sheet.teacher_ref


def read_stored_sheet(
    factory: Callable[[], Session], store: BlobStore, sheet_id: str, ctx: CallContext
) -> str:
    """Call 8 on one stored sheet; returns the sheet's new status. The photo stays in the bucket
    (retention deletes it); the per-box reads are dropped as soon as the counts are added."""
    with factory() as db:
        sheet = db.get(PilotSheet, sheet_id)
        if sheet is None or sheet.status != "stored":
            return sheet.status if sheet else "missing"
        if sheet.mime not in READABLE or sheet.bytes > MAX_READ_BYTES:
            return _flag(db, sheet, "format")
        try:
            data = store.get(sheet.object_key)
        except Exception:
            return _flag(db, sheet, "missing_file")
        try:
            outcome = read_sheet(base64.b64encode(data).decode(), sheet.mime, FORM_A, context=ctx)
        except BudgetExceeded:
            outcome = None
        finally:
            del data
        if outcome is None:
            return _flag(db, sheet, "unreadable")
        if any(c.status == "check" for c in outcome.cells):
            return _flag(db, sheet, "unsure")
        if all(c.status == "blank" for c in outcome.cells):
            return _flag(db, sheet, "blank")
        # claim the sheet first so two workers cannot count it twice
        claimed = db.execute(
            update(PilotSheet)
            .where(PilotSheet.id == sheet.id, PilotSheet.status == "stored")
            .values(status="read", note=None)
        )
        if claimed.rowcount != 1:  # type: ignore[attr-defined]
            return "read"
        _count_read(db, sheet, [c.text for c in outcome.cells])
        db.commit()
        return "read"


def _flag(db: Session, sheet: PilotSheet, note: str) -> str:
    sheet.status = "needs_look"
    sheet.note = note
    db.commit()
    return "needs_look"


def summary(db: Session) -> dict[str, Any]:
    """The counts the Upload page shows: uploaded, read, needs a second look."""
    by_status = dict(
        db.execute(select(PilotSheet.status, func.count()).group_by(PilotSheet.status)).all()
    )
    uploaded = sum(by_status.get(s, 0) for s in DONE)
    teachers = [
        r[0]
        for r in db.execute(
            select(PilotSheet.teacher_ref).distinct().order_by(PilotSheet.teacher_ref)
        ).all()
    ]
    schools = [
        r[0]
        for r in db.execute(
            select(PilotSheet.school_code).distinct().order_by(PilotSheet.school_code)
        ).all()
    ]
    return {
        "uploaded": uploaded,
        "read": by_status.get("read", 0),
        "needs_look": by_status.get("needs_look", 0),
        "waiting": by_status.get("stored", 0),
        "teachers": teachers,
        "schools": schools,
    }


def delete_sheets(db: Session, store: BlobStore, rows: list[PilotSheet]) -> int:
    for row in rows:
        try:
            store.delete(row.object_key)
        except Exception:
            pass  # the row goes anyway; a stray object is left to the bucket's lifecycle rule
        db.delete(row)
    db.commit()
    return len(rows)


def delete_school(db: Session, store: BlobStore, actor: str, school_code: str) -> dict[str, int]:
    """Erase everything held for one school: its photos, its sheet rows and its class counts."""
    school = check_code(school_code, "school code", CODE)
    rows = list(db.execute(select(PilotSheet).where(PilotSheet.school_code == school)).scalars())
    n = delete_sheets(db, store, rows)
    counts = db.execute(
        select(PilotClassCount).where(PilotClassCount.school_code == school)
    ).scalars()
    classes = 0
    for c in list(counts):
        db.delete(c)
        classes += 1
    db.commit()
    audit(db, actor, "sheets.delete_school", school, sheets=n, classes=classes)
    return {"sheets": n, "classes": classes}


def purge_expired(db: Session, store: BlobStore, *, now: datetime | None = None) -> int:
    """Delete photos and sheet rows older than the retention period. Class counts stay: they hold
    no child and no photo. Runs on each upload and at start-up; the audit row says how many."""
    cutoff = (now or datetime.now(UTC)) - timedelta(days=retention_days(db))
    rows = [r for r in db.execute(select(PilotSheet)).scalars() if _aware(r.uploaded_at) < cutoff]
    if not rows:
        return 0
    n = delete_sheets(db, store, rows)
    audit(db, "system", "sheets.retention", "", sheets=n, days=retention_days(db))
    return n


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def list_sheets(db: Session, limit: int = 200) -> list[dict[str, Any]]:
    rows = db.execute(
        select(PilotSheet).order_by(PilotSheet.uploaded_at.desc()).limit(limit)
    ).scalars()
    return [
        {
            "id": r.id,
            "school_code": r.school_code,
            "class_code": r.class_code,
            "teacher_ref": r.teacher_ref,
            "status": r.status,
            "note": r.note,
            "bytes": r.bytes,
            "uploaded_at": _aware(r.uploaded_at).isoformat(),
        }
        for r in rows
    ]
