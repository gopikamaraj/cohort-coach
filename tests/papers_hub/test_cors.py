"""The web app and the API run on different origins in development and in the cloud: every header the
Papers page sends must be allowed in the preflight, or the browser blocks the call before it is made."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.api.main import create_app

SENT = [
    "content-type",
    "x-role",
    "x-class-id",
    "x-person",
    "x-user",
    "x-demo-session",
    "x-demo-person",
]


def test_the_preflight_allows_every_header_the_papers_page_sends(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PWA_ORIGIN", "http://localhost:5173")
    client = TestClient(create_app())
    for method in ("GET", "POST", "DELETE"):
        r = client.options(
            "/api/paper-hub/papers",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": ",".join(SENT),
            },
        )
        assert r.status_code == 200, (method, r.text)
        allowed = r.headers["access-control-allow-headers"].lower()
        assert all(h in allowed for h in SENT), allowed
