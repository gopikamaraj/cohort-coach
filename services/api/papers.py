"""Paper Studio over HTTP: generate and print check papers, the review queue, and the rules.

A teacher (or a coach for her) generates and prints; only the coach, who is the reviewer, uses the
review queue and the rules. The role comes from the server's session, never the request body. In
the judge demo, `X-Demo-Person` (a or b) lets one browser act as two different coaches, so the
two-person rule can be shown; it is ignored outside judge mode. No AI is called anywhere here.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.api.profiles import SESSION
from services.api.roles import judge_session, require
from services.papers import generator as gen
from services.papers import render, store
from services.papers.models import Immutable, PaperEvent, PaperReview, PaperRow, RuleVersion
from services.papers.rules import LAYOUTS, from_data, to_yaml

router = APIRouter(prefix="/api/papers", tags=["papers"])

GENERATE = Depends(require("papers.generate"))
REVIEW = Depends(require("papers.review"))
RULES = Depends(require("papers.rules"))
RULES_VIEW = Depends(require("papers.rules_view"))


def actor(role: str, person: str | None) -> str:
    """The pseudonymous id of the person acting (never a name)."""
    if judge_session() and person in ("a", "b"):
        return f"{role}-{person}"
    return f"{role}-demo"


def _db(db: Session) -> Session:
    store.ensure_seeded(db)
    return db


def _call(fn: Any, *args: Any, **kwargs: Any) -> Any:
    try:
        return fn(*args, **kwargs)
    except store.NotAllowed as exc:
        raise HTTPException(403, str(exc)) from exc
    except (store.BadState, Immutable) as exc:
        raise HTTPException(409, str(exc)) from exc
    except gen.CannotMeet as exc:
        raise HTTPException(422, {"rule": exc.rule, "explanation": exc.detail}) from exc
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def _paper(db: Session, paper_id: str) -> PaperRow:
    row = db.get(PaperRow, paper_id)
    if row is None:
        raise HTTPException(404, "No such paper.")
    return row


# --- papers --------------------------------------------------------------------------------


class CheckIn(BaseModel):
    id: str = Field(min_length=3, max_length=60, pattern=r"^[A-Za-z0-9:_#.-]+$")
    kind: str = "pre"
    form: str = Field(default="A", pattern=r"^[ABC]$")
    class_label: str = Field(default="", max_length=20)
    term: int = Field(default=1, ge=1, le=12)


class ProfileIn(BaseModel):
    """Class-level only: counts per error code, the number checked, or the intake answers."""

    source: str = "baseline"
    counts: dict[str, int] = Field(default_factory=dict)
    checked: int = Field(default=0, ge=0, le=200)
    built_from: list[str] = Field(default_factory=list, max_length=10)
    struggles: list[str] = Field(default_factory=list, max_length=3)
    taught: list[str] = Field(default_factory=list, max_length=3)
    not_assessed: list[str] = Field(default_factory=list, max_length=3)
    strength: int | None = Field(default=None, ge=1, le=200)
    similar_test: bool | None = None
    language: str = "en"


class GenerateIn(BaseModel):
    check: CheckIn
    profile: ProfileIn = Field(default_factory=ProfileIn)
    blueprint: str = "standard_10_5"
    language: str = "en"
    # the sample paper: the published numbers the judge's sample sheets and photos were made on
    sample: bool = False


@router.post("/generate")
def generate(
    body: GenerateIn,
    role: str = GENERATE,
    person: str | None = Header(default=None, alias="X-Demo-Person"),
    db: Session = SESSION,
) -> dict[str, Any]:
    db = _db(db)
    who = actor(role, person)
    if body.sample:
        form = "B" if body.check.kind == "post" else "A"
        row = _call(store.sample_paper, db, body.check.model_dump(), form, who, body.language)
        return {"paper": store.summary(row), "twin": None}
    row = _call(
        store.generate,
        db,
        body.check.model_dump(),
        body.profile.model_dump(),
        body.blueprint,
        body.language,
        who,
    )
    twin = store.twin_of(db, row.id)
    return {"paper": store.summary(row), "twin": store.summary(twin) if twin else None}


@router.get("")
def list_papers(
    class_id: str | None = None, _: str = GENERATE, db: Session = SESSION
) -> list[dict[str, Any]]:
    # every paper is listed for everyone for now (`class_id` stays so old callers still work)
    db = _db(db)
    rows = db.scalars(select(PaperRow).order_by(PaperRow.created_at)).all()
    return [store.summary(r) for r in rows]


@router.get("/queue")
def queue(_: str = REVIEW, db: Session = SESSION) -> list[dict[str, Any]]:
    db = _db(db)
    out = []
    for q in db.scalars(
        select(PaperReview).where(PaperReview.status == "open").order_by(PaperReview.created_at)
    ):
        row = db.get(PaperRow, q.paper_id)
        if row is not None:
            out.append(
                {
                    "queue_id": q.id,
                    "reason": q.reason,
                    "since": q.created_at.isoformat(),
                    "paper": store.summary(row),
                }
            )
    return out


@router.get("/events")
def events(limit: int = 50, _: str = REVIEW, db: Session = SESSION) -> list[dict[str, Any]]:
    rows = db.scalars(select(PaperEvent).order_by(PaperEvent.id.desc()).limit(min(limit, 200)))
    return [
        {
            "at": e.at.isoformat(),
            "event": e.event,
            "actor": e.actor,
            "paper_id": e.paper_id,
            "class_id": e.class_id,
            "check_id": e.check_id,
            "blueprint": e.blueprint,
            "rules_version": e.rules_version,
            "seed": e.seed,
            "hash": e.hash,
            "detail": e.detail,
        }
        for e in rows
    ]


@router.get("/{paper_id}")
def get_paper(paper_id: str, _: str = GENERATE, db: Session = SESSION) -> dict[str, Any]:
    row = _paper(_db(db), paper_id)
    twin = store.twin_of(db, row.id)
    return {**store.summary(row), "twin": store.summary(twin) if twin else None}


def _rules_of(db: Session, row: PaperRow) -> Any:
    """The rules version the paper pinned (it prints the same even after that version retires)."""
    return from_data(store.version(db, row.rules_version).body)


def _pdf_allowed(row: PaperRow, role: str) -> None:
    # A reviewer previews any paper; everyone else prints approved papers only.
    if store.imported(row):
        raise HTTPException(
            409, "This paper was imported: it is already printed, so the system does not print it."
        )
    if not store.printable(row) and role != "coach":
        raise HTTPException(409, "This paper is not approved yet, so it cannot be printed.")


def _layout(layout: str | None, row: PaperRow, role: str = "coach") -> str:
    lang = layout or row.language
    if lang not in LAYOUTS:
        raise HTTPException(422, f"No layout {lang}.")
    # The wording of each language is approved with the paper, so a teacher prints the language the
    # paper was made and approved in; a reviewer may preview any layout.
    if role != "coach" and lang != row.language:
        raise HTTPException(409, "Make the paper in this language to print it in this language.")
    return lang


@router.get("/{paper_id}/paper.pdf")
def paper_pdf(
    paper_id: str, layout: str | None = None, role: str = GENERATE, db: Session = SESSION
) -> Response:
    row = _paper(_db(db), paper_id)
    _pdf_allowed(row, role)
    pdf, _ = render.render_paper(row.body, _rules_of(db, row), _layout(layout, row, role))
    name = f"paper-{row.form}-{row.id}.pdf"
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{name}"'},
    )


@router.get("/{paper_id}/key.pdf")
def key_pdf(
    paper_id: str, layout: str | None = None, role: str = GENERATE, db: Session = SESSION
) -> Response:
    row = _paper(_db(db), paper_id)
    _pdf_allowed(row, role)
    pdf = render.render_key(row.body, _rules_of(db, row), _layout(layout, row, role))
    return Response(
        pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="key-{row.id}.pdf"'},
    )


@router.get("/{paper_id}/layout.json")
def layout_json(
    paper_id: str, layout: str | None = None, _: str = GENERATE, db: Session = SESSION
) -> dict[str, Any]:
    row = _paper(_db(db), paper_id)
    return render.render_paper(row.body, _rules_of(db, row), _layout(layout, row))[1]


@router.get("/{paper_id}/phone-key")
def phone_key(paper_id: str, _: str = GENERATE, db: Session = SESSION) -> dict[str, Any]:
    row = _paper(_db(db), paper_id)
    if not store.printable(row):
        raise HTTPException(409, "This paper is not approved yet.")
    return store.phone_key(row)


@router.post("/{paper_id}/freeze")
def freeze(paper_id: str, role: str = GENERATE, db: Session = SESSION) -> dict[str, Any]:
    return store.summary(_call(store.freeze, _db(db), paper_id, f"{role}-demo"))


class CustomIn(BaseModel):
    edits: list[dict[str, int]] = Field(min_length=1, max_length=15)


@router.post("/{paper_id}/custom")
def custom(
    paper_id: str, body: CustomIn, role: str = GENERATE, db: Session = SESSION
) -> dict[str, Any]:
    return store.summary(_call(store.custom_paper, _db(db), paper_id, body.edits, f"{role}-demo"))


class RejectIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


@router.post("/{paper_id}/approve")
def approve(
    paper_id: str,
    role: str = REVIEW,
    person: str | None = Header(default=None, alias="X-Demo-Person"),
    db: Session = SESSION,
) -> dict[str, Any]:
    return store.summary(_call(store.approve_paper, _db(db), paper_id, actor(role, person)))


@router.post("/{paper_id}/reject")
def reject(
    paper_id: str,
    body: RejectIn,
    role: str = REVIEW,
    person: str | None = Header(default=None, alias="X-Demo-Person"),
    db: Session = SESSION,
) -> dict[str, Any]:
    return store.summary(
        _call(store.reject_paper, _db(db), paper_id, actor(role, person), body.reason)
    )


# --- rules ---------------------------------------------------------------------------------

rules_router = APIRouter(prefix="/api/paper-rules", tags=["papers"])


def _version(v: RuleVersion, body: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {
        "number": v.number,
        "status": v.status,
        "author": v.author,
        "approver": v.approver,
        "parent": v.parent,
        "hash": v.body_hash,
        "diff": v.diff,
        "note": v.note,
        "created_at": v.created_at.isoformat() if v.created_at else None,
        "published_at": v.published_at.isoformat() if v.published_at else None,
        "retired_at": v.retired_at.isoformat() if v.retired_at else None,
    }
    if body:
        out["body"] = v.body
    return out


@rules_router.get("")
def list_rules(_: str = RULES_VIEW, db: Session = SESSION) -> dict[str, Any]:
    db = _db(db)
    rows = db.scalars(select(RuleVersion).order_by(RuleVersion.number.desc())).all()
    return {"published": store.published(db).number, "versions": [_version(v) for v in rows]}


@rules_router.get("/{number}")
def get_rules(number: int, _: str = RULES_VIEW, db: Session = SESSION) -> dict[str, Any]:
    v = _call(store.version, _db(db), number)
    return _version(v, body=True)


@rules_router.get("/{number}/export.yaml")
def export_yaml(number: int, _: str = RULES_VIEW, db: Session = SESSION) -> Response:
    v = _call(store.version, _db(db), number)
    return Response(
        to_yaml(from_data(v.body)),
        media_type="application/yaml",
        headers={"Content-Disposition": f'attachment; filename="rules-v{number}.yaml"'},
    )


class DraftIn(BaseModel):
    yaml: str | None = Field(default=None, max_length=200_000)
    body: dict[str, Any] | None = None
    note: str = Field(default="", max_length=500)


def _who(role: str, person: str | None) -> str:
    return actor(role, person)


@rules_router.post("/drafts")
def draft(
    body: DraftIn,
    role: str = RULES,
    person: str | None = Header(default=None, alias="X-Demo-Person"),
    db: Session = SESSION,
) -> dict[str, Any]:
    db = _db(db)
    who = _who(role, person)
    if body.yaml is not None:
        return _version(_call(store.import_yaml, db, body.yaml, who))
    if body.body is None:
        raise HTTPException(422, "Send the rules as YAML or as a body.")
    return _version(_call(store.create_draft, db, body.body, who, body.note))


@rules_router.post("/{number}/submit")
def submit(
    number: int,
    role: str = RULES,
    person: str | None = Header(default=None, alias="X-Demo-Person"),
    db: Session = SESSION,
) -> dict[str, Any]:
    return _version(_call(store.submit, _db(db), number, _who(role, person)))


@rules_router.post("/{number}/publish")
def publish(
    number: int,
    role: str = RULES,
    person: str | None = Header(default=None, alias="X-Demo-Person"),
    db: Session = SESSION,
) -> dict[str, Any]:
    return _version(_call(store.publish, _db(db), number, _who(role, person)))


@rules_router.post("/{number}/return")
def return_draft(
    number: int,
    body: RejectIn,
    role: str = RULES,
    person: str | None = Header(default=None, alias="X-Demo-Person"),
    db: Session = SESSION,
) -> dict[str, Any]:
    return _version(_call(store.return_draft, _db(db), number, _who(role, person), body.reason))


@rules_router.post("/{number}/retire")
def retire(
    number: int,
    role: str = RULES,
    person: str | None = Header(default=None, alias="X-Demo-Person"),
    db: Session = SESSION,
) -> dict[str, Any]:
    return _version(_call(store.retire, _db(db), number, _who(role, person)))


@rules_router.post("/{number}/test")
def test_rules(number: int, _: str = RULES, db: Session = SESSION) -> dict[str, Any]:
    """Test this rule: five sample items per template with their keys and wrong answers, and one
    sample paper per blueprint through every automatic check. Nothing is stored."""
    v = _call(store.version, _db(db), number)
    rules = from_data(v.body)
    samples: dict[str, Any] = {}
    for t in rules.templates:
        try:
            ref = gen.CheckRef("sample:1", "pre", "A", "sample", 1)
            picks = []
            for seed in range(5):
                rng = gen._rng("sample", t.id, seed)  # noqa: SLF001
                a, b = gen._pick(rng, rules, t, None, set())  # noqa: SLF001
                wrong, untracked, _p = gen.item_answers(rules, t, a, b)
                picks.append(
                    {
                        "a": a,
                        "b": b,
                        "correct": gen._correct(t.operation, a, b),  # noqa: SLF001
                        "wrong": wrong,
                        "untracked": untracked,
                    }
                )
            samples[t.id] = {"items": picks}
        except gen.CannotMeet as exc:
            samples[t.id] = {"error": {"rule": exc.rule, "explanation": exc.detail}}
    checks: dict[str, Any] = {}
    for bp in rules.blueprints:
        try:
            ref = gen.CheckRef("sample:1", "pre", "A", "sample", 1)
            paper = gen.generate_paper(ref, gen.baseline_profile("en"), rules, bp.id, v.number, 1)
            checks[bp.id] = {"findings": store.run_checks(paper.to_dict(), rules, "en")}
        except gen.CannotMeet as exc:
            checks[bp.id] = {"error": {"rule": exc.rule, "explanation": exc.detail}}
    return {"number": v.number, "samples": samples, "blueprints": checks}
