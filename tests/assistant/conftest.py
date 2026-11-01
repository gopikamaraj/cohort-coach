"""Fixtures for the assistant tests: a stand-in model, clean caps, and the app in judge or normal mode."""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import BaseModel

from ai.audit import SqlAuditSink
from ai.client import CallContext
from services.assistant import answer, limits
from tests.support_ai import FakeClient

ModelFactory = Callable[..., tuple[CallContext, FakeClient]]


@pytest.fixture(autouse=True)
def clean(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for name in (
        "ASSISTANT_SESSION_MAX_PER_HOUR",
        "ASSISTANT_ROLE_MAX_CALLS_PER_DAY",
        "ASSISTANT_ROLE_MAX_USD_PER_DAY",
        "GIT_SHA",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("RATE_LIMIT_ASSISTANT_PER_MIN", "0")
    monkeypatch.setenv("RETRIEVAL", "off")  # tests never call Gemini or Firestore
    limits.CAPS.reset()
    answer.reload()
    yield
    limits.CAPS.reset()
    answer.reload()


@pytest.fixture
def model(sink: SqlAuditSink) -> ModelFactory:
    """A context whose model returns the given replies in order; the fake records what it was sent."""

    def make(*replies: BaseModel | Exception | None) -> tuple[CallContext, FakeClient]:
        fake = FakeClient(list(replies))
        return CallContext(mode="stub", client=fake, sink=sink), fake

    return make


@pytest.fixture
def judge_app(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    from services.api.main import create_app

    monkeypatch.setenv("JUDGE_MODE", "1")
    monkeypatch.setenv("AI_MODE", "recorded")
    return TestClient(create_app())


@pytest.fixture
def prod_app(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    from services.api.main import create_app

    monkeypatch.setenv("JUDGE_MODE", "0")
    monkeypatch.setenv("AI_MODE", "recorded")
    return TestClient(create_app())
