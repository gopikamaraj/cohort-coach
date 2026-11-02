"""The Papers page over HTTP: import from a PDF or photos, the scoped list and detail, assignments.

Who is acting: the role comes from the server's session; a coach or mentor is a pseudonymous id
(`X-Person`, judge deployment only, else "<role>-demo"); a teacher is her class (`X-Class-Id`). The
server enforces every scope here. Responses carry counts and papers only: no child, no name.
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.client import BudgetExceeded, CallContext
from services.api.cohorts.routes import person_id
from services.api.db import CohortMember, Teacher
from services.api.practice import AI_CONTEXT
from services.api.profiles import SESSION
from services.api.roles import require
from services.papers import explain, keys, store
from services.papers.models import PaperReview, PaperRow
from services.papers_hub import importer as imp
from services.papers_hub import service as svc
from services.papers_hub.models import PaperAssignment, PaperImport

router = APIRouter(prefix="/api/paper-hub", tags=["paper-hub"])
ACT = Depends(require("papers.generate"))
CLASS = re.compile(r"^[A-Za-z0-9:_-]{1,40}$")
NO_STORE = {"Cache-Control": "no-store, max-age=0", "X-Content-Type-Options": "nosniff"}


class Who:
    def __init__(self, role: str, person: str, own_class: str | None) -> None:
        self.role, self.person, self.own_class = role, person, own_class


def who(
    role: str = ACT,
    x_person: str | None = Header(default=None),
    x_class_id: str | None = Header(default=None),
) -> Who:
    own = x_class_id if x_class_id and CLASS.match(x_class_id) else None
    if role == "teacher":
        if own is None:
            raise HTTPException(422, "X-Class-Id must be the class id this phone made.")
        return Who(role, f"teacher-{own[:20]}", own)
    return Who(role, person_id(role, x_person), own)


WHO = Depends(who)


def _wrap(fn: Any, *args: Any, **kw: Any) -> Any:
    try:
        return fn(*args, **kw)
    except svc.Refused as exc:
        raise HTTPException(403, str(exc)) from exc
    except svc.ReaderUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except (svc.Invalid, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except store.BadState as exc:
        raise HTTPException(409, str(exc)) from exc


def _imp_view(row: PaperImport, db: Session | None = None) -> dict[str, Any]:
    d = row.draft
    return {
        "id": row.id,
        "status": row.status,
        "pages": row.pages,
        "expires_at": row.expires_at.isoformat(),
        "paper_id": row.paper_id,
        "draft": {k: d[k] for k in d if k != "history"},
        "can_undo": bool(row.history),
        "blocking": [q["id"] for q in imp.blocking(d)],
        # a post-test that repeats a pre-test's numbers: the pre-tests it shares a pair with
        "reuses": svc.pairs_shared_with_pre_tests(db, d) if db is not None else [],
        "note": "Only the printed questions are read. Handwriting and names are ignored and not kept. "
        "The upload is deleted when you confirm, or after 24 hours.",
    }


# --- import -------------------------------------------------------------------------------------


@router.post("/imports")
def start_import(
    files: list[UploadFile] = File(...),
    roles: list[str] = Form(default=[]),  # noqa: B008
    note: str = Form(default=""),
    key_json: str = Form(default=""),
    kind: str = Form(default=""),
    w: Who = WHO,
    db: Session = SESSION,
    ctx: CallContext = AI_CONTEXT,
) -> dict[str, Any]:
    data = [
        (f.filename or "file", f.file.read(svc.MAX_BYTES + 1)) for f in files[: svc.MAX_FILES + 1]
    ]
    try:
        row = _wrap(
            svc.start_import,
            db,
            w.person,
            w.role,
            data,
            svc.live_reader(ctx),
            roles,
            note,
            svc.parse_key(key_json),
            kind,
        )
    except BudgetExceeded as exc:
        raise HTTPException(503, "Reading is paused. Type the items in instead.") from exc
    return _imp_view(row, db)


class EditIn(BaseModel):
    edits: list[dict[str, Any]] = Field(min_length=1, max_length=20)
    via: str = Field(default="user", pattern="^(user|assistant)$")


@router.get("/imports/{import_id}")
def get_import(import_id: str, w: Who = WHO, db: Session = SESSION) -> dict[str, Any]:
    return _imp_view(_wrap(svc.get_import, db, import_id, w.person), db)


@router.get("/imports/{import_id}/page/{n}")
def import_page(import_id: str, n: int, w: Who = WHO, db: Session = SESSION) -> Response:
    row = _wrap(svc.get_import, db, import_id, w.person)
    return Response(_wrap(svc.page_bytes, row, n), media_type="image/jpeg", headers=NO_STORE)


@router.post("/imports/{import_id}/edit")
def edit_import(
    import_id: str, body: EditIn, w: Who = WHO, db: Session = SESSION
) -> dict[str, Any]:
    return _imp_view(_wrap(svc.edit_draft, db, import_id, w.person, body.edits, body.via), db)


@router.post("/imports/{import_id}/undo")
def undo_import(import_id: str, w: Who = WHO, db: Session = SESSION) -> dict[str, Any]:
    return _imp_view(_wrap(svc.undo, db, import_id, w.person), db)


class ConfirmIn(BaseModel):
    keep_for_check: bool = False


@router.post("/imports/{import_id}/confirm")
def confirm_import(
    import_id: str, body: ConfirmIn, w: Who = WHO, db: Session = SESSION
) -> dict[str, Any]:
    if body.keep_for_check:
        raise HTTPException(
            422, "Keeping the sheet for a check is not available yet. The upload is deleted."
        )
    paper = _wrap(svc.confirm, db, import_id, w.person, w.person)
    return store.summary(paper)


@router.delete("/imports/{import_id}")
def abandon_import(import_id: str, w: Who = WHO, db: Session = SESSION) -> dict[str, Any]:
    _wrap(svc.abandon, db, import_id, w.person)
    return {"deleted": True}


# --- the scoped list, the status and the detail ------------------------------------------------------


def paper_status(db: Session, row: PaperRow) -> dict[str, Any]:
    """What became of a paper, as counts and a reason. Read-only; the assistant reads the same."""
    imported = store.imported(row)
    review_open = db.scalars(
        select(PaperReview).where(PaperReview.paper_id == row.id, PaperReview.status == "open")
    ).first()
    asg = db.scalars(
        select(PaperAssignment).where(
            PaperAssignment.paper_id == row.id, PaperAssignment.status != "withdrawn"
        )
    ).all()
    classes = {a.class_id for a in asg} | {row.class_id}
    teachers = [
        t for (t,) in db.execute(select(Teacher.teacher_id).where(Teacher.class_id.in_(classes)))
    ]
    cohorts = (
        {
            c
            for (c,) in db.execute(
                select(CohortMember.cohort_id).where(CohortMember.teacher_id.in_(teachers))
            )
        }
        if teachers
        else set()
    )
    if cohorts:
        reason = "formed"
    elif not asg:
        reason = "no_check"
    elif any(a.status in ("assigned", "opened") for a in asg):
        reason = "entering"
    elif any(a.status == "in_progress" for a in asg):
        reason = "entering"
    else:
        reason = "waiting_others"
    frozen_reason = "the first sheet of a check is entered" if row.frozen_at else None
    return {
        "paper_id": row.id,
        "status": row.status,
        "kind": row.kind,
        "form": row.form,
        "source": "imported_pdf" if imported else "generated",
        "review": "awaiting_review"
        if (imported and row.status == "confirmed")
        else ("in_queue" if review_open else "none"),
        "frozen": row.frozen_at is not None,
        "frozen_reason": frozen_reason,
        "printable": store.printable(row),
        "findings": [f"{f['rule']}: {f['detail']}" for f in (row.findings or [])][:5],
        "assignments": {
            "assigned": len(asg),
            "opened": sum(a.status in ("opened", "in_progress", "completed") for a in asg),
            "completed": sum(a.status == "completed" for a in asg),
        },
        "cohorts": {"formed": bool(cohorts), "count": len(cohorts), "reason": reason},
    }


def _visible(db: Session, w: Who, row: PaperRow) -> bool:
    if w.role == "coach" or row.class_id == svc.SHARED:
        return True
    if w.role == "teacher":
        if row.class_id == w.own_class:
            return True
        return (
            db.scalars(
                select(PaperAssignment).where(
                    PaperAssignment.paper_id == row.id,
                    PaperAssignment.class_id == w.own_class,
                    PaperAssignment.status != "withdrawn",
                )
            ).first()
            is not None
        )
    mine = svc.scope_classes(db, w.role, w.person, w.own_class)
    return row.class_id in mine or (row.body or {}).get("imported_by") == w.person


def _row(db: Session, row: PaperRow) -> dict[str, Any]:
    st = paper_status(db, row)
    body = row.body or {}
    return {
        "id": row.id,
        "twin_of": row.twin_of,
        "rules_version": row.rules_version,
        "title": f"Grade 3 maths, {row.kind}, {row.check_code}",
        "check_code": row.check_code,
        "class_id": row.class_id,
        "form": row.form,
        "kind": row.kind,
        "language": row.language,
        "items": len(body.get("items", [])),
        "status": row.status,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "created_by": body.get("imported_by") or row.approved_by or "rules",
        **{
            k: st[k]
            for k in (
                "source",
                "review",
                "frozen",
                "frozen_reason",
                "printable",
                "cohorts",
                "assignments",
            )
        },
    }


@router.get("/papers")
def list_papers(
    class_id: str | None = None,
    form: str | None = None,
    kind: str | None = None,
    status: str | None = None,
    source: str | None = None,
    w: Who = WHO,
    db: Session = SESSION,
) -> list[dict[str, Any]]:
    store.ensure_seeded(db)
    rows = db.scalars(select(PaperRow).order_by(PaperRow.created_at.desc())).all()
    out = []
    for r in rows:
        if r.status == "archived":  # every created paper is listed for everyone; only changes stay scoped
            continue
        v = _row(db, r)
        if (
            (form and v["form"] != form)
            or (kind and v["kind"] != kind)
            or (status and v["status"] != status)
            or (source and v["source"] != source)
        ):
            continue
        out.append(v)
    return out


def _read(db: Session, paper_id: str) -> PaperRow:
    """Reading a paper is open to every role for now; changing one still goes through `_own`."""
    row = db.get(PaperRow, paper_id)
    if row is None:
        raise HTTPException(404, "No such paper.")
    return row


def _own(db: Session, w: Who, paper_id: str) -> PaperRow:
    row = db.get(PaperRow, paper_id)
    if row is None or not _visible(db, w, row):
        raise HTTPException(404, "No such paper.")
    return row


@router.get("/papers/{paper_id}/status")
def status_of(paper_id: str, w: Who = WHO, db: Session = SESSION) -> dict[str, Any]:
    return paper_status(db, _read(db, paper_id))


@router.get("/papers/{paper_id}/detail")
def detail(paper_id: str, w: Who = WHO, db: Session = SESSION) -> dict[str, Any]:
    row = _read(db, paper_id)
    body = row.body or {}
    asg = db.scalars(
        select(PaperAssignment)
        .where(PaperAssignment.paper_id == row.id)
        .order_by(PaperAssignment.assigned_at)
    ).all()
    from services.papers.models import PaperEvent

    events = db.scalars(
        select(PaperEvent).where(PaperEvent.paper_id == row.id).order_by(PaperEvent.at)
    ).all()
    return {
        "overview": _row(db, row),
        "questions": [
            {
                k: it.get(k)
                for k in (
                    "n",
                    "operation",
                    "a",
                    "b",
                    "correct",
                    "competency",
                    "wrong",
                    "is_anchor",
                    "template",
                    "why",
                )
            }
            for it in explain.attach(body, store.template_skills(row))
        ],
        "editable": svc.locked_reason(db, row) is None
        and svc.may_change(w.role, w.person, w.own_class, row),
        "edit_mode": "in_place",
        "locked_reason": svc.locked_reason(db, row),
        "deletable": svc.in_use(db, row) is None
        and svc.may_change(w.role, w.person, w.own_class, row),
        "in_use": svc.in_use(db, row),
        "coverage": body.get("coverage", {}),
        "usage": {
            "assignments": [
                {
                    "id": a.id,
                    "kind": a.kind,
                    "status": a.status,
                    "due_date": a.due_date,
                    "sheets_entered": a.sheets_entered,
                    "sheets_expected": a.sheets_expected,
                }
                for a in asg
            ],
            "status": paper_status(db, row),
        },
        "history": [
            {"at": e.at.isoformat(), "event": e.event, "actor": e.actor, "detail": e.detail}
            for e in events
        ],
        "files": {
            "paper_pdf": store.printable(row),
            "key_pdf": store.printable(row),
            "layout": body.get("layout_map", "paper_studio"),
            "imported": store.imported(row),
        },
    }


# --- assignments -------------------------------------------------------------------------------------------


@router.get("/assignable")
def assignable(w: Who = WHO, db: Session = SESSION) -> dict[str, Any]:
    """Who this person may assign to: classes, and cohorts with member counts (counts only)."""
    classes = sorted(svc.scope_classes(db, w.role, w.person, w.own_class))
    cohorts = [
        {
            "id": c.id,
            "error": c.error,
            "status": c.status,
            "classes": len(svc.cohort_classes(db, c.id)),
        }
        for c in svc.my_cohorts(db, w.role, w.person)
    ]
    return {
        "classes": classes,
        "cohorts": cohorts,
        "note": "Cohorts form from the pre-test results, so a pre-test goes to teachers or classes."
        if not cohorts
        else "",
    }


class AssignIn(BaseModel):
    paper_id: str
    target_type: str = Field(pattern="^(teacher|class|cohort)$")
    target_id: str = Field(min_length=1, max_length=40)
    kind: str = Field(pattern="^(pre|post|termly)$")
    form: str = Field(pattern="^[AB]$")
    start_date: str | None = None
    due_date: str | None = None
    note: str = Field(default="", max_length=200)
    via: str = Field(default="user", pattern="^(user|assistant)$")


def _assignment_view(a: PaperAssignment) -> dict[str, Any]:
    return {
        "id": a.id,
        "paper_id": a.paper_id,
        "class_id": a.class_id,
        "cohort_id": a.cohort_id,
        "kind": a.kind,
        "form": a.form,
        "start_date": a.start_date,
        "due_date": a.due_date,
        "status": a.status,
        "note": a.note,
        "sheets_entered": a.sheets_entered,
        "sheets_expected": a.sheets_expected,
        "via_assistant": a.via_assistant,
    }


@router.post("/assignments")
def assign(body: AssignIn, w: Who = WHO, db: Session = SESSION) -> dict[str, Any]:
    if body.via == "assistant":
        raise HTTPException(403, "The assistant prepares a draft; only a person presses Assign.")
    rows = _wrap(
        svc.assign,
        db,
        role=w.role,
        person=w.person,
        own_class=w.own_class,
        paper_id=body.paper_id,
        target_type=body.target_type,
        target_id=body.target_id,
        kind=body.kind,
        form=body.form,
        start_date=body.start_date,
        due_date=body.due_date,
        note=body.note,
    )
    paper = db.get(PaperRow, body.paper_id)
    warnings = (
        [m for m in (svc.post_test_warning(db, paper, r.class_id) for r in rows) if m]
        if paper
        else []
    )
    return {"assignments": [_assignment_view(r) for r in rows], "warnings": sorted(set(warnings))}


@router.get("/assignments/mine")
def mine(w: Who = WHO, db: Session = SESSION) -> list[dict[str, Any]]:
    """Assigned to you: the papers assigned to this teacher's class."""
    if w.own_class is None:
        return []
    return [_assignment_view(a) for a in svc.for_class(db, w.own_class)]


