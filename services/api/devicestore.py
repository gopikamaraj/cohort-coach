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
from sqlalchemy import JSON, DateTime, Integer, String, delete, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from engine.diagnosis import RULE_CONFIRMED, counts_for_rule, valid_rule
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


class DocVersion(Base):
    """The version of a stored document: it goes up by one at every write. A device sends the version it last
    read; a write that is based on an older one still wins (the later write wins), but the version it replaced
    is kept in `doc_conflicts`, so nothing is lost silently. A separate table so no existing table changes."""

    __tablename__ = "doc_versions"

    owner: Mapped[str] = mapped_column(String(32), primary_key=True)
    collection: Mapped[str] = mapped_column(String(12), primary_key=True)
    doc_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=0)


class DocConflict(Base):
    """A version of a document that a later write replaced while it was based on something older."""

    __tablename__ = "doc_conflicts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner: Mapped[str] = mapped_column(String(32), index=True)
    collection: Mapped[str] = mapped_column(String(12))
    doc_id: Mapped[str] = mapped_column(String(80))
    data: Mapped[Any] = mapped_column(JSON)  # the overwritten version
    overwritten_version: Mapped[int] = mapped_column(Integer)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


MAX_CONFLICTS = 50  # a short list: the newest ones per user


def _collection(name: str) -> str:
    if name not in COLLECTIONS:
        raise HTTPException(404, "Unknown collection.")
    return name


class DocIn(BaseModel):
    data: Any = Field(...)
    base_version: int | None = Field(default=None, ge=0)  # the version this device last read, if it knows one


@router.get("")
def read_all(owner: str = Depends(user_of), db: Session = SESSION) -> dict[str, dict[str, Any]]:
    """Everything this user has stored, by collection and id."""
    out: dict[str, dict[str, Any]] = {c: {} for c in COLLECTIONS}
    for row in db.scalars(select(UserDoc).where(UserDoc.owner == owner)):
        out[row.collection][row.doc_id] = row.data
    return out


@router.get("/versions")
def versions(owner: str = Depends(user_of), db: Session = SESSION) -> dict[str, dict[str, int]]:
    """The version of each of this user's documents, by collection and id."""
    out: dict[str, dict[str, int]] = {c: {} for c in COLLECTIONS}
    for row in db.scalars(select(DocVersion).where(DocVersion.owner == owner)):
        if row.collection in out:
            out[row.collection][row.doc_id] = row.version
    return out


@router.get("/conflicts")
def conflicts(owner: str = Depends(user_of), db: Session = SESSION) -> list[dict[str, Any]]:
    """Versions of this user's documents that a later write replaced, newest first (her own only)."""
    rows = db.scalars(select(DocConflict).where(DocConflict.owner == owner).order_by(DocConflict.id.desc()).limit(MAX_CONFLICTS))
    return [{"id": r.id, "collection": r.collection, "doc_id": r.doc_id, "at": r.at.isoformat(), "overwritten_version": r.overwritten_version, "data": r.data} for r in rows]


@router.delete("/conflicts/{conflict_id}")
def dismiss_conflict(conflict_id: int, owner: str = Depends(user_of), db: Session = SESSION) -> dict[str, bool]:
    db.execute(delete(DocConflict).where(DocConflict.owner == owner, DocConflict.id == conflict_id))
    db.commit()
    return {"ok": True}


