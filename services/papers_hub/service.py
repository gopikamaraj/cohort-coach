"""Import drafts, confirmation and assignments. Plain functions over a session; the API only wires.

Privacy: an upload is rendered to page images that live on disk for at most 24 hours (the review
screen shows them beside the table) and are deleted when the paper is confirmed or abandoned.
Only the printed questions are kept in the draft; handwriting and names are never read into it.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import secrets
import shutil
from collections.abc import Callable, Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ai.schemas import PaperRead
from services.api.db import ClassRoom, CohortMember, CohortSpace, Teacher
from services.papers import generator as gen
from services.papers import store, verifier
from services.papers.models import PaperEvent, PaperItemRow, PaperReview, PaperRow
from services.papers_hub import importer as imp
from services.papers_hub.models import PaperAssignment, PaperImport

ROOT = Path(__file__).resolve().parents[2]
TTL = timedelta(hours=24)
MAX_FILES = 6  # uploads
MAX_PAGES = 10  # pages read in all
ROLES = ("paper", "guide", "other")
MAX_NOTE = 500
SHARED = (
    "shared"  # papers are common to a block or school for now; per-class papers are on the roadmap
)
KINDS_OK = ("pre", "post", "termly")
MAX_KEY_ITEMS = 30
MAX_KEY_ANSWER = 999
MAX_BYTES = 8_000_000
LONG_EDGE = 1400
CLASS_RE = re.compile(r"^[A-Za-z0-9:_-]{1,40}$")
PERSON_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,29}$")
KINDS = ("pre", "post", "termly")
FORMS = ("A", "B")
EDITABLE_ITEM_FIELDS = ("a", "b", "operation", "include", "acknowledged", "unsure")
NOTE_BAD = re.compile(
    r"\d{6,}|@|https?://", re.I
)  # phone numbers, handles and links: no child data


class Refused(Exception):
    """The request is not allowed for this person or in this state."""


class Invalid(ValueError):
    """The input is not acceptable."""


class ReaderUnavailable(RuntimeError):
    """The model could not be asked (an API error, a usage limit, the budget): not a bad photo."""


READER_DOWN = (
    "The paper reader is not available right now, so nothing was read and nothing was kept. "
    "Try again later. Generate from rules still works: it needs no AI."
)


def import_dir() -> Path:
    return Path(os.environ.get("PAPER_IMPORT_DIR", str(ROOT / "data" / "paper_import")))


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def parse_key(raw: str) -> dict[int, int]:
    """The answer key the browser extracted from a key file: {"answers": {"1": 346, ...}}. Whole numbers only."""
    if not raw.strip():
        return {}
    try:
        answers = json.loads(raw)["answers"]
        out = {int(k): v for k, v in answers.items()}
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise Invalid("The answer key could not be read. Add the file again.") from exc
    if len(out) > MAX_KEY_ITEMS or any(
        not 1 <= n <= MAX_KEY_ITEMS
        or not isinstance(v, int)
        or isinstance(v, bool)
        or not 0 <= v <= MAX_KEY_ANSWER
        for n, v in out.items()
    ):
        raise Invalid("The answer key has a question or answer out of range.")
    return out


# --- upload to draft --------------------------------------------------------------------------


def render_pages(
    files: Sequence[tuple[str, bytes]], roles: Sequence[str] | None = None
) -> list[tuple[str, bytes]]:
    """(role, JPEG page) from PDFs and photos, scaled for the reader, at most MAX_PAGES in all.
    Pages of the question paper come first, then the teacher's guide, then anything else."""
    from PIL import Image, ImageOps

    if not files or len(files) > MAX_FILES:
        raise Invalid(f"Send up to {MAX_FILES} files: PDFs or photos.")
    if sum(len(d) for _, d in files) > MAX_BYTES:
        raise Invalid("That upload is too large.")
    kinds = [r if r in ROLES else "paper" for r in (roles or [])]
    kinds += ["paper"] * (len(files) - len(kinds))
    pages: list[tuple[str, Image.Image]] = []
    for (name, data), role in zip(files, kinds, strict=False):
        if data[:5] == b"%PDF-":
            import pypdfium2 as pdfium

            pdf = pdfium.PdfDocument(data)
            for i in range(min(len(pdf), MAX_PAGES - len(pages))):
                pages.append((role, pdf[i].render(scale=1.6).to_pil().convert("RGB")))
        else:
            if len(pages) >= MAX_PAGES:
                break
            try:
                img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
            except OSError as exc:
                raise Invalid(f"{name[:40]} is not a PDF or a photo.") from exc
            pages.append((role, img))
    order = {r: i for i, r in enumerate(ROLES)}
    pages.sort(key=lambda p: order[p[0]])  # stable: files keep their order inside a role
    out: list[tuple[str, bytes]] = []
    for role, img in pages[:MAX_PAGES]:
        scale = LONG_EDGE / max(img.size)
        if scale < 1:
            img = img.resize((round(img.width * scale), round(img.height * scale)))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=85)
        out.append((role, buf.getvalue()))
    return out


# A reader takes the page; for a teacher's guide or with a note it is also given role= and note=.
Reader = Callable[..., "tuple[PaperRead | None, float]"]


