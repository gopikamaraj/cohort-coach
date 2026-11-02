# ruff: noqa: E501
"""The states of one module and the only moves between them. One place, tested."""

from __future__ import annotations

PLANNED, READY, DOWNLOADED = "planned", "ready", "downloaded"
FEEDBACK_GIVEN, COMPLETED, SKIPPED, EXPIRED = "feedback_given", "completed", "skipped", "expired"
STATES = (PLANNED, READY, DOWNLOADED, FEEDBACK_GIVEN, COMPLETED, SKIPPED, EXPIRED)

# planned: only title and due date shown. ready: generated. downloaded: audio taken.
# feedback_given: worked / partly / not yet answered. completed: the next module was made after the answer
# (or the track ended). skipped: left out because the track stopped. expired: the next module came
# on its due date with no answer; a late answer can still attach (expired -> feedback_given).
TRANSITIONS: dict[str, frozenset[str]] = {
    PLANNED: frozenset({READY, SKIPPED}),
    READY: frozenset({DOWNLOADED, FEEDBACK_GIVEN, EXPIRED}),
    DOWNLOADED: frozenset({FEEDBACK_GIVEN, EXPIRED}),
    FEEDBACK_GIVEN: frozenset({COMPLETED}),
    EXPIRED: frozenset({FEEDBACK_GIVEN}),
    COMPLETED: frozenset(),
    SKIPPED: frozenset(),
}

TRIGGERS = ("start", "teacher", "due_date", "coach")
BRANCHES = ("first", "worked", "partly", "not_yet", "no_feedback")
# not_tried is a HOLD, not a result: it never advances the track and is never counted as one
ANSWERS = ("worked", "partly", "not_yet", "not_tried")
RESULTS = ("worked", "partly", "not_yet")
TRACK_STATES = ("active", "completed", "stopped")


class IllegalTransition(ValueError):
    pass


def can(old: str, new: str) -> bool:
    return new in TRANSITIONS.get(old, frozenset())


def check(old: str, new: str) -> None:
    if not can(old, new):
        raise IllegalTransition(f"A module cannot go from {old} to {new}.")
