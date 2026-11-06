# ruff: noqa: E501
"""The private check-in, and the masked summary she may share with her cohort.

THE RULE: the check-in (her answer, note, follow-up answers, "what changes next") is private to the
teacher. Nothing reaches the cohort chat unless she reads the exact text and confirms. The draft is built
by CODE from her answer, the validated tags and her own masked note; no AI writes or rewrites it. The text
is masked again on Share and blocked if a name, roll number, class code, phone number or percentage
remains. Sharing twice makes one post. She can retract (soft delete, audited) and can share later until
the next module is made. Coaches and mentors see counts of answers, never her note, unless she shared it.
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ai.validators.mask import mask_personal
from ai.validators.thread import check_thread_post
from services.api import strings
from services.api.cohorts import lifecycle, thread
from services.api.db import ClassCohort, CohortMember, CohortSpace, ThreadPost
from services.modules import review, service
from services.modules.models import (
    CheckinShare,
    ModuleEvent,
    ModuleFeedback,
    ModuleReview,
    Track,
    TrackModule,
)

FIELDS = ("how", "note", "help", "counts", "name")
DEFAULT_FIELDS = {"how": True, "note": True, "help": True, "counts": False, "name": False}
MAX_TEXT = 600
_PERCENT = re.compile(r"(%|\bpercent\b|\bper cent\b|प्रतिशत|சதவீதம்)", re.IGNORECASE)
_CLASS_CODE = re.compile(r"\b(?:cc|trk|mod|chk|c)-[0-9a-z]{3,}(?::\d+)?\b", re.IGNORECASE)
_ROLL_WORD = re.compile(r"\broll\b|\bरोल\b|ரோல்", re.IGNORECASE)


# ---- where it can be shared ----------------------------------------------------------------------


SOLO = "so-"  # the id prefix of a chat space that belongs to one teacher's own class cohort


def solo_space(db: Session, teacher_id: str, error: str) -> CohortSpace:
    """The chat of a cohort of one class (decided 2026-11-06). There are no other teachers in it, but the guide (the AI,
    answering a question nobody replied to), the coach and the mentor are, once the officer assigns them. It belongs to
    this teacher alone: `officer_id` holds her id, and the open list shows it to nobody else. She still joins with her own tap."""
    sid = SOLO + hashlib.sha1(f"{teacher_id}|{error}".encode()).hexdigest()[:12]  # noqa: S324 (a label, not security)
    space = db.get(CohortSpace, sid)
    if space is None:
        space = CohortSpace(id=sid, error=error, status="active", coach_id=None, officer_id=teacher_id, mentor_ids=[], school_count=1, simulated=False)
        db.add(space)
        lifecycle.audit(db, sid, "system", "solo", "created", error=error)
        db.commit()
    return space


def chat_space(db: Session, teacher_id: str, track: Track) -> CohortSpace | None:
    """The cohort chat she belongs to for this error. For a cohort of one class it is her own space with the guide, the
    coach and the mentor and no other teacher; None only when she has no cohort for this error."""
    rows = db.execute(
        select(CohortSpace)
        .join(CohortMember, CohortMember.cohort_id == CohortSpace.id)
        .where(
            CohortMember.teacher_id == teacher_id,
            CohortSpace.error == track.error,
            CohortSpace.status.in_(("proposed", "active")),
        )
        .order_by(CohortSpace.created_at)
    ).scalars()
    found = next(iter(rows), None)
    if found is not None:
        return found
    own = db.execute(select(ClassCohort).where(ClassCohort.teacher_id == teacher_id)).scalars()
    if any(track.error in (c.errors or []) for c in own):
        return solo_space(db, teacher_id, track.error)
    return None


def chat_state(
    db: Session, teacher_id: str, track: Track, since: datetime | None = None
) -> dict[str, Any]:
    """For the Open cohort chat button: is there a chat, can she post, how many new posts (not hers)."""
    space = chat_space(db, teacher_id, track)
    if space is None:
        return {
            "available": False,
            "reason": "no_peers",
            "cohort_id": None,
            "open": False,
            "unread": 0,
        }
    q = (
        select(func.count())
        .select_from(ThreadPost)
        .where(
            ThreadPost.cohort_id == space.id,
            ThreadPost.status == "visible",
            func.coalesce(ThreadPost.author_teacher_id, "") != teacher_id,
        )
    )
    if since is not None:
        q = q.where(ThreadPost.created_at > since.astimezone(UTC))  # stored in UTC
    unread = int(db.execute(q).scalar_one()) if since is not None else 0
    return {
        "available": True,
        "reason": None,
        "cohort_id": space.id,
        "open": lifecycle.thread_state(db, space) == "open",
        "unread": unread,
    }


# ---- the draft, built by code --------------------------------------------------------------------


def _fields(fields: dict[str, bool] | None) -> dict[str, bool]:
    out = dict(DEFAULT_FIELDS)
    for k, v in (fields or {}).items():
        if k in FIELDS:
            out[k] = bool(v)
    return out


def build_draft(
    db: Session, track: Track, module: TrackModule, fields: dict[str, bool] | None, lang: str
) -> str:
    """The exact text that would be posted: from her answer, the validated tags and her masked note.
    No roll number, class code, name or percentage is ever put in by code."""
    f = _fields(fields)
    fb = db.get(ModuleFeedback, module.id)
    rev = db.get(ModuleReview, module.id)
    if fb is None:
        return ""
    parts: list[str] = []
    if f["how"]:
        answer = strings.text(lang, f"module.share.answer.{fb.answer}")
        parts.append(
            strings.text(
                lang, "module.share.how", n=module.number, title=module.title, answer=answer
            )
        )
    if f["note"]:
        if fb.note.strip():
            parts.append(fb.note.strip())
        if rev and not rev.safety and rev.barrier_tags:
            told = ", ".join(review.tag_label("barrier_tags", t, lang) for t in rev.barrier_tags)
            parts.append(strings.text(lang, "module.share.barrier", list=told))
    if f["counts"]:
        cohort = db.get(ClassCohort, track.class_cohort_id)
        if cohort is not None and track.error in (cohort.counts or {}):
            parts.append(
                strings.text(
                    lang,
                    "module.share.counts",
                    k=cohort.counts[track.error],
                    n=cohort.children_checked,
                )
            )
    if f["help"]:
        focus = [t for t in (rev.focus_tags if rev and not rev.safety else [])]
        if focus:
            parts.append(
                strings.text(
                    lang,
                    "module.share.help_focus",
                    focus=review.tag_label("focus_tags", focus[0], lang),
                )
            )
        else:
            parts.append(strings.text(lang, "module.share.help"))
    return " ".join(p for p in parts if p).strip()[:MAX_TEXT]


def problems(text: str, lang: str) -> list[str]:
    """What stops a text being shared: codes the screen words ("please remove ..."). Empty means it may go."""
    t = text.strip()
    out: list[str] = []
    if not t:
        return ["empty"]
    if len(t) > MAX_TEXT:
        out.append("length")
    for kind in mask_personal(t).kinds:
        out.append(kind)
    try:
        out.extend(v.code for v in check_thread_post(t, lang))
    except Exception:  # noqa: BLE001 - the check could not run: hold, never pass
        out.append("check_unavailable")
    if _PERCENT.search(t):
        out.append("percent")
    if _CLASS_CODE.search(t):
        out.append("class_code")
    if _ROLL_WORD.search(t):
        out.append("roll_number")
    return list(dict.fromkeys(out))


# ---- the state of one check-in -------------------------------------------------------------------


def _share(db: Session, module: TrackModule) -> CheckinShare | None:
    return db.get(CheckinShare, module.id)


def _next_made(db: Session, track: Track, module: TrackModule) -> bool:
    return any(
        m.number == module.number + 1 and m.status not in ("planned", "skipped")
        for m in service.modules_of(db, track.id)
    )


def state(
    db: Session,
    track: Track,
    module: TrackModule,
    teacher_id: str,
    lang: str,
    since: datetime | None = None,
) -> dict[str, Any]:
    """Everything the check-in screen needs; private to her."""
    fb = db.get(ModuleFeedback, module.id)
    share = _share(db, module)
    active = share is not None and share.retracted_at is None
    chat = chat_state(db, teacher_id, track, since)
    rev = review.view(db, module, lang)
    later = fb is not None and not active and not _next_made(db, track, module)
    return {
        "answer": fb.answer if fb else None,
        "note": fb.note if fb else "",
        "review": rev,
        "chat": chat,
        "share": {
            "shared": active,
            "retracted": share is not None and share.retracted_at is not None,
            "posted_text": share.posted_text if active and share else None,
            "fields": share.fields if active and share else None,
            "anonymous": share.anonymous if active and share else None,
            "can_share": fb is not None
            and chat["available"]
            and not active
            and (later or share is None),
            "share_later_open": later,
            "default_fields": dict(DEFAULT_FIELDS),
            "draft": build_draft(db, track, module, None, lang) if fb is not None else "",
        },
    }


# ---- share and retract ---------------------------------------------------------------------------


def share(
    db: Session,
    track: Track,
    module: TrackModule,
    teacher_id: str,
    *,
    text: str,
    fields: dict[str, bool] | None,
    named: bool,
    ai_help: bool,
    lang: str,
    now: datetime,
) -> CheckinShare:
    """Post the summary she confirmed. Masked again; blocked if anything identifying remains."""
    fb = db.get(ModuleFeedback, module.id)
    if fb is None:
        raise service.ModulesError("no_answer", "Give your answer first.")
    existing = _share(db, module)
    if existing is not None and existing.retracted_at is None:
        return existing  # pressing Share twice does nothing
    if _next_made(db, track, module):
        raise service.ModulesError(
            "share_closed",
            "The next module is already made, so this check-in can no longer be shared.",
        )
    space = chat_space(db, teacher_id, track)
    if space is None:
        raise service.ModulesError("no_peers", "This cohort has no chat.")
    f = _fields(fields)
    found = problems(
        text.strip(), lang
    )  # what she typed, before anything is replaced: say what to remove
    if found:
        raise service.ModulesError("blocked:" + ",".join(found), "That cannot be shared yet.")
    final = mask_personal(text.strip()).text  # and masked again on Share, after any edit
    try:
        post = thread.post_checkin(db, space.id, teacher_id, final, lang, anonymous=not named)
    except thread.PostRejected as exc:
        raise service.ModulesError(
            "blocked:" + ",".join(exc.codes), "That cannot be shared yet."
        ) from exc
    except thread.ThreadClosed as exc:
        raise service.ModulesError("thread_closed", str(exc)) from exc
    except thread.NotMember as exc:
        raise service.ModulesError("no_peers", str(exc)) from exc
    row = existing or CheckinShare(module_id=module.id, cohort_id=space.id, thread_post_id=post.id)
    row.cohort_id, row.thread_post_id = space.id, post.id
    row.fields, row.posted_text, row.anonymous = f, final, not named
    row.shared_at, row.retracted_at = now.astimezone(UTC), None
    asked = False
    if f["help"]:
        asked = _ask_for_help(db, track, module, space, teacher_id, lang, ai_help, now)
    row.help_asked = asked
    if existing is None:
        db.add(row)
    lifecycle.audit(
        db,
        space.id,
        "teacher",
        "member",
        "checkin_shared",
        module=module.number,
        fields=[k for k, v in f.items() if v],
        named=named,
        asked=asked,
    )
    service._event(db, track, "checkin_shared", "teacher", now, module, named=named, asked=asked)
    db.commit()
    return row


def _ask_for_help(
    db: Session,
    track: Track,
    module: TrackModule,
    space: CohortSpace,
    teacher_id: str,
    lang: str,
    ai_help: bool,
    now: datetime,
) -> bool:
    """ "What I would like help with" goes through the EXISTING question flow (draft from approved
    sources, coach inbox, 60 second timeout, labelled, correctable). The AI draft only if she ticked it."""
    from services.chat import service as chat

    q = strings.text(lang, "module.share.question", n=module.number, title=module.title)
    try:
        db.commit()  # no write is held open across the chat flow
        chat.ask(
            db,
            cohort_id=space.id,
            teacher_id=teacher_id,
            text=q,
            language=lang,
            ai_consent=ai_help,
            now=now,
        )
        return True
    except Exception:  # noqa: BLE001 - the share stands even if the question could not be asked
        return False


def retract(
    db: Session, track: Track, module: TrackModule, teacher_id: str, now: datetime
) -> CheckinShare:
    row = _share(db, module)
    if row is None or row.retracted_at is not None:
        raise service.ModulesError("not_shared", "Nothing is shared.")
    post = db.get(ThreadPost, row.thread_post_id)
    if post is not None:
        post.body, post.status, post.decided_at = None, "deleted", now.astimezone(UTC)
    row.retracted_at = now.astimezone(UTC)
    lifecycle.audit(
        db, row.cohort_id, "teacher", "member", "checkin_retracted", module=module.number
    )
    service._event(db, track, "checkin_retracted", "teacher", now, module)
    db.commit()
    return row


def call_me(db: Session, track: Track, module: TrackModule, now: datetime) -> None:
    """ "Ask my coach to call me": the only way the coach hears of a safety flag, and no content is sent."""
    rev = db.get(ModuleReview, module.id)
    if rev is None or not rev.safety:
        raise service.ModulesError("not_needed", "There is nothing to send.")
    service._event(db, track, "call_me_requested", "teacher", now, module)
    db.commit()


def call_me_count(db: Session, cohort_id: str) -> int:
    ids = list(db.execute(select(Track.id).where(Track.class_cohort_id == cohort_id)).scalars())
    if not ids:
        return 0
    return int(
        db.execute(
            select(func.count())
            .select_from(ModuleEvent)
            .where(ModuleEvent.track_id.in_(ids), ModuleEvent.event == "call_me_requested")
        ).scalar_one()
    )


# ---- the card in the chat ------------------------------------------------------------------------


def card_for(db: Session, post_id: str) -> dict[str, Any] | None:
    """What a check-in card in the chat shows: the module, the answer, and whether it is anonymous."""
    row = db.execute(
        select(CheckinShare).where(CheckinShare.thread_post_id == post_id)
    ).scalar_one_or_none()
    if row is None or row.retracted_at is not None:
        return None
    module = db.get(TrackModule, row.module_id)
    fb = db.get(ModuleFeedback, row.module_id)
    if module is None or fb is None:
        return None
    return {"module": module.number, "answer": fb.answer, "anonymous": row.anonymous}
