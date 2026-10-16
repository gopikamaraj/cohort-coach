"""A fake Anthropic client for tests: same .messages.parse(...) shape, no network."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from pydantic import BaseModel


class FakeMessages:
    def __init__(self, replies: list[BaseModel | Exception | None], usage: dict[str, int]) -> None:
        self.replies = replies
        self.usage = usage
        self.calls: list[dict[str, Any]] = []

    def parse(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        reply = self.replies[min(len(self.calls) - 1, len(self.replies) - 1)]
        if isinstance(reply, Exception):
            raise reply
        return SimpleNamespace(
            parsed_output=reply,
            usage=SimpleNamespace(
                input_tokens=self.usage.get("input_tokens", 100),
                output_tokens=self.usage.get("output_tokens", 20),
                cache_read_input_tokens=self.usage.get("cache_read", 0),
                cache_creation_input_tokens=self.usage.get("cache_write", 0),
            ),
        )


class FakeClient:
    def __init__(
        self, replies: list[BaseModel | Exception | None], usage: dict[str, int] | None = None
    ) -> None:
        self.messages = FakeMessages(replies, usage or {})
