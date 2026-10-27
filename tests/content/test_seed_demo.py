"""P10: the judge-deployment seed switches a demo track on, only from drafts that passed every
automatic gate, and refuses to run anywhere else."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.calls.c05_track_draft import draft_part
from ai.client import CallContext
from ai.schemas import TrackPart, Verdict
from scripts.seed_demo_track import NotAJudgeDeployment, seed
from services.api.db import ContentAudit, TrackManifest
from services.content import drafting
from services.content.track import load_track
from services.pilot import storage as storage_mod
from services.pilot.storage import LocalBlobStore
from tests.ai.test_c05_track_draft import GOOD, PASS
from tests.content.test_publish import MODEL, TAGGED, Voice, fake_join
from tests.support_ai import FakeClient

FAIL = Verdict(passed=False, failed_items=["tone"], reason_short="no", reason_for_user="no")


def queue_all(db: Session, language: str = "en", *, hold_day: int | None = None) -> None:
    track = load_track("sub-sfl.v1")
    for day in range(1, 7):
        part = TrackPart(kind="lesson", day=day, script=TAGGED)
        verdict = FAIL if day == hold_day else PASS
        ctx = CallContext(mode="stub", client=FakeClient([part, verdict]))  # type: ignore[arg-type]
        drafting.store_draft(db, draft_part(track, "lesson", day, language, context=ctx), track)
    part = TrackPart(kind="model_lesson", day=0, script=MODEL)
    ctx = CallContext(mode="stub", client=FakeClient([part, PASS]))  # type: ignore[arg-type]
    drafting.store_draft(db, draft_part(track, "model_lesson", 0, language, context=ctx), track)


@pytest.fixture
def judge_env(monkeypatch: pytest.MonkeyPatch) -> LocalBlobStore:
    monkeypatch.setenv("JUDGE_MODE", "1")
    store = LocalBlobStore(b"s")
    monkeypatch.setattr(storage_mod, "audio_store", lambda: store)
    monkeypatch.setattr("services.speech.service.default_service", lambda: Voice())
    monkeypatch.setattr("services.content.publish.encode", fake_join)
    return store


def test_the_seed_refuses_to_run_outside_a_judge_deployment(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("JUDGE_MODE", "0")
    queue_all(db)
    with pytest.raises(NotAJudgeDeployment):
        seed(db, ["en"], draft=False)
    assert db.execute(select(TrackManifest)).first() is None  # nothing was approved or published


def test_it_approves_only_drafts_that_passed_and_publishes_a_manifest(
    db: Session, judge_env: LocalBlobStore
) -> None:
    queue_all(db)
    out = seed(db, ["en"], draft=False)
    assert out["published"] and out["languages"]["en"]["missing"] == []
    manifest = db.execute(select(TrackManifest)).scalar_one()
    assert len(manifest.body["parts"]) == 7 and manifest.body["simulated"] is True
    audit = (
        db.execute(select(ContentAudit).where(ContentAudit.actor == "demo-seed")).scalars().all()
    )
    assert {a.role for a in audit} >= {"coach", "officer"}  # both keys, by the seed


def test_a_part_the_checker_held_is_never_approved_by_the_seed(
    db: Session, judge_env: LocalBlobStore
) -> None:
    queue_all(db, hold_day=4)
    out = seed(db, ["en"], draft=False)
    assert out["published"] is False and out["languages"]["en"]["missing"] == ["lesson:4"]
    assert db.execute(select(TrackManifest)).first() is None
    assert GOOD  # the held draft stays in the queue for a person
