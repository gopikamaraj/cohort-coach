# ruff: noqa: E501
"""The one place a billable event is written to the ledger, and the wrapper that meters a speech provider.

`record()` does nothing when no action is in progress (traffic that is not an action is not counted),
refuses anything that is not a whitelisted number or flag (so no text, audio or name can reach the
ledger), and never lets a ledger failure break the call that was being metered.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from services.usage import context, pricing, store
from services.usage.models import UsageEntry

log = logging.getLogger(__name__)

ALLOWED_UNITS: dict[str, set[str]] = {
    "llm": {"input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens"},
    "tts": {"characters", "seconds"},
    "stt": {"seconds"},
    "cloud_run": {"request_ms"},
}
ALLOWED_META = {"cold", "cached", "estimated"}


def _check(kind: str, units: dict[str, float], meta: dict[str, bool]) -> None:
    if kind not in ALLOWED_UNITS:
        raise ValueError(f"unknown kind {kind!r}")
    bad = set(units) - ALLOWED_UNITS[kind]
    if bad:
        raise ValueError(f"not a unit of {kind}: {sorted(bad)}")
    if not all(isinstance(v, int | float) and not isinstance(v, bool) for v in units.values()):
        raise ValueError("units are numbers only")
    if set(meta) - ALLOWED_META or not all(isinstance(v, bool) for v in meta.values()):
        raise ValueError("meta is the known flags only")


def record(
    kind: str,
    provider: str,
    *,
    model_or_voice: str = "",
    units: dict[str, float] | None = None,
    cost_usd: float | None = None,
    started_at: datetime | None = None,
    duration_ms: int = 0,
    status: str = "ok",
    request_id: str = "",
    meta: dict[str, bool] | None = None,
) -> None:
    units, meta = units or {}, meta or {}
    _check(kind, units, meta)
    action = context.current()
    if not action:
        return
    try:
        with store.factory()() as db:
            db.add(
                UsageEntry(
                    action_id=action,
                    kind=kind,
                    provider=provider[:30],
                    model_or_voice=model_or_voice[:60],
                    units=units,
                    cost_usd=cost_usd,
                    started_at=started_at or datetime.now(UTC),
                    duration_ms=int(duration_ms),
                    status=status if status in ("ok", "failed", "retried") else "ok",
                    request_id=(request_id or uuid.uuid4().hex[:12])[:40],
                    meta=meta,
                )
            )
            db.commit()
    except Exception:  # noqa: BLE001 - a ledger failure must never break the action
        log.warning("usage: could not write a ledger entry", exc_info=True)


def record_llm(fields: dict[str, Any]) -> None:
    """From the audit row of one Claude call (ai/audit.py): tokens, model, latency, retries."""
    if not context.current():
        return
    tin, tout = int(fields.get("tokens_in", 0)), int(fields.get("tokens_out", 0))
    cr, cw = int(fields.get("tokens_cache_read", 0)), int(fields.get("tokens_cache_write", 0))
    model = str(fields.get("model", ""))
    record(
        "llm",
        "anthropic",
        model_or_voice=model,
        units={
            "input_tokens": tin,
            "output_tokens": tout,
            "cache_read_tokens": cr,
            "cache_write_tokens": cw,
        },
        cost_usd=pricing.llm_cost(
            model, input_tokens=tin, output_tokens=tout, cache_read=cr, cache_write=cw
        ),
        started_at=datetime.now(UTC),
        duration_ms=int(fields.get("latency_ms", 0)),
        status="retried" if int(fields.get("retries", 0)) > 0 else "ok",
        request_id=str(fields.get("call_key", ""))[:40],
    )


class MeteredProvider:
    """Wraps a speech provider (Bodhan, Sarvam): every transcribe and synthesize call is written to
    the ledger, failures included. Everything else is the provider itself."""

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.name = inner.name

    def __getattr__(self, item: str) -> Any:
        return getattr(self._inner, item)

    def configured_for(self, function: str) -> Any:
        return self._inner.configured_for(function)

    @property
    def capabilities(self) -> Any:
        return self._inner.capabilities

    def synthesize(self, text: str, language: str, voice: str, style: str | None) -> Any:
        t0, started = time.perf_counter(), datetime.now(UTC)
        try:
            got = self._inner.synthesize(text, language, voice, style)
        except Exception:
            record(
                "tts",
                self.name,
                model_or_voice=voice,
                units={"characters": 0},
                started_at=started,
                duration_ms=int((time.perf_counter() - t0) * 1000),
                status="failed",
            )
            raise
        chars = int(got.chars_billed)
        record(
            "tts",
            self.name,
            model_or_voice=voice,
            units={"characters": chars},
            cost_usd=pricing.speech_cost(self.name, "tts", characters=chars),
            started_at=started,
            duration_ms=int((time.perf_counter() - t0) * 1000),
            request_id=str(got.request_id or ""),
        )
        return got

    def transcribe(self, wav: bytes, language: str) -> Any:
        t0, started = time.perf_counter(), datetime.now(UTC)
        try:
            got = self._inner.transcribe(wav, language)
        except Exception:
            record(
                "stt",
                self.name,
                units={"seconds": 0},
                started_at=started,
                duration_ms=int((time.perf_counter() - t0) * 1000),
                status="failed",
            )
            raise
        sec = float(got.seconds_billed)
        record(
            "stt",
            self.name,
            units={"seconds": round(sec, 2)},
            cost_usd=pricing.speech_cost(self.name, "stt", seconds=sec),
            started_at=started,
            duration_ms=int((time.perf_counter() - t0) * 1000),
            request_id=str(got.request_id or ""),
        )
        return got
