# ruff: noqa: E501
"""Reads `X-Action-Id` (and `X-Action-Name`) on a request, keeps the id in the request's context for the
metering hooks, counts the request as in flight until it and its background tasks are done, and writes the
Cloud Run entry (the request's wall time) when it ends. A pure ASGI middleware, so background tasks run
inside the call and the action stays open until they finish."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

import anyio

from services.usage import context, meter, pricing, store

log = logging.getLogger(__name__)
_served = False  # this instance has served a request already; the first one pays the cold start


def _header(scope: dict[str, Any], name: bytes) -> str:
    for k, v in scope.get("headers", []):
        if k == name:
            return str(v.decode("latin-1"))
    return ""


def _open(action_id: str, name: str) -> None:
    try:
        with store.factory()() as db:
            store.maybe_purge(db)
            store.open_action(db, action_id, name)
    except Exception:  # noqa: BLE001
        log.warning("usage: could not open an action", exc_info=True)


def _close(action_id: str) -> None:
    try:
        with store.factory()() as db:
            store.close_action(db, action_id)
    except Exception:  # noqa: BLE001
        log.warning("usage: could not close an action", exc_info=True)


class ActionMeterMiddleware:
    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        global _served
        action_id = _header(scope, b"x-action-id") if scope["type"] == "http" else ""
        path = scope.get("path", "")
        if (
            not context.ACTION_ID.match(action_id)
            or scope.get("method") == "OPTIONS"
            or path.startswith("/api/actions/")
        ):
            await self.app(scope, receive, send)
            return
        name = _header(scope, b"x-action-name")
        name = name if context.ACTION_NAME.match(name) else ""
        cold = not _served
        _served = True
        started, t0 = datetime.now(UTC), time.perf_counter()
        status = {"code": 200}

        async def watch(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                status["code"] = int(message["status"])
            await send(message)

        tokens = context.enter(action_id, name)
        await anyio.to_thread.run_sync(_open, action_id, name)
        try:
            await self.app(scope, receive, watch)
        except BaseException:
            status["code"] = 500
            raise
        finally:
            ms = int((time.perf_counter() - t0) * 1000)
            with anyio.CancelScope(shield=True):
                await anyio.to_thread.run_sync(
                    lambda: meter.record(
                        "cloud_run",
                        "cloud_run",
                        units={"request_ms": ms},
                        cost_usd=pricing.cloud_run_cost(ms),
                        started_at=started,
                        duration_ms=ms,
                        status="failed" if status["code"] >= 500 else "ok",
                        meta={"cold": cold, "estimated": True},
                    ),
                    abandon_on_cancel=False,
                )
                await anyio.to_thread.run_sync(_close, action_id)
            context.leave(tokens)
