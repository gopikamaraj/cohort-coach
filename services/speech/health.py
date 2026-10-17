"""A circuit breaker for the speech services: after 3 failures in a row it opens, and speech is
skipped (the Practice Class switches to text) until a trial request is let through after the
cool-down. A success closes it again."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Literal

State = Literal["closed", "open", "half_open"]


class CircuitBreaker:
    def __init__(
        self,
        failures: int = 3,
        cool_down_s: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limit = failures
        self._cool = cool_down_s
        self._clock = clock
        self._fails = 0
        self._opened_at: float | None = None
        self._trial_out = False
        self._lock = threading.Lock()

    @property
    def state(self) -> State:
        with self._lock:
            if self._opened_at is None:
                return "closed"
            if self._clock() - self._opened_at >= self._cool:
                return "half_open"
            return "open"

    def allow(self) -> bool:
        """True if a request may go out. In half-open state exactly one trial is let through."""
        with self._lock:
            if self._opened_at is None:
                return True
            if self._clock() - self._opened_at < self._cool:
                return False
            if self._trial_out:
                return False
            self._trial_out = True
            return True

    def success(self) -> None:
        with self._lock:
            self._fails = 0
            self._opened_at = None
            self._trial_out = False

    def failure(self) -> None:
        with self._lock:
            self._fails += 1
            self._trial_out = False
            if self._fails >= self._limit or self._opened_at is not None:
                self._opened_at = self._clock()