@router.get("/assignments/progress")
def progress(w: Who = WHO, db: Session = SESSION) -> dict[str, Any]:
    return svc.progress(db, w.role, w.person)


class MarkIn(BaseModel):
    status: str = Field(pattern="^(opened|in_progress|completed)$")
    entered: int | None = Field(default=None, ge=0, le=200)
    expected: int | None = Field(default=None, ge=0, le=200)


@router.post("/assignments/{assignment_id}/mark")
def mark(assignment_id: str, body: MarkIn, w: Who = WHO, db: Session = SESSION) -> dict[str, Any]:
    if w.own_class is None:
        raise HTTPException(403, "Only a teacher's own phone marks progress.")
    a = _wrap(svc.mark, db, assignment_id, w.own_class, body.status, body.entered, body.expected)
    return _assignment_view(a)


@router.post("/assignments/{assignment_id}/withdraw")
def withdraw(assignment_id: str, w: Who = WHO, db: Session = SESSION) -> dict[str, Any]:
    return _assignment_view(_wrap(svc.withdraw, db, assignment_id, w.role, w.person))


# --- archive (a person's click) and duplicate ---------------------------------------------------------------


@router.post("/papers/{paper_id}/archive")
def archive(paper_id: str, w: Who = WHO, db: Session = SESSION) -> dict[str, Any]:
    if w.role != "coach":
        raise HTTPException(403, "Only a coach archives papers.")
    row = _own(db, w, paper_id)
    if db.scalars(
        select(PaperAssignment).where(
            PaperAssignment.paper_id == row.id,
            PaperAssignment.status.in_(("assigned", "opened", "in_progress")),
        )
    ).first():
        raise HTTPException(409, "Withdraw or finish its assignments first.")
    from services.papers.models import PaperEvent

    row.status = "archived"
    db.add(PaperEvent(event="archived", actor=w.person, paper_id=row.id))
    db.commit()
    return {"id": row.id, "status": row.status}