def sweep(db: Session) -> int:
    """Delete expired or finished imports' files and mark them gone. Runs on every request."""
    n = 0
    for row in db.scalars(
        select(PaperImport).where(PaperImport.status.in_(("draft", "confirmed")))
    ):
        if _aware(row.expires_at) < _now() and row.status == "draft":
            _delete_files(row.id)
            row.status = "gone"
            n += 1
    if n:
        db.commit()
    return n


def _delete_files(import_id: str) -> None:
    shutil.rmtree(import_dir() / import_id, ignore_errors=True)


def daily_cap() -> int:
    return int(os.environ.get("PAPER_IMPORTS_PER_DAY", "10"))


def start_import(
    db: Session,
    owner: str,
    role: str,
    files: Sequence[tuple[str, bytes]],
    reader: Reader,
    roles: Sequence[str] | None = None,
    note: str = "",
    key: dict[int, int] | None = None,
    kind: str = "",
) -> PaperImport:
    sweep(db)
    note = note.strip()[:MAX_NOTE]
    file_hash = hashlib.sha256(
        b"".join(d for _, d in files)
        + "|".join(roles or []).encode()
        + note.encode()
        + json.dumps(key or {}, sort_keys=True).encode()
        + kind.encode()
    ).hexdigest()
    same = db.scalars(
        select(PaperImport).where(
            PaperImport.owner == owner,
            PaperImport.file_hash == file_hash,
            PaperImport.status == "draft",
        )
    ).first()
    if same is not None:
        return same
    since = _now() - timedelta(days=1)
    made = db.scalar(
        select(func.count())
        .select_from(PaperImport)
        .where(PaperImport.owner == owner, PaperImport.created_at >= since)
    )
    if (made or 0) >= daily_cap():
        raise Refused("You have used today's paper imports. Try tomorrow, or type the items in.")
    pages = render_pages(files, roles)
    reads: list[PaperRead] = []
    guide_reads: list[PaperRead] = []
    cost = 0.0
    for page_role, jpeg in pages:
        if page_role == "other":
            continue  # kept for her to look at, never read
        extra = {} if page_role == "paper" and not note else {"role": page_role, "note": note}
        read, c = reader(jpeg, **extra)
        cost += c
        if read is not None:
            (guide_reads if page_role == "guide" else reads).append(read)
    if not reads:
        raise Invalid("The reader could not find a paper on these pages. Try a clearer photo.")
    draft = imp.merge(reads, guide_reads, key)
    if kind in KINDS_OK:  # chosen on the Papers page before the upload
        draft = {**draft, "kind": kind, "form": "B" if kind == "post" else "A"}
    draft = imp.recompute(draft)
    imp_id = "I-" + secrets.token_hex(8)
    folder = import_dir() / imp_id
    folder.mkdir(parents=True, exist_ok=True)
    for i, (_, jpeg) in enumerate(pages, 1):
        (folder / f"p{i}.jpg").write_bytes(jpeg)
    row = PaperImport(
        id=imp_id,
        owner=owner,
        role=role,
        file_hash=file_hash,
        draft=draft,
        history=[],
        pages=len(pages),
        cost_usd=cost,
        expires_at=_now() + TTL,
    )
    db.add(row)
    db.commit()
    return row


def live_reader(ctx: Any) -> Reader:
    """Call 16 through the product's client (audited, prompt-versioned, cost-capped)."""
    import base64

    from ai.client import BudgetExceeded, CallInput, run_call

    def read(jpeg: bytes, role: str = "paper", note: str = "") -> tuple[PaperRead | None, float]:
        trusted = {} if role == "paper" else {"file_role": role}
        untrusted = {"teacher_note": note} if note else {}
        try:
            run = run_call(
                16,
                CallInput(
                    trusted=trusted,
                    untrusted=untrusted,
                    images=[("image/jpeg", base64.b64encode(jpeg).decode())],
                ),
                context=ctx,
            )
        except BudgetExceeded as exc:
            raise ReaderUnavailable(READER_DOWN) from exc
        if run.output is None and (run.fallback_used or "").endswith("api_error"):
            raise ReaderUnavailable(READER_DOWN)  # the request failed: the page was never read
        out = run.output
        return (out if run.ok and isinstance(out, PaperRead) else None), run.cost_usd

    return read


# --- reading and editing a draft ------------------------------------------------------------------


def get_import(db: Session, import_id: str, owner: str) -> PaperImport:
    sweep(db)
    row = db.get(PaperImport, import_id)
    if row is None or row.owner != owner or row.status == "gone":
        raise Refused("This import has ended. Upload the paper again.")
    return row


def page_bytes(row: PaperImport, n: int) -> bytes:
    path = import_dir() / row.id / f"p{n}.jpg"
    if row.status != "draft" or not path.is_file():
        raise Refused("The page is no longer kept.")
    return path.read_bytes()


def _find_item(draft: dict[str, Any], n: int) -> dict[str, Any]:
    it = next((i for i in draft["items"] if i["n"] == n), None)
    if it is None:
        raise Invalid(f"No item {n}.")
    return it


