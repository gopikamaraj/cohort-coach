"""Shared pytest setup and AI-test fixtures (temp audit database, recordings folder)."""

from __future__ import annotations

import json
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
