from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

import services.api.main as main_module


def client_with(monkeypatch: pytest.MonkeyPatch, origin: str | None) -> TestClient:
    if origin is None:
        monkeypatch.delenv("PWA_ORIGIN", raising=False)
    else:
        monkeypatch.setenv("PWA_ORIGIN", origin)
    fresh = importlib.reload(main_module)
    return TestClient(fresh.app)


def preflight(c: TestClient, origin: str) -> dict[str, str]:
    res = c.options(
        "/api/practice/sessions",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    return dict(res.headers)


def test_only_the_pwa_origin_may_call_the_api(monkeypatch: pytest.MonkeyPatch) -> None:
    try:
        c = client_with(monkeypatch, "https://cohort-coach.pages.example/")
        ok = preflight(c, "https://cohort-coach.pages.example")
        assert ok.get("access-control-allow-origin") == "https://cohort-coach.pages.example"
        assert "access-control-allow-credentials" not in ok  # no cookies: the app has no login
        other = preflight(c, "https://evil.example")
        assert "access-control-allow-origin" not in other
        assert "*" not in ok.get("access-control-allow-origin", "")
    finally:
        monkeypatch.undo()
        importlib.reload(main_module)


def test_without_a_configured_origin_no_cors_headers_are_added(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    try:
        c = client_with(monkeypatch, None)
        res = c.get("/api/health", headers={"Origin": "https://anywhere.example"})
        assert res.status_code == 200 and "access-control-allow-origin" not in res.headers
    finally:
        monkeypatch.undo()
        importlib.reload(main_module)
