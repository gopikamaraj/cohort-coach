"""Caps on the assistant's model use: per session and per role, with tokens and cost counted.

In memory, per process (like services/api/ratelimit.py): it stops a loop or a crowd from draining the
budget during judging, and the budget hard-stop in ai/client.py stays the backstop. Pre-written
answers cost nothing and are never counted; only a model-backed answer to typed text is.

Settings (environment, 0 switches a cap off):
  ASSISTANT_SESSION_MAX_PER_HOUR      model answers one session may ask for in an hour (default 30)
  ASSISTANT_ROLE_MAX_CALLS_PER_DAY    model answers one role may use in a day (default 300)
  ASSISTANT_ROLE_MAX_USD_PER_DAY      what one role's model answers may cost in a day (default 3.0)
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Any


class Capped(Exception):
    def __init__(self, which: str) -> None:
        super().__init__(which)
        self.which = which  # "session", "role_calls" or "role_spend"


def _num(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    try:
        return float(raw) if raw else default
    except ValueError:
        return default


class Caps:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._sessions: dict[str, deque[float]] = defaultdict(deque)
        self._role: dict[tuple[str, int], dict[str, float]] = defaultdict(
            lambda: {"calls": 0, "tokens_in": 0, "tokens_out": 0, "usd": 0.0}
        )

    @staticmethod
    def _day(now: float) -> int:
        return int(now // 86400)

    def check(self, role: str, session: str, now: float | None = None) -> None:
        """Raise Capped if this role or session has used its share. Call before a model answer."""
        t = time.time() if now is None else now
        per_hour = int(_num("ASSISTANT_SESSION_MAX_PER_HOUR", 30))
        if per_hour > 0:
            hits = self._sessions[session]
            while hits and t - hits[0] >= 3600:
                hits.popleft()
            if len(hits) >= per_hour:
                raise Capped("session")
        today = self._role[(role, self._day(t))]
        max_calls = int(_num("ASSISTANT_ROLE_MAX_CALLS_PER_DAY", 300))
        if max_calls > 0 and today["calls"] >= max_calls:
            raise Capped("role_calls")
        max_usd = _num("ASSISTANT_ROLE_MAX_USD_PER_DAY", 3.0)
        if max_usd > 0 and today["usd"] >= max_usd:
            raise Capped("role_spend")

    def record(
        self,
        role: str,
        session: str,
        tokens_in: int,
        tokens_out: int,
        usd: float,
        now: float | None = None,
    ) -> None:
        t = time.time() if now is None else now
        self._sessions[session].append(t)
        today = self._role[(role, self._day(t))]
        today["calls"] += 1
        today["tokens_in"] += tokens_in
        today["tokens_out"] += tokens_out
        today["usd"] += usd

    def snapshot(self, now: float | None = None) -> dict[str, Any]:
        """Today's counts per role: calls, tokens and cost (no text, no identity)."""
        day = self._day(time.time() if now is None else now)
        return {role: dict(v) for (role, d), v in self._role.items() if d == day}


CAPS = Caps()
