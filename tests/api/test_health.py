"""The health check says which AI mode the server runs in, so screens can label replayed answers."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.api.main import create_app


@pytest.mark.parametrize("mode", ["recorded", "off", "live"])
def test_health_reports_the_ai_mode(monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    monkeypatch.setenv("AI_MODE", mode)
    body = TestClient(create_app()).get("/api/health").json()
    assert body["status"] == "ok" and body["ai_mode"] == mode


def test_health_says_dev_testing_only_when_the_flag_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEV_TESTING", raising=False)
    assert "dev_testing" not in TestClient(create_app()).get("/api/health").json()
    monkeypatch.setenv("DEV_TESTING", "0")
    assert "dev_testing" not in TestClient(create_app()).get("/api/health").json()
    monkeypatch.setenv("DEV_TESTING", "1")
    assert TestClient(create_app()).get("/api/health").json()["dev_testing"] is True