def apply_edit(draft: dict[str, Any], field: str, value: Any) -> tuple[dict[str, Any], Any]:
    """One whitelisted change to the draft. Returns the new draft and the value it replaced."""
    if field == "class_id":
        if not isinstance(value, str) or not CLASS_RE.match(value):
            raise Invalid("The class is not valid.")
        old = draft.get("class_id")
        return {**draft, "class_id": value}, old
    if field == "kind":
        if value not in KINDS:
            raise Invalid("The kind must be pre, post or termly.")
        # the pairing letter inside the paper follows from the kind; nobody is asked for it
        return {**draft, "kind": value, "form": "B" if value == "post" else "A"}, draft.get("kind")
    if field == "language":
        if value not in ("en", "hi", "ta"):
            raise Invalid("The language must be en, hi or ta.")
        return {**draft, "language": value}, draft.get("language")
    m = re.fullmatch(r"items\.(\d{1,2})\.(\w+)", field)
    if m and m[2] in EDITABLE_ITEM_FIELDS:
        n, name = int(m[1]), m[2]
        items = [dict(i) for i in draft["items"]]
        it = next(i for i in items if i["n"] == _find_item(draft, n)["n"])
        old = it.get(name)
        if name in ("a", "b"):
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or not 0 <= value <= imp.MAX_OPERAND
            ):
                raise Invalid("A number must be a whole number from 0 to 999.")
            it[name] = value
            it["unsure"] = False  # she looked at it and fixed it
        elif name == "operation":
            if value not in ("dictate", "add", "subtract"):
                raise Invalid("The operation must be dictate, add or subtract.")
            it[name] = value
        elif name == "include":
            it["user_excluded"] = not bool(value)  # her choice outlasts a later edit
            it[name] = bool(value)
        else:
            it[name] = bool(value)
        return {**draft, "items": items}, old
    raise Invalid("That field cannot be changed this way.")


def edit_draft(
    db: Session, import_id: str, owner: str, edits: Sequence[dict[str, Any]], via: str = "user"
) -> PaperImport:
    row = get_import(db, import_id, owner)
    if row.status != "draft":
        raise Refused("This paper is already confirmed.")
    draft = dict(row.draft)
    history = list(row.history)
    for e in edits[:20]:
        draft, old = apply_edit(draft, str(e.get("field")), e.get("value"))
        history.append(
            {
                "field": e["field"],
                "old": old,
                "new": e["value"],
                "via": via,
                "at": _now().isoformat(),
            }
        )
        draft.setdefault("changes", {})
        draft["changes"] = {**draft["changes"], e["field"]: {"old": old, "via": via}}
        draft = imp.recompute(draft) if "items" in draft else draft
    row.draft, row.history = draft, history
    db.commit()
    return row


def _restore(draft: dict[str, Any], field: str, old: Any) -> dict[str, Any]:
    """Put a field back to what it was, including "nothing" (no validation: it was valid before)."""
    if field == "kind":
        return {**draft, "kind": old, "form": ("B" if old == "post" else "A") if old else None}
    if field in ("class_id", "language"):
        return {**draft, field: old}
    m = re.fullmatch(r"items\.(\d{1,2})\.(\w+)", field)
    if not m:
        return draft
    items = [dict(i) for i in draft["items"]]
    for it in items:
        if it["n"] == int(m[1]):
            it[m[2]] = old
            if m[2] == "include":
                it["user_excluded"] = not bool(old)
    return {**draft, "items": items}


def undo(db: Session, import_id: str, owner: str) -> PaperImport:
    row = get_import(db, import_id, owner)
    if row.status != "draft" or not row.history:
        raise Refused("There is nothing to undo.")
    last = row.history[-1]
    draft = _restore(dict(row.draft), last["field"], last["old"])
    changes = {k: v for k, v in draft.get("changes", {}).items() if k != last["field"]}
    draft = imp.recompute({**draft, "changes": changes})
    row.draft, row.history = draft, list(row.history[:-1])
    db.commit()
    return row


def abandon(db: Session, import_id: str, owner: str) -> None:
    row = get_import(db, import_id, owner)
    _delete_files(row.id)
    row.status = "gone"
    db.commit()


# --- confirm: the draft becomes a paper --------------------------------------------------------------


