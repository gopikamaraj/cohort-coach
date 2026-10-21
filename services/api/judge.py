"""Read-only judge endpoints: the AI map and the audit trail (metadata only)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from ai.audit import SqlAuditSink, default_sink
from ai.prompt_loader import load_prompt
from ai.registry import CALLS, LAYERS
from services.api.roles import require

router = APIRouter(
    prefix="/api/judge",
    tags=["judge"],
    dependencies=[Depends(require("judge.inspect"))],
)


def get_sink() -> SqlAuditSink:
    return default_sink()


SINK = Depends(get_sink)


@router.get("/ai-map")
def ai_map() -> dict[str, Any]:
    """Every call, what it does, and its five layers (input to output)."""
    return {
        "layers": list(LAYERS),
        "calls": [
            {
                "id": c.id,
                "key": c.key,
                "name": c.name,
                "purpose": c.purpose,
                "model": c.model,
                "prompt": c.prompt_path,
                "prompt_version": load_prompt(c.key).version,
                "when": c.when,
                "validators": list(c.validators),
                "gates": list(c.gates),
                "eval": {"id": c.eval_id, "bar": c.eval_bar},
                "metadata_only": c.metadata_only,
                "layers": c.layers,
            }
            for c in CALLS
        ],
    }


@router.get("/audit")
def audit(limit: int = Query(50, ge=1, le=200), sink: SqlAuditSink = SINK) -> dict[str, Any]:
    """The latest AI calls. Metadata only: never prompt text, teacher text or model output."""
    rows = sink.recent(limit)
    return {
        "count": len(rows),
        "calls": [
            {
                "id": r.id,
                "at": r.created_at.isoformat() if r.created_at else None,
                "call_id": r.call_id,
                "call": r.call_key,
                "prompt_version": r.prompt_version,
                "model": r.model,
                "mode": r.mode,
                "judge": r.judge,
                "tokens": {
                    "in": r.tokens_in,
                    "out": r.tokens_out,
                    "cache_read": r.tokens_cache_read,
                    "cache_write": r.tokens_cache_write,
                },
                "cost_usd": r.cost_usd,
                "latency_ms": r.latency_ms,
                "validators": r.validator_results,
                "checker": {"verdict": r.checker_verdict, "reason": r.checker_reason},
                "retries": r.retries,
                "fallback_used": r.fallback_used,
                "reviewer": {
                    "decision": r.reviewer_decision,
                    "reason": r.reviewer_reason,
                    "at": r.reviewed_at.isoformat() if r.reviewed_at else None,
                },
            }
            for r in rows
        ],
    }
