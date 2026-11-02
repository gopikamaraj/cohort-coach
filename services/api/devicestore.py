# ruff: noqa: E501
"""The cloud copy of what a phone used to keep: classes, entered checks, results and settings.

Decided 2 Nov 2026 (docs/build/DECISIONS.md): while online the app writes every change here and reads
everything back from here; the phone keeps only a cache and an offline queue. A document belongs to the
random device id the app made for that phone (the same pseudonymous id the cohort chat uses): another
teacher's id cannot read it. Coaches and mentors can list every device's entered checks, by a label
("Teacher 1"), never the device id. Rehearsal transcripts and sheet photos are never stored here."""

from __future__ import annotations

import os
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


SHARED = "0" * 16


def _device(key: str | None) -> str:
    """The key a request's documents live under. A teacher is her nickname: the app sends a key made
    from it (`X-Store-Key`), so the same nickname on any browser reads and writes the same documents and
    another nickname gets its own (decided 2 Nov 2026). With no nickname the phone's random device id is
    the key. STORE_SHARED=1 puts everyone in one shared set instead."""
    if not key or not DEVICE.match(key):
        raise HTTPException(422, "The store key must be the 16-character id the app made.")
    return SHARED if os.environ.get("STORE_SHARED") == "1" else key


def _adopt_earlier(db: Session) -> None:
    """Shared mode, first read: documents written before sharing (under a phone's own id) join the shared set.
    The latest write of each document wins. Runs only while the shared set is empty."""
    if db.scalars(select(DeviceDoc).where(DeviceDoc.device == SHARED).limit(1)).first() is not None:
        return
    rows = db.scalars(select(DeviceDoc).where(DeviceDoc.device != SHARED).order_by(DeviceDoc.updated_at)).all()
    latest: dict[tuple[str, str], DeviceDoc] = {(r.collection, r.doc_id): r for r in rows}
    for (coll, doc_id), r in latest.items():
        db.add(DeviceDoc(device=SHARED, collection=coll, doc_id=doc_id, data=r.data))
    if latest:
        db.commit()


def _collection(name: str) -> str:
    if name not in COLLECTIONS:
        raise HTTPException(404, "Unknown collection.")
    return name


class DocIn(BaseModel):
    data: Any = Field(...)


@router.get("")
def read_all(x_device_id: str | None = Header(default=None), x_store_key: str | None = Header(default=None), db: Session = SESSION) -> dict[str, dict[str, Any]]:
    """Everything this phone has stored, by collection and id."""
    device = _device(x_store_key or x_device_id)
    if device == SHARED:
        _adopt_earlier(db)
    out: dict[str, dict[str, Any]] = {c: {} for c in COLLECTIONS}
    for row in db.scalars(select(DeviceDoc).where(DeviceDoc.device == device)):
        out[row.collection][row.doc_id] = row.data
    return out


@router.put("/{collection}/{doc_id}")
def write(collection: str, doc_id: str, body: DocIn, x_device_id: str | None = Header(default=None), x_store_key: str | None = Header(default=None), db: Session = SESSION) -> dict[str, bool]:
    device, coll = _device(x_store_key or x_device_id), _collection(collection)
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
def remove(collection: str, doc_id: str, x_device_id: str | None = Header(default=None), x_store_key: str | None = Header(default=None), db: Session = SESSION) -> dict[str, bool]:
    device, coll = _device(x_store_key or x_device_id), _collection(collection)
    db.execute(delete(DeviceDoc).where(DeviceDoc.device == device, DeviceDoc.collection == coll, DeviceDoc.doc_id == doc_id))
    db.commit()
    return {"ok": True}


@router.delete("")
def clear(x_device_id: str | None = Header(default=None), x_store_key: str | None = Header(default=None), db: Session = SESSION) -> dict[str, bool]:
    """Delete everything this phone stored (the 'delete my data' action)."""
    db.execute(delete(DeviceDoc).where(DeviceDoc.device == _device(x_store_key or x_device_id)))
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


def _seen(prof: dict[str, Any]) -> dict[str, Any]:
    """Children per mistake counting a mistake seen even once (confirmed or possible): `anyCounts`, which the app
    writes with each class result. An older result without it falls back to its confirmed counts."""
    got = prof.get("anyCounts")
    return got if isinstance(got, dict) else (prof.get("counts") or {})


ERROR_CODE = re.compile(r"^[A-Z0-9-]{3,16}$")


