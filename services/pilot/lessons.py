"""The pilot's lesson chain, one slot at a time.

class counts from the read sheets -> diagnosis (engine) -> approach from the approved move lists ->
script draft -> code validators, pre-filter, call 7 (the existing gates) -> review queue.
Nothing here is published: a card that passes the gates waits for the coach (gate 3).

Drafting is a template drafter: the words come from `content/pilot/lessons.v1.yaml` and the
approved move lists, and every number is filled in by code (counts from the engine, wrong answers
from `engine.bugs`). Call 5 (the AI track drafter) is not built yet; `ScriptDrafter` is the seam
where it plugs in, and its output would go through the same gates.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any, Protocol

import yaml
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ai.client import CallContext
from ai.guard.explain import error_name
from ai.guard.gates import ContentType, GateInput, run_gates
from ai.validators.check_items import check_items
from ai.validators.numbers import extract_numbers
from engine.bugs import add_nocarry, pv_heard, sub_nodec, sub_sfl
from engine.diagnosis import profile_from_counts
from engine.model import ErrorCode
from services.api.db import PilotAudio, PilotClassCount, ReviewItem
from services.pilot.common import audit
from services.practice.content import MoveDef, load_scenario

CONTENT = Path(__file__).resolve().parents[2] / "content" / "pilot" / "lessons.v1.yaml"
STATUSES = ("draft", "needs_review", "approved", "audio_ready", "failed")


@cache
def lesson_content() -> dict[str, Any]:
    data = yaml.safe_load(CONTENT.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


@dataclass(frozen=True)
class Pooled:
    """Counts across every class whose sheets were read. No class, school or teacher is in it."""

    children_checked: int
    classes: int
    counts: dict[str, int]
    anchor_wrong_count: int

    @property
    def hash(self) -> str:
        raw = json.dumps(
            [self.children_checked, self.classes, sorted(self.counts.items())], sort_keys=True
        )
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


class NoTrack(Exception):
    """Why no lesson can be made yet: no_sheets | not_enough | no_error."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def pooled_counts(db: Session) -> Pooled:
    rows = list(db.execute(select(PilotClassCount)).scalars())
    counts: dict[str, int] = {}
    for r in rows:
        for code, n in (r.counts or {}).items():
            counts[code] = counts.get(code, 0) + int(n)
    return Pooled(
        children_checked=sum(r.children_checked for r in rows),
        classes=len(rows),
        counts=counts,
        anchor_wrong_count=sum(r.anchor_wrong_count for r in rows),
    )


def read_sheet_count(db: Session) -> int:
    return int(
        db.execute(
            select(func.coalesce(func.sum(PilotClassCount.children_checked), 0))
        ).scalar_one()
    )


def choose_error(pooled: Pooled) -> tuple[ErrorCode, int]:
    """Diagnosis: the engine picks the error (PV-HEARD first, else the commonest at 1 in 4 or
    more of the children checked, at least 10 checked). Returns it with its count."""
    if pooled.children_checked == 0:
        raise NoTrack("no_sheets")
    counts = {
        ErrorCode(k): v for k, v in pooled.counts.items() if k in ErrorCode._value2member_map_
    }
    profile = profile_from_counts(pooled.children_checked, counts, pooled.anchor_wrong_count)
    if profile.children_checked < 10:
        raise NoTrack("not_enough")
    if profile.track is None:
        raise NoTrack("no_error")
    return profile.track, profile.counts[profile.track]


# ---- drafting ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class SlotPlan:
    slot: int
    total: int
    error: ErrorCode
    n_showing: int
    n_checked: int
    kind: str  # spot | move
    move_id: str | None
    round: int  # which worked example to use (0, 1, 2)


@dataclass(frozen=True)
class Draft:
    title: str
    script: str
    allowed_numbers: frozenset[int]


class ScriptDrafter(Protocol):
    def draft(self, plan: SlotPlan, lang: str) -> Draft: ...


def plan_slots(error: ErrorCode, n_showing: int, n_checked: int, total: int) -> list[SlotPlan]:
    """Lesson 1 shows what to look for; each later lesson teaches one approved move. With one
    lesson only, that lesson also carries the first move."""
    moves = lesson_content()["track_moves"][error.value]
    plans = [SlotPlan(1, total, error, n_showing, n_checked, "spot", None, 0)]
    for slot in range(2, total + 1):
        i = slot - 2
        plans.append(
            SlotPlan(
                slot,
                total,
                error,
                n_showing,
                n_checked,
                "move",
                moves[i % len(moves)],
                i // len(moves),
            )
        )
    return plans


def _wrong_and_correct(error: ErrorCode, operands: list[int]) -> tuple[int, int]:
    if error is ErrorCode.PV_HEARD:
        n = operands[0]
        return min(pv_heard(n)), n
    a, b = operands
    if error is ErrorCode.ADD_NOCARRY:
        return min(add_nocarry(a, b)), a + b
    if error is ErrorCode.SUB_SFL:
        return min(sub_sfl(a, b)), a - b
    return min(sub_nodec(a, b)), a - b


def _move(error: ErrorCode, move_id: str) -> MoveDef:
    for m in load_scenario(error.value).movelist.moves:
        if m.id == move_id:
            return m
    raise KeyError(move_id)


def _first_line(m: MoveDef, lang: str) -> str:
    return (m.sample_lines.get(lang) or m.examples[lang])[0]


