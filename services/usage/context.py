# ruff: noqa: E501
"""The action id of the request being served, kept in a context variable so metering works without
passing it through every function. Worker threads do not inherit it: start them with `submit`."""

from __future__ import annotations

import contextvars
import re
from collections.abc import Callable
from concurrent.futures import Executor, Future
from typing import Any

ACTION_ID = re.compile(r"^[A-Za-z0-9-]{8,40}$")
ACTION_NAME = re.compile(r"^[a-z0-9_]{1,40}$")

_action_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "usage_action_id", default=None
)
_action_name: contextvars.ContextVar[str] = contextvars.ContextVar("usage_action_name", default="")


def current() -> str | None:
    return _action_id.get()


def current_name() -> str:
    return _action_name.get()


def enter(
    action_id: str, name: str
) -> tuple[contextvars.Token[str | None], contextvars.Token[str]]:
    return _action_id.set(action_id), _action_name.set(name)


def leave(tokens: tuple[contextvars.Token[str | None], contextvars.Token[str]]) -> None:
    _action_id.reset(tokens[0])
    _action_name.reset(tokens[1])


def submit[T](pool: Executor, fn: Callable[..., T], *args: Any, **kwargs: Any) -> Future[T]:
    """pool.submit that carries the action id into the worker thread (a copy of this thread's context)."""
    ctx = contextvars.copy_context()
    return pool.submit(ctx.run, fn, *args, **kwargs)
