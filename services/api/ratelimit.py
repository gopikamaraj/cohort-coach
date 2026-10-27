"""A per-client sliding-window limit for the endpoints that cost money (Practice Class, speech,
sheet reading). In memory, per process: it stops a loop or a crowd from draining the budget during
judging; the budget hard-stop in `ai/client.py` is still the backstop.

The limit is requests per minute, from `RATE_LIMIT_<NAME>_PER_MIN` (0 switches it off).
"""

from __future__ import annotations

import math
import os
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

WINDOW_SECONDS = 60.0


def client_ip(request: Request) -> str:
    """The first forwarded address (Cloud Run and most proxies set it), else the socket's."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded.strip():
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client and request.client.host else "unknown"


class RateLimiter:
    def __init__(self, name: str, default_per_minute: int) -> None:
        self.name = name
        self.default = default_per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def limit(self) -> int:
        raw = os.environ.get(f"RATE_LIMIT_{self.name.upper()}_PER_MIN", "")
        try:
            return int(raw) if raw.strip() else self.default
        except ValueError:
            return self.default

    def __call__(self, request: Request) -> None:
        limit = self.limit()
        if limit <= 0:
            return
        now = time.monotonic()
        hits = self._hits[client_ip(request)]
        while hits and now - hits[0] >= WINDOW_SECONDS:
            hits.popleft()
        if len(hits) >= limit:
            wait = max(1, math.ceil(WINDOW_SECONDS - (now - hits[0])))
            raise HTTPException(
                429,
                "Too many requests from this connection. Wait a moment and try again.",
                headers={"Retry-After": str(wait)},
            )
        hits.append(now)
