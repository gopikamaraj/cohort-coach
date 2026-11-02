# ruff: noqa: E501
"""The cloud copy of what a phone used to keep: classes, entered checks, results and settings.

Decided 2 Nov 2026 (docs/build/DECISIONS.md): while online the app writes every change here and reads
everything back from here; the phone keeps only a cache and an offline queue. A document belongs to the
random device id the app made for that phone (the same pseudonymous id the cohort chat uses): another
teacher's id cannot read it. Coaches and mentors can list every device's entered checks, by a label
("Teacher 1"), never the device id. Rehearsal transcripts and sheet photos are never stored here."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, String, delete, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from services.api.db import Base
from services.api.profiles import SESSION
from services.api.roles import role_of

router = APIRouter(prefix="/api/store", tags=["store"])

DEVICE = re.compile(r"^[0-9a-f]{16}$")
COLLECTIONS = ("classes", "checks", "profiles", "settings")
DOC_ID = re.compile(r"^[A-Za-z0-9:_.\-]{1,80}$")
MAX_DOC_BYTES = 200_000


def _now() -> datetime:
    return datetime.now(UTC)


class DeviceDoc(Base):
    __tablename__ = "device_docs"

    device: Mapped[str] = mapped_column(String(16), primary_key=True)
    collection: Mapped[str] = mapped_column(String(12), primary_key=True)
    doc_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    data: Mapped[Any] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


def _device(x_device_id: str | None) -> str:
    if not x_device_id or not DEVICE.match(x_device_id):
        raise HTTPException(422, "X-Device-Id must be the random id the app made for this phone.")
    return x_device_id


def _collection(name: str) -> str:
    if name not in COLLECTIONS:
        raise HTTPException(404, "Unknown collection.")
    return name


class DocIn(BaseModel):
    data: Any = Field(...)


@router.get("")
def read_all(x_device_id: str | None = Header(default=None), db: Session = SESSION) -> dict[str, dict[str, Any]]:
    """Everything this phone has stored, by collection and id."""
    device = _device(x_device_id)
    out: dict[str, dict[str, Any]] = {c: {} for c in COLLECTIONS}
    for row in db.scalars(select(DeviceDoc).where(DeviceDoc.device == device)):
        out[row.collection][row.doc_id] = row.data
    return out


@router.put("/{collection}/{doc_id}")
def write(collection: str, doc_id: str, body: DocIn, x_device_id: str | None = Header(default=None), db: Session = SESSION) -> dict[str, bool]:
    device, coll = _device(x_device_id), _collection(collection)
    if not DOC_ID.match(doc_id):
        raise HTTPException(422, "Bad document id.")
    if len(str(body.data)) > MAX_DOC_BYTES:
        raise HTTPException(413, "This document is too large.")
    row = db.get(DeviceDoc, (device, coll, doc_id))
    if row is None:
        db.add(DeviceDoc(device=device, collection=coll, doc_id=doc_id, data=body.data))
    else:
        row.data = body.data
        row.updated_at = _now()
    db.commit()
    return {"ok": True}


@router.delete("/{collection}/{doc_id}")
def remove(collection: str, doc_id: str, x_device_id: str | None = Header(default=None), db: Session = SESSION) -> dict[str, bool]:
    device, coll = _device(x_device_id), _collection(collection)
    db.execute(delete(DeviceDoc).where(DeviceDoc.device == device, DeviceDoc.collection == coll, DeviceDoc.doc_id == doc_id))
    db.commit()
    return {"ok": True}


@router.delete("")
def clear(x_device_id: str | None = Header(default=None), db: Session = SESSION) -> dict[str, bool]:
    """Delete everything this phone stored (the 'delete my data' action)."""
    db.execute(delete(DeviceDoc).where(DeviceDoc.device == _device(x_device_id)))
    db.commit()
    return {"ok": True}


def _counts_only(coll: str, data: Any) -> Any:
    """What a coach or mentor may see of a check: its label and counts, never a child's answers."""
    if coll != "checks" or not isinstance(data, dict):
        return data
    rows = data.get("children") or []
    entered = sum(1 for r in rows if isinstance(r, list) and any(str(c).strip() for c in r))
    keep = ("id", "kind", "term", "checkDate", "status", "updatedAt", "expectedChildren")
    return {**{k: data[k] for k in keep if k in data}, "entered": entered, "absent": len(data.get("absent") or [])}


@router.get("/all/{collection}")
def read_everyone(collection: str, role: str = Depends(role_of), db: Session = SESSION) -> list[dict[str, Any]]:
    """Coaches and mentors: every phone's documents in one collection, labelled, never by device id.
    A check comes back as its label and counts only: no child's answers."""
    if role not in ("coach", "mentor"):
        raise HTTPException(403, "Only a coach or a mentor can see every teacher's checks.")
    coll = _collection(collection)
    rows = db.scalars(select(DeviceDoc).where(DeviceDoc.collection == coll).order_by(DeviceDoc.device, DeviceDoc.doc_id)).all()
    labels: dict[str, str] = {}
    out = []
    for row in rows:
        label = labels.setdefault(row.device, f"Teacher {len(labels) + 1}")
        out.append({"teacher": label, "id": row.doc_id, "data": _counts_only(coll, row.data), "updated_at": row.updated_at.isoformat()})
    return out