def _persist_imported(
    db: Session,
    draft: dict[str, Any],
    owner: str,
    actor: str,
    import_id: str,
    *,
    twin_of: str | None = None,
    status: str = "confirmed",
    findings: list[Any] | None = None,
    review: str | None = "imported_pdf",
    source: str = "imported_pdf",
) -> PaperRow:
    """Store a paper whose items are in `draft` (from an import, or the twin of one)."""
    store.ensure_seeded(db)
    rv = store.published(db)
    items = [i for i in draft["items"] if i["include"]]
    body_items = [
        {
            "n": k,
            "slot": k,
            "template": "imported",
            "competency": i["competency"],
            "section": "imported",
            "operation": i["operation"],
            "a": i["a"],
            "b": i["b"] or 0,
            "correct": i["correct"],
            "wrong": i["wrong"],
            "untracked": {},
            "is_anchor": False,
            "difficulty": None,
            "twin_of": i.get("twin_of"),
        }
        for k, i in enumerate(items, 1)
    ]
    check_code = draft["header"].get("check_code") or f"{draft['kind'].upper()} · IMPORTED"
    digest = hashlib.sha256(json.dumps(body_items, sort_keys=True).encode()).hexdigest()
    pid = "P-" + digest[:12]
    if db.get(PaperRow, pid) is not None:
        pid = "P-" + hashlib.sha256((digest + import_id).encode()).hexdigest()[:12]
    layout = "approximate"

    body = {
        "check_id": f"{draft['class_id']}:import",
        "check_code": check_code,
        "form": draft["form"],
        "kind": draft["kind"],
        "seed": "imported",
        "blueprint": "imported",
        "rules_version": rv.number,
        "language": draft["language"] if draft["language"] in ("en", "hi", "ta") else "en",
        "profile": {
            "source": "imported",
            "weights": {},
            "not_assessed": [],
            "language": "en",
            "strength": None,
            "built_from": [],
        },
        "not_assessed": [],
        "coverage": draft["coverage"],
        "items": body_items,
        "source": source,
        "layout_map": layout,
        "imported_by": owner,
        "dropped_items": [i["n"] for i in draft["items"] if not i["include"]],
        "hash": digest,
    }
    paper = PaperRow(
        id=pid,
        check_id=body["check_id"],
        class_id=draft["class_id"],
        check_code=check_code,
        form=draft["form"],
        kind=draft["kind"],
        seed="imported",
        blueprint="imported",
        blueprint_version=rv.number,
        rules_version=rv.number,
        language=body["language"],
        profile_id=None,
        status=status,
        hash=digest,
        twin_of=twin_of,
        custom=False,
        findings=findings or [],
        body=body,
    )
    db.add(paper)
    db.flush()  # the paper exists before its items point at it (Postgres checks the order)
    for it in body_items:
        db.add(
            PaperItemRow(
                paper_id=pid,
                n=it["n"],
                slot=it["slot"],
                template="imported",
                a=it["a"],
                b=it["b"],
                correct=it["correct"],
                wrong=it["wrong"],
                is_anchor=False,
                twin_of=None,
            )
        )
    db.flush()
    if review:
        db.add(PaperReview(paper_id=pid, reason=review))
    db.add(
        PaperEvent(
            event="imported",
            actor=actor,
            paper_id=pid,
            class_id=draft["class_id"],
            hash=digest,
            detail=f"{len(items)} items, {draft.get('sheets_read', 0)} sheet(s)",
        )
    )
    return paper


def confirm(db: Session, import_id: str, owner: str, actor: str) -> PaperRow:
    row = get_import(db, import_id, owner)
    if row.status != "draft":
        raise Refused("This paper is already confirmed.")
    draft = imp.recompute(dict(row.draft))
    blocked = imp.blocking(draft)
    if blocked:
        raise Refused(
            "Answer the open questions first: " + "; ".join(q["why"] for q in blocked[:3])
        )
    paper = _persist_imported(db, draft, owner, actor, row.id)
    row.status, row.paper_id = "confirmed", paper.id
    row.draft = {
        **draft,
        "items": [{k: v for k, v in i.items() if k != "printed_answer"} for i in draft["items"]],
    }
    _delete_files(row.id)  # the upload goes when the paper is confirmed
    db.commit()
    return paper


# --- the post-test twin of an imported pre-test --------------------------------------------------------


def _template_for(rules: Any, operation: str, a: int, b: int) -> Any | None:
    """The most specific rule template an item fits: same operation, and its digit rules hold."""
    best = None
    for t in rules.templates:
        if t.retired or t.operation != operation or not gen._fits(t, a, b):  # noqa: SLF001
            continue
        if best is None or len(t.constraints) > len(best.constraints):
            best = t
    return best


def twin_numbers(
    pre_items: Sequence[dict[str, Any]], rules: Any, seed: str
) -> list[tuple[int, int]]:
    """New numbers for every item, with the shape of the old one (same operation, digits, carry or
    borrow, ones total or gap), never repeating a pair from the pre-test. Code only: no AI."""
    import random

    rng = random.Random(f"{seed}|twin")
    avoid = {(int(i["a"]), int(i["b"])) for i in pre_items}
    out: list[tuple[Any, int, int]] = []
    cannot: list[int] = []
    for it in pre_items:
        a, b = int(it["a"]), int(it["b"])
        t = _template_for(rules, it["operation"], a, b)
        if t is None:
            cannot.append(it["n"])
            continue
        try:
            pair = gen._pick(rng, rules, t, gen._difficulty(t, a, b), avoid, (a, b))  # noqa: SLF001
        except gen.CannotMeet:
            cannot.append(it["n"])
            continue
        avoid.add(pair)
        out.append((t, pair[0], pair[1]))
    if cannot:
        listed = ", ".join(str(n) for n in cannot)
        raise Invalid(f"A twin cannot be made for item {listed}: no rule fits it.")
    return out


