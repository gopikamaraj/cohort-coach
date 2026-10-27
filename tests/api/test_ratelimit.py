from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from services.api.ratelimit import RateLimiter, client_ip


def _app(limit: int) -> TestClient:
    app = FastAPI()
    limiter = RateLimiter("t", default_per_minute=limit)

    @app.get("/x", dependencies=[Depends(limiter)])
    def x() -> dict[str, bool]:
        return {"ok": True}

    return TestClient(app)


def test_the_call_over_the_limit_gets_429_with_retry_after() -> None:
    c = _app(3)
    assert [c.get("/x").status_code for _ in range(3)] == [200, 200, 200]
    r = c.get("/x")
    assert r.status_code == 429 and int(r.headers["retry-after"]) >= 1
    assert "try again" in r.json()["detail"].lower()


def test_each_client_has_its_own_budget() -> None:
    c = _app(1)
    assert c.get("/x", headers={"x-forwarded-for": "1.1.1.1"}).status_code == 200
    assert c.get("/x", headers={"x-forwarded-for": "1.1.1.1"}).status_code == 429
    assert c.get("/x", headers={"x-forwarded-for": "2.2.2.2"}).status_code == 200


def test_the_window_slides(monkeypatch: pytest.MonkeyPatch) -> None:
    now = [1000.0]
    monkeypatch.setattr("services.api.ratelimit.time.monotonic", lambda: now[0])
    c = _app(1)
    assert c.get("/x").status_code == 200
    assert c.get("/x").status_code == 429
    now[0] += 61
    assert c.get("/x").status_code == 200


def test_the_limit_comes_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_T_PER_MIN", "2")
    c = _app(100)
    assert [c.get("/x").status_code for _ in range(3)] == [200, 200, 429]


def test_zero_switches_the_limit_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RATE_LIMIT_T_PER_MIN", "0")
    c = _app(1)
    assert all(c.get("/x").status_code == 200 for _ in range(5))


def test_the_client_is_the_first_forwarded_address_else_the_socket() -> None:
    class Req:
        def __init__(self, h: dict[str, str], host: str | None) -> None:
            self.headers = h
            self.client = type("C", (), {"host": host})() if host else None

    assert client_ip(Req({"x-forwarded-for": "9.9.9.9, 10.0.0.1"}, "10.0.0.1")) == "9.9.9.9"  # type: ignore[arg-type]
    assert client_ip(Req({}, "7.7.7.7")) == "7.7.7.7"  # type: ignore[arg-type]
    assert client_ip(Req({}, None)) == "unknown"  # type: ignore[arg-type]
