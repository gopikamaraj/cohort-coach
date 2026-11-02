# ruff: noqa: E501
"""GET /api/actions/{action_id}/usage: what one action cost, summed over every call it caused.

The action id is a random uuid the app made at the click, so it works as its own key; the reply holds
only kinds, models, units, durations and costs. `complete` is false while any request or background step
of the action is still running, so the app keeps asking until it is true.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from services.usage import context, pricing, store
from services.usage.models import UsageAction, UsageEntry

router = APIRouter(prefix="/api/actions", tags=["usage"])

UNIT_KEYS: dict[str, tuple[str, ...]] = {
    "llm": ("input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens"),
    "tts": ("characters", "seconds"),
    "stt": ("seconds",),
    "cloud_run": ("request_ms",),
}


def summarise(action: UsageAction | None, entries: list[UsageEntry]) -> dict[str, Any]:
    """Pure: the totals the footer shows. A cost is the sum of the priced entries; `priced` is false
    when any entry of the kind had no price (the footer then says n/a, never 0)."""
    by_kind: dict[str, dict[str, Any]] = {}
    for kind, keys in UNIT_KEYS.items():
        rows = [e for e in entries if e.kind == kind]
        block: dict[str, Any] = {
            "calls": len(rows),
            "failed": sum(1 for e in rows if e.status == "failed"),
            "retried": sum(1 for e in rows if e.status == "retried"),
            "cost_usd": sum(e.cost_usd for e in rows if e.cost_usd is not None),
            "priced": all(e.cost_usd is not None for e in rows),
        }
        for k in keys:
            block[k] = sum(float(e.units.get(k, 0)) for e in rows)
        if kind == "cloud_run":
            block["estimated"] = True
            block["cold"] = any(bool(e.meta.get("cold")) for e in rows)
        by_kind[kind] = block
    calls = [e for e in entries if e.kind != "cloud_run"]
    start = min((e.started_at.timestamp() for e in calls), default=0.0)
    end = max((e.started_at.timestamp() + e.duration_ms / 1000 for e in calls), default=0.0)
    return {
        "action_id": action.id if action else "",
        "name": action.name if action else "",
        "complete": action is not None and action.inflight <= 0,
        "totals": {
            "cost_usd": sum(b["cost_usd"] for b in by_kind.values()),
            "priced": all(b["priced"] for b in by_kind.values()),
            "entries": len(entries),
        },
        "by_kind": by_kind,
        # the summed time of the calls, and the time they took together (less when they ran in parallel)
        "time": {
            "calls_sum_ms": sum(e.duration_ms for e in calls),
            "calls_wall_ms": int((end - start) * 1000) if calls else 0,
            "request_ms": int(by_kind["cloud_run"]["request_ms"]),
        },
        "entries": [
            {
                "kind": e.kind,
                "provider": e.provider,
                "model_or_voice": e.model_or_voice,
                "units": e.units,
                "cost_usd": e.cost_usd,
                "started_at": e.started_at.isoformat(),
                "duration_ms": e.duration_ms,
                "status": e.status,
                "request_id": e.request_id,
                "meta": e.meta,
            }
            for e in entries
        ],
        "display": pricing.display(),
    }


@router.get("/{action_id}/usage")
def usage(action_id: str) -> dict[str, Any]:
    if not context.ACTION_ID.match(action_id):
        raise HTTPException(422, "Bad action id.")
    with store.factory()() as db:
        action = db.get(UsageAction, action_id)
        rows = list(
            db.execute(
                select(UsageEntry)
                .where(UsageEntry.action_id == action_id)
                .order_by(UsageEntry.started_at, UsageEntry.id)
            ).scalars()
        )
    if action is None and not rows:
        raise HTTPException(404, "No such action.")
    return summarise(action, rows)
