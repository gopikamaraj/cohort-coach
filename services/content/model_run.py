"""The model run: the track's move done well, with the same five simulated children.

About three minutes of audio a teacher can hear before she rehearses. Teacher lines come only from
the approved model-lesson script; children's lines come from the Practice Class engine and call 1
(so every number a child says is the engine's). It is rendered offline with a fixed seed and
frozen as a review item; the coach approves it (gate 3); only then is it voiced (one adult voice
for the teacher, the child voices for the children), encoded as OGG/Opus and listed in the track
manifest, always labelled simulated. No new AI call: call 1 voices the children as in any session.

The teacher's moves are assigned by code from the track's strategy order, not by a model, so the
engine reacts to the move the approved script describes. A new render needs a new approved script
version: the same version is never rendered twice.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.client import CallContext
from ai.guard.explain import error_name
from ai.guard.rejections import RejectionReason
from ai.prompt_loader import load_prompt
from ai.registry import get_call
from services.api.db import ContentAudit, ReviewDecision, ReviewItem
from services.content import publish, rejections, slots, versions
from services.content.track import load_track
from services.pilot.storage import BlobStore
from services.practice.session import ScriptedMove, start_session, take_turn
from services.speech.audio import join_to_file
from services.speech.voices import Voice, voice_for

CONTENT_TYPE = "model_run"
CAPTION = "Simulated: the teacher's words are from an approved lesson; the children are made up."
FORMAT = "ogg"
KBPS = 16
FALLBACK_KBPS = 12
BUDGET_BYTES_PER_3_MIN = 350_000  # CLAUDE.md section 9: ~0.35 MB per 3 minutes
TEACHER_SPEAKER = "ritu"
MIME = "audio/ogg"
_SPLIT = re.compile(r"(Teacher|Child)\s+says\s*:", re.IGNORECASE)


@dataclass(frozen=True)
class Line:
    speaker: str  # teacher | child
    text: str


def parse_script(script: str) -> list[Line]:
    """Split "Teacher says: ... Child says: ..." into lines, in order. The labels are the ones the
    call 5 prompt asks for."""
    parts = _SPLIT.split(script)
    lines: list[Line] = []
    for who, text in zip(parts[1::2], parts[2::2], strict=False):
        cleaned = text.strip()
        if cleaned:
            lines.append(Line(who.lower(), cleaned))
    return lines


def assign_moves(n: int, strategies: tuple[str, ...] | list[str]) -> list[str]:
    """One move per teacher line: pose the problem, then the strategies in the track's order, then
    praise. Decided by code from the track definition."""
    if n <= 0:
        return []
    if n == 1:
        return ["pose_problem"]
    middle = list(itertools.islice(itertools.cycle(strategies), n - 2)) if strategies else []
    middle += ["ask_explain"] * (n - 2 - len(middle))
    return ["pose_problem", *middle, "praise"]


def simulated_values(error: str, language: str, example: tuple[int, int]) -> dict[str, str]:
    """Slot values for a run: the engine's worked example and stand-in class numbers. A model run
    is about a simulated class, so these are never shown as a real class's figures."""
    return {
        **slots.SAMPLE_VALUES,
        **slots.example_values(error, *example),
        "track.error_name": error_name(error, language),
        "track.total_days": "6",
    }


def _source(db: Session, item_id: str) -> ReviewItem:
    row = db.get(ReviewItem, item_id)
    if row is None or row.content_type != "track_draft":
        raise versions.BadState("That script does not exist.")
    if row.content.get("kind") != "model_lesson":
        raise versions.BadState("A model run is built from a model-lesson script.")
    if row.status != "approved":
        raise versions.BadState("Only an approved model-lesson script can be rendered.")
    return row


def _provenance(seed: int, language: str, track_id: str) -> dict[str, Any]:
    return {
        "seed": seed,
        "language": language,
        "track_id": track_id,
        "models": {str(i): get_call(i).model for i in (1, 7)},
        "prompt_versions": {k: load_prompt(k).version for k in ("c01_child_voice", "c07_checker")},
        "rendered_at": datetime.now(UTC).isoformat(),
    }


def _build(source: ReviewItem, *, seed: int, context: CallContext) -> dict[str, Any]:
    track = load_track(str(source.content["track_id"]))
    language = source.language
    values = simulated_values(track.error, language, track.example)
    script = publish.checked_text(str(source.content["script"]), values, "model lesson")
    teacher_lines = [x.text for x in parse_script(script) if x.speaker == "teacher"]
    if not teacher_lines:
        raise versions.BadState("The script has no teacher lines.")
    moves = assign_moves(len(teacher_lines), track.model_strategies)
    session = start_session(track.error, language, seed=seed)
    kids = list(session.personas)
    turns: list[dict[str, Any]] = []
    for i, (line, move) in enumerate(zip(teacher_lines, moves, strict=True)):
        cfg = session.loaded.config
        problem = (
            session.state.problem or cfg.problems[session.state.next_problem % len(cfg.problems)]
        )
        addressed = None if move == "pose_problem" else kids[i % len(kids)]
        r = take_turn(
            session,
            text=line,
            scripted=ScriptedMove(move, addressed, problem if move == "pose_problem" else None),
            context=context,
        )
        persona = session.personas.get(r.speaker or "")
        turns.append(
            {
                "n": r.turn,
                "teacher": {"line": line, "move_id": move},
                "child": {
                    "speaker": r.speaker,
                    "persona_id": persona.id if persona else None,
                    "text": r.child_text,
                    "text_en": r.child_text_en,
                    "written": r.written,
                    "said": r.answer,
                },
                "engine_numbers": sorted(session.plan_numbers),
            }
        )
    return {
        "kind": "model_run",
        "track_id": track.id,
        "error": track.error,
        "language": language,
        "source_item_id": source.item_id,
        "script_sha256": hashlib.sha256(str(source.content["script"]).encode()).hexdigest(),
        "simulated": True,
        "caption": CAPTION,
        "children": [{"name": n, "persona_id": p.id} for n, p in session.personas.items()],
        "turns": turns,
        "provenance": _provenance(seed, language, track.id),
        "audio": None,
    }