def make_twin(db: Session, paper_id: str, owner: str, role: str) -> PaperRow:
    """A post-test with the same skills and level as an imported pre-test and different numbers."""
    pre = db.get(PaperRow, paper_id)
    if pre is None or (pre.body or {}).get("source") != "imported_pdf":
        raise Invalid("A twin can be made for a paper you brought in.")
    if pre.kind != "pre":
        raise Invalid("Only a pre-test has a post-test twin.")
    existing = store.twin_of(db, pre.id)
    if existing is not None:
        return existing
    store.ensure_seeded(db)
    rules, rv = store.usable_rules(db, None)
    items = [i for i in pre.body["items"]]
    picks = twin_numbers(items, rules, pre.id)
    new_items = []
    for it, (t, a, b) in zip(items, picks, strict=True):
        # the wrong answers come from the same rules the generated papers use, so the checks agree
        wrong, _, _ = gen.item_answers(rules, t, a, b)
        new_items.append(
            {
                "n": it["n"],
                "operation": t.operation,
                "a": a,
                "b": b if t.operation != "dictate" else 0,
                "correct": gen._correct(t.operation, a, b),  # noqa: SLF001
                "wrong": wrong,
                "competency": imp.COMPETENCY.get(t.operation),
                "supported": True,
                "include": True,
                "twin_of": it["n"],
            }
        )
    cover = imp.coverage(new_items)
    code = (pre.check_code or "").strip()
    twin_code = re.sub(r"PRE", "POST", code) if re.search(r"PRE", code) else f"POST · {code}"
    draft = {
        "header": {"check_code": twin_code},
        "kind": "post",
        "form": "B",
        "class_id": pre.class_id,
        "language": pre.language,
        "coverage": cover,
        "items": new_items,
    }
    # the automatic checks the rules papers go through, including the twin check against the pre-test
    probe = {
        "items": [
            {**i, "is_anchor": False, "difficulty": None, "template": "imported"}
            for i in _body(draft)
        ]
    }
    findings = [
        {"rule": f.rule, "item": f.item, "detail": f.detail}
        for f in verifier.verify_items(probe, {"items": pre.body["items"]})
    ]
    twin = _persist_imported(
        db,
        draft,
        owner,
        owner,
        pre.id,
        twin_of=pre.id,
        status="queued" if findings else "auto_approved",
        findings=findings,
        review="twin_made" if findings else None,
        source="imported_twin",
    )
    db.commit()
    return twin


def _body(draft: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "n": k,
            "operation": i["operation"],
            "a": i["a"],
            "b": i["b"] or 0,
            "correct": i["correct"],
            "wrong": i["wrong"],
            "twin_of": i.get("twin_of"),
        }
        for k, i in enumerate(draft["items"], 1)
    ]


def pairs_shared_with_pre_tests(
    db: Session, draft: dict[str, Any], exclude: str | None = None
) -> list[str]:
    """A post-test must not repeat a pre-test's numbers: the codes of the pre-tests that share a pair."""
    if draft.get("kind") != "post":
        return []
    mine = {(int(i["a"]), int(i["b"] or 0)) for i in draft["items"] if i.get("a") is not None}
    out = []
    for r in db.scalars(select(PaperRow).where(PaperRow.kind == "pre")):
        if r.id == exclude:
            continue
        theirs = {(int(i["a"]), int(i["b"] or 0)) for i in (r.body or {}).get("items", [])}
        if mine & theirs:
            out.append(r.check_code)
    return sorted(set(out))


# --- assignments ------------------------------------------------------------------------------------------


def known_classes(db: Session) -> set[str]:
    ids = {c for (c,) in db.execute(select(Teacher.class_id).where(Teacher.class_id.is_not(None)))}
    ids |= {c for (c,) in db.execute(select(ClassRoom.class_id))}
    return {i for i in ids if i}


def cohort_classes(db: Session, cohort_id: str) -> list[str]:
    tids = [
        t
        for (t,) in db.execute(
            select(CohortMember.teacher_id).where(CohortMember.cohort_id == cohort_id)
        )
    ]
    if not tids:
        return []
    return sorted(
        {
            c
            for (c,) in db.execute(
                select(Teacher.class_id).where(
                    Teacher.teacher_id.in_(tids), Teacher.class_id.is_not(None)
                )
            )
            if c
        }
    )


def my_cohorts(db: Session, role: str, person: str) -> list[CohortSpace]:
    rows = db.scalars(select(CohortSpace)).all()
    if role == "mentor":
        return [c for c in rows if person in (c.mentor_ids or [])]
    if role == "coach":
        return [c for c in rows if c.coach_id == person]
    return []


def scope_classes(db: Session, role: str, person: str, own_class: str | None) -> set[str]:
    """The classes this person may assign to. Teacher: her own. Mentor: classes in cohorts she
    mentors. Coach: classes in her cohorts, and any known class before cohorts exist."""
    if role == "teacher":
        return {own_class} if own_class else set()
    cohorts = my_cohorts(db, role, person)
    classes = {c for co in cohorts for c in cohort_classes(db, co.id)}
    if role == "coach":
        classes |= known_classes(db)
    return classes