@router.put("/{collection}/{doc_id}")
def write(collection: str, doc_id: str, body: DocIn, owner: str = Depends(user_of), db: Session = SESSION) -> dict[str, Any]:
    coll = _collection(collection)
    if not DOC_ID.match(doc_id):
        raise HTTPException(422, "Bad document id.")
    if len(str(body.data)) > MAX_DOC_BYTES:
        raise HTTPException(413, "This document is too large.")
    row = db.get(UserDoc, (owner, coll, doc_id))
    ver = db.get(DocVersion, (owner, coll, doc_id))
    current = ver.version if ver is not None else 0
    conflict = False
    if row is not None and body.base_version is not None and body.base_version != current:
        # the device wrote from an older version: the later write wins, the version it replaces is kept
        conflict = True
        db.add(DocConflict(owner=owner, collection=coll, doc_id=doc_id, data=row.data, overwritten_version=current))
        db.flush()
        old = db.scalars(select(DocConflict.id).where(DocConflict.owner == owner).order_by(DocConflict.id.desc()).offset(MAX_CONFLICTS)).all()
        if old:
            db.execute(delete(DocConflict).where(DocConflict.id.in_(old)))
    if row is None:
        db.add(UserDoc(owner=owner, collection=coll, doc_id=doc_id, data=body.data))
    else:
        row.data = body.data
        row.updated_at = _now()
    if ver is None:
        db.add(DocVersion(owner=owner, collection=coll, doc_id=doc_id, version=current + 1))
    else:
        ver.version = current + 1
    db.commit()
    return {"ok": True, "version": current + 1, "conflict": conflict}


@router.delete("/{collection}/{doc_id}")
def remove(collection: str, doc_id: str, owner: str = Depends(user_of), db: Session = SESSION) -> dict[str, bool]:
    coll = _collection(collection)
    db.execute(delete(UserDoc).where(UserDoc.owner == owner, UserDoc.collection == coll, UserDoc.doc_id == doc_id))
    ver = db.get(DocVersion, (owner, coll, doc_id))
    if ver is not None:
        ver.version += 1  # a delete is a change too, so a device holding an older copy is told
    db.commit()
    return {"ok": True}


@router.delete("")
def clear(owner: str = Depends(user_of), db: Session = SESSION) -> dict[str, bool]:
    """Delete everything this user stored (the 'delete my data' action)."""
    db.execute(delete(UserDoc).where(UserDoc.owner == owner))
    db.execute(delete(DocVersion).where(DocVersion.owner == owner))
    db.execute(delete(DocConflict).where(DocConflict.owner == owner))
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


def _seen(prof: dict[str, Any], min_hits: int = RULE_CONFIRMED) -> dict[str, Any]:
    """Children per mistake under the rule (engine/diagnosis.py `counts_for_rule`): confirmed (seen in two or more
    questions, the result's `counts`) or possible (seen in one or more, `anyCounts`, which the app writes with each
    class result). An older result without `anyCounts` falls back to its confirmed counts."""
    got = prof.get("anyCounts")
    return counts_for_rule(prof.get("counts") or {}, got if isinstance(got, dict) else None, min_hits)


def saved_rule(db: Session, uid: str) -> int:
    """The rule this user saved (the settings document `errorRule`); confirmed (two or more) when she has none."""
    row = db.get(UserDoc, (uid, "settings", "errorRule"))
    return valid_rule((row.data or {}).get("value") if row is not None and isinstance(row.data, dict) else None)


def rule_for(db: Session, uid: str, requested: int | None) -> int:
    """The rule a request counts under: the one it asks for, else the one the user saved, else confirmed."""
    return valid_rule(requested, saved_rule(db, uid)) if requested is not None else saved_rule(db, uid)


def form_for(db: Session, form_key: str) -> tuple[Any, frozenset[int] | None, dict[str, str | None]]:
    """What a result was made on: the engine form (a stored paper, by its own numbers, or a built-in form), the
    numbers of its anchor items (None when every item is one), and how it is linked to its twin: the id of the paper it
    is the twin of, and its own content hash and the hash of the pre-test it is the twin of."""
    if form_key.startswith("P-"):
        from services.papers import keys as paper_keys
        from services.papers.models import PaperRow

        paper = db.get(PaperRow, form_key)
        if paper is None:
            return None, None, {}
        imported = (paper.body or {}).get("source") == "imported_pdf"
        anchors = frozenset(int(it["n"]) for it in paper.body["items"] if imported or bool(it.get("is_anchor", True)))
        body = paper.body or {}
        return paper_keys.form_of(paper.body, paper.check_code), anchors, {"twin_of": paper.twin_of, "hash": body.get("hash"), "twin_hash": body.get("twin_of_paper")}
    from engine.forms import FORM_A, FORM_B

    # the pilot's printed forms: B is A's twin by construction
    link = {"A": {"hash": "builtin:A"}, "B": {"hash": "builtin:B", "twin_hash": "builtin:A"}}.get(form_key, {})
    return {"A": FORM_A, "B": FORM_B}.get(form_key), None, link