class TemplateDrafter:
    def draft(self, plan: SlotPlan, lang: str) -> Draft:
        glue = lesson_content()["glue"][lang]
        examples = lesson_content()["examples"][plan.error.value]
        operands = examples[min(plan.round, len(examples) - 1)]
        wrong, correct = _wrong_and_correct(plan.error, operands)
        slots: dict[str, Any] = {
            "slot": plan.slot,
            "total": plan.total,
            "n_showing": plan.n_showing,
            "n_checked": plan.n_checked,
            "error_name": error_name(plan.error.value, lang),
            "a": operands[0],
            "b": operands[1] if len(operands) > 1 else "",
            "wrong": wrong,
            "correct": correct,
        }
        allowed = {plan.slot, plan.total, plan.n_showing, plan.n_checked, wrong, correct, *operands}
        paragraphs: list[str] = []
        if plan.kind == "spot":
            ask = _first_line(_move(plan.error, lesson_content()["ask_move"]), lang)
            slots["ask_line"] = ask
            title = glue["title_spot"].format(**slots)
            paragraphs += [
                glue["spot_intro"].format(**slots),
                glue["example"][plan.error.value].format(**slots),
                glue["spot_ask"].format(**slots),
                glue["spot_listen"].format(**slots),
            ]
            allowed |= set(extract_numbers(ask))
            if plan.total == 1:  # one lesson only: it also carries the first approved move
                first = lesson_content()["track_moves"][plan.error.value][0]
                paragraphs += self._move_block(plan, first, lang, glue, slots, allowed, intro=False)
        else:
            assert plan.move_id is not None
            move = _move(plan.error, plan.move_id)
            slots["move_label"] = move.label[lang]
            title = glue["title_move"].format(**slots)
            paragraphs += self._move_block(
                plan, plan.move_id, lang, glue, slots, allowed, intro=True
            )
        paragraphs.append(glue["closing"].format(**slots))
        return Draft(
            title=title[:120], script="\n".join(paragraphs), allowed_numbers=frozenset(allowed)
        )

    @staticmethod
    def _move_block(
        plan: SlotPlan,
        move_id: str,
        lang: str,
        glue: dict[str, Any],
        slots: dict[str, Any],
        allowed: set[int],
        *,
        intro: bool,
    ) -> list[str]:
        move = _move(plan.error, move_id)
        example = move.examples[lang][min(plan.round, len(move.examples[lang]) - 1)]
        local = {
            **slots,
            "move_label": move.label[lang],
            "move_description": move.description[lang],
            "move_example": example,
        }
        allowed |= set(extract_numbers(example)) | set(extract_numbers(move.description[lang]))
        parts = [glue["move_intro"].format(**local)] if intro else []
        parts += [
            glue["move_how"].format(**local),
            glue["move_sound"].format(**local),
            glue["move_try"].format(**local),
        ]
        return parts


# ---- the chain --------------------------------------------------------------------------------


def next_version(db: Session, slot: int, lang: str) -> int:
    top = db.execute(
        select(func.max(PilotAudio.version)).where(
            PilotAudio.slot == slot, PilotAudio.language == lang
        )
    ).scalar_one()
    return (top or 0) + 1


def make_card(
    db: Session,
    plan: SlotPlan,
    lang: str,
    voice: str,
    pooled: Pooled,
    actor: str,
    ctx: CallContext,
    drafter: ScriptDrafter | None = None,
) -> PilotAudio:
    """Draft, gate and queue one slot. The row ends as needs_review or failed, never published."""
    draft = (drafter or TemplateDrafter()).draft(plan, lang)
    row = PilotAudio(
        id=uuid.uuid4().hex,
        slot=plan.slot,
        language=lang,
        version=next_version(db, plan.slot, lang),
        title=draft.title,
        script=draft.script,
        track=plan.error.value,
        voice=voice,
        status="draft",
        counts_hash=pooled.hash,
        created_by=actor,
    )
    db.add(row)
    db.commit()

    problems = [v.code for v in check_items(draft.script)]
    if "%" in draft.script:
        problems.append("percent_sign")  # teacher-facing numbers are counts, never percentages
    if problems:
        return _fail(db, row, f"gate1:{problems[0]}", actor)

    result = run_gates(
        GateInput(
            text=draft.script,
            content_type=ContentType.TRACK_DRAFT,
            language=lang,
            target_error=plan.error.value,
            allowed_numbers=draft.allowed_numbers,
        ),
        context=ctx,
    )
    if result.passed_automatic or (result.stage_failed == "gate2" and result.needs_human):
        # Passed, or the checker was down: either way a person looks before anything is voiced.
        item = ReviewItem(
            item_id=uuid.uuid4().hex,
            content_type="track_draft",
            language=lang,
            target_error=plan.error.value,
            content={"slot": plan.slot, "title": draft.title, "script": draft.script},
            badge="checked" if result.passed_automatic else "none",
            status="pending",
        )
        db.add(item)
        row.review_item_id = item.item_id
        row.status = "needs_review"
        row.note = None if result.passed_automatic else "checker_down"
        db.commit()
        audit(db, actor, "audio.drafted", row.id, slot=row.slot, lang=lang, status=row.status)
        return row
    return _fail(db, row, f"{result.stage_failed}:{result.explanation[:40]}", actor)


def _fail(db: Session, row: PilotAudio, note: str, actor: str) -> PilotAudio:
    row.status = "failed"
    row.note = note[:60]
    db.commit()
    audit(db, actor, "audio.failed", row.id, slot=row.slot, lang=row.language, note=row.note)
    return row