def render_dry(
    db: Session, source_item_id: str, *, seed: int, context: CallContext
) -> dict[str, Any]:
    """Build a run without storing it (used to prove a fixed seed gives the same run)."""
    return _build(_source(db, source_item_id), seed=seed, context=context)


def _audit(db: Session, role: str, actor: str, action: str, item: ReviewItem, **d: Any) -> None:
    db.add(
        ContentAudit(
            role=role,
            actor=actor,
            action=action,
            content_type=CONTENT_TYPE,
            content_id=item.item_id,
            version=0,
            detail=d,
        )
    )


def render(
    db: Session,
    source_item_id: str,
    *,
    seed: int,
    context: CallContext,
    actor: str = "system",
    role: str = "system",
) -> ReviewItem:
    """Render a run from an approved script and freeze it as a review item for the coach."""
    source = _source(db, source_item_id)
    for row in db.execute(
        select(ReviewItem).where(ReviewItem.content_type == CONTENT_TYPE)
    ).scalars():
        if row.content.get("source_item_id") == source_item_id and row.status != "rejected":
            raise versions.BadState(
                "This script version already has a model run. A new render needs a new approved "
                "script version."
            )
    content = _build(source, seed=seed, context=context)
    item = ReviewItem(
        item_id=uuid.uuid4().hex,
        content_type=CONTENT_TYPE,
        language=source.language,
        target_error=content["error"],
        content=content,
        badge="checked",
        status="pending",
    )
    db.add(item)
    _audit(db, role, actor, "render", item, seed=seed, source=source_item_id)
    db.commit()
    return item


def _run(db: Session, item_id: str) -> ReviewItem:
    row = db.get(ReviewItem, item_id)
    if row is None or row.content_type != CONTENT_TYPE:
        raise versions.BadState("That model run does not exist.")
    return row


def approve(db: Session, item_id: str, actor: str, role: str) -> ReviewItem:
    if role != "coach":
        raise versions.NotAllowed("Only the coach can approve a model run.")
    row = _run(db, item_id)
    if row.status != "pending":
        raise versions.BadState(f"A {row.status} model run cannot be approved.")
    row.status = "approved"
    row.badge = "checked_reviewed"
    db.add(ReviewDecision(item_id=item_id, decision="approve", reviewer_role="reviewer"))
    _audit(db, role, actor, "approve", row)
    db.commit()
    return row


def reject(
    db: Session,
    item_id: str,
    actor: str,
    role: str,
    *,
    reason: str,
    note: str = "",
    pending_dir: Path | None = None,
) -> ReviewItem:
    if role != "coach":
        raise versions.NotAllowed("Only the coach can return a model run.")
    code = RejectionReason(reason)
    row = _run(db, item_id)
    if row.status != "pending":
        raise versions.BadState(f"A {row.status} model run cannot be returned.")
    row.status = "rejected"
    db.add(
        ReviewDecision(
            item_id=item_id, decision="reject", reason=code.value, reviewer_role="reviewer"
        )
    )
    _audit(db, role, actor, "reject", row, reason=code.value)
    db.commit()
    children = " ".join(t["child"]["text"] for t in row.content["turns"] if t["child"]["text"])
    rejections.write_pending(
        children, code, row.language, item_id=item_id, note=note, directory=pending_dir
    )
    return row


def encode(clips: list[bytes]) -> tuple[bytes, float]:
    """OGG/Opus mono at 16 kbps; 12 kbps if the file would pass 0.35 MB per three minutes."""
    data, seconds = join_to_file(clips, fmt=FORMAT, kbps=KBPS)
    if seconds > 0 and len(data) / seconds * 180 > BUDGET_BYTES_PER_3_MIN:
        data, seconds = join_to_file(clips, fmt=FORMAT, kbps=FALLBACK_KBPS)
    return data, seconds


def voice(db: Session, item_id: str, *, store: BlobStore, speech: Any) -> dict[str, Any]:
    """Voice an approved run once and publish the file. A run that is not approved is refused."""
    row = _run(db, item_id)
    if row.status != "approved":
        raise versions.BadState("Only an approved model run can be voiced.")
    if row.content.get("audio"):
        return dict(row.content)
    language = row.language
    plan: list[tuple[str, Voice]] = []
    for t in row.content["turns"]:
        plan.append((t["teacher"]["line"], Voice(TEACHER_SPEAKER, 1.0, 1.0)))
        if t["child"]["text"]:
            plan.append((t["child"]["text"], voice_for(t["child"]["persona_id"] or "")))
    digest = hashlib.sha256(
        json.dumps([(text, v.speaker, v.pitch) for text, v in plan], ensure_ascii=False).encode()
    ).hexdigest()
    key = f"model-runs/{row.content['track_id']}/{language}/{digest[:16]}.{FORMAT}"
    data, seconds = encode([speech.synthesize(text, language, v) for text, v in plan])
    store.put(key, data, MIME)
    row.content = {
        **row.content,
        "audio": {
            "key": key,
            "bytes": len(data),
            "seconds": round(seconds, 1),
            "sha256": digest,
            "mime": MIME,
        },
    }
    _audit(db, "system", "publisher", "voice", row, bytes=len(data))
    db.commit()
    return dict(row.content)
