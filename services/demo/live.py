"""The demo's live steps on real code paths: the first audio, the cohort chat and the coach queue.

- First audio (step 8): the track for her class's track error; call 5 drafts lesson 1 (real model
  call), code fills the class-number slots and the gates run; the script is voiced by the server
  voice once per scenario and cached. It carries "Demo: pre-approved": in the demo the coach's
  approval of this first lesson is skipped, and only this one (DECISIONS 2026-10-31).
- Cohort chat (step 10): a real cohort space with her as a member, the real chat service (call 12
  classifies, call 13 drafts from approved material with citations, or abstains), a 60 second wait
  in the demo and "Skip the wait", which runs the real auto-send gates.
- Coach queue (step 11): her question and the AI reply, a simulated mentor's method card, and the
  AI draft of the second lesson in the real review queue.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.calls.c05_track_draft import draft_part
from ai.client import CallContext
from engine.bugs import correct_answer, error_answers
from engine.model import ErrorCode, Item, ItemType
from services.api.cohorts import lifecycle, mentor_items, thread
from services.api.db import ChatConfig, ChatMessage, MentorItem, ReviewItem
from services.chat import scheduler
from services.chat import service as chat
from services.content import drafting
from services.content.slots import fill
from services.content.track import load_track
from services.demo.models import DemoSession

ROOT = Path(__file__).resolve().parents[2]
TRACKS = {"SUB-SFL": "sub-sfl.v1"}  # the tracks with approved content today
CHAT_WAIT_S = 60
COACH, MENTOR, OFFICER = "coach-demo", "mentor-demo", "officer-demo"


def teacher_id(row: DemoSession) -> str:
    return "t-" + row.id[5:21]


def _state(row: DemoSession, **kw: Any) -> None:
    row.state = {**(row.state or {}), **kw}


def _error_name(code: str, lang: str = "en") -> str:
    names = yaml.safe_load((ROOT / "content" / "lang" / "error_names.yaml").read_text("utf-8"))
    return str(names.get(code, {}).get(lang) or code)


def slot_values(
    code: str, counts: dict[str, int], checked: int, day: int, total: int, example: tuple[int, int]
) -> dict[str, str]:
    """Every class number in the script comes from here (code), never from the model."""
    item = Item(0, ItemType.SUB_BORROW, example[0], example[1])
    wrong = sorted(error_answers(item).get(ErrorCode(code), frozenset()))
    return {
        "class.count_showing": str(int(counts.get(code, 0))),
        "class.children_checked": str(checked),
        "class.example_a": str(example[0]),
        "class.example_b": str(example[1]),
        "class.example_wrong_answer": str(wrong[0]) if wrong else "",
        "class.example_correct_answer": str(correct_answer(item)),
        "track.error_name": _error_name(code),
        "track.day": str(day),
        "track.total_days": str(total),
    }


# --- step 8: the first audio ------------------------------------------------------------------


def _audio_dir() -> Path:
    from services.demo.api import CACHE

    return CACHE / "audio"


def first_audio(
    db: Session, row: DemoSession, ctx: CallContext, speech: Any, regenerate: bool = False
) -> dict[str, Any]:
    state = row.state or {}
    plan = state.get("cohorts")
    if not plan:
        raise LookupError("Form the cohorts first (step 7).")
    code = plan["you"]["track"]
    track_id = TRACKS.get(code or "")
    if track_id is None:
        raise LookupError(f"There is no approved track content for {code} yet.")
    track = load_track(track_id)
    key = f"{row.scenario}-{row.seed}-{track_id}-day1"
    folder = _audio_dir()
    folder.mkdir(parents=True, exist_ok=True)
    meta_path = folder / f"{key}.json"
    if meta_path.exists() and not regenerate:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    else:
        draft = draft_part(track, "lesson", 1, "en", context=ctx)
        total = len(track.lessons)
        values = slot_values(
            code,
            state.get("counts", {}),
            int(state.get("checked", 0)),
            1,
            total,
            tuple(track.example),
        )  # type: ignore[arg-type]
        if draft.part is not None and draft.status in ("needs_review",):
            script = fill(draft.part.script, values)
            source = "ai"
        else:
            script = template_script(track, values)
            source = "template"
        meta = {
            "track": track_id,
            "error": code,
            "day": 1,
            "script": script,
            "source": source,
            "status": draft.status,
            "explanation": draft.explanation,
            "badge": "Demo: pre-approved",
            "audio": None,
        }
        meta["audio"] = _voice(script, folder / key, speech)
        meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    _state(row, audio={"key": key, "track": meta["track"], "source": meta["source"]})
    db.commit()
    return meta


def template_script(track: Any, values: dict[str, str]) -> str:
    """When the AI draft is not available: the approved lesson topic with the class's numbers."""
    lesson = next(lesson for lesson in track.lessons if lesson.day == 1)
    topic = lesson.topic.get("en") or next(iter(lesson.topic.values()))
    return (
        f"{topic}. In your class, {values['class.count_showing']} of "
        f"{values['class.children_checked']} children showed this mistake: "
        f"{values['track.error_name']}. Write {values['class.example_a']} minus "
        f"{values['class.example_b']} on the board. A child with this mistake writes "
        f"{values['class.example_wrong_answer']}. Ask: how did you get that? Listen before you "
        f"correct. The answer is {values['class.example_correct_answer']}. Try it with three "
        "children this week."
    )


