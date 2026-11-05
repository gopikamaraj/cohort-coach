"""The two-class run on real code paths.

1. Each teacher submits her class's check (counts only). Formation runs on every submit, and the
   coach can run it from a button too. The first class waits; the second forms the cohort.
2. When the cohort forms: a cohort space (the coach, the mentor, both teachers), its chat setting,
   and lesson 1 in each teacher's language. Call 5 drafts it from the track's approved topic and
   strategies; when no draft comes back, code writes it from the same content. Every lesson goes to
   the coach's review queue (a real review item). It is voiced per teacher with her class's numbers
   (filled by code); a voice failure leaves the text and a retry.
3. After the coach approves, the teacher plays it (or marks it heard), answers tried / partly /
   not yet with an optional note (masked), and can press Generate next lesson: code picks the next
   lesson (services/cohort_run/next_lesson.py), call 5 words it, and it goes to review. With no
   answer by the set date the planned lesson is queued instead, and silence is never counted.
4. The cohort chat is the real chat service (masking, call 12, call 13 with sources or abstain, the
   coach's inbox, a 60 second wait here, the labelled AI reply and correction). A teacher may share
   a question with her cohort; then the others see it with its released answers, by pseudonym.
5. The coach's view and timeline are built from these records: counts only.
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.calls.c05_track_draft import draft_part, review_content
from ai.client import CallContext
from ai.validators.mask import mask_personal
from ai.validators.prefilter import check_prefilter
from engine.bugs import correct_answer, error_answers
from engine.model import ErrorCode, Item, ItemType
from services.api.cohorts import lifecycle, thread
from services.api.db import ChatConfig, ChatMessage, ReviewItem
from services.chat import scheduler
from services.chat import service as chat
from services.cohort_run import formation, next_lesson
from services.cohort_run import scenario as sc
from services.cohort_run import settings as cs
from services.cohort_run.models import CohortRun
from services.content import review
from services.content.slots import fill
from services.content.track import load_strategies, load_track

log = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
TRACKS = {"SUB-SFL": "sub-sfl.v1"}  # tracks with approved lesson content today
CHAT_WAIT_S = 60
MIN_CELL = 5  # officers: a figure over fewer than 5 classes is hidden
NOTE_MAX = 300
ROLE_LABELS = ("T1", "T2", "T3", "C1", "M1", "M2", "officer")


class NotAllowed(PermissionError):
    pass


def cache_dir() -> Path:
    return Path(os.environ.get("DEMO_CACHE_DIR", str(ROOT / "data" / "demo_cache"))) / "cohort_run"


# --- people and state ---------------------------------------------------------------------------


def person(run: CohortRun, label: str) -> str:
    """Pseudonymous ids for the run's people. T3 is a teacher outside the cohort."""
    h = hashlib.sha256(f"{run.id}|{label}".encode()).hexdigest()
    if label.startswith("T"):
        return "t-" + h[:16]
    prefix = {"C1": "coach", "M1": "mentor", "M2": "mentor", "officer": "officer"}[label]
    return f"{prefix}-{h[:12]}"


def _st(run: CohortRun) -> dict[str, Any]:
    return copy.deepcopy(run.state or {})


def _save(db: Session, run: CohortRun, st: dict[str, Any]) -> None:
    run.state = st
    db.commit()


def _event(st: dict[str, Any], kind: str, link: str | None = None, **facts: Any) -> None:
    events = st.setdefault("events", [])
    events.append(
        {
            "seq": len(events) + 1,
            "day": st.get("clock", 0),
            "kind": kind,
            "link": link,
            "facts": facts,
        }
    )


def scenario_of(run: CohortRun) -> dict[str, Any]:
    return sc.load(run.scenario)


def settings_of(run: CohortRun) -> cs.CohortSettings:
    return cs.for_scenario(scenario_of(run))


def new_run(
    db: Session, run_id: str, scenario: str = sc.DEFAULT, source: str = "synthetic"
) -> CohortRun:
    row = db.get(CohortRun, run_id)
    if row is None:
        sc.load(scenario)  # fails early on an unknown scenario
        row = CohortRun(id=run_id, scenario=scenario, source=source, state={"clock": 0})
        db.add(row)
        db.commit()
    return row


