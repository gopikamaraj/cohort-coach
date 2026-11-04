# ruff: noqa: E501
"""The cloud copy of what a phone used to keep: classes, entered checks, results and settings.

Decided 2 Nov 2026 (docs/build/DECISIONS.md): while online the app writes every change here and reads
everything back from here; the phone keeps only a cache and an offline queue. Since the identity clean-up
(3 Nov 2026) a document belongs to the signed-in user (the normalised nickname) and to nobody else: another
user's id cannot read, write or delete it, and a class is identified by its owner plus its class code.
Coaches and mentors see counts for the cohorts assigned to them (and a label, never a nickname); the officer
sees counts across all. Rehearsal transcripts and sheet photos are never stored here."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import JSON, DateTime, String, delete, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from services.api.db import Base
from services.api.identity import user_of
from services.api.profiles import SESSION
from services.api.roles import role_of

router = APIRouter(prefix="/api/store", tags=["store"])

COLLECTIONS = ("classes", "checks", "profiles", "settings")
DOC_ID = re.compile(r"^[A-Za-z0-9:_.\-]{1,80}$")
MAX_DOC_BYTES = 200_000


def _now() -> datetime:
    return datetime.now(UTC)


class UserDoc(Base):
    """One document of one user. The primary key is (owner, collection, doc id): a class is its owner plus its code."""

    __tablename__ = "user_docs"

    owner: Mapped[str] = mapped_column(String(32), primary_key=True)  # the user id
    collection: Mapped[str] = mapped_column(String(12), primary_key=True)
    doc_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    data: Mapped[Any] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


def _collection(name: str) -> str:
    if name not in COLLECTIONS:
        raise HTTPException(404, "Unknown collection.")
    return name


class DocIn(BaseModel):
    data: Any = Field(...)


@router.get("")
def read_all(owner: str = Depends(user_of), db: Session = SESSION) -> dict[str, dict[str, Any]]:
    """Everything this user has stored, by collection and id."""
    out: dict[str, dict[str, Any]] = {c: {} for c in COLLECTIONS}
    for row in db.scalars(select(UserDoc).where(UserDoc.owner == owner)):
        out[row.collection][row.doc_id] = row.data
    return out


@router.put("/{collection}/{doc_id}")
def write(collection: str, doc_id: str, body: DocIn, owner: str = Depends(user_of), db: Session = SESSION) -> dict[str, bool]:
    coll = _collection(collection)
    if not DOC_ID.match(doc_id):
        raise HTTPException(422, "Bad document id.")
    if len(str(body.data)) > MAX_DOC_BYTES:
        raise HTTPException(413, "This document is too large.")
    row = db.get(UserDoc, (owner, coll, doc_id))
    if row is None:
        db.add(UserDoc(owner=owner, collection=coll, doc_id=doc_id, data=body.data))
    else:
        row.data = body.data
        row.updated_at = _now()
    db.commit()
    return {"ok": True}


@router.delete("/{collection}/{doc_id}")
def remove(collection: str, doc_id: str, owner: str = Depends(user_of), db: Session = SESSION) -> dict[str, bool]:
    coll = _collection(collection)
    db.execute(delete(UserDoc).where(UserDoc.owner == owner, UserDoc.collection == coll, UserDoc.doc_id == doc_id))
    db.commit()
    return {"ok": True}


@router.delete("")
def clear(owner: str = Depends(user_of), db: Session = SESSION) -> dict[str, bool]:
    """Delete everything this user stored (the 'delete my data' action)."""
    db.execute(delete(UserDoc).where(UserDoc.owner == owner))
    db.commit()
    return {"ok": True}


def _counts_only(coll: str, data: Any) -> Any:
    """What a coach or mentor may see of a check: its label and counts, never a child's answers."""
    if coll != "checks" or not isinstance(data, dict):
        return data
    rows = data.get("children") or []
    entered = sum(1 for r in rows if isinstance(r, list) and any(str(c).strip() for c in r))
    keep = ("id", "kind", "checkDate", "status", "updatedAt", "expectedChildren")
    return {**{k: data[k] for k in keep if k in data}, "entered": entered, "absent": len(data.get("absent") or [])}


def _seen(prof: dict[str, Any]) -> dict[str, Any]:
    """Children per mistake counting a mistake seen even once (confirmed or possible): `anyCounts`, which the app
    writes with each class result. An older result without it falls back to its confirmed counts."""
    got = prof.get("anyCounts")
    return got if isinstance(got, dict) else (prof.get("counts") or {})


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