def paper_for_assignment(db: Session, paper_id: str) -> PaperRow:
    p = db.get(PaperRow, paper_id)
    if p is None:
        raise Invalid("No such paper.")
    ok = p.status in ("auto_approved", "approved", "confirmed")
    if not ok or p.status == "rejected":
        raise Refused("A paper must be approved or confirmed before it can be assigned.")
    return p


def _clean_note(note: str) -> str:
    note = (note or "").strip()[:200]
    if NOTE_BAD.search(note):
        raise Invalid(
            "A note cannot hold phone numbers, handles or links, or anything about a child."
        )
    return note


def _date(v: str | None) -> str | None:
    if not v:
        return None
    try:
        return date.fromisoformat(v).isoformat()
    except ValueError as exc:
        raise Invalid("Dates look like 2026-11-07.") from exc


def assign(
    db: Session,
    *,
    role: str,
    person: str,
    own_class: str | None,
    paper_id: str,
    target_type: str,
    target_id: str,
    kind: str,
    form: str,
    start_date: str | None,
    due_date: str | None,
    note: str,
    via_assistant: bool = False,
) -> list[PaperAssignment]:
    paper = paper_for_assignment(db, paper_id)
    if kind not in KINDS or form not in FORMS:
        raise Invalid("Choose the kind and the form.")
    if paper.kind != kind or paper.form != form:
        raise Invalid("The kind and form must be the paper's own.")
    note = _clean_note(note)
    start, due = _date(start_date), _date(due_date)
    if start and due and due < start:
        raise Invalid("The due date is before the start date.")
    allowed = scope_classes(db, role, person, own_class)
    cohort_id: str | None = None
    if target_type == "cohort":
        if kind == "pre":
            raise Invalid("A pre-test cannot go to a cohort: cohorts form from its results.")
        if role == "teacher":
            raise Refused("A teacher assigns only to her own class.")
        cohorts = {c.id for c in my_cohorts(db, role, person)}
        if target_id not in cohorts:
            raise Refused("That cohort is not one you run.")
        cohort_id = target_id
        classes = cohort_classes(db, target_id)
        if not classes:
            raise Invalid("That cohort has no classes yet.")
    elif target_type in ("class", "teacher"):
        cid = target_id
        if target_type == "teacher":
            t = db.get(Teacher, target_id)
            cid = (t.class_id if t else None) or ""
        if not cid or cid not in allowed:
            raise Refused("You cannot assign to that class.")
        classes = [cid]
    else:
        raise Invalid("Choose a teacher, a class or a cohort.")
    rows: list[PaperAssignment] = []
    for c in classes:
        dup = db.scalars(
            select(PaperAssignment).where(
                PaperAssignment.class_id == c,
                PaperAssignment.paper_id == paper_id,
                PaperAssignment.kind == kind,
                PaperAssignment.status != "withdrawn",
            )
        ).first()
        if dup is not None:
            raise Invalid("This paper is already assigned to that class for this kind.")
        row = PaperAssignment(
            id="A-" + secrets.token_hex(8),
            paper_id=paper_id,
            target_type=target_type,
            target_id=target_id,
            class_id=c,
            cohort_id=cohort_id,
            kind=kind,
            form=form,
            assigned_by=person,
            assigned_role=role,
            start_date=start,
            due_date=due,
            note=note,
            via_assistant=via_assistant,
        )
        db.add(row)
        rows.append(row)
    db.add(
        PaperEvent(
            event="assigned",
            actor=person,
            paper_id=paper_id,
            detail=f"{kind} to {len(rows)} class(es) via {target_type}",
        )
    )
    db.commit()
    return rows


def post_test_warning(db: Session, paper: PaperRow, class_id: str) -> str | None:
    """A post-test goes with the pre-test it twins; say so if that pre-test was never assigned."""
    if paper.kind != "post":
        return None
    if paper.twin_of is None:
        return None
    done = db.scalars(
        select(PaperAssignment).where(
            PaperAssignment.class_id == class_id,
            PaperAssignment.paper_id == paper.twin_of,
            PaperAssignment.status != "withdrawn",
        )
    ).first()
    return None if done else "The pre-test it twins has not been assigned to this class."


def withdraw(db: Session, assignment_id: str, role: str, person: str) -> PaperAssignment:
    a = db.get(PaperAssignment, assignment_id)
    if a is None:
        raise Invalid("No such assignment.")
    if a.assigned_by != person and role != "coach":
        raise Refused("Only the person who assigned it, or a coach, can withdraw it.")
    if a.sheets_entered > 0 or a.status in ("in_progress", "completed"):
        raise Refused("Sheets are already entered, so it cannot be withdrawn.")
    a.status = "withdrawn"
    db.commit()
    return a


def for_class(db: Session, class_id: str) -> list[PaperAssignment]:
    return list(
        db.scalars(
            select(PaperAssignment)
            .where(PaperAssignment.class_id == class_id, PaperAssignment.status != "withdrawn")
            .order_by(PaperAssignment.assigned_at.desc())
        )
    )


