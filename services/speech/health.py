"""A circuit breaker for the speech services: after 3 failures in a row it opens, and speech is
skipped (the Practice Class switches to text) until a trial request is let through after the
cool-down. A success closes it again. With `window_s`, it opens after `failures` failures within
that many seconds instead (the provider chain uses 3 in 60 s, per provider and function)."""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable
from typing import Literal

State = Literal["closed", "open", "half_open"]


class CircuitBreaker:
    def __init__(
        self,
        failures: int = 3,
        cool_down_s: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
        window_s: float | None = None,
    ) -> None:
        self._limit = failures
        self._window = window_s
        self._times: deque[float] = deque()
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
            self._times.clear()
            self._opened_at = None
            self._trial_out = False

    def failure(self) -> None:
        with self._lock:
            self._fails += 1
            self._trial_out = False
            now = self._clock()
            if self._window is not None:
                self._times.append(now)
                while self._times and now - self._times[0] > self._window:
                    self._times.popleft()
                tripped = len(self._times) >= self._limit
            else:
                tripped = self._fails >= self._limit
            if tripped or self._opened_at is not None:
                self._opened_at = now