def reset(db: Session, run: CohortRun) -> None:
    cid = (run.state or {}).get("cohort", {}).get("space")
    if cid:
        try:
            lifecycle.transition(
                db,
                cid,
                "cancelled",
                role="officer",
                actor=person(run, "officer"),
                reason="run reset",
            )
        except Exception:  # noqa: BLE001 - already closed
            db.rollback()
    db.delete(run)
    db.commit()


# --- flow 1: checks and formation ---------------------------------------------------------------


def _teacher_of(scn: dict[str, Any], code: str) -> str:
    return str(sc.class_of(scn, code)["teacher"])


def submit_check(
    db: Session,
    run: CohortRun,
    code: str,
    as_label: str,
    counts: sc.ClassCounts | None,
    ctx: CallContext,
    speech: Any,
) -> dict[str, Any]:
    """A teacher submits her class's check. `counts` None means the synthetic class (made by code);
    otherwise the counts her phone (or the local pilot script) worked out."""
    scn = scenario_of(run)
    if _teacher_of(scn, code) != as_label:
        raise NotAllowed("Only the class's own teacher submits its check.")
    if counts is None:
        counts = sc.synthetic_class(scn, code)
    st = _st(run)
    st.setdefault("classes", {})[code] = counts.to_dict()
    _event(
        st,
        "check_submitted",
        None,
        cls=code,
        teacher=as_label,
        checked=counts.children_checked,
        source=counts.source,
    )
    _save(db, run, st)
    return form_now(db, run, ctx, speech, by="auto")


def form_now(db: Session, run: CohortRun, ctx: CallContext, speech: Any, by: str) -> dict[str, Any]:
    st = _st(run)
    classes = [sc.ClassCounts.from_dict(d) for d in st.get("classes", {}).values()]
    s = settings_of(run)
    result = formation.form(classes, s)
    st["formation"] = result
    # One cohort per mistake: the run follows the formed cohort whose mistake has approved lesson content
    # (TRACKS); a cohort formed for a mistake with no approved track yet is listed in the formation only.
    runnable = next((k for k in result["cohorts"] if k["error"] in TRACKS), None)
    formed_now = runnable is not None and not st.get("cohort")
    if result["status"] == "waiting_for_classes":
        w = result["waiting"][0]
        _event(st, "waiting", None, have=w["have"], need=w["min_classes"], error=w["error"], by=by)
    elif result["status"] == "no_cohort":
        _event(st, "no_cohort", None, classes=len(classes), by=by)
    if formed_now:
        c = runnable
        _event(
            st,
            "cohort_formed",
            None,
            error=c["error"],
            classes=len(c["classes"]),
            labels=c["labels"],
            by=by,
            mentor=c["mentor"]["suggested"],
        )
    _save(db, run, st)
    if formed_now and runnable is not None:
        _materialize(db, run, runnable, ctx, speech)
    return result


def _materialize(
    db: Session, run: CohortRun, c: dict[str, Any], ctx: CallContext, speech: Any
) -> None:
    """The cohort as a space people belong to, its chat setting, and lesson 1 per language."""
    space = lifecycle.create(
        db,
        error=c["error"],
        coach_id=person(run, "C1"),
        mentor_ids=[person(run, "M1")],
        officer_id=person(run, "officer"),
        simulated=run.source != "pilot",
        cohort_id="co-run-" + run.id[4:16],
    )
    lifecycle.transition(db, space.id, "active", role="officer", actor=person(run, "officer"))
    for t in c["teachers"]:
        thread.join(db, space.id, person(run, t))
    db.add(
        ChatConfig(
            id=space.id,
            scope="cohort",
            cohort_id=space.id,
            ai_timeout_hours=1,
            ai_auto_send_enabled=True,
            set_by=person(run, "C1"),
        )
    )
    db.commit()
    st = _st(run)
    st["cohort"] = {**c, "space": space.id}
    _save(db, run, st)
    scn = scenario_of(run)
    by_lang: dict[str, list[str]] = {}
    for t in c["teachers"]:
        by_lang.setdefault(str(scn["teachers"][t]["language"]), []).append(t)
    for lang, audience in sorted(by_lang.items()):
        _new_lesson(
            db,
            run,
            n=1,
            day=1,
            language=lang,
            audience=audience,
            decision=None,
            next_of=None,
            ctx=ctx,
            speech=speech,
        )


# --- flow 2: lessons ----------------------------------------------------------------------------


def _error_name(code: str, lang: str) -> str:
    names = yaml.safe_load((ROOT / "content" / "lang" / "error_names.yaml").read_text("utf-8"))
    return str(names.get(code, {}).get(lang) or names.get(code, {}).get("en") or code)


