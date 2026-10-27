"""T4 My track and lessons, and T6 My result.

T4 shows the lessons of her track, one at a time, from the manifest a published track version made
(only content both keys switched on). Each lesson is one `media` step: the voice note where the
channel plays one, the script as text everywhere, and the badge line. After each lesson two taps:
"Tried it in class?" then "How did it go?". Taps are self-report and are stored per lesson per
pseudonymous teacher id. A judge sees lesson 1 at once and a "Next lesson" button; a real teacher
gets two lessons a week (`lessons_view.LESSON_OFFSETS_DAYS`).

Not built (cut in P10, see DECISIONS): the call 9 reflection pointer, voice reflections and the
biweekly "Still using it?" prompts.

T6 shows her class's change on the error that was tracked, in counts, with no comparison with other
teachers and no percentage.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from engine.diagnosis import profile_from_counts
from engine.model import ErrorCode
from services.api.db import LessonTap, ProfileSync
from services.api.flows import facts
from services.api.flows.links import sign
from services.api.flows.steps import Answer, Flow, LinkSpec, Node, Option, Step
from services.api.flows.t1 import base_url
from services.content import lessons_view

TRACKS = ("PV-HEARD", "ADD-NOCARRY", "SUB-SFL", "SUB-NODEC")


def track_error(ctx: Any) -> str | None:
    """The error her track is for: from her own class's counts, or SUB-SFL for a judge."""
    s = ctx.summary
    if s and s.track in TRACKS:
        return str(s.track)
    return "SUB-SFL" if ctx.teacher.judge else None


def manifest_for(ctx: Any) -> Any:
    err = track_error(ctx)
    return lessons_view.latest_manifest(ctx.db, err) if err else None


def has_track(ctx: Any) -> bool:
    return manifest_for(ctx) is not None


def _lessons(ctx: Any) -> list[dict[str, Any]]:
    m = manifest_for(ctx)
    return lessons_view.lessons(m, ctx.teacher.lang) if m is not None else []


def _simulated(ctx: Any) -> bool:
    m = manifest_for(ctx)
    return bool(m and m.body.get("simulated"))


def audio_url(manifest_id: int, part: dict[str, Any]) -> str | None:
    if not part.get("audio_key"):
        return None
    token = sign({"m": manifest_id, "p": part["id"]}, ttl_s=3 * 24 * 3600)
    api = (os.environ.get("PUBLIC_BASE_URL") or base_url()).rstrip("/")
    return f"{api}/api/lessons/audio?t={token}"


def _day(ctx: Any) -> int:
    return int(ctx.data.get("day", 1))


# ---- steps -----------------------------------------------------------------------------------


def _intro_build(ctx: Any) -> Step:
    err = track_error(ctx)
    lessons = _lessons(ctx)
    if not err or not lessons:
        return Step(kind="message", id="intro", copy="t4.none")
    return Step(
        kind="message",
        id="intro",
        copy="t4.intro",
        params={"n": len(lessons), "desc_key": f"err.desc.{err}"},
        simulated=_simulated(ctx),
    )


def _intro_advance(ctx: Any, a: Answer) -> str | None:
    if not _lessons(ctx):
        return "t1:menu"
    ctx.data.setdefault("t4_start", datetime.now(UTC).isoformat())
    ctx.data["day"] = int(ctx.data.get("day", 1))
    return "lesson"


def _due(ctx: Any, day: int) -> bool:
    if ctx.teacher.judge:  # a judge sees every lesson at once
        return True
    started = datetime.fromisoformat(ctx.data.get("t4_start") or datetime.now(UTC).isoformat())
    return lessons_view.due_day(day, started, datetime.now(UTC))


def _lesson_build(ctx: Any) -> Step:
    lessons = _lessons(ctx)
    day = min(_day(ctx), len(lessons))
    part = lessons[day - 1]
    m = manifest_for(ctx)
    return Step(
        kind="media",
        id="lesson",
        copy="t4.lesson",
        params={"day": day, "total": len(lessons), "script": str(part["script"])},
        audio=audio_url(m.id, part) if m is not None else None,
        badge="lesson.badge" if part.get("badge") == "checked_reviewed" else None,
        simulated=_simulated(ctx),
    )