def _voice(script: str, stem: Path, speech: Any) -> dict[str, Any] | None:
    """Voice the script with the server voice; on any failure the lesson stays text only."""
    from services.media.voice import audio_format, chunks, voice_options
    from services.speech.audio import join_to_file
    from services.speech.voices import Voice

    try:
        fmt = audio_format()
        voice = Voice(
            speaker=str(voice_options().get("default", "ritu")),
            pitch=1.0,
            pace=float(voice_options().get("pace", 1.0)),
        )
        clips = [speech.synthesize(c, "en", voice) for c in chunks(script)]
        data, seconds = join_to_file(clips, fmt=fmt)
    except Exception as exc:  # noqa: BLE001 - the demo shows the text instead
        return {"error": type(exc).__name__}
    path = stem.with_suffix(f".{fmt}")
    path.write_bytes(data)
    return {"file": path.name, "seconds": round(seconds, 1), "bytes": len(data), "format": fmt}


def audio_file(row: DemoSession) -> Path | None:
    audio = (row.state or {}).get("audio")
    if not audio:
        return None
    meta_path = _audio_dir() / f"{audio['key']}.json"
    if not meta_path.exists():
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    name = (meta.get("audio") or {}).get("file")
    return _audio_dir() / name if name else None


# --- step 10: the cohort chat ------------------------------------------------------------------


def ensure_cohort(db: Session, row: DemoSession) -> str:
    """Her cohort as a real cohort space (simulated), active, with her as a member."""
    state = row.state or {}
    cid = state.get("chat_cohort")
    if cid:
        return str(cid)
    plan = state.get("cohorts")
    if not plan:
        raise LookupError("Form the cohorts first (step 7).")
    error = plan["you"]["track"]
    cohort = lifecycle.create(
        db,
        error=error,
        coach_id=COACH,
        mentor_ids=[MENTOR],
        officer_id=OFFICER,
        simulated=True,
        cohort_id="co-demo-" + row.id[5:17],
    )
    lifecycle.transition(db, cohort.id, "active", role="officer", actor=OFFICER)
    thread.join(db, cohort.id, teacher_id(row))
    # The coach's chat setting for this demo cohort: the AI may answer when nobody does.
    db.add(
        ChatConfig(
            id=cohort.id,
            scope="cohort",
            cohort_id=cohort.id,
            ai_timeout_hours=1,
            ai_auto_send_enabled=True,
            set_by=COACH,
        )
    )
    _state(row, chat_cohort=cohort.id)
    db.commit()
    return cohort.id


def ask(db: Session, row: DemoSession, text: str, ctx: CallContext) -> dict[str, Any]:
    cid = ensure_cohort(db, row)
    asked = chat.ask(
        db,
        cohort_id=cid,
        teacher_id=teacher_id(row),
        text=text,
        language="en",
        ai_consent=True,
        context=ctx,
    )
    q = asked.message
    if q.ai_due_at is not None:  # the demo waits 60 seconds, not the coach's hours
        q.ai_due_at = datetime.now(UTC) + timedelta(seconds=CHAT_WAIT_S)
        db.commit()
    return chat_view(db, row)


def skip_wait(db: Session, row: DemoSession) -> dict[str, Any]:
    """Skip the wait: the question is due now, and the real auto-send gates decide."""
    cid = ensure_cohort(db, row)
    now = datetime.now(UTC)
    for q in db.scalars(
        select(ChatMessage).where(ChatMessage.cohort_id == cid, ChatMessage.kind == "question")
    ):
        if q.status == "ai_draft_ready" and q.ai_due_at is not None:
            q.ai_due_at = now - timedelta(seconds=1)
    db.commit()
    result = scheduler.tick(db, now=now, cohort_ids=[cid])
    view = chat_view(db, row)
    view["tick"] = scheduler.summary(result)
    return view