def values_for(run: CohortRun, teacher: str, day: int, language: str) -> dict[str, str]:
    """Every class number in a lesson comes from here (code): her class's counts."""
    st = run.state or {}
    code = st["cohort"]["error"]
    track = load_track(TRACKS[code])
    cls = next(d for d in st["classes"].values() if d["teacher"] == teacher)
    used = formation.used_counts(sc.ClassCounts.from_dict(cls), settings_of(run))
    a, b = track.example
    item = Item(0, ItemType.SUB_BORROW, a, b)
    wrong = sorted(error_answers(item).get(ErrorCode(code), frozenset()))
    return {
        "class.count_showing": str(used.get(code, 0)),
        "class.children_checked": str(cls["children_checked"]),
        "class.example_a": str(a),
        "class.example_b": str(b),
        "class.example_wrong_answer": str(wrong[0]) if wrong else "",
        "class.example_correct_answer": str(correct_answer(item)),
        "track.error_name": _error_name(code, language),
        "track.day": str(day),
        "track.total_days": str(len(track.lessons)),
    }


def _template(track: Any, day: int, language: str, smaller: bool) -> str:
    data = yaml.safe_load(
        (ROOT / "content" / "templates" / "lesson_fallback.yaml").read_text("utf-8")
    )
    lesson = next(x for x in track.lessons if x.day == day)
    lib = load_strategies()
    approach = ", ".join(
        lib[s].label.get(language) or lib[s].label["en"] for s in lesson.strategies if s in lib
    )
    body = data["body"].get(language) or data["body"]["en"]
    extra = (
        (data["smaller_step"].get(language) or data["smaller_step"]["en"]) + " " if smaller else ""
    )
    topic = lesson.topic.get(language) or lesson.topic["en"]
    return (
        str(body)
        .replace("{topic}", topic)
        .replace("{approach}", approach)
        .replace("{extra}", extra)
    )


def _sources(track: Any, day: int, language: str) -> list[dict[str, str]]:
    lesson = next(x for x in track.lessons if x.day == day)
    lib = load_strategies()
    out = [
        {
            "kind": "track",
            "id": f"{track.id}#day{day}",
            "label": lesson.topic.get(language) or lesson.topic["en"],
            "status": "approved structure",
        }
    ]
    for s in lesson.strategies:
        if s in lib:
            out.append(
                {
                    "kind": "strategy",
                    "id": s,
                    "label": lib[s].label.get(language) or lib[s].label["en"],
                    "status": lib[s].status,
                }
            )
    return out


def _new_lesson(
    db: Session,
    run: CohortRun,
    *,
    n: int,
    day: int,
    language: str,
    audience: list[str],
    decision: dict[str, Any] | None,
    next_of: str | None,
    ctx: CallContext,
    speech: Any,
) -> dict[str, Any]:
    st = _st(run)
    code = st["cohort"]["error"]
    track_id = TRACKS.get(code)
    lid = f"L{n}-{language}" if n == 1 else f"L{n}-{audience[0]}"
    if track_id is None:
        _event(st, "no_track_content", None, error=code)
        _save(db, run, st)
        raise LookupError(f"There is no approved track content for {code} yet.")
    track = load_track(track_id)
    smaller = bool(decision and decision.get("mode") == "smaller_step")
    draft = draft_part(
        track,
        "lesson",
        day,
        language,
        context=ctx,
        variant="smaller_step_more_practice" if smaller else None,
        practice_level=(decision or {}).get("practice_level"),
    )
    if draft.part is not None and draft.status in ("needs_review", "held_by_checker"):
        script, source = draft.part.script, "ai"
        content = review_content(draft, track)
    else:
        script, source = _template(track, day, language, smaller), "template"
        content = {
            "track_id": track.id,
            "track_version": track.version,
            "kind": "lesson",
            "day": day,
            "language": language,
            "error": track.error,
            "script": script,
            "slots_used": [],
            "strategies": list(next(x for x in track.lessons if x.day == day).strategies),
            "results": [],
            "status": "needs_review",
            "badge": "none",
            "audit_id": None,
            "explanation": "Written by code from the approved lesson topic and strategies; the AI "
            "draft was not available (" + draft.status + ").",
        }
    content.update(
        {
            "cohort_id": st["cohort"]["space"],
            "run_id": run.id,
            "lesson_id": lid,
            "lesson_n": n,
            "source": source,
        }
    )
    item = ReviewItem(
        item_id=hashlib.sha256(f"{run.id}|{lid}".encode()).hexdigest()[:32],
        content_type="track_draft",
        ai_call_id=content.get("audit_id"),
        language=language,
        target_error=code,
        content=content,
        badge=content.get("badge", "none"),
        status="pending",
    )
    db.add(item)
    db.commit()
    lesson = {
        "id": lid,
        "n": n,
        "day": day,
        "language": language,
        "audience": audience,
        "decision": decision,
        "next_of": next_of,
        "script": script,
        "source": source,
        "ai_status": draft.status,
        "explanation": content.get("explanation"),
        "sources": _sources(track, day, language),
        "review_item": item.item_id,
        "voices": {},
        "released_day": None,
    }
    st = _st(run)
    st.setdefault("lessons", []).append(lesson)
    _event(
        st,
        "lesson_drafted",
        "review",
        lesson=lid,
        n=n,
        language=language,
        source=source,
        decision=(decision or {}).get("reason"),
    )
    _save(db, run, st)
    for t in audience:
        voice(db, run, lid, t, speech)
    return lesson


