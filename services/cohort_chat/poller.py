"""Answers due questions every second, so the AI's timer belongs to the server and a closed browser
changes nothing. The same `tick` also runs when anyone loads a thread, so a restart or a sleeping
instance loses nothing. Off with CHAT_POLLER=0 (the tests)."""

from __future__ import annotations

import logging
import os
import threading
import time

from services.api.profiles import get_session
from services.cohort_chat import service

log = logging.getLogger(__name__)
_started = threading.Event()


def _loop() -> None:
    every = float(os.environ.get("CHAT_POLL_SECONDS", "1"))
    while True:
        try:
            gen = get_session()
            db = next(gen)
            try:
                service.tick(db)
            finally:
                gen.close()
        except Exception:  # noqa: BLE001 - a bad sweep must not stop the next one
            log.exception("chat poller sweep failed")
        time.sleep(every)


def start() -> None:
    if _started.is_set():
        return
    _started.set()
    threading.Thread(target=_loop, name="chat-poller", daemon=True).start()
