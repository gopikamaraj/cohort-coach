"""Demo Studio over HTTP: the judge's 11-step demo on a made-up class. Judge deployment only.

Every route refuses outside a server-side judge session, and the router is never mounted in pilot
mode, so the demo cannot touch pilot data. Each judge device has its own demo session id (made by
the browser); its data is keyed by that id and Reset deletes it. Everything returned is labelled
simulated. Sheet 1 (and any sheet re-read on request) is read by the real model (call 8), cached
by the image's hash and counted against a per-session cap; the other sheets load from the demo
answer file and say so.
"""

from __future__ import annotations

import base64
import hashlib
import io
import os
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from PIL import Image
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ai.calls.c08_answer_reading import read_sheet
from ai.client import BudgetExceeded, CallContext
from ai.config import ai_mode
from services.api.practice import AI_CONTEXT
from services.api.profiles import SESSION
from services.api.roles import judge_session
from services.demo import cohorts as demo_cohorts
from services.demo import scenario as sc
from services.demo import sheets
from services.demo.models import DemoAiRead, DemoReadCache, DemoSession
from services.papers import keys
from services.papers import store as paper_store
from services.papers.models import PaperRow
from services.papers.rules import from_data

ROOT = Path(__file__).resolve().parents[2]
CACHE = Path(os.environ.get("DEMO_CACHE_DIR", str(ROOT / "data" / "demo_cache")))
SESSION_RE = re.compile(r"^demo-[a-z0-9]{8,32}$")
MAX_UPLOAD = 2_500_000


def ai_reads_cap() -> int:
    """AI sheet reads one demo session may make (sheet 1 plus re-reads). Cached reads are free."""
    return int(os.environ.get("DEMO_AI_READS_PER_SESSION", "6"))


def _judge() -> None:
    if not judge_session():
        raise HTTPException(404, "The demo runs only in the judge deployment.")


router = APIRouter(prefix="/api/demo", tags=["demo"], dependencies=[Depends(_judge)])


def _session(db: Session, sid: str) -> DemoSession:
    if not SESSION_RE.match(sid):
        raise HTTPException(422, "Bad demo session id.")
    row = db.get(DemoSession, sid)
    if row is None:
        raise HTTPException(404, "This demo session has ended. Start the demo again.")
    return row


def _class(row: DemoSession, db: Session | None = None) -> sc.DemoClass:
    """The demo class, answering the paper made in step 2 once there is one."""
    paper = db.get(PaperRow, row.paper_id) if db is not None and row.paper_id else None
    form = (paper.id, keys.form_of(paper.body, paper.check_code)) if paper else None
    return sc.build_class(sc.load_scenario(row.scenario), row.seed, paper=form)


# --- session ---------------------------------------------------------------------------------


class StartIn(BaseModel):
    session: str = Field(pattern=SESSION_RE.pattern)
    seed: int | None = Field(default=None, ge=0, le=10**9)


@router.post("/session")
def start(body: StartIn, db: Session = SESSION) -> dict[str, Any]:
    scenario = sc.load_scenario()
    row = db.get(DemoSession, body.session)
    seed = int(scenario["seed"] if body.seed is None else body.seed)
    if row is None:
        row = DemoSession(
            id=body.session,
            scenario=str(scenario["id"]),
            seed=seed,
            class_code=str(scenario["class_code"]),
            state={},
        )
        db.add(row)
    elif body.seed is not None and body.seed != row.seed:  # Regenerate: a new class, same session
        row.seed, row.paper_id, row.state = seed, None, {}
    db.commit()
    return _summary(row)


def _summary(row: DemoSession) -> dict[str, Any]:
    scenario = sc.load_scenario(row.scenario)
    return {
        "session": row.id,
        "simulated": True,
        "label": "Demo: simulated class",
        "scenario": row.scenario,
        "seed": row.seed,
        "class_code": row.class_code,
        "strength": int(scenario["strength"]),
        "form": scenario["form"],
        "paper_id": row.paper_id,
        "ai_reads": row.ai_reads,
        "ai_reads_cap": ai_reads_cap(),
        "state": {k: v for k, v in (row.state or {}).items() if k in ("cohorts", "audio", "post")},
    }


@router.get("/session/{sid}")
def get_session_view(sid: str, db: Session = SESSION) -> dict[str, Any]:
    return _summary(_session(db, sid))