def _lesson(st: dict[str, Any], lid: str) -> dict[str, Any]:
    for x in st.get("lessons", []):
        if x["id"] == lid:
            return dict(x)
    raise LookupError("No such lesson.")


def _put_lesson(st: dict[str, Any], lesson: dict[str, Any]) -> None:
    st["lessons"] = [lesson if x["id"] == lesson["id"] else x for x in st.get("lessons", [])]


def voice(db: Session, run: CohortRun, lid: str, teacher: str, speech: Any) -> dict[str, Any]:
    """Voice her copy with her class's numbers. On any failure the lesson stays text, the failure is
    logged (ids only, never the text), and the screen offers a retry."""
    from services.media.voice import audio_format, chunks, voice_options
    from services.speech.audio import join_to_file
    from services.speech.voices import Voice

    st = _st(run)
    lesson = _lesson(st, lid)
    text = fill(lesson["script"], values_for(run, teacher, lesson["day"], lesson["language"]))
    try:
        fmt = audio_format()
        v = Voice(
            speaker=str(voice_options().get("default", "ritu")),
            pitch=1.0,
            pace=float(voice_options().get("pace", 1.0)),
        )
        clips = [speech.synthesize(c, lesson["language"], v) for c in chunks(text)]
        data, seconds = join_to_file(clips, fmt=fmt)
        folder = cache_dir()
        folder.mkdir(parents=True, exist_ok=True)
        name = f"{run.id}-{lid}-{teacher}.{fmt}"
        (folder / name).write_bytes(data)
        meta: dict[str, Any] = {
            "file": name,
            "seconds": round(seconds, 1),
            "bytes": len(data),
            "format": fmt,
        }
    except Exception as exc:  # noqa: BLE001 - the lesson stays text, with a retry
        log.warning(
            "cohort_run voice failed run=%s lesson=%s error=%s", run.id, lid, type(exc).__name__
        )
        meta = {"error": type(exc).__name__}
        _event(st, "voice_failed", None, lesson=lid, error=type(exc).__name__)
    lesson["voices"] = {**lesson.get("voices", {}), teacher: meta}
    _put_lesson(st, lesson)
    _save(db, run, st)
    return meta


def lesson_status(db: Session, lesson: dict[str, Any]) -> str:
    item = db.get(ReviewItem, lesson["review_item"])
    if item is None:
        return "held"
    if item.status == "approved":
        return "released"
    if item.status == "pending":
        return "in_review" if item.content.get("status") == "needs_review" else "held"
    return str(item.status)


def coach_decide(db: Session, run: CohortRun, lid: str, decision: str, reason: str | None) -> None:
    st = _st(run)
    lesson = _lesson(st, lid)
    if decision == "approve":
        review.approve(db, lesson["review_item"], person(run, "C1"), "coach")
        lesson["released_day"] = st.get("clock", 0)
        _event(st, "lesson_released", None, lesson=lid, n=lesson["n"])
    else:
        review.reject(
            db,
            lesson["review_item"],
            person(run, "C1"),
            "coach",
            reason=reason or "tone_issue",
            note="",
        )
        _event(st, "lesson_rejected", "review", lesson=lid, reason=reason or "tone_issue")
    _put_lesson(st, lesson)
    _save(db, run, st)