def _lesson_advance(ctx: Any, a: Answer) -> str | None:
    if not _due(ctx, _day(ctx)):
        return "later"
    return "tried"


def _later_build(ctx: Any) -> Step:
    started = datetime.fromisoformat(ctx.data.get("t4_start") or datetime.now(UTC).isoformat())
    days = lessons_view.days_until(_day(ctx), started, datetime.now(UTC))
    return Step(
        kind="message",
        id="later",
        copy="t4.later",
        params={"day": _day(ctx), "days": days},
    )


def _tried_build(ctx: Any) -> Step:
    return Step(
        kind="choice",
        id="tried",
        copy="t4.tried",
        options=[Option(id="yes", copy="t4.o.yes"), Option(id="notyet", copy="t4.o.notyet")],
    )


def _tap(ctx: Any, **fields: Any) -> None:
    err = track_error(ctx) or ""
    track_id = f"{err}"
    row = ctx.db.execute(
        select(LessonTap).where(
            LessonTap.teacher_id == ctx.teacher.teacher_id,
            LessonTap.track_id == track_id,
            LessonTap.lesson_day == _day(ctx),
        )
    ).scalar_one_or_none()
    if row is None:
        row = LessonTap(teacher_id=ctx.teacher.teacher_id, track_id=track_id, lesson_day=_day(ctx))
        ctx.db.add(row)
    for k, v in fields.items():
        setattr(row, k, v)
    row.updated_at = datetime.now(UTC)
    ctx.db.commit()


def _tried_advance(ctx: Any, a: Answer) -> str | None:
    _tap(ctx, tried=a.value == "yes")
    return "how" if a.value == "yes" else "next"


def _how_build(ctx: Any) -> Step:
    return Step(
        kind="choice",
        id="how",
        copy="t4.how",
        options=[
            Option(id="worked", copy="t4.o.worked"),
            Option(id="partly", copy="t4.o.partly"),
            Option(id="didnt", copy="t4.o.didnt"),
        ],
    )


def _how_advance(ctx: Any, a: Answer) -> str | None:
    _tap(ctx, outcome=a.value)
    return "thanks"


def _next_build(ctx: Any) -> Step:
    lessons = _lessons(ctx)
    options = []
    if _day(ctx) < len(lessons):
        options.append(Option(id="next", copy="t4.o.next"))
    m = manifest_for(ctx)
    if m is not None and lessons_view.model_lesson(m, ctx.teacher.lang):
        options.append(Option(id="model", copy="t4.o.model"))
    options += [Option(id="rehearse", copy="t4.o.rehearse"), Option(id="back", copy="t4.o.back")]
    last = _day(ctx) >= len(lessons)
    return Step(kind="choice", id="next", copy="t4.done" if last else "t4.next", options=options)


def _next_advance(ctx: Any, a: Answer) -> str | None:
    if a.value == "next":
        ctx.data["day"] = _day(ctx) + 1
        return "lesson"
    return {"model": "model", "rehearse": "rehearse", "back": "t1:menu"}[a.value]


def _model_build(ctx: Any) -> Step:
    m = manifest_for(ctx)
    part = lessons_view.model_lesson(m, ctx.teacher.lang) if m is not None else None
    return Step(
        kind="message",
        id="model",
        copy="t4.model",
        params={"script": str(part["script"]) if part else ""},
        badge="lesson.badge" if part and part.get("badge") == "checked_reviewed" else None,
        simulated=_simulated(ctx),
    )


def _rehearse_build(ctx: Any) -> Step:
    token = sign({"lang": ctx.teacher.lang, "scenario": track_error(ctx) or "SUB-SFL"})
    return Step(
        kind="link",
        id="rehearse",
        copy="t4.rehearse",
        link=LinkSpec(
            kind="practice", label_copy="t1.practice_open", url=f"{base_url()}/#/practice?t={token}"
        ),
        options=[Option(id="back", copy="t4.o.back")],
    )