def chat_view(db: Session, row: DemoSession) -> dict[str, Any]:
    cid = ensure_cohort(db, row)
    view = chat.my_questions(db, cid, teacher_id(row))
    due = {
        q.id: q.ai_due_at.isoformat() if q.ai_due_at else None
        for q in db.scalars(
            select(ChatMessage).where(ChatMessage.cohort_id == cid, ChatMessage.kind == "question")
        )
    }
    for q in view["questions"]:
        q["ai_due_at"] = due.get(q["id"])
    view["cohort"] = cid
    view["wait_seconds"] = CHAT_WAIT_S
    return view


# --- step 11: the coach's queue ------------------------------------------------------------------


def seed_coach(db: Session, row: DemoSession, ctx: CallContext) -> None:
    """The mentor's method card and the AI draft of lesson 2 in the real queues (once)."""
    state = row.state or {}
    cid = ensure_cohort(db, row)
    if not state.get("mentor_item"):
        item = mentor_items.create(db, cid, MENTOR, "method_card")
        mentor_items.submit(db, item.id, MENTOR)
        _state(row, mentor_item=item.id)
    if not state.get("review_item"):
        plan = state["cohorts"]
        track_id = TRACKS.get(plan["you"]["track"] or "")
        if track_id:
            track = load_track(track_id)
            stored = drafting.store_draft(
                db, draft_part(track, "lesson", 2, "en", context=ctx), track
            )
            _state(
                row,
                review_item=stored.item_id if stored else None,
                review_note=None if stored else "The AI draft of lesson 2 was held by a check.",
            )
    db.commit()


def mentor_card() -> dict[str, Any]:
    data = yaml.safe_load((ROOT / "demo" / "scenarios" / "mentor_card.yaml").read_text("utf-8"))
    assert isinstance(data, dict)
    return data


def coach_view(db: Session, row: DemoSession) -> dict[str, Any]:
    state = row.state or {}
    cid = ensure_cohort(db, row)
    inbox = chat.inbox(db, role="coach", person=COACH)
    mine = [q for q in inbox.get("pending", []) if q.get("cohort_id") == cid]
    sent = [a for a in inbox.get("needs_review", []) if a.get("question_id") in _ids(db, cid)]
    item = db.get(MentorItem, state.get("mentor_item") or "")
    review = (
        db.get(ReviewItem, state.get("review_item") or "") if state.get("review_item") else None
    )
    return {
        "simulated": True,
        "cohorts": state.get("cohorts", {}).get("cohorts", []),
        "chat": {"questions": mine, "ai_answers": sent},
        "mentor_card": {
            **mentor_card(),
            "item_id": item.id if item else None,
            "status": item.status if item else None,
        },
        "lesson2": {
            "item_id": review.item_id if review else None,
            "status": review.status if review else None,
            "note": state.get("review_note"),
        },
    }


def _ids(db: Session, cid: str) -> set[str]:
    return set(db.scalars(select(ChatMessage.id).where(ChatMessage.cohort_id == cid)))


def pending_count(db: Session, row: DemoSession) -> int:
    state = row.state or {}
    n = 0
    item = db.get(MentorItem, state.get("mentor_item") or "")
    n += int(item is not None and item.status == "awaiting_coach")
    review = (
        db.get(ReviewItem, state.get("review_item") or "") if state.get("review_item") else None
    )
    n += int(review is not None and review.status == "pending")
    cid = state.get("chat_cohort")
    if cid:
        n += len(
            [
                q
                for q in db.scalars(
                    select(ChatMessage).where(
                        ChatMessage.cohort_id == cid,
                        ChatMessage.kind == "question",
                        ChatMessage.status.in_(chat.OPEN),
                    )
                )
            ]
        )
    return n


def forget(db: Session, row: DemoSession) -> None:
    """Reset: her demo cohort is cancelled and she leaves it; the rest is this session's state."""
    cid = (row.state or {}).get("chat_cohort")
    if cid:
        try:
            lifecycle.transition(
                db, cid, "cancelled", role="officer", actor=OFFICER, reason="demo reset"
            )
        except Exception:  # noqa: BLE001 - already closed or cancelled
            pass
        try:
            thread.leave(db, cid, teacher_id(row))
        except Exception:  # noqa: BLE001
            pass