def mark(
    db: Session,
    assignment_id: str,
    class_id: str,
    status: str,
    entered: int | None = None,
    expected: int | None = None,
) -> PaperAssignment:
    """The teacher's phone says what became of it: opened, in progress, completed. Counts only."""
    a = db.get(PaperAssignment, assignment_id)
    if a is None or a.class_id != class_id:
        raise Refused("That is not assigned to your class.")
    if a.status == "withdrawn":
        raise Refused("This assignment was withdrawn.")
    if status not in ("opened", "in_progress", "completed"):
        raise Invalid("The status must be opened, in_progress or completed.")
    order = ["assigned", "opened", "in_progress", "completed"]
    if order.index(status) >= order.index(a.status):
        a.status = status
    if entered is not None:
        a.sheets_entered = max(0, min(entered, 200))
    if expected is not None:
        a.sheets_expected = max(0, min(expected, 200))
    db.commit()
    return a


def progress(db: Session, role: str, person: str) -> dict[str, Any]:
    """Counts only, for the person who assigned: how many, opened, sheets entered, completed."""
    rows = db.scalars(
        select(PaperAssignment).where(
            PaperAssignment.assigned_by == person, PaperAssignment.status != "withdrawn"
        )
    ).all()
    return {
        "assigned": len(rows),
        "opened": sum(r.status in ("opened", "in_progress", "completed") for r in rows),
        "sheets_entered": sum(r.sheets_entered for r in rows),
        "sheets_expected": sum(r.sheets_expected for r in rows),
        "completed": sum(r.status == "completed" for r in rows),
    }


# --- edit and delete a paper ------------------------------------------------------------------------------


def in_use(db: Session, row: PaperRow) -> str | None:
    """Why this paper can no longer change or go: a sheet was entered on it, or an assignment is live.
    None means it is free. (A post-test twin is frozen when made; that alone is not use.)"""
    sheet = db.scalars(
        select(PaperEvent).where(
            PaperEvent.paper_id == row.id,
            PaperEvent.event == "frozen",
            PaperEvent.detail == "first sheet entered",
        )
    ).first()
    if sheet is not None:
        return "a sheet of a check is entered on it"
    live = db.scalars(
        select(PaperAssignment).where(
            PaperAssignment.paper_id == row.id, PaperAssignment.status != "withdrawn"
        )
    ).first()
    return "it is assigned to a class" if live is not None else None


def locked_reason(db: Session, row: PaperRow) -> str | None:
    """Why the numbers of this paper cannot change: in use, or frozen when it was made (a post-test
    twin stays as it is until its track ends)."""
    why = in_use(db, row)
    if why:
        return why
    return "it is a post-test, locked until its track ends" if row.frozen_at is not None else None


def edit_generated(
    db: Session, row: PaperRow, person: str, edits: Sequence[dict[str, Any]]
) -> PaperRow:
    """A paper made by the rules, changed in the same paper: the generator's own functions work out
    every answer and check again, and the paper goes back to review, as any hand-chosen numbers do."""
    base = {i["n"]: (i["a"], i["b"]) for i in row.body["items"]}
    changed: dict[int, tuple[int, int]] = {}
    for e in edits[:20]:
        m = re.fullmatch(r"items\.(\d{1,2})\.(a|b)", str(e.get("field")))
        v = e.get("value")
        if not m or int(m[1]) not in base:
            raise Invalid("Only the numbers of the items can be changed on this paper.")
        if not isinstance(v, int) or isinstance(v, bool) or not 0 <= v <= imp.MAX_OPERAND:
            raise Invalid("A number must be a whole number from 0 to 999.")
        n = int(m[1])
        a, b = changed.get(n, base[n])
        changed[n] = (v, b) if m[2] == "a" else (a, v)
    if not changed:
        raise Invalid("Nothing was changed.")
    try:
        return store.edit_in_place(
            db, row.id, [{"n": n, "a": a, "b": b} for n, (a, b) in changed.items()], person
        )
    except (store.BadState, ValueError, KeyError) as exc:
        db.rollback()
        raise Invalid(f"Those numbers cannot be used on this paper: {exc}") from exc


