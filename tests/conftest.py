# ruff: noqa: E501
"""Shared pytest setup and AI-test fixtures (temp audit database, recordings folder)."""

from __future__ import annotations

import json
import os
import socket
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from hypothesis import settings
from sqlalchemy.orm import sessionmaker

import ai.client as client_mod
from ai.audit import SqlAuditSink
from ai.client import CallInput, input_hash
from ai.prompt_loader import load_prompt
from ai.registry import get_call
from services.api.db import Base, make_engine

# A developer's .env may switch pilot mode on; the suite always starts from the normal app (the
# pilot tests turn it on themselves). Set before any test module imports services.api.main.
os.environ["PILOT_MODE"] = "0"
# The suite never touches the developer's database file: tests that do not build their own engine get a throwaway one.
import tempfile as _tempfile  # noqa: E402

os.environ["DATABASE_URL"] = f"sqlite:///{_tempfile.mkdtemp(prefix='cc-suite-')}/suite.sqlite"

# Property tests check logic, not speed: a loaded CI or laptop must not fail them on timing.
settings.register_profile("default", deadline=None)
settings.load_profile("default")


@pytest.fixture
def sink(tmp_path: Path) -> SqlAuditSink:
    engine = make_engine(f"sqlite:///{tmp_path / 'audit.sqlite'}")
    Base.metadata.create_all(engine)
    return SqlAuditSink(sessionmaker(engine, expire_on_commit=False))


@pytest.fixture
def fixture_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    d = tmp_path / "recorded"
    monkeypatch.setattr(client_mod, "FIXTURE_DIR", d)
    return d


@pytest.fixture
def write_recording(fixture_dir: Path) -> Callable[..., Path]:
    def _write(
        call: str,
        inp: CallInput,
        outputs: list[dict[str, Any]],
        usage: dict[str, int] | None = None,
        extra_system: str = "",
    ) -> Path:
        spec = get_call(call)
        digest = input_hash(spec, load_prompt(spec.key), spec.model, inp, extra_system)
        path = fixture_dir / spec.key / f"{digest[:16]}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        body = {"outputs": outputs, "usage": usage or {"input_tokens": 120, "output_tokens": 20}}
        path.write_text(json.dumps(body), encoding="utf-8")
        return path

    return _write


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests never reach the network: only loopback connections are allowed."""
    real_connect = socket.socket.connect

    def guarded(self: socket.socket, address: Any) -> None:
        host = address[0] if isinstance(address, tuple) else address
        if host not in ("127.0.0.1", "::1", "localhost") and self.family != socket.AF_UNIX:
            raise RuntimeError(f"network access blocked in tests: {host}")
        real_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded)


@pytest.fixture(autouse=True)
def _judge_mode_on_for_the_suite(monkeypatch: pytest.MonkeyPatch) -> None:
    """The suite runs as the demo deployment (the server default is off); tests that check the
    production behaviour set JUDGE_MODE=0 themselves."""
    monkeypatch.setenv("JUDGE_MODE", "1")


@pytest.fixture(autouse=True)
def _rate_limits_off_for_the_suite(monkeypatch: pytest.MonkeyPatch) -> None:
    """Many tests hit one endpoint from one test client; tests of the limit set their own."""
    for name in (
        "practice_session", "practice_turn", "practice_voice", "practice_watch", "sheets_read",
    ):  # fmt: skip
        monkeypatch.setenv(f"RATE_LIMIT_{name.upper()}_PER_MIN", "0")


@pytest.fixture(autouse=True)
def _practice_speed_switches_off_for_the_suite(monkeypatch: pytest.MonkeyPatch) -> None:
    """A developer's .env may turn the Practice Class speed switches on, and the app reads .env at
    start-up without overriding what is set. The suite tests the defaults; the tests of a switch
    set it themselves."""
    monkeypatch.setenv("PRACTICE_SKIP_CHECKER", "0")
    monkeypatch.setenv("PRACTICE_AI_INTENTS", "all")


@pytest.fixture(autouse=True)
def _no_chat_poller(monkeypatch: pytest.MonkeyPatch) -> None:
    """The chat poller is off in tests: a test runs `tick` itself with a frozen clock."""
    monkeypatch.setenv("CHAT_POLLER", "0")


@pytest.fixture(autouse=True)
def _developer_switches_out_of_the_suite(monkeypatch: pytest.MonkeyPatch) -> None:
    """The same for the switches added on 1 Nov: speech provider keys and order, the child model and
    the testing shortcuts. The suite tests the defaults; a test of a switch sets it itself."""
    for name in (
        "BODHAN_API_KEY", "BODHAN_SPEAK_API_KEY", "BODHAN_TRANSCRIBE_API_KEY", "BODHAN_BASE_URL",
        "SPEECH_TTS_PROVIDERS", "SPEECH_STT_PROVIDERS", "SIMULATOR_MODEL", "DEV_TESTING",
        "BAYES_PRIOR_CONCENTRATION", "BAYES_RESPONSIVENESS_SCALE", "BAYES_RESPONSIVENESS_SHAPE",
        "BAYES_LEARN_CAP", "BAYES_EFFECT_SCALE", "BAYES_GUESS", "BAYES_SLIP",
        "BAYES_PARAMS",
    ):  # fmt: skip
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def _register_users_seen_in_headers(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """A request that names a user in `X-User` is from someone who registered that nickname. Tests state it in a
    header and this registers the nickname the first time a client sees it, so most tests do not repeat the sign-up.
    A request that names no one is made by the signed-in "test user", so the many tests about features (not about
    who may call them) keep their meaning now that every route needs a user.
    Tests of sign-in itself and of "not signed in" mark themselves `no_autoregister` and register by hand."""
    if request.node.get_closest_marker("no_autoregister"):
        return
    from fastapi.testclient import TestClient

    original = TestClient.request

    def request_with_user(self: TestClient, method: str, url: Any, **kw: Any) -> Any:  # noqa: ANN401
        headers = dict(kw.get("headers") or {})
        uid = headers.get("X-User") or headers.get("x-user")
        if not uid and str(url).startswith("/api/") and not str(url).startswith("/api/users/"):
            uid = headers["X-User"] = "test user"  # the default signed-in user of a test that is not about who is calling
            kw["headers"] = headers
        seen: set[str] = self.__dict__.setdefault("_seen_users", set())
        if uid and uid not in seen and not str(url).startswith("/api/users/"):
            seen.add(uid)
            original(self, "POST", "/api/users/register", json={"nickname": uid})  # 409 when already there: fine
        return original(self, method, url, **kw)

    monkeypatch.setattr(TestClient, "request", request_with_user)
