# ruff: noqa: E501
"""Improvement tracks: start one, generate its modules one at a time, take feedback, and show it.

Only the next module is ever generated. Every trigger (the start, the teacher's "Get the next module",
the daily job, a coach) goes through `generate_module`, which is safe to repeat: the row for a number is
claimed with a compare-and-set on its status (and a unique constraint on (track, number)), so a double
press, a repeated job run or a retry cannot make two copies. Code picks the module (branch.py); the text
is the library's own (library.py).

All dates are Indian dates (UTC+5:30, no daylight saving). The clock is always passed in.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ai.validators.mask import mask_personal
from ai.validators.prefilter import check_prefilter
from services.api import strings
from services.api.db import ClassCohort
from services.modules import branch, library, states
from services.modules.branch import Done
from services.modules.models import ModuleEvent, ModuleFeedback, Track, TrackModule

IST = timezone(timedelta(hours=5, minutes=30))
JOB_HOUR = 6  # the daily job runs at 06:00 Indian time
NOTE_MAX = 300


class ModulesError(Exception):
    """Something the caller can fix; `code` is a short machine code the screen words."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code


def calendar_day(now: datetime) -> date:
    """The Indian calendar date at `now`."""
    return now.astimezone(IST).date()


def job_day(now: datetime) -> date:
    """The day whose modules the daily job may generate: it changes at 06:00 Indian time, so a run at
    05:59 on the 17th still belongs to the 16th and a run at 06:00 belongs to the 17th."""
    return (now.astimezone(IST) - timedelta(hours=JOB_HOUR)).date()


def _utc(now: datetime) -> datetime:
    return now.astimezone(UTC)


# ---- helpers ------------------------------------------------------------------------------------


def _event(
    db: Session,
    track: Track,
    event: str,
    actor: str,
    now: datetime,
    module: TrackModule | None = None,
    **detail: Any,
) -> None:
    db.add(
        ModuleEvent(
            track_id=track.id,
            module_id=module.id if module else None,
            event=event,
            detail=detail,
            actor=actor,
            at=_utc(now),
        )
    )


def modules_of(db: Session, track_id: str) -> list[TrackModule]:
    return list(
        db.execute(
            select(TrackModule).where(TrackModule.track_id == track_id).order_by(TrackModule.number)
        ).scalars()
    )


def _generated(rows: list[TrackModule]) -> list[TrackModule]:
    return [m for m in rows if m.status not in (states.PLANNED, states.SKIPPED)]


def _feedback(db: Session, module: TrackModule) -> ModuleFeedback | None:
    return db.get(ModuleFeedback, module.id)


def _history(rows: list[TrackModule]) -> list[Done]:
    return [Done(m.number, m.approach_id or "", m.branch or "first") for m in _generated(rows)]


def _move(module: TrackModule, new: str) -> None:
    states.check(module.status, new)
    module.status = new


def get_track(db: Session, track_id: str) -> Track:
    track = db.get(Track, track_id)
    if track is None:
        raise ModulesError("no_track", "There is no such track.")
    return track


def _template_id(error: str, approach: str, smaller: bool) -> str:
    return f"{error}:{approach}" + (":small" if smaller else "")


# ---- planning -----------------------------------------------------------------------------------