@router.delete("/session/{sid}")
def reset(sid: str, db: Session = SESSION) -> dict[str, Any]:
    """Reset: this session's own rows go; other sessions and the shared caches stay."""
    row = _session(db, sid)
    from services.demo import live

    live.forget(db, row)
    db.execute(delete(DemoAiRead).where(DemoAiRead.session_id == sid))
    db.delete(row)
    db.commit()
    return {"reset": True}


# --- step 3: the demo sheets --------------------------------------------------------------------


class SheetsIn(BaseModel):
    paper_id: str = Field(min_length=3, max_length=24)


def _paper(db: Session, row: DemoSession, paper_id: str | None = None) -> PaperRow:
    pid = paper_id or row.paper_id
    paper = db.get(PaperRow, pid) if pid else None
    if paper is None:
        raise HTTPException(409, "Make the pre-test paper first (step 2).")
    return paper


def _sheet_dir(row: DemoSession, paper: PaperRow) -> Path:
    return CACHE / f"{row.scenario}-{row.seed}-{paper.hash[:12]}"


def _reads(row: DemoSession, paper: PaperRow, db: Session) -> dict[str, Any]:
    return sc.reads_file(_class(row, db), paper.check_code, paper.hash)


@router.post("/{sid}/sheets")
def make_sheets(sid: str, body: SheetsIn, db: Session = SESSION) -> dict[str, Any]:
    row = _session(db, sid)
    paper = _paper(db, row, body.paper_id)
    rules = from_data(paper_store.version(db, paper.rules_version).body)
    row.paper_id = paper.id
    db.commit()
    paths = sheets.render_sheets(_class(row, db), paper.body, rules, _sheet_dir(row, paper))
    return {
        "simulated": True,
        "label": "Demo sheets: synthetic, made by code. Not real children's work.",
        "class_code": row.class_code,
        "check_code": paper.check_code,
        "sheets": [
            {"name": p.name, "roll": i + 1, "bytes": p.stat().st_size} for i, p in enumerate(paths)
        ],
    }


def _sheet_paths(row: DemoSession, db: Session) -> tuple[PaperRow, list[Path]]:
    paper = _paper(db, row)
    folder = _sheet_dir(row, paper)
    demo = _class(row, db)
    paths = [folder / demo.sheet_name(c.roll) for c in demo.children]
    if not all(p.exists() for p in paths):
        raise HTTPException(409, "Make the demo sheets first (step 3).")
    return paper, paths