def _mine(db: Session, run: CohortRun, teacher: str) -> list[dict[str, Any]]:
    st = run.state or {}
    return [x for x in st.get("lessons", []) if teacher in x["audience"]]


def played(db: Session, run: CohortRun, lid: str, teacher: str, heard: bool) -> None:
    st = _st(run)
    lesson = _lesson(st, lid)
    if teacher not in lesson["audience"]:
        raise NotAllowed("This lesson is not hers.")
    if lesson_status(db, lesson) != "released":
        raise LookupError("The lesson is waiting for the coach.")
    key = "heard" if heard else "plays"
    rows = st.setdefault(key, {}).setdefault(lid, {})
    rows[teacher] = int(rows.get(teacher, 0)) + 1
    _event(st, "lesson_heard" if heard else "lesson_played", None, lesson=lid)
    _save(db, run, st)


def give_feedback(
    db: Session, run: CohortRun, lid: str, teacher: str, answer: str, note: str
) -> dict[str, Any]:
    if answer not in next_lesson.ANSWERS:
        raise ValueError("Choose tried, partly or not yet.")
    st = _st(run)
    lesson = _lesson(st, lid)
    if teacher not in lesson["audience"]:
        raise NotAllowed("This lesson is not hers.")
    if not (
        st.get("plays", {}).get(lid, {}).get(teacher)
        or st.get("heard", {}).get(lid, {}).get(teacher)
    ):
        raise LookupError("Play the lesson, or mark it heard, first.")
    masked = mask_personal(note.strip()[:NOTE_MAX]) if note.strip() else None
    if masked is not None and check_prefilter(masked.text, lesson["language"], max_chars=NOTE_MAX):
        raise ValueError("That note was held by a check. Change it and try again.")
    st.setdefault("feedback", {}).setdefault(lid, {})[teacher] = {
        "answer": answer,
        "note": masked.text if masked else "",
        "masked": list(masked.kinds) if masked else [],
        "day": st.get("clock", 0),
    }
    _event(st, "feedback", None, lesson=lid, answer=answer, note=bool(masked))
    _save(db, run, st)
    return dict(st["feedback"][lid][teacher])


def generate_next(
    db: Session,
    run: CohortRun,
    teacher: str,
    by: str,
    ctx: CallContext,
    speech: Any,
    answer_override: str | None = None,
) -> dict[str, Any]:
    """Code picks her next lesson from her last answer; call 5 words it; it goes to review."""
    st = _st(run)
    mine = [x for x in st.get("lessons", []) if teacher in x["audience"]]
    if not mine:
        raise LookupError("She has no lesson yet.")
    last = mine[-1]
    if any(x.get("next_of") == last["id"] for x in st.get("lessons", [])):
        raise LookupError("The next lesson is already made.")
    fb = st.get("feedback", {}).get(last["id"], {}).get(teacher)
    answer = answer_override if answer_override is not None else (fb or {}).get("answer")
    if answer is None and by != "silence":
        raise LookupError("Give feedback on the lesson first.")
    track = load_track(TRACKS[st["cohort"]["error"]])
    d = next_lesson.decide(track, [x["day"] for x in mine], last["day"], answer)
    if d.mode == "end":
        st2 = _st(run)
        _event(st2, "track_end", None, teacher=teacher)
        _save(db, run, st2)
        return {"decision": d.to_dict(), "lesson": None}
    lang = str(scenario_of(run)["teachers"][teacher]["language"])
    lesson = _new_lesson(
        db,
        run,
        n=last["n"] + 1,
        day=d.day,
        language=lang,
        audience=[teacher],
        decision={**d.to_dict(), "answer": answer, "by": by},
        next_of=last["id"],
        ctx=ctx,
        speech=speech,
    )
    return {"decision": d.to_dict(), "lesson": lesson["id"]}