def _replan(
    db: Session, track: Track, rows: list[TrackModule], answer: str | None
) -> branch.NextModule:
    """Make the planned rows after the last generated module match what code would give next: the
    next module (from the answer on the last one) and the unused plan approaches after it, within the
    cap and the end date. Due dates already set (or edited by a coach) are kept. Returns the preview of
    the next module (its `stop` says why nothing is planned)."""
    plan = library.plan_for(track.error)
    made = _generated(rows)
    planned = [m for m in rows if m.status == states.PLANNED]
    n = len(made)
    cursor = made[-1].due_date if made else track.start_date - timedelta(days=library.gap_days())
    preview = branch.next_module(plan, _history(rows), answer, track.cap)
    wanted: list[tuple[str, bool]] = []
    if not preview.stops and preview.approach:
        wanted.append((preview.approach, preview.smaller))
        used = {d.approach for d in _history(rows)} | {preview.approach}
        for t in plan.templates:
            if t.approach not in used:
                wanted.append((t.approach, False))
                used.add(t.approach)
    keep = 0
    for i, (approach, smaller) in enumerate(wanted[: max(0, track.cap - n)]):
        existing = planned[i] if i < len(planned) else None
        due = existing.due_date if existing else cursor + timedelta(days=library.gap_days())
        if due > track.end_date:
            break
        row = existing or TrackModule(
            id="mod-" + secrets.token_hex(6),
            track_id=track.id,
            number=n + 1 + i,
            due_date=due,
            status=states.PLANNED,
        )
        if existing is None:
            db.add(row)
        row.approach_id = approach
        row.template_id = _template_id(track.error, approach, smaller)
        row.title = library.title(track.error, approach, track.language)
        cursor = due
        keep += 1
    for row in planned[keep:]:
        db.delete(row)
    db.flush()
    return preview


# ---- start --------------------------------------------------------------------------------------