@router.get("/{sid}/sheets/{name}")
def sheet_png(sid: str, name: str, db: Session = SESSION) -> Response:
    row = _session(db, sid)
    if not re.match(r"^[A-Za-z0-9]{1,8}-roll\d{2}\.png$", name):
        raise HTTPException(404, "No such sheet.")
    _, paths = _sheet_paths(row, db)
    path = next((p for p in paths if p.name == name), None)
    if path is None:
        raise HTTPException(404, "No such sheet.")
    return Response(
        path.read_bytes(),
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.get("/{sid}/reads.json")
def reads_json(sid: str, db: Session = SESSION) -> dict[str, Any]:
    row = _session(db, sid)
    return _reads(row, _paper(db, row), db)


@router.get("/{sid}/sheets.zip")
def sheets_zip(sid: str, db: Session = SESSION) -> Response:
    row = _session(db, sid)
    paper, paths = _sheet_paths(row, db)
    rules = from_data(paper_store.version(db, paper.rules_version).body)
    from services.papers import render

    blank, _ = render.render_paper(paper.body, rules, paper.language)
    data = sheets.zip_bytes(paths, _reads(row, paper, db), blank, row.class_code)
    return Response(
        data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{row.class_code}-demo-sheets.zip"'},
    )


# --- step 4: the AI read (sheet 1, and any re-read) -------------------------------------------


def _model_image(data: bytes) -> tuple[str, str]:
    """The upload as the model sees it: a JPEG at most 1100 px wide (same bytes every time)."""
    img = Image.open(io.BytesIO(data)).convert("RGB")
    if img.width > 1100:
        img = img.resize((1100, round(img.height * 1100 / img.width)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode(), "image/jpeg"


def _score(cells: list[dict[str, Any]], truth: list[str]) -> int:
    right = 0
    for cell, want in zip(cells, truth, strict=False):
        got = "" if cell.get("status") == "blank" else str(cell.get("text", ""))
        right += got == want
    return right


def _no_read_message(mode: str) -> str:
    """Why no read came back, in plain words, with what still works (QA-DEMO H5)."""
    rest = "Use Auto-fill from the demo answer file, or open the sheet and type the answers."
    if mode == "recorded":
        # every demo paper prints its own fingerprint, so a new sheet can never match a recording
        return "Recorded AI answers only: this new sheet has no recorded AI read to replay. " + rest
    if mode == "off":
        return "The AI reader is off right now, so nothing was read. " + rest
    return "Could not read this sheet. " + rest


@router.post("/{sid}/read")
def ai_read(
    sid: str,
    image: UploadFile = File(...),  # noqa: B008
    name: str = Form(""),
    db: Session = SESSION,
    ctx: CallContext = AI_CONTEXT,
) -> dict[str, Any]:
    row = _session(db, sid)
    data = image.file.read(MAX_UPLOAD + 1)
    if not data or len(data) > MAX_UPLOAD:
        raise HTTPException(413, "That image was empty or too large.")
    digest = hashlib.sha256(data).hexdigest()
    flag = sheets.demo_flag(data)
    cached = db.get(DemoReadCache, digest)
    was_cached = cached is not None
    if cached is not None:
        cells = cached.cells
    else:
        if row.ai_reads >= ai_reads_cap():
            raise HTTPException(
                429,
                {
                    "message": f"This demo has used its {ai_reads_cap()} AI reads. Type the "
                    "answers, or use Auto-fill for the demo sheets.",
                },
            )
        b64, media = _model_image(data)
        demo = _class(row, db)
        try:
            outcome = read_sheet(b64, media, demo.form, context=ctx)
        except BudgetExceeded as exc:
            raise HTTPException(
                503, {"message": "AI reading is paused. Type the answers."}
            ) from exc
        if outcome is None:
            raise HTTPException(503, {"message": _no_read_message(ctx.mode or ai_mode())})
        cells = [{"text": c.text, "status": c.status} for c in outcome.cells]
        row.ai_reads += 1
        row.ai_cost_usd += sum(r.cost_usd for r in outcome.runs)
        db.add(DemoReadCache(image_hash=digest, cells=cells, retried=outcome.retried))
    roll = int(flag["demo-roll"]) if flag and flag.get("demo-roll", "").isdigit() else None
    if roll is not None:
        truth = list(_class(row, db).children[roll - 1].answers)
        db.add(
            DemoAiRead(
                session_id=sid,
                image_hash=digest,
                sheet=name[:40] or f"roll {roll}",
                boxes=len(truth),
                boxes_right=_score(cells, truth),
                cached=was_cached,
            )
        )
    db.commit()
    return {
        "source": "ai",
        "label": "Read by AI",
        "cached": was_cached,
        "cells": cells,
        "demo_sheet": flag is not None,
        "roll": roll,
        "check_code": flag.get("demo-check-code") if flag else None,
        "ai_reads": row.ai_reads,
        "ai_reads_cap": ai_reads_cap(),
    }


@router.get("/{sid}/reading-summary")
def reading_summary(sid: str, db: Session = SESSION) -> dict[str, Any]:
    _session(db, sid)
    reads = db.scalars(select(DemoAiRead).where(DemoAiRead.session_id == sid)).all()
    return {
        "label": "Synthetic sheets",
        "note": "AI reads of synthetic demo sheets only, compared with what the code drew. Sheets "
        "loaded from the demo answer file are left out. Not evidence of accuracy on real "
        "children's handwriting.",
        "sheets_read_by_ai": len(reads),
        "boxes": sum(r.boxes for r in reads),
        "boxes_read_correctly": sum(r.boxes_right for r in reads),
        "sheets_all_correct": sum(1 for r in reads if r.boxes_right == r.boxes),
    }


# --- steps 6 and 7: the other classes and the cohorts --------------------------------------------


class CountsIn(BaseModel):
    """Her class's result as her phone computed it: class-level counts only."""

    counts: dict[str, int] = Field(default_factory=dict)
    checked: int = Field(ge=1, le=200)


@router.post("/{sid}/simulate-classes")
def simulate(sid: str, body: CountsIn, db: Session = SESSION) -> dict[str, Any]:
    row = _session(db, sid)
    scenario = sc.load_scenario(row.scenario)
    codes = {e.value for e in demo_cohorts.ErrorCode}
    counts = {k: int(v) for k, v in body.counts.items() if k in codes}
    p = demo_cohorts.plan(scenario, counts, body.checked)
    row.state = {**(row.state or {}), "cohorts": p, "counts": counts, "checked": body.checked}
    db.commit()
    return p


@router.get("/{sid}/cohorts")
def cohorts(sid: str, db: Session = SESSION) -> dict[str, Any]:
    row = _session(db, sid)
    p = (row.state or {}).get("cohorts")
    if not p:
        raise HTTPException(409, "Submit the check and simulate the other classes first (step 6).")
    return dict(p)


@router.get("/{sid}/dashboard")
def dashboard(sid: str, db: Session = SESSION) -> dict[str, Any]:
    row = _session(db, sid)
    p = (row.state or {}).get("cohorts")
    if not p:
        raise HTTPException(409, "Simulate the other classes first (step 6).")
    from services.demo import live

    out = demo_cohorts.dashboard(p)
    out["approvals_pending"] = live.pending_count(db, row)
    out["before_after"] = (row.state or {}).get("post", {}).get("by_cohort")
    return out


# --- step 12: the post-test -----------------------------------------------------------------------


@router.post("/{sid}/post-test")
def post_test(sid: str, db: Session = SESSION) -> dict[str, Any]:
    """Her class on the pre-test's twin paper after the track, and the cohorts' before and after
    from the simulated block's second term. Simulated; the phone pairs the children itself."""
    row = _session(db, sid)
    scenario = sc.load_scenario(row.scenario)
    pre = _class(row, db)
    twin_row = paper_store.twin_of(db, row.paper_id) if row.paper_id else None
    twin = (twin_row.id, keys.form_of(twin_row.body, twin_row.check_code)) if twin_row else None
    post = sc.post_class(scenario, pre, twin)
    p = (row.state or {}).get("cohorts")
    by_cohort = (
        demo_cohorts.before_after(
            scenario, row.state["counts"], row.state["checked"], sc.truth_profile(post)
        )
        if p
        else None
    )
    row.state = {**(row.state or {}), "post": {"by_cohort": by_cohort}}
    db.commit()
    return {
        "simulated": True,
        "label": "Simulated post-test (the twin paper)",
        "form": post.form_key,
        "paper_code": twin_row.check_code if twin_row else None,
        "rows": [list(c.answers) for c in post.children],
        "by_cohort": by_cohort,
    }


# --- steps 8 to 11: audio, chat, coach ---------------------------------------------------------

from services.api.practice import SPEECH  # noqa: E402
from services.demo import live  # noqa: E402


def _live(fn: Any, *args: Any, **kwargs: Any) -> Any:
    from services.api.cohorts import mentor_items
    from services.chat import service as chat
    from services.content import review, versions

    try:
        return fn(*args, **kwargs)
    except LookupError as exc:
        raise HTTPException(409, str(exc)) from exc
    except (chat.BadState, mentor_items.BadState, versions.BadState) as exc:
        raise HTTPException(409, str(exc)) from exc
    except (chat.PostRejected, review.EditBlocked) as exc:
        raise HTTPException(422, "That text was held by a check. Change it and try again.") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


class AudioIn(BaseModel):
    regenerate: bool = False


@router.post("/{sid}/audio")
def audio(
    sid: str,
    body: AudioIn,
    db: Session = SESSION,
    ctx: CallContext = AI_CONTEXT,
    speech: Any = SPEECH,
) -> dict[str, Any]:
    row = _session(db, sid)
    meta = _live(live.first_audio, db, row, ctx, speech, body.regenerate)
    return {
        **meta,
        "audio_url": f"/api/demo/{sid}/audio-file"
        if (meta.get("audio") or {}).get("file")
        else None,
    }


@router.get("/{sid}/audio-file")
def audio_file(sid: str, db: Session = SESSION) -> Response:
    path = live.audio_file(_session(db, sid))
    if path is None or not path.exists():
        raise HTTPException(404, "No audio yet.")
    mime = {"ogg": "audio/ogg", "mp3": "audio/mpeg", "m4a": "audio/mp4"}.get(
        path.suffix[1:], "audio/mpeg"
    )
    return Response(path.read_bytes(), media_type=mime)


class AskIn(BaseModel):
    text: str = Field(min_length=3, max_length=500)


@router.post("/{sid}/chat/ask")
def chat_ask(
    sid: str, body: AskIn, db: Session = SESSION, ctx: CallContext = AI_CONTEXT
) -> dict[str, Any]:
    return dict(_live(live.ask, db, _session(db, sid), body.text, ctx))


@router.get("/{sid}/chat")
def chat_view(sid: str, db: Session = SESSION) -> dict[str, Any]:
    return dict(_live(live.chat_view, db, _session(db, sid)))


@router.post("/{sid}/chat/skip")
def chat_skip(sid: str, db: Session = SESSION) -> dict[str, Any]:
    return dict(_live(live.skip_wait, db, _session(db, sid)))


@router.post("/{sid}/coach/seed")
def coach_seed(sid: str, db: Session = SESSION, ctx: CallContext = AI_CONTEXT) -> dict[str, Any]:
    row = _session(db, sid)
    _live(live.seed_coach, db, row, ctx)
    return dict(_live(live.coach_view, db, row))


@router.get("/{sid}/coach")
def coach_view(sid: str, db: Session = SESSION) -> dict[str, Any]:
    return dict(_live(live.coach_view, db, _session(db, sid)))


class ReplyIn(BaseModel):
    mode: str = Field(pattern=r"^(as_is|edit|own)$")
    text: str | None = Field(default=None, max_length=1000)
    tags: list[str] = Field(default_factory=list, max_length=5)


@router.post("/{sid}/coach/questions/{message_id}/reply")
def coach_reply(sid: str, message_id: str, body: ReplyIn, db: Session = SESSION) -> dict[str, Any]:
    from services.chat import service as chat

    row = _session(db, sid)
    _live(
        chat.reply,
        db,
        message_id,
        role="coach",
        person=live.COACH,
        mode=body.mode,
        text=body.text,
        tags=tuple(body.tags),
    )
    return dict(_live(live.coach_view, db, row))


class CorrectIn(BaseModel):
    text: str = Field(min_length=3, max_length=1000)
    tags: list[str] = Field(min_length=1, max_length=5)


@router.post("/{sid}/coach/answers/{answer_id}/correct")
def coach_correct(
    sid: str, answer_id: str, body: CorrectIn, db: Session = SESSION
) -> dict[str, Any]:
    from services.chat import service as chat

    row = _session(db, sid)
    _live(
        chat.correct,
        db,
        answer_id,
        role="coach",
        person=live.COACH,
        text=body.text,
        tags=tuple(body.tags),
    )
    return dict(_live(live.coach_view, db, row))


class DecideIn(BaseModel):
    decision: str = Field(pattern=r"^(approve|request_changes|reject)$")
    reason: str | None = Field(default=None, max_length=40)
    note: str = Field(default="", max_length=300)


@router.post("/{sid}/coach/mentor-card")
def coach_mentor_card(sid: str, body: DecideIn, db: Session = SESSION) -> dict[str, Any]:
    from services.api.cohorts import mentor_items

    row = _session(db, sid)
    item_id = (row.state or {}).get("mentor_item")
    if not item_id:
        raise HTTPException(409, "Open the coach's queue first.")
    _live(
        mentor_items.decide,
        db,
        item_id,
        body.decision,
        coach_id=live.COACH,
        reason=body.reason,
        note=body.note,
    )
    return dict(_live(live.coach_view, db, row))


@router.post("/{sid}/coach/lesson2")
def coach_lesson2(sid: str, body: DecideIn, db: Session = SESSION) -> dict[str, Any]:
    from services.content import review

    row = _session(db, sid)
    item_id = (row.state or {}).get("review_item")
    if not item_id:
        raise HTTPException(409, "There is no lesson 2 draft in the queue.")
    if body.decision == "approve":
        _live(review.approve, db, item_id, live.COACH, "coach")
    else:
        _live(
            review.reject,
            db,
            item_id,
            live.COACH,
            "coach",
            reason=body.reason or "tone_issue",
            note=body.note,
        )
    return dict(_live(live.coach_view, db, row))
