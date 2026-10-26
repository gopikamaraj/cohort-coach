"""Drafting a track: the Message Batches requests, the cost estimate, and storing drafts.

A track is drafted one part at a time: six lessons and the model lesson, in each language. This
module builds the requests (for the batch API, at half price), estimates the cost before anything
runs, gates a result however it arrived, and stores what passes as a review item for the coach.
It never approves or publishes anything.
"""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai import config
from ai.calls.c05_track_draft import KINDS, PartDraft, build_payload, gate_part, review_content
from ai.client import CallContext, render_user_content
from ai.pricing import Usage, cost_usd
from ai.prompt_loader import load_prompt
from ai.schemas import TrackPart
from services.api.db import ReviewItem
from services.content.track import Track

CALL_KEY = "c05_track_draft"
CHARS_PER_TOKEN = 3.5  # a rough rule for the input estimate; the live run prints the real count
# Output assumptions, per spoken lesson (tokens). Hindi and Tamil need more tokens per word.
OUTPUT_TOKENS = {"en": 1000, "hi": 2200, "ta": 3000}
MODEL_LESSON_FACTOR = 1.3
_ID = re.compile(r"^(?P<track>.+)_(?P<kind>lesson|model_lesson)_(?P<day>\d+)_(?P<lang>en|hi|ta)$")


@dataclass(frozen=True)
class BatchRequest:
    custom_id: str
    kind: str
    day: int
    language: str
    params: dict[str, Any]


@dataclass(frozen=True)
class Estimate:
    requests: int
    input_tokens: int
    output_tokens: int
    usd: float
    batch: bool

    def summary(self) -> str:
        how = "Message Batches rate (half price)" if self.batch else "standard rate"
        return (
            f"Estimated cost: {self.requests} requests, about {self.input_tokens:,} input and "
            f"{self.output_tokens:,} output tokens, USD {self.usd:.2f} at the {how}. "
            "An estimate from the price file and stated assumptions, not a measurement."
        )


def custom_id(track: Track, kind: str, day: int, language: str) -> str:
    """Letters, digits, "_" and "-" only (the Batches API limit), up to 64 characters."""
    return f"{track.id.replace('.', '-')}_{kind}_{day}_{language}"


def parts(track: Track) -> list[tuple[str, int]]:
    return [("lesson", lesson.day) for lesson in track.lessons] + [("model_lesson", 0)]


def build_requests(
    track: Track, languages: Sequence[str], *, method_cards: Sequence[str] = ()
) -> list[BatchRequest]:
    prompt = load_prompt(CALL_KEY)
    policy = config.POLICIES[CALL_KEY]
    model = config.model_for(prompt.model_env)
    schema = TrackPart.model_json_schema()
    out: list[BatchRequest] = []
    for language in languages:
        for kind, day in parts(track):
            payload = build_payload(track, kind, day, language, method_cards=method_cards)
            params: dict[str, Any] = {
                "model": model,
                "max_tokens": policy.max_tokens,
                "system": [
                    {"type": "text", "text": prompt.body, "cache_control": {"type": "ephemeral"}}
                ],
                "messages": [{"role": "user", "content": render_user_content(payload)}],
                "output_config": {
                    "effort": policy.effort,
                    "format": {"type": "json_schema", "schema": schema},
                },
            }
            think = config.thinking_param(model, policy)
            if think:
                params["thinking"] = think
            out.append(
                BatchRequest(custom_id(track, kind, day, language), kind, day, language, params)
            )
    return out


def estimate(requests: Sequence[BatchRequest], *, batch: bool) -> Estimate:
    input_tokens = output_tokens = 0
    for r in requests:
        input_tokens += int(len(json.dumps(r.params, ensure_ascii=False)) / CHARS_PER_TOKEN)
        base = OUTPUT_TOKENS[r.language]
        output_tokens += int(base * (MODEL_LESSON_FACTOR if r.kind == "model_lesson" else 1))
    model = str(requests[0].params["model"]) if requests else config.model_for("MODEL_DRAFT")
    usd = cost_usd(model, Usage(input_tokens, output_tokens), batch=batch)
    return Estimate(len(requests), input_tokens, output_tokens, usd, batch)


def store_draft(db: Session, draft: PartDraft, track: Track) -> ReviewItem | None:
    """Queue a draft for the coach. Blocked-by-code drafts never reach the queue, and a part that is
    already waiting is not queued twice."""
    if draft.part is None or draft.status not in ("needs_review", "held_by_checker"):
        return None
    pending = db.execute(
        select(ReviewItem).where(
            ReviewItem.content_type == "track_draft", ReviewItem.status == "pending"
        )
    ).scalars()
    for row in pending:
        c = row.content
        if (
            c.get("track_id") == track.id
            and c.get("kind") == draft.kind
            and c.get("day") == draft.day
            and c.get("language") == draft.language
        ):
            return None
    content = review_content(draft, track)
    item = ReviewItem(
        item_id=uuid.uuid4().hex,
        content_type="track_draft",
        ai_call_id=content.get("audit_id"),
        language=draft.language,
        target_error=track.error,
        content=content,
        badge=content["badge"],
        status="pending",
    )
    db.add(item)
    db.commit()
    return item


def ingest_results(
    db: Session,
    track: Track,
    results: Sequence[dict[str, str]],
    *,
    context: CallContext | None = None,
) -> dict[str, str]:
    """Gate and store the results of a Message Batch: [{"custom_id", "text"}]. Each part is parsed
    into the schema, then goes through the same gates as a synchronous draft."""
    outcomes: dict[str, str] = {}
    for result in results:
        cid = result["custom_id"]
        m = _ID.match(cid)
        if m is None or m.group("kind") not in KINDS:
            outcomes[cid] = "no_output"
            continue
        kind, day, language = m.group("kind"), int(m.group("day")), m.group("lang")
        try:
            part = TrackPart.model_validate_json(result["text"])
        except ValidationError:
            outcomes[cid] = "no_output"
            continue
        draft = gate_part(track, kind, day, language, part, context=context)
        store_draft(db, draft, track)
        outcomes[cid] = draft.status
    return outcomes