def recomputed(db: Session, prof: dict[str, Any], check: dict[str, Any] | None) -> dict[str, Any]:
    """The result with its numbers worked out again from the answers and the paper, by the engine (engine/class_counts.py).
    The phone writes counts too, but an officer or coach number is never a copy: where the answers and the paper are
    here, children checked, the confirmed counts and the seen-once counts come from them. A result whose answers or
    paper cannot be found keeps the numbers it was saved with."""
    rows = (check or {}).get("children")
    form, anchors, link = form_for(db, str(prof.get("formKey") or ""))
    if form is None or not isinstance(rows, list):
        return prof
    from engine.class_counts import count_class

    rows = [r if isinstance(r, list) else [] for r in rows]
    absent = list((check or {}).get("absent") or [])
    got = count_class(form, rows, absent)
    anchor = count_class(form, rows, absent, anchors) if anchors is not None else got
    return {**prof, "childrenChecked": got.children_checked, "counts": got.confirmed, "anyCounts": got.seen_once, "_recomputed": True, "_link": link, "_kind": str((check or {}).get("kind") or ""), "_anchor": anchor}


def entered_summary(db: Session, owners: set[str] | None = None, min_hits: int = RULE_CONFIRMED) -> dict[str, Any]:
    """Entered classes, added up. There are no terms: each class counts once, by its most recent check (by date
    saved), and `all` lists every check so a before-and-after can be read. A class is its owner plus its class
    code. `owners` limits it to those users (a coach's or mentor's assigned cohorts); None means everyone (the
    officer, and the cohort-forming code). Counts only, under the rule `min_hits` (2 confirmed, 1 possible)."""
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
            check = d.get("checks", {}).get(str(prof.get("id")))
            prof = recomputed(db, prof, check)
            if not int(prof.get("childrenChecked", 0) or 0):
                continue
            at = int((check or {}).get("updatedAt") or prof.get("createdAt") or 0)
            cname = str((d.get("classes", {}).get(str(prof.get("classId"))) or {}).get("name") or "")
            every.append({"teacher": nicks.get(owner, owner), "class": cname, "children_checked": int(prof["childrenChecked"]), "errors": sorted(c for c, v in _seen(prof, min_hits).items() if int(v or 0) > 0), "_counts": {c: int(v or 0) for c, v in _seen(prof, min_hits).items()}, "_class": f"{owner}/{prof.get('classId')}", "_owner": owner, "_check": str(prof.get("id") or ""), "_at": at, "_form": str(prof.get("formKey") or ""), "_kind": prof.get("_kind", ""), "_link": prof.get("_link") or {}, "_anchor": prof.get("_anchor")})
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
def coach_summary(role: str = Depends(role_of), uid: str = Depends(user_of), db: Session = SESSION, min_hits: int | None = None) -> dict[str, Any]:
    """Counts. The officer: across all classes, groups only. A coach or mentor: the classes of their assigned
    cohorts, with the nickname and class name, plus `pool`: how many classes across all show each mistake (a
    count and nothing else), so a coach can start a cohort. A teacher is refused."""
    if role not in ("coach", "mentor", "officer"):
        raise HTTPException(403, "Only a coach, a mentor or the officer can see this.")
    rule = rule_for(db, uid, min_hits)
    if role == "officer":
        s = entered_summary(db, None, rule)
        return {"rule": {"min_hits": rule}, "totals": s["totals"], "classes": [{"errors": c["errors"]} for c in s["classes"]]}
    mine = entered_summary(db, assigned_owners(db, uid, role), rule)
    pool = entered_summary(db, None, rule)["totals"]
    return {"rule": {"min_hits": rule}, "totals": mine["totals"], "classes": [{k: c[k] for k in ("teacher", "class", "errors")} for c in mine["classes"]], "pool": pool["children_showing"] | {"_classes": pool["classes"]}}


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