def start_track(
    db: Session,
    cohort: ClassCohort,
    error: str,
    language: str,
    now: datetime,
    end_date: date | None = None,
) -> Track:
    """Plan the modules and generate Module 1 at once. Starting again returns the same track."""
    if error not in (cohort.errors or []):
        raise ModulesError("bad_error", "That error is not one this cohort chose.")
    existing = db.execute(
        select(Track).where(Track.class_cohort_id == cohort.id, Track.error == error)
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    start = calendar_day(now)
    length = library.planned_length(error)
    track = Track(
        id="trk-" + secrets.token_hex(6),
        class_cohort_id=cohort.id,
        teacher_id=cohort.teacher_id,
        error=error,
        language=language if language in library.LANGS else "en",
        start_date=start,
        end_date=end_date or start + timedelta(days=library.gap_days() * length),
        cap=library.cap(),
        note=None if library.has_plan(error) else "no plan for this error: one module",
    )
    try:
        with db.begin_nested():
            db.add(track)
    except IntegrityError:  # a second start at the same moment: the first one stands
        return db.execute(
            select(Track).where(Track.class_cohort_id == cohort.id, Track.error == error)
        ).scalar_one()
    _event(db, track, "track_started", "system", now, planned=length, plan=library.has_plan(error))
    if track.note:
        _event(db, track, "no_plan", "system", now, error=error)
    plan = library.plan_for(error)
    for i, t in enumerate(plan.templates[:length]):
        db.add(
            TrackModule(
                id="mod-" + secrets.token_hex(6),
                track_id=track.id,
                number=i + 1,
                template_id=_template_id(error, t.approach, False),
                approach_id=t.approach,
                title=library.title(error, t.approach, track.language),
                due_date=start + timedelta(days=library.gap_days() * i),
                status=states.PLANNED,
            )
        )
    db.flush()
    generate_module(db, track.id, 1, "start", now)
    db.commit()
    return track


# ---- generate -----------------------------------------------------------------------------------


@dataclass
class Generated:
    module: TrackModule | None  # None when the track stopped instead
    stop: str | None = None  # a branch.STOP_* code
    created: bool = False  # this call made it (False: it already existed)


def generate_module(
    db: Session, track_id: str, number: int, trigger: str, now: datetime
) -> Generated:
    """The one function every trigger uses. Safe to call twice for the same module."""
    if trigger not in states.TRIGGERS:
        raise ValueError(f"trigger must be one of {states.TRIGGERS}")
    track = get_track(db, track_id)
    rows = modules_of(db, track.id)
    row = next((m for m in rows if m.number == number), None)
    if row is not None and row.status not in (states.PLANNED,):
        return Generated(row if row.status != states.SKIPPED else None, None, False)
    if track.status != "active":
        return Generated(None, track.stop_reason, False)
    made = _generated(rows)
    if number != len(made) + 1:
        raise ModulesError("not_ready", "The module before this one is not made yet.")
    prev = made[-1] if made else None
    fb = _feedback(db, prev) if prev else None
    if trigger == "teacher" and prev is not None and fb is None:
        raise ModulesError("needs_feedback", "Give feedback on the last module first.")
    answer = fb.answer if fb else None
    plan = library.plan_for(track.error)
    from services.modules import review  # here to avoid an import loop

    prefs = review.prefs_for(db, prev) if prev else review.Prefs()
    due = (
        row.due_date
        if row
        else (prev.due_date if prev else track.start_date) + timedelta(days=library.gap_days())
    )
    default = branch.next_module(plan, _history(rows), answer, track.cap)
    result = branch.next_module(plan, _history(rows), answer, track.cap, prefer=prefs.approaches)
    if row is None and not result.stops:
        # the plan has no row for it (it was dropped at the end date, or never planned)
        result = branch.next_module(plan, _history(rows), answer, track.cap, past_end=True)
    if result.stops:
        _finish(db, track, rows, result.stop or "done", trigger, now)
        db.commit()
        return Generated(None, result.stop, True)
    smaller = result.smaller
    mt = library.module_text(track.error, result.approach or "", smaller, track.language)
    text = mt.to_dict()
    if prefs:  # what code changed because of her note (validated tags only)
        text["parts"] = library.reorder(text["parts"], list(prefs.sections))
        text["emphasis"] = list(prefs.sections)
        text["changed"] = {
            "barrier": list(prefs.barrier),
            "focus": list(prefs.focus),
            "approach": result.approach != default.approach,
        }
    claim = {
        "template_id": _template_id(track.error, result.approach or "", smaller),
        "approach_id": result.approach,
        "title": mt.title,
        "status": states.READY,
        "generated_at": _utc(now),
        "generated_by": trigger,
        "branch": result.branch,
        "reason": result.reason.to_dict(),
        "text": text,
        "language": mt.language,
    }
    if row is None:
        row = TrackModule(
            id="mod-" + secrets.token_hex(6),
            track_id=track.id,
            number=number,
            due_date=due,
            **claim,
        )
        try:
            with db.begin_nested():
                db.add(row)
        except IntegrityError:  # another request made it first
            db.expire_all()
            return Generated(_by_number(db, track.id, number), None, False)
    else:
        got = db.execute(
            update(TrackModule)
            .where(TrackModule.id == row.id, TrackModule.status == states.PLANNED)
            .values(**claim)
        )
        if getattr(got, "rowcount", 0) == 0:  # lost the race: the other run's module stands
            db.expire_all()
            return Generated(_by_number(db, track.id, number), None, False)
        db.expire_all()
        row = _by_number(db, track.id, number)
    if prev is not None:
        prev = _by_number(db, track.id, prev.number)
        if prev.status == states.FEEDBACK_GIVEN:
            _move(prev, states.COMPLETED)
        elif prev.status in (states.READY, states.DOWNLOADED):
            _move(prev, states.EXPIRED)
            _event(db, track, "no_feedback", "system", now, prev, next_by=trigger)
    actor = "coach" if trigger == "coach" else ("teacher" if trigger == "teacher" else "system")
    _event(
        db,
        track,
        "module_generated",
        actor,
        now,
        row,
        trigger=trigger,
        branch=result.branch,
        reason=result.reason.code,
        approach=result.approach,
    )
    rows = modules_of(db, track.id)
    _replan(db, track, rows, None)
    db.commit()
    return Generated(_by_number(db, track.id, number), None, True)


def _by_number(db: Session, track_id: str, number: int) -> TrackModule:
    return db.execute(
        select(TrackModule).where(TrackModule.track_id == track_id, TrackModule.number == number)
    ).scalar_one()


def _finish(
    db: Session, track: Track, rows: list[TrackModule], stop: str, trigger: str, now: datetime
) -> None:
    """The track ends: nothing planned stays planned; she is sent to a person when the plan and its
    alternatives ran out or the cap was reached, and the coach is told."""
    for m in rows:
        if m.status == states.PLANNED:
            _move(m, states.SKIPPED)
    last = _generated(rows)[-1] if rows and _generated(rows) else None
    if last is not None and last.status == states.FEEDBACK_GIVEN:
        _move(last, states.COMPLETED)
    track.status = "completed" if stop == branch.STOP_DONE else "stopped"
    track.stop_reason = stop
    _event(db, track, "track_stopped", "system", now, reason=stop, trigger=trigger)
    if stop in (branch.STOP_CAP, branch.STOP_EXHAUSTED):
        _event(db, track, "coach_notified", "system", now, reason=stop)


# ---- feedback and download ----------------------------------------------------------------------


def _owned(db: Session, track_id: str, teacher_id: str) -> Track:
    track = get_track(db, track_id)
    if track.teacher_id != teacher_id:
        raise ModulesError("not_hers", "This track is not hers.")
    return track


def give_feedback(
    db: Session,
    track_id: str,
    number: int,
    teacher_id: str,
    answer: str,
    note: str,
    now: datetime,
) -> ModuleFeedback:
    if answer not in states.ANSWERS:
        raise ModulesError("bad_answer", "Choose worked, partly, not yet or not tried.")
    track = _owned(db, track_id, teacher_id)
    rows = modules_of(db, track.id)
    module = next((m for m in rows if m.number == number), None)
    if module is None or module.status in (states.PLANNED, states.SKIPPED):
        raise ModulesError("not_made", "That module is not made yet.")
    text = note.strip()[:NOTE_MAX]
    masked = mask_personal(text) if text else None
    if masked is not None and check_prefilter(masked.text, track.language, max_chars=NOTE_MAX):
        raise ModulesError("note_held", "That note was held by a check. Change it and try again.")
    fb = _feedback(db, module)
    late = module.number < len(_generated(rows))
    was = fb.answer if fb else None
    if fb is None:
        fb = ModuleFeedback(module_id=module.id, answer=answer, note="", given_at=_utc(now))
        db.add(fb)
    fb.answer, fb.note, fb.given_at = answer, masked.text if masked else "", _utc(now)
    held = answer == "not_tried"
    if not held and states.can(module.status, states.FEEDBACK_GIVEN):
        _move(module, states.FEEDBACK_GIVEN)  # a hold keeps the module open
    _event(
        db,
        track,
        "feedback_given",
        "teacher",
        now,
        module,
        answer=answer,
        late=late,
        note=bool(masked),
    )
    if held and not late and was != "not_tried" and track.status == "active":
        _defer(db, track, module, now)  # the first deferral; the daily job makes the second
    elif not held and not late and track.status == "active":
        # her answer on the newest module decides what is planned next (and may end the track)
        preview = _replan(db, track, modules_of(db, track.id), answer)
        if not any(m.status == states.PLANNED for m in modules_of(db, track.id)):
            _finish(
                db,
                track,
                modules_of(db, track.id),
                preview.stop or branch.STOP_END_DATE,
                "teacher",
                now,
            )
    db.commit()
    return fb


def deferrals_of(db: Session, module: TrackModule) -> int:
    return int(
        db.execute(
            select(func.count())
            .select_from(ModuleEvent)
            .where(ModuleEvent.module_id == module.id, ModuleEvent.event == "deferred")
        ).scalar_one()
    )


def _defer(
    db: Session, track: Track, module: TrackModule, now: datetime, actor: str = "teacher"
) -> bool:
    """Hold: the next planned dates (and the end date) move by MODULE_DEFER_DAYS, at most
    MODULE_MAX_DEFERRALS times per module. The second deferral tells the coach. Returns True when
    the dates moved. Not tried is never counted as a result."""
    done = deferrals_of(db, module)
    if done >= library.max_deferrals():
        return False
    days = library.defer_days()
    planned = [m for m in modules_of(db, track.id) if m.status == states.PLANNED]
    for m in planned:
        m.due_date = m.due_date + timedelta(days=days)
    track.end_date = track.end_date + timedelta(days=days)
    nxt = planned[0].due_date.isoformat() if planned else None
    _event(db, track, "deferred", actor, now, module, n=done + 1, days=days, next_due=nxt)
    if done + 1 >= library.max_deferrals():
        _event(db, track, "coach_notified", "system", now, module, reason="deferred_twice")
    return True


def maybe_defer(db: Session, track_id: str, number: int, now: datetime) -> bool:
    """For the daily job, before it makes module `number`: if the module before it is held (her answer
    is not tried) and has deferrals left, defer again instead of making it. After the last deferral
    the job makes the planned module as no_feedback."""
    track = get_track(db, track_id)
    prev = next((m for m in modules_of(db, track.id) if m.number == number - 1), None)
    fb = _feedback(db, prev) if prev else None
    if prev is None or fb is None or fb.answer != "not_tried":
        return False
    moved = _defer(db, track, prev, now, "system")
    db.commit()
    return moved


CHIPS = ("no_time", "materials", "not_sure", "absent", "other")


def record_reason(
    db: Session, track_id: str, number: int, teacher_id: str, chip: str, now: datetime
) -> None:
    """Why not yet?: one approved chip, kept as an event (private to her; coaches see only counts)."""
    if chip not in CHIPS:
        raise ModulesError("bad_chip", "Choose one of the reasons.")
    track = _owned(db, track_id, teacher_id)
    module = _by_number(db, track.id, number)
    fb = _feedback(db, module)
    if fb is None or fb.answer != "not_tried":
        raise ModulesError("not_held", "Say you have not tried it yet first.")
    _event(db, track, "not_tried_reason", "teacher", now, module, chip=chip)
    db.commit()


def mark_downloaded(
    db: Session, track_id: str, number: int, teacher_id: str, audio_ref: str, now: datetime
) -> TrackModule:
    track = _owned(db, track_id, teacher_id)
    module = _by_number(db, track.id, number)
    if module.status in (states.PLANNED, states.SKIPPED):
        raise ModulesError("not_made", "That module is not made yet.")
    first = module.audio_ref is None
    module.audio_ref = audio_ref[:120]
    if states.can(module.status, states.DOWNLOADED):
        _move(module, states.DOWNLOADED)
    if first:
        _event(db, track, "downloaded", "teacher", now, module)
    db.commit()
    return module


def next_for_teacher(db: Session, track_id: str, teacher_id: str, now: datetime) -> Generated:
    """ "Get the next module": only after feedback on the newest one."""
    track = _owned(db, track_id, teacher_id)
    rows = modules_of(db, track.id)
    return generate_module(db, track.id, len(_generated(rows)) + 1, "teacher", now)


# ---- the teacher's view -------------------------------------------------------------------------


def reason_text(code_dict: dict[str, Any] | None, lang: str) -> str:
    if not code_dict:
        return ""
    return strings.text(
        lang,
        "module.reason." + str(code_dict["code"]),
        n=code_dict.get("n", 0),
        prev=code_dict.get("prev", 0),
    )


def module_view(db: Session, track: Track, m: TrackModule, lang: str, total: int) -> dict[str, Any]:
    out: dict[str, Any] = {
        "number": m.number,
        "status": m.status,
        "title": m.title,
        "due_date": m.due_date.isoformat(),
        "branch": m.branch,
    }
    if m.status in (states.PLANNED, states.SKIPPED):
        out["title"] = (
            library.title(track.error, m.approach_id or "", lang) if m.approach_id else m.title
        )
        return out
    stored = m.text or {}
    live = (
        library.module_text(
            track.error, m.approach_id or "", (m.template_id or "").endswith(":small"), lang
        )
        if m.approach_id and not _gone(track.error, m.approach_id)
        else None
    )
    mt = live.to_dict() if live is not None and not live.omitted else stored
    out["title"] = mt.get("title") or m.title
    if stored.get("emphasis"):
        from services.modules import review

        mt = {**mt, "parts": library.reorder(mt["parts"], stored["emphasis"])}
        ch = stored.get("changed", {})
        out["changed_text"] = review.changes_line(
            review.Prefs(
                sections=tuple(stored["emphasis"]),
                barrier=tuple(ch.get("barrier", [])),
                focus=tuple(ch.get("focus", [])),
            ),
            lang,
            bool(ch.get("approach")),
        )
    out["text"] = mt
    out["language"] = mt.get("language", m.language)
    out["reason"] = m.reason
    out["reason_text"] = reason_text(m.reason, lang)
    out["generated_by"] = m.generated_by
    out["audio_ref"] = m.audio_ref
    fb = _feedback(db, m)
    out["feedback"] = {"answer": fb.answer, "note": fb.note} if fb else None
    if fb is not None and fb.answer == "not_tried":
        short = library.module_text(track.error, m.approach_id or "", True, lang)
        out["hold"] = {
            "deferrals": deferrals_of(db, m),
            "max": library.max_deferrals(),
            "days": library.defer_days(),
            "short": None if short.omitted else short.to_dict(),
        }
    if live is not None and not live.omitted:
        intro = strings.text(lang, "module.spoken.intro", n=m.number, total=total, title=live.title)
        out["spoken"] = library.spoken(live, intro)
    return out


def _gone(error: str, approach: str) -> bool:
    """The template was removed from the library after the track began: the stored text stands."""
    return approach not in library.plan_for(error).approaches()


def track_view(db: Session, track: Track, lang: str, now: datetime) -> dict[str, Any]:
    rows = modules_of(db, track.id)
    made = _generated(rows)
    live = [m for m in rows if m.status != states.SKIPPED]
    total = len(live)
    latest = made[-1] if made else None
    nxt = next((m for m in rows if m.status == states.PLANNED), None)
    can: dict[str, Any]
    if track.status != "active":
        can = {"enabled": False, "code": "track_" + (track.stop_reason or "done")}
    elif nxt is None:
        can = {"enabled": False, "code": "no_more"}
    elif latest is not None and _feedback(db, latest) is None:
        can = {
            "enabled": False,
            "code": "needs_feedback",
            "number": latest.number,
            "next": nxt.number,
            "due_date": nxt.due_date.isoformat(),
        }
    else:
        can = {
            "enabled": True,
            "code": "ok",
            "next": nxt.number,
            "due_date": nxt.due_date.isoformat(),
        }
    return {
        "id": track.id,
        "cohort_id": track.class_cohort_id,
        "error": track.error,
        "status": track.status,
        "stop_reason": track.stop_reason,
        "start_date": track.start_date.isoformat(),
        "end_date": track.end_date.isoformat(),
        "language": track.language,
        "note": track.note,
        "total": total,
        "current": latest.number if latest else 0,
        "can_next": can,
        "modules": [
            module_view(db, track, m, lang, total) for m in rows if m.status != states.SKIPPED
        ],
    }


def tracks_of(db: Session, teacher_id: str, cohort_id: str | None = None) -> list[Track]:
    q = select(Track).where(Track.teacher_id == teacher_id)
    if cohort_id:
        q = q.where(Track.class_cohort_id == cohort_id)
    return list(db.execute(q.order_by(Track.created_at)).scalars())


# ---- the coach's view (counts only) --------------------------------------------------------------


def coach_counts(db: Session, cohort_id: str, now: datetime) -> dict[str, Any]:
    """Per module of a cohort's track: how many are at it, downloaded it, answered, and what is overdue
    or failed. Counts only: no teacher id and no name leave this function."""
    tracks = list(db.execute(select(Track).where(Track.class_cohort_id == cohort_id)).scalars())
    today = job_day(now)
    per: dict[int, dict[str, Any]] = {}

    def slot(n: int) -> dict[str, Any]:
        return per.setdefault(
            n,
            {
                "number": n,
                "at": 0,
                "generated": 0,
                "downloaded": 0,
                "feedback": {"worked": 0, "partly": 0, "not_yet": 0, "not_tried": 0},
                "overdue": 0,
                "failed": 0,
                "not_downloaded_flag": 0,
            },
        )

    stopped = {"cap": 0, "exhausted": 0}
    for t in tracks:
        rows = modules_of(db, t.id)
        made = _generated(rows)
        if made and t.status == "active":
            slot(made[-1].number)["at"] += 1
        if t.status == "stopped" and t.stop_reason in stopped:
            stopped[t.stop_reason] += 1
        for m in rows:
            s = slot(m.number)
            if m.status not in (states.PLANNED, states.SKIPPED):
                s["generated"] += 1
                if m.audio_ref:  # only audio she actually took counts, not a later state
                    s["downloaded"] += 1
                fb = _feedback(db, m)
                if fb:
                    s["feedback"][fb.answer] += 1
                flagged = db.execute(
                    select(func.count())
                    .select_from(ModuleEvent)
                    .where(ModuleEvent.module_id == m.id, ModuleEvent.event == "no_download_flag")
                ).scalar_one()
                s["not_downloaded_flag"] += 1 if flagged else 0
            elif m.status == states.PLANNED:
                if t.status == "active" and m.due_date <= today:
                    s["overdue"] += 1
                if m.failures:
                    s["failed"] += 1
    return {
        "cohort_id": cohort_id,
        "tracks": len(tracks),
        "modules": [per[k] for k in sorted(per)],
        "stopped": stopped,
    }


def _audit_date_change(
    db: Session, track: Track, module: TrackModule, old: date, new: date, reason: str, now: datetime
) -> None:
    _event(
        db,
        track,
        "due_changed",
        "coach",
        now,
        module,
        old=old.isoformat(),
        new=new.isoformat(),
        reason=reason,
    )


def _clean_reason(reason: str) -> str:
    text = mask_personal(reason.strip()[:120]).text
    if not text:
        raise ModulesError("reason_needed", "Say why the date changes.")
    return text


def set_due_date(
    db: Session, track_id: str, number: int, new: date, reason: str, now: datetime
) -> TrackModule:
    """A coach moves one planned module's date. A module already made keeps its date."""
    reason = _clean_reason(reason)
    track = get_track(db, track_id)
    rows = modules_of(db, track.id)
    m = next((x for x in rows if x.number == number), None)
    if m is None or m.status != states.PLANNED:
        raise ModulesError("fixed_date", "Only a module that is not made yet can change its date.")
    before = next((x for x in reversed(rows) if x.number < number), None)
    if before is not None and new < before.due_date:
        raise ModulesError("before_previous", "A module cannot be due before the one ahead of it.")
    after = next((x for x in rows if x.number > number and x.status == states.PLANNED), None)
    if after is not None and new > after.due_date:
        raise ModulesError("after_next", "A module cannot be due after the one that follows it.")
    old = m.due_date
    m.due_date = new
    if new > track.end_date:
        track.end_date = new
    _audit_date_change(db, track, m, old, new, reason, now)
    db.commit()
    return m


def shift_dates(db: Session, cohort_id: str, days: int, reason: str, now: datetime) -> int:
    """Shift every module of the cohort that is not made yet, and the end date, by `days` (a holiday).
    Returns how many dates moved. Dates of made modules never change."""
    if days == 0 or abs(days) > 60:
        raise ModulesError("bad_shift", "Shift by 1 to 60 days, earlier or later.")
    reason = _clean_reason(reason)
    moved = 0
    for track in db.execute(select(Track).where(Track.class_cohort_id == cohort_id)).scalars():
        if track.status != "active":
            continue
        rows = modules_of(db, track.id)
        floor = max((m.due_date for m in _generated(rows)), default=None)
        for m in rows:
            if m.status != states.PLANNED:
                continue
            new = m.due_date + timedelta(days=days)
            if floor is not None and new < floor:
                new = floor
            if new != m.due_date:
                _audit_date_change(db, track, m, m.due_date, new, reason, now)
                m.due_date = new
                moved += 1
        track.end_date = track.end_date + timedelta(days=days)
    db.commit()
    return moved


def coach_generate(db: Session, track_id: str, now: datetime) -> Generated:
    """A coach makes the next module for a track (audited as trigger "coach")."""
    track = get_track(db, track_id)
    return generate_module(
        db, track.id, len(_generated(modules_of(db, track.id))) + 1, "coach", now
    )