def entered_summary(db: Session, owners: set[str] | None = None) -> dict[str, Any]:
    """Entered classes, added up. There are no terms: each class counts once, by its most recent check (by date
    saved), and `all` lists every check so a before-and-after can be read. A class is its owner plus its class
    code. `owners` limits it to those users (a coach's or mentor's assigned cohorts); None means everyone (the
    officer, and the cohort-forming code). Counts only."""
    q = select(UserDoc).where(UserDoc.collection.in_(("profiles", "classes", "checks")))
    if owners is not None:
        q = q.where(UserDoc.owner.in_(owners or {""}))
    rows = db.scalars(q.order_by(UserDoc.owner)).all()
    docs: dict[str, dict[str, dict[str, Any]]] = {}
    for r in rows:
        docs.setdefault(r.owner, {}).setdefault(r.collection, {})[r.doc_id] = r.data if isinstance(r.data, dict) else {}
    from services.api.db import User

    nicks = {u.id: u.nickname for u in db.scalars(select(User).where(User.id.in_(list(docs) or [""])))}
    every: list[dict[str, Any]] = []
    for owner, d in docs.items():
        for prof in d.get("profiles", {}).values():
            if not int(prof.get("childrenChecked", 0) or 0):
                continue
            check = d.get("checks", {}).get(str(prof.get("id")))
            prof = _with_any(db, prof, check)
            at = int((check or {}).get("updatedAt") or prof.get("createdAt") or 0)
            cname = str((d.get("classes", {}).get(str(prof.get("classId"))) or {}).get("name") or "")
            every.append({"teacher": nicks.get(owner, owner), "class": cname, "children_checked": int(prof["childrenChecked"]), "errors": sorted(c for c, v in _seen(prof).items() if int(v or 0) > 0), "_counts": {c: int(v or 0) for c, v in _seen(prof).items()}, "_class": f"{owner}/{prof.get('classId')}", "_owner": owner, "_check": str(prof.get("id") or ""), "_at": at})
    latest: dict[str, dict[str, Any]] = {}
    for c in every:
        if c["_class"] not in latest or c["_at"] > latest[c["_class"]]["_at"]:
            latest[c["_class"]] = c
    classes = list(latest.values())
    totals: dict[str, Any] = {"classes": len(classes), "children_checked": sum(c["children_checked"] for c in classes), "children_showing": {}}
    for c in classes:
        for code, k in c["_counts"].items():
            totals["children_showing"][code] = totals["children_showing"].get(code, 0) + k
    return {"totals": totals, "classes": classes, "all": every}


def assigned_owners(db: Session, uid: str, role: str) -> set[str]:
    """The users whose classes a coach or mentor may see: the members of the cohorts assigned to them. A cohort
    made from entered classes records its coach; a cohort space names its coach and mentors. In the judge-mode
    demo the simulated cohort spaces (no real teacher in them) add nobody."""
    from services.api.db import ClassCohort, CohortMember, CohortSpace

    out: set[str] = set()
    for g in db.scalars(select(ClassCohort).where(ClassCohort.scope == "coach")):
        if role == "coach" and g.counts.get("_coach") == uid:
            out.update(str(k) for k in (g.counts.get("_members") or {}))
    if role == "coach":
        spaces = list(db.scalars(select(CohortSpace.id).where(CohortSpace.coach_id == uid)))
    else:
        spaces = [sp.id for sp in db.scalars(select(CohortSpace)) if uid in (sp.mentor_ids or [])]
    if spaces:
        out.update(m for m in db.scalars(select(CohortMember.teacher_id).where(CohortMember.cohort_id.in_(spaces))))
    return out


@router.get("/coach-summary")
def coach_summary(role: str = Depends(role_of), uid: str = Depends(user_of), db: Session = SESSION) -> dict[str, Any]:
    """Counts. The officer: across all classes, groups only. A coach or mentor: the classes of their assigned
    cohorts, with the nickname and class name, plus `pool`: how many classes across all show each mistake (a
    count and nothing else), so a coach can start a cohort. A teacher is refused."""
    if role not in ("coach", "mentor", "officer"):
        raise HTTPException(403, "Only a coach, a mentor or the officer can see this.")
    if role == "officer":
        s = entered_summary(db)
        return {"totals": s["totals"], "classes": [{"errors": c["errors"]} for c in s["classes"]]}
    mine = entered_summary(db, assigned_owners(db, uid, role))
    pool = entered_summary(db)["totals"]
    return {"totals": mine["totals"], "classes": [{k: c[k] for k in ("teacher", "class", "errors")} for c in mine["classes"]], "pool": pool["children_showing"] | {"_classes": pool["classes"]}}


@router.get("/all/{collection}")
def read_everyone(collection: str, role: str = Depends(role_of), uid: str = Depends(user_of), db: Session = SESSION) -> list[dict[str, Any]]:
    """Coaches and mentors: the documents of the users in their assigned cohorts, in one collection. A check
    comes back as its label and counts only: no child's answers. Results and settings are not offered."""
    if role not in ("coach", "mentor"):
        raise HTTPException(403, "Only a coach or a mentor can see their cohorts' checks.")
    coll = _collection(collection)
    if coll != "checks":
        raise HTTPException(404, "Only checks are listed, as counts.")
    owners = assigned_owners(db, uid, role)
    rows = db.scalars(select(UserDoc).where(UserDoc.collection == coll, UserDoc.owner.in_(owners or {""})).order_by(UserDoc.owner, UserDoc.doc_id)).all()
    out = []
    for row in rows:
        out.append({"teacher": row.owner, "id": row.doc_id, "data": _counts_only(coll, row.data), "updated_at": row.updated_at.isoformat()})
    return out