# --- edit and delete -------------------------------------------------------------------------------------------


class ItemEditIn(BaseModel):
    edits: list[dict[str, Any]] = Field(min_length=1, max_length=20)


@router.post("/papers/{paper_id}/items")
def edit_items(
    paper_id: str, body: ItemEditIn, w: Who = WHO, db: Session = SESSION
) -> dict[str, Any]:
    """Change the numbers of a paper in place, imported or generated. No copy is made."""
    _own(db, w, paper_id)
    row = _wrap(svc.edit_imported, db, paper_id, w.role, w.person, w.own_class, body.edits)
    found = [f"{f['rule']}: {f['detail']}" for f in (row.findings or [])][:5]
    return {**_row(db, row), "findings": found}


@router.get("/papers/{paper_id}/key")
def paper_key(paper_id: str, w: Who = WHO, db: Session = SESSION) -> dict[str, Any]:
    """The paper's own answer key for entering and reading its answers: every answer, wrong answer,
    probe and stage signature, worked out by the engine from the paper's numbers."""
    _read(db, paper_id)  # reading a key is open to every role for now
    row = db.get(PaperRow, paper_id)
    if row is None:
        raise HTTPException(404, "No such paper.")
    return keys.key_of(row.id, row.body, f"{row.kind} · {row.check_code}")


class CheckIn(BaseModel):
    items: list[dict[str, Any]] = Field(min_length=1, max_length=20)


@router.post("/papers/{paper_id}/items/check")
def check_items(
    paper_id: str, body: CheckIn, w: Who = WHO, db: Session = SESSION
) -> dict[str, Any]:
    """Would these numbers meet the rule of each item? Nothing is saved."""
    _own(db, w, paper_id)
    return {
        "items": _wrap(svc.check_numbers, db, paper_id, w.role, w.person, w.own_class, body.items)
    }


@router.delete("/papers/{paper_id}")
def delete_paper(paper_id: str, w: Who = WHO, db: Session = SESSION) -> dict[str, Any]:
    _own(db, w, paper_id)
    gone = _wrap(svc.delete_paper, db, paper_id, w.role, w.person, w.own_class)
    return {"deleted": gone}


@router.post("/papers/{paper_id}/twin")
def make_twin(paper_id: str, w: Who = WHO, db: Session = SESSION) -> dict[str, Any]:
    """The post-test twin of an imported pre-test: same skills and level, different numbers."""
    _own(db, w, paper_id)
    row = _wrap(svc.make_twin, db, paper_id, w.person, w.role)
    return _row(db, row)