@router.get("/peers")
def peers(
    errors: str,
    x_device_id: str | None = Header(default=None),
    x_store_key: str | None = Header(default=None),
    db: Session = SESSION,
) -> list[dict[str, Any]]:
    """The other teachers whose latest class result shows any of these mistakes: a label and a class name,
    never a count (a teacher sees no number about another teacher's class). Empty while everyone shares."""
    me = _device(x_store_key or x_device_id)
    wanted = {e for e in errors.split(",") if ERROR_CODE.match(e)}
    if not wanted or os.environ.get("STORE_SHARED") == "1":
        return []
    rows = db.scalars(
        select(DeviceDoc).where(DeviceDoc.device.notin_([me, SHARED]), DeviceDoc.collection.in_(("profiles", "classes", "settings")))
    ).all()
    by_device: dict[str, dict[str, dict[str, Any]]] = {}
    for r in rows:
        by_device.setdefault(r.device, {}).setdefault(r.collection, {})[r.doc_id] = r.data if isinstance(r.data, dict) else {}
    out: list[dict[str, Any]] = []
    for n, (_device_key, docs) in enumerate(sorted(by_device.items()), start=1):
        shared: list[str] = []
        class_name = ""
        for prof in docs.get("profiles", {}).values():
            hit = [e for e in wanted if int(_seen(prof).get(e, 0) or 0) > 0]
            if hit:
                shared = sorted(set(shared) | set(hit))
                class_name = str((docs.get("classes", {}).get(str(prof.get("classId"))) or {}).get("name") or "")
        if shared:
            nick = str((docs.get("settings", {}).get("nickname") or {}).get("value") or "").strip()
            out.append({"teacher": nick or f"Teacher {n}", "class": class_name, "errors": shared})
    return sorted(out, key=lambda p: p["teacher"].lower())


def _with_any(db: Session, prof: dict[str, Any], check: dict[str, Any] | None) -> dict[str, Any]:
    """A class result saved before `anyCounts` existed: work it out from the check's answers and the paper's own
    key (engine-built from the paper's numbers), the same way the phone does. Children who made a mistake at
    least once, confirmed or possible, per mistake. Anything that cannot be read leaves the result as it was."""
    got = prof.get("anyCounts")
    if isinstance(got, dict) and got:
        return prof
    paper_id = str(prof.get("formKey") or "")
    rows = (check or {}).get("children")
    if not paper_id.startswith("P-") or not isinstance(rows, list):
        return prof
    from engine.normalize import normalize_answer
    from services.papers import keys as paper_keys
    from services.papers.models import PaperRow

    paper = db.get(PaperRow, paper_id)
    if paper is None:
        return prof
    items = paper_keys.key_of(paper.id, paper.body, "")["forms"][paper.id]["items"]
    absent = {int(i) for i in (check or {}).get("absent") or []}
    out: dict[str, int] = {}
    for i, row in enumerate(rows):
        if i in absent or not isinstance(row, list) or not any(str(c).strip() for c in row):
            continue
        codes: set[str] = set()
        for q, item in enumerate(items):
            raw = row[q] if q < len(row) else ""
            ans = normalize_answer(str(raw) if str(raw).strip() else None)
            if isinstance(ans, int):
                codes.update(item["wrong"].get(str(ans), []))
        for code in codes:
            out[code] = out.get(code, 0) + 1
    return {**prof, "anyCounts": out}


def entered_summary(db: Session) -> dict[str, Any]:
    """Every teacher's entered classes, added up for a coach: per term the number of classes, children checked
    and children showing each mistake, plus a label per class ("Teacher 1", class name). Counts only."""
    rows = db.scalars(
        select(DeviceDoc).where(DeviceDoc.collection.in_(("profiles", "classes", "settings", "checks"))).order_by(DeviceDoc.device)
    ).all()
    docs: dict[str, dict[str, dict[str, Any]]] = {}
    for r in rows:
        docs.setdefault(r.device, {}).setdefault(r.collection, {})[r.doc_id] = r.data if isinstance(r.data, dict) else {}
    terms: dict[str, dict[str, Any]] = {}
    classes: list[dict[str, Any]] = []
    for n, (_dev, d) in enumerate(docs.items(), start=1):
        nick = str((d.get("settings", {}).get("nickname") or {}).get("value") or "").strip()
        for prof in d.get("profiles", {}).values():
            if not int(prof.get("childrenChecked", 0) or 0):
                continue
            prof = _with_any(db, prof, d.get("checks", {}).get(str(prof.get("id"))))
            term = str(prof.get("term", 1))
            t = terms.setdefault(term, {"classes": 0, "children_checked": 0, "children_showing": {}})
            t["classes"] += 1
            t["children_checked"] += int(prof["childrenChecked"])
            for code, c in _seen(prof).items():
                t["children_showing"][code] = t["children_showing"].get(code, 0) + int(c or 0)
            cname = str((d.get("classes", {}).get(str(prof.get("classId"))) or {}).get("name") or "")
            classes.append({"teacher": nick or f"Teacher {n}", "class": cname, "term": int(term), "children_checked": int(prof["childrenChecked"]), "errors": sorted(c for c, v in _seen(prof).items() if int(v or 0) > 0), "_counts": {c: int(v or 0) for c, v in _seen(prof).items()}, "_class": f"{n}:{prof.get('classId')}", "_key": _dev, "_check": str(prof.get("id") or "")})
    return {"terms": terms, "classes": classes}


@router.get("/coach-summary")
def coach_summary(role: str = Depends(role_of), db: Session = SESSION) -> dict[str, Any]:
    """Added-up counts, and which classes (teacher label, class name) show which mistake. No class's own count."""
    if role not in ("coach", "mentor", "officer"):
        raise HTTPException(403, "Only a coach, a mentor or the officer can see this.")
    s = entered_summary(db)
    keep = ("term", "errors") if role == "officer" else ("teacher", "class", "term", "errors")  # the officer sees groups, never a class or teacher
    return {"terms": s["terms"], "classes": [{k: c[k] for k in keep} for c in s["classes"]]}


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