T4 = Flow(
    id="t4",
    version=1,
    start="intro",
    nodes={
        "intro": Node(
            _intro_build,
            _intro_advance,
            ("t4.none", "t4.intro", "err.desc.PV-HEARD", *[f"err.desc.{c}" for c in TRACKS]),
            auto=True,
        ),
        "lesson": Node(_lesson_build, _lesson_advance, ("t4.lesson", "lesson.badge"), auto=True),
        "later": Node(_later_build, lambda ctx, a: "next", ("t4.later",), auto=True),
        "tried": Node(_tried_build, _tried_advance, ("t4.tried", "t4.o.yes", "t4.o.notyet")),
        "how": Node(
            _how_build,
            _how_advance,
            ("t4.how", "t4.o.worked", "t4.o.partly", "t4.o.didnt"),
        ),
        "thanks": Node(
            lambda ctx: Step(kind="message", id="thanks", copy="t4.thanks"),
            lambda ctx, a: "next",
            ("t4.thanks",),
            auto=True,
        ),
        "next": Node(
            _next_build,
            _next_advance,
            ("t4.next", "t4.done", "t4.o.next", "t4.o.model", "t4.o.rehearse", "t4.o.back"),
        ),
        "model": Node(_model_build, lambda ctx, a: "next", ("t4.model", "lesson.badge"), auto=True),
        "rehearse": Node(
            _rehearse_build,
            lambda ctx, a: "next",
            ("t4.rehearse", "t1.practice_open", "t4.o.back"),
        ),
    },
)


# ---- T6: her result --------------------------------------------------------------------------


def result_counts(ctx: Any) -> tuple[str, int, int, int, int] | None:
    """(error, before, total_before, after, total_after) for her class on the tracked error,
    from her first and latest check of her own class (the tracked error is the one her first
    check chose); a judge's come from the simulated block. None if there are not two checks yet."""
    if ctx.teacher.judge:
        err = track_error(ctx)
        return facts.demo_change(err) if err else None
    if not ctx.teacher.class_id:
        return None
    rows = list(
        ctx.db.execute(
            select(ProfileSync)
            .where(ProfileSync.class_id == ctx.teacher.class_id)
            .order_by(ProfileSync.term)
        ).scalars()
    )
    if len(rows) < 2:
        return None
    first, last = rows[0], rows[-1]
    known = {ErrorCode(k): v for k, v in first.counts.items() if k in ErrorCode._value2member_map_}
    track = profile_from_counts(first.children_checked, known).track
    if track is None:
        return None
    err = track.value
    return (
        err,
        int(first.counts.get(err, 0)),
        first.children_checked,
        int(last.counts.get(err, 0)),
        last.children_checked,
    )


def has_result(ctx: Any) -> bool:
    return result_counts(ctx) is not None


def _result_build(ctx: Any) -> Step:
    got = result_counts(ctx)
    if got is None:
        return Step(kind="message", id="result", copy="t6.none")
    err, before, total_before, after, total_after = got
    return Step(
        kind="message",
        id="result",
        copy="t6.result",
        params={
            "before": before,
            "total_before": total_before,
            "after": after,
            "total_after": total_after,
            "desc_key": f"err.desc.{err}",
        },
        lines=[],
        simulated=bool(ctx.teacher.judge),
    )


T6 = Flow(
    id="t6",
    version=1,
    start="result",
    nodes={
        "result": Node(
            _result_build,
            lambda ctx, a: "fail_note" if has_result(ctx) else "t1:menu",
            ("t6.none", "t6.result", *[f"err.desc.{c}" for c in TRACKS]),
            auto=True,
        ),
        "fail_note": Node(
            lambda ctx: Step(kind="message", id="fail_note", copy="t6.fail"),
            lambda ctx, a: "t1:menu",
            ("t6.fail",),
            auto=True,
        ),
    },
)
