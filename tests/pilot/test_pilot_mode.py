"""PILOT_MODE=1 leaves two working pages and sign-in; every other route is a 404 on the server."""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from ai import config
from services.api.main import create_app
from tests.pilot.conftest import Env

PILOT_PATHS = ("/api/pilot/", "/api/health")


def _routes_of(app) -> list[tuple[str, str]]:  # type: ignore[no-untyped-def]
    """Every (method, path) the app serves, from its OpenAPI document."""
    out = []
    for path, ops in app.openapi()["paths"].items():
        for method in ops:
            out.append((method.upper(), re.sub(r"\{[^}]+\}", "x", path)))
    return out


def test_pilot_mode_is_off_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PILOT_MODE", raising=False)
    assert config.pilot_mode() is False
    client = TestClient(create_app())
    assert client.get("/api/pilot/config").status_code == 404  # not mounted at all
    assert "pilot" not in client.get("/api/health").json()  # the normal health answer is unchanged


def test_env_example_lists_the_pilot_switch() -> None:
    from pathlib import Path

    text = (Path(__file__).resolve().parents[2] / ".env.example").read_text(encoding="utf-8")
    for key in (
        "PILOT_MODE=0",
        "PILOT_AUDIO_MAX",
        "S3_SHEETS_BUCKET",
        "PILOT_ACCOUNTS",
        "PILOT_RETENTION_DAYS",
    ):
        assert key in text


def test_every_non_pilot_route_returns_404_in_pilot_mode(env: Env) -> None:
    normal = create_app(pilot=False)
    others = [
        (m, p)
        for m, p in _routes_of(normal)
        if not p.startswith(PILOT_PATHS) and p != "/api/health"
    ]
    assert len(others) > 30  # the whole normal API, not a handful
    bad = []
    for method, path in others:
        res = env.client.request(method, path, headers=env.h("seema"))
        if res.status_code != 404:
            bad.append((method, path, res.status_code))
    assert not bad, bad


def test_the_api_docs_are_off_in_pilot_mode(env: Env) -> None:
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert env.client.get(path).status_code == 404


def test_health_says_it_is_pilot_mode(env: Env) -> None:
    assert env.client.get("/api/health").json()["pilot"] is True


def test_the_only_routes_are_pilot_routes_and_health(env: Env) -> None:
    paths = {p for _, p in _routes_of(env.client.app)}
    assert all(p.startswith(PILOT_PATHS) for p in paths), sorted(paths)


def test_a_role_header_or_judge_mode_cannot_stand_in_for_sign_in(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("JUDGE_MODE", "1")
    for headers in ({}, {"X-Role": "coach"}, {"X-Role": "officer"}, {"X-Judge": "1"}):
        res = env.client.get("/api/pilot/config", headers=headers)
        assert res.status_code == 401, headers
