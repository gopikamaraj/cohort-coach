"""lessons-pregen: it finds the published demo lessons, prints the plan, and after it has run the
demo lessons play from the cache with every provider down."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy.orm import Session

from services.content import publish, versions
from services.media.storage import LocalBlobStore
from services.speech import lessons
from tests.content.test_publish import COACH, OFFICER, approve_all, fake_mp3
from tests.speech.test_lessons import Scripted, Speech

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "lessons_pregen.py"


def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("lessons_pregen", SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["lessons_pregen"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def quick(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lessons, "encode_mp3", fake_mp3)


def test_the_demo_lessons_play_from_the_cache_with_every_provider_disabled(db: Session) -> None:
    mod = load()
    v = approve_all(db)
    versions.coach_approve(db, v.id, *COACH)
    versions.officer_activate(db, v.id, *OFFICER)
    publish_store = LocalBlobStore(b"p")
    publish.publish_version(
        db, v.id, "SUB-SFL-g3-hindi-X-1", store=publish_store, speech=Speech(Scripted("bodhan"))
    )
    items = mod.demo_lessons(db)
    assert len(items) == 6 and all(i["script"] for i in items)
    plan = mod.plan(items)
    assert plan["lessons"] == 6 and plan["chars"] > 0 and plan["cost_inr"] > 0

    store = LocalBlobStore(b"cache")
    up = Scripted("bodhan")
    rows = mod.run(db, store, Speech(up), items)
    assert all(r["ok"] for r in rows) and len(up.said) > 0

    down = Speech(Scripted("bodhan", configured=False), Scripted("sarvam", configured=False))
    again = mod.run(db, store, down, items)
    assert all(r["ok"] and r["cached"] for r in again)  # nothing to call, everything plays


def test_without_yes_nothing_is_spent(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    mod = load()
    monkeypatch.setattr(
        mod,
        "demo_lessons",
        lambda db: [
            {"track": "t", "language": "en", "day": 1, "script": "Hello there. Count to 10."}
        ],
    )
    called: list[str] = []
    monkeypatch.setattr(mod, "run", lambda *a, **k: called.append("run") or [])
    monkeypatch.setattr(
        mod, "make_engine", lambda: __import__("sqlalchemy").create_engine("sqlite://")
    )
    assert mod.main([]) == 0
    assert called == [] and "Nothing spent" in capsys.readouterr().out