def tick(db: Session, run: CohortRun, days: int, ctx: CallContext, speech: Any) -> list[str]:
    """Move the run's clock on. A released lesson with no answer by the set date gets the planned
    next lesson (queued for review), and the silence is recorded but never counted as a result."""
    st = _st(run)
    st["clock"] = int(st.get("clock", 0)) + max(0, days)
    _save(db, run, st)
    due_after = int(scenario_of(run).get("feedback_days", 3))
    made: list[str] = []
    for lesson in list((run.state or {}).get("lessons", [])):
        if lesson.get("released_day") is None:
            continue
        for t in lesson["audience"]:
            st = run.state or {}
            answered = st.get("feedback", {}).get(lesson["id"], {}).get(t)
            has_next = any(
                x.get("next_of") == lesson["id"] and t in x["audience"]
                for x in st.get("lessons", [])
            )
            later = [
                x for x in st.get("lessons", []) if t in x["audience"] and x["n"] > lesson["n"]
            ]
            if answered or has_next or later:
                continue
            if st.get("clock", 0) - lesson["released_day"] < due_after:
                continue
            s2 = _st(run)
            s2.setdefault("silence", {}).setdefault(lesson["id"], []).append(t)
            _event(s2, "silence_planned", "review", lesson=lesson["id"])
            _save(db, run, s2)
            out = generate_next(db, run, t, "silence", ctx, speech, answer_override=None)
            if out["lesson"]:
                made.append(out["lesson"])
    return made


# --- flow 4: chat -------------------------------------------------------------------------------


def _space(run: CohortRun) -> str:
    cid = (run.state or {}).get("cohort", {}).get("space")
    if not cid:
        raise LookupError("No cohort has formed yet.")
    return str(cid)


def ask(
    db: Session, run: CohortRun, teacher: str, text: str, share: bool, ctx: CallContext
) -> dict[str, Any]:
    cid = _space(run)
    asked = chat.ask(
        db,
        cohort_id=cid,
        teacher_id=person(run, teacher),
        text=text,
        language=str(scenario_of(run)["teachers"].get(teacher, {}).get("language", "en")),
        ai_consent=True,
        context=ctx,
    )
    q = asked.message
    if q.ai_due_at is not None:  # 60 seconds here, not the coach's hours
        q.ai_due_at = datetime.now(UTC) + timedelta(seconds=CHAT_WAIT_S)
        db.commit()
    st = _st(run)
    if share:
        st.setdefault("shared", []).append(q.id)
    from services.api.db import AiReplyDraft

    d = db.execute(select(AiReplyDraft).where(AiReplyDraft.message_id == q.id)).scalar_one_or_none()
    _event(
        st,
        "chat_asked",
        "chat",
        masked=list(asked.replaced),
        shared=share,
        drafted=bool(d and d.status != "discarded"),
    )
    _save(db, run, st)
    return chat_view(db, run, teacher)


def chat_view(db: Session, run: CohortRun, teacher: str) -> dict[str, Any]:
    cid = _space(run)
    mine = chat.my_questions(db, cid, person(run, teacher))  # raises NotMember for an outsider
    own = {q["id"] for q in mine["questions"]}
    shared = []
    for qid in (run.state or {}).get("shared", []):
        if qid in own:
            continue
        q = db.get(ChatMessage, qid)
        if q is None:
            continue
        sent = [chat._answer_view(a) for a in chat.answers_for(db, qid)]
        shared.append({"id": q.id, "from": q.author_label, "body": q.body, "answers": sent})
    due = {
        q.id: q.ai_due_at.isoformat() if q.ai_due_at else None
        for q in db.scalars(
            select(ChatMessage).where(ChatMessage.cohort_id == cid, ChatMessage.kind == "question")
        )
    }
    for q in mine["questions"]:
        q["ai_due_at"] = due.get(q["id"])
        q["shared"] = q["id"] in (run.state or {}).get("shared", [])
    return {**mine, "cohort_shared": shared, "wait_seconds": CHAT_WAIT_S}


def coach_inbox(db: Session, run: CohortRun) -> dict[str, Any]:
    cid = _space(run)
    box = chat.inbox(db, role="coach", person=person(run, "C1"))
    ids = set(db.scalars(select(ChatMessage.id).where(ChatMessage.cohort_id == cid)))
    return {
        "pending": [q for q in box.get("pending", []) if q.get("cohort_id") == cid],
        "needs_review": [a for a in box.get("needs_review", []) if a.get("question_id") in ids],
    }


def coach_reply(
    db: Session, run: CohortRun, message_id: str, mode: str, text: str | None, tags: tuple[str, ...]
) -> None:
    chat.reply(
        db, message_id, role="coach", person=person(run, "C1"), mode=mode, text=text, tags=tags
    )
    st = _st(run)
    _event(st, "chat_sent", "chat", by="coach", mode=mode)
    _save(db, run, st)