def check_numbers(
    db: Session,
    paper_id: str,
    role: str,
    person: str,
    own_class: str | None,
    items: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Dry run for the edit form: would these numbers meet the rule of each item? Nothing is saved.
    Code works out the answer and names the rule in words, so the screen never holds a rule."""
    row = db.get(PaperRow, paper_id)
    if row is None or not may_change(role, person, own_class, row):
        raise Refused("You cannot change this paper.")
    if store.imported(row):
        return [
            {"n": int(i["n"]), "ok": True, "problems": [], "answer": None, "rule": None}
            for i in items[:20]
        ]
    rules, _rv = store.usable_rules(db, row.rules_version)
    out: list[dict[str, Any]] = []
    for i in items[:20]:
        n, a, b = int(i["n"]), int(i["a"]), int(i.get("b", 0))
        it = next((x for x in row.body["items"] if x["n"] == n), None)
        if it is None:
            raise Invalid("No such item.")
        t = rules.template(it["template"])
        problems: list[str] = []
        answer: int | None = None
        if not store.gen._fits(t, a, b):  # noqa: SLF001
            problems.append(f"{a}, {b} do not fit: {t.digit_pattern}")
        else:
            answer = store.gen._correct(t.operation, a, b)  # noqa: SLF001
            _w, _u, found = store.gen.item_answers(rules, t, a, b)
            problems += found
        out.append(
            {
                "n": n,
                "ok": not problems,
                "problems": problems,
                "answer": answer,
                "rule": t.digit_pattern,
            }
        )
    return out


def may_change(role: str, person: str, own_class: str | None, row: PaperRow) -> bool:
    """A coach, the class's own teacher or mentor, or the person who imported it."""
    if role == "coach":
        return True
    return row.class_id == own_class or (row.body or {}).get("imported_by") == person


def edit_imported(
    db: Session,
    paper_id: str,
    role: str,
    person: str,
    own_class: str | None,
    edits: Sequence[dict[str, Any]],
) -> PaperRow:
    """Change the numbers of an imported paper in place. Code recomputes every key and probe, the
    paper goes back to "confirmed" and, if a reviewer had approved it, back into the review queue."""
    row = db.get(PaperRow, paper_id)
    if row is None:
        raise Invalid("No such paper.")
    if not may_change(role, person, own_class, row):
        raise Refused("You cannot change this paper.")
    why = locked_reason(db, row)
    if why:
        raise Refused(f"This paper cannot change because {why}.")
    if not store.imported(row):
        return edit_generated(db, row, person, edits)
    items = [
        {
            "n": i["n"],
            "operation": i["operation"],
            "a": i["a"],
            "b": i["b"],
            "include": True,
            "supported": True,
        }
        for i in row.body["items"]
    ]
    draft: dict[str, Any] = {"contains_handwritten_answers": True, "items": items}
    for e in edits[:20]:
        field = str(e.get("field"))
        draft, _ = (
            apply_edit(draft, field, e.get("value"))
            if field.startswith("items.")
            else (draft, None)
        )
        if not field.startswith("items."):
            raise Invalid("Only the items can be changed here.")
    draft = imp.recompute(draft)
    kept = [i for i in draft["items"] if i["include"]]
    if not kept:
        raise Invalid("A paper needs at least one item.")
    if any(i["unsure"] for i in kept):
        raise Invalid("Check the numbers of every item before saving.")
    body_items = [
        {
            **old,
            "operation": i["operation"],
            "a": i["a"],
            "b": i["b"] or 0,
            "correct": i["correct"],
            "wrong": i["wrong"],
            "competency": i["competency"],
        }
        for i in kept
        for old in row.body["items"]
        if old["n"] == i["n"]
    ]
    digest = hashlib.sha256(json.dumps(body_items, sort_keys=True).encode()).hexdigest()
    row.body = {**row.body, "items": body_items, "coverage": draft["coverage"], "hash": digest}
    row.hash = digest
    if row.status == "approved":
        row.status, row.approved_by, row.approved_at = "confirmed", None, None
    for old in db.scalars(select(PaperItemRow).where(PaperItemRow.paper_id == row.id)).all():
        db.delete(old)
    db.flush()
    for it in body_items:
        db.add(
            PaperItemRow(
                paper_id=row.id,
                n=it["n"],
                slot=it["slot"],
                template="imported",
                a=it["a"],
                b=it["b"],
                correct=it["correct"],
                wrong=it["wrong"],
                is_anchor=False,
                twin_of=None,
            )
        )
    if not db.scalars(
        select(PaperReview).where(PaperReview.paper_id == row.id, PaperReview.status == "open")
    ).first():
        db.add(PaperReview(paper_id=row.id, reason="imported_pdf"))
    db.add(
        PaperEvent(
            event="edited",
            actor=person,
            paper_id=row.id,
            hash=digest,
            detail=f"{len(edits)} change(s), in place",
        )
    )
    db.commit()
    return row


def delete_paper(
    db: Session, paper_id: str, role: str, person: str, own_class: str | None
) -> list[str]:
    """Delete a paper nobody has used, with its items, its review rows and its withdrawn assignments.
    Its post-test twin goes with it if that is unused too. The events stay, as the audit trail."""
    row = db.get(PaperRow, paper_id)
    if row is None:
        raise Invalid("No such paper.")
    if not may_change(role, person, own_class, row):
        raise Refused("You cannot delete this paper.")
    twins = [
        t
        for t in (store.twin_of(db, row.id), db.get(PaperRow, row.twin_of) if row.twin_of else None)
        if t is not None
    ]
    for victim in (row, *twins):
        why = in_use(db, victim)
        if why:
            raise Refused(
                f"This paper cannot be deleted because {why}."
                if victim is row
                else f"Its twin cannot be deleted because {why}."
            )
    gone = []
    for victim in (row, *twins):
        for model in (PaperItemRow, PaperReview, PaperAssignment):
            col = model.paper_id
            for r in db.scalars(select(model).where(col == victim.id)).all():
                db.delete(r)
        db.flush()  # children first
        db.add(
            PaperEvent(
                event="deleted",
                actor=person,
                paper_id=victim.id,
                class_id=victim.class_id,
                hash=victim.hash,
                detail=victim.check_code,
            )
        )
        db.delete(victim)
        gone.append(victim.id)
    db.commit()
    return gone