def coach_correct(
    db: Session, run: CohortRun, answer_id: str, text: str, tags: tuple[str, ...]
) -> None:
    chat.correct(db, answer_id, role="coach", person=person(run, "C1"), text=text, tags=tags)
    st = _st(run)
    _event(st, "chat_corrected", "chat")
    _save(db, run, st)


def skip_wait(db: Session, run: CohortRun) -> dict[str, Any]:
    """The wait is over: the question is due now, and the real auto-send gates decide."""
    cid = _space(run)
    now = datetime.now(UTC)
    for q in db.scalars(
        select(ChatMessage).where(ChatMessage.cohort_id == cid, ChatMessage.kind == "question")
    ):
        if q.status == "ai_draft_ready" and q.ai_due_at is not None:
            q.ai_due_at = now - timedelta(seconds=1)
    db.commit()
    result = scheduler.summary(scheduler.tick(db, now=now, cohort_ids=[cid]))
    st = _st(run)
    if result["sent"]:
        _event(st, "chat_auto_sent", "chat", sent=result["sent"])
    _save(db, run, st)
    return result


# --- flow 5: the coach's view -------------------------------------------------------------------


def _chat_counts(db: Session, cid: str) -> dict[str, int]:
    qs = list(
        db.scalars(
            select(ChatMessage).where(ChatMessage.cohort_id == cid, ChatMessage.kind == "question")
        )
    )
    answers = list(
        db.scalars(
            select(ChatMessage).where(ChatMessage.cohort_id == cid, ChatMessage.kind == "answer")
        )
    )
    return {
        "questions": len(qs),
        "open": sum(q.status in chat.OPEN for q in qs),
        "drafts_waiting": sum(q.status == "ai_draft_ready" for q in qs),
        "auto_sent": sum(a.author_role == "ai" for a in answers),
        "corrected": sum(a.status == "corrected" for a in answers),
    }


def cohort_summary(db: Session, run: CohortRun) -> dict[str, Any] | None:
    """The cohort as a coach or mentor sees it: cohort-level counts, never a child."""
    st = run.state or {}
    c = st.get("cohort")
    if not c:
        return None
    lessons = st.get("lessons", [])
    first = [x for x in lessons if x["n"] == 1]
    later = [x for x in lessons if x["n"] > 1]
    fb = st.get("feedback", {})
    counts = {k: 0 for k in next_lesson.ANSWERS}
    notes = []
    for x in first:
        for t, f in fb.get(x["id"], {}).items():
            counts[f["answer"]] += 1
            if f.get("note"):
                notes.append({"from": _display(db, run, t), "note": f["note"]})
    silent = sum(len(v) for k, v in st.get("silence", {}).items() if k in {x["id"] for x in first})
    status_count: dict[str, int] = {}
    for x in later:
        s = lesson_status(db, x)
        status_count[s] = status_count.get(s, 0) + 1
    return {
        "id": c["space"],
        "error": c["error"],
        "labels": c["labels"],
        "classes": len(c["classes"]),
        "teachers": len(c["teachers"]),
        "showing": c["showing"],
        "checked": c["checked"],
        "mentor": c["mentor"],
        "lesson1": {
            "by_language": [
                {"language": x["language"], "status": lesson_status(db, x), "source": x["source"]}
                for x in first
            ],
            "plays": sum(sum(st.get("plays", {}).get(x["id"], {}).values()) for x in first),
            "heard": sum(len(st.get("heard", {}).get(x["id"], {})) for x in first),
            "feedback": counts,
            "no_answer": silent,
            "notes": notes,
        },
        "lesson2": status_count,
        "chat": _chat_counts(db, c["space"]),
        "next_check": "awaiting_next_check",
    }


def _display(db: Session, run: CohortRun, teacher: str) -> str:
    from services.api.db import CohortMember

    cid = (run.state or {}).get("cohort", {}).get("space")
    m = db.get(CohortMember, (cid, person(run, teacher))) if cid else None
    return m.display_name if m else "Teacher"


def view(db: Session, run: CohortRun, as_label: str) -> dict[str, Any]:
    """Everything one person may see, by role. Teachers see their own class; the coach and the
    assigned mentor see the cohort's counts; another mentor sees nothing; the officer sees totals
    with any figure over fewer than 5 classes hidden."""
    if as_label not in ROLE_LABELS:
        raise NotAllowed("No such person in this run.")
    st = run.state or {}
    scn = scenario_of(run)
    base: dict[str, Any] = {
        "run": run.id,
        "as": as_label,
        "source": run.source,
        "simulated": run.source != "pilot",
        "clock": st.get("clock", 0),
        "settings": formation.form([], settings_of(run))["settings"],
        "classes_in": sorted(st.get("classes", {})),
        "expected": [c["code"] for c in scn["classes"]],
    }
    f = st.get("formation")
    summary = cohort_summary(db, run)
    if as_label.startswith("T"):
        cls = next((c for c in (f or {}).get("classes", []) if c["teacher"] == as_label), None)
        member = bool(summary and as_label in st["cohort"]["teachers"])
        base.update(
            {
                "class": cls,
                "status": (f or {}).get("status"),
                "waiting": (f or {}).get("waiting", []),
                "cohort": {
                    k: summary[k]
                    for k in ("id", "error", "labels", "classes", "teachers", "mentor")
                }
                if member and summary
                else None,
                "lessons": [_lesson_view(db, run, x, as_label) for x in _mine(db, run, as_label)]
                if member
                else [],
            }
        )
        return base
    if as_label in ("C1", "M1"):
        base["cohorts"] = [summary] if summary else []
        base["status"] = (f or {}).get("status")
        base["waiting"] = (f or {}).get("waiting", [])
        base["timeline"] = st.get("events", [])
        if as_label == "C1" and summary:
            base["inbox"] = coach_inbox(db, run)
            base["lessons"] = [
                {
                    "id": x["id"],
                    "n": x["n"],
                    "language": x["language"],
                    "for": [_display(db, run, t) for t in x["audience"]],
                    "status": lesson_status(db, x),
                    "source": x["source"],
                    "decision": x.get("decision"),
                    "sources": x["sources"],
                    "script": x["script"],
                    "review_item": x["review_item"],
                }
                for x in st.get("lessons", [])
            ]
        return base
    if as_label == "M2":
        base["cohorts"] = []
        return base
    n = summary["classes"] if summary else 0
    base["totals"] = {
        "cohorts": 1 if summary else 0,
        "classes": n if n >= MIN_CELL else None,
        "feedback": summary["lesson1"]["feedback"] if summary and n >= MIN_CELL else None,
        "min_cell": MIN_CELL,
    }
    return base


def _lesson_view(db: Session, run: CohortRun, x: dict[str, Any], teacher: str) -> dict[str, Any]:
    st = run.state or {}
    status = lesson_status(db, x)
    v = x.get("voices", {}).get(teacher) or {}
    fb = st.get("feedback", {}).get(x["id"], {}).get(teacher)
    has_next = any(
        y.get("next_of") == x["id"] and teacher in y["audience"] for y in st.get("lessons", [])
    )
    played_n = st.get("plays", {}).get(x["id"], {}).get(teacher, 0)
    heard = bool(st.get("heard", {}).get(x["id"], {}).get(teacher))
    return {
        "id": x["id"],
        "n": x["n"],
        "day": x["day"],
        "language": x["language"],
        "status": status,
        "script": fill(x["script"], values_for(run, teacher, x["day"], x["language"]))
        if status == "released"
        else None,
        "source": x["source"],
        "sources": x["sources"],
        "decision": x.get("decision"),
        "audio": {"seconds": v.get("seconds"), "format": v.get("format")}
        if v.get("file")
        else None,
        "voice_error": v.get("error"),
        "played": played_n,
        "heard": heard,
        "feedback": fb,
        "can_feedback": status == "released" and (played_n > 0 or heard) and not fb,
        "can_generate": bool(fb) and not has_next,
    }


def audio_path(run: CohortRun, lid: str, teacher: str) -> Path | None:
    lesson = _lesson(run.state or {}, lid)
    v = lesson.get("voices", {}).get(teacher) or {}
    return cache_dir() / v["file"] if v.get("file") else None


def counts_from_rows(run: CohortRun, code: str, rows: list[list[Any]]) -> sc.ClassCounts:
    """For a local pilot script: the class's answers (in memory) to counts by the engine."""
    scn = scenario_of(run)
    form = sc.form_for(scn, code)
    checked, counts, possible = sc.counts_from_rows(form, rows)
    teacher = _teacher_of(scn, code)
    return sc.ClassCounts(
        code,
        teacher,
        str(scn["teachers"][teacher]["language"]),
        int(scn["grade"]),
        str(scn["medium"]),
        checked,
        counts,
        possible,
        "pilot",
    )


def dump(run: CohortRun) -> str:
    return json.dumps(run.state, ensure_ascii=False, sort_keys=True)
