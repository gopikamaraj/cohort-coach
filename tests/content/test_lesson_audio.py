"""Lesson audio after publishing: what the manifest carries, text only when every provider fails,
and the coach's review over HTTP (list, open, regenerate a sentence or the lesson, approve), with
the roles, the audit trail and the rule that a cohort of fewer than 5 classes is never shown."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ai.client import CallContext
from services.api import practice as practice_api
from services.api.db import Base, ContentAudit, TrackManifest, make_engine
from services.api.main import create_app
from services.api.profiles import get_session
from services.content import lesson_audio, publish, versions
from services.media.storage import LocalBlobStore, get_audio_store
from services.speech import lessons
from services.speech.sarvam import SpeechError
from tests.content.test_publish import COACH, OFFICER, approve_all, fake_mp3
from tests.speech.test_lessons import Scripted, Speech
from tests.support_ai import FakeClient

BIG = "SUB-SFL-g3-hindi-X-1"  # 9 classes in the simulated block
SMALL = "SUB-SFL-g3-english-X-1"  # 3 classes


@pytest.fixture(autouse=True)
def quick(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lessons, "encode_mp3", fake_mp3)


def published(db: Session, store: LocalBlobStore, speech: object, cohort: str = BIG) -> dict:  # type: ignore[type-arg]
    v = approve_all(db)
    versions.coach_approve(db, v.id, *COACH)
    versions.officer_activate(db, v.id, *OFFICER)
    return publish.publish_version(db, v.id, cohort, store=store, speech=speech)


def test_the_manifest_carries_the_mp3_its_timing_and_the_ai_voice_label(db: Session) -> None:
    store = LocalBlobStore(b"a")
    manifest = published(db, store, Speech(Scripted("bodhan")))
    lesson = next(p for p in manifest["parts"] if p["kind"] == "lesson")
    assert lesson["mime"] == "audio/mpeg" and lesson["audio_key"].endswith(".mp3")
    assert lesson["ai_voice"] is True and lesson["voice_provider"] == "bodhan"
    assert lesson["audio_review"] == "unreviewed" and lesson["sentences"] and lesson["timing"]
    assert len(lesson["timing"]) == len(lesson["sentences"])
    rows = db.execute(select(lesson_audio.LessonAudioRecord)).scalars().all()
    assert len(rows) == 6 and {r.cohort_id for r in rows} == {BIG} and rows[0].cohort_classes == 9
    voiced = db.execute(select(ContentAudit).where(ContentAudit.action == "voice_lesson")).scalars()
    assert len(list(voiced)) == 6


def test_every_provider_down_publishes_the_lessons_as_text_only(db: Session) -> None:
    class Down:
        chain = None

        def synthesize(self, text: str, lang: str, voice: object) -> bytes:
            raise SpeechError("unavailable", 503)

    manifest = published(db, LocalBlobStore(b"a"), Down())
    lessons_ = [p for p in manifest["parts"] if p["kind"] == "lesson"]
    assert len(lessons_) == 6 and all(p["audio_key"] is None for p in lessons_)
    assert all(p["audio_status"] == "text_only" and p["script"] for p in lessons_)
    audit = db.execute(select(ContentAudit).where(ContentAudit.action == "publish")).scalar_one()
    assert audit.detail["text_only"] == 6


def test_the_teacher_lesson_step_carries_the_size_sentences_and_timing(db: Session) -> None:
    from types import SimpleNamespace

    from services.api.flows import t4

    store = LocalBlobStore(b"a")
    published(db, store, Speech(Scripted("bodhan")))
    m = db.execute(select(TrackManifest)).scalar_one()
    part = next(p for p in m.body["parts"] if p["kind"] == "lesson")
    ctx = SimpleNamespace(db=db, data={"day": 1}, teacher=SimpleNamespace(lang="en", judge=True))
    t4_manifest, t4_lessons = t4.manifest_for, t4._lessons
    try:
        t4.manifest_for = lambda c: m  # type: ignore[assignment]
        t4._lessons = lambda c: [part]  # type: ignore[assignment]
        step = t4._lesson_build(ctx)
    finally:
        t4.manifest_for, t4._lessons = t4_manifest, t4_lessons  # type: ignore[assignment]
    assert step.audio and step.audio_info is not None
    assert step.audio_info["bytes"] == part["bytes"] and step.audio_info["ai_voice"] is True
    assert step.audio_info["sentences"] == part["sentences"]


# --- the review API -------------------------------------------------------------------------------


@pytest.fixture
def api(tmp_path: Path) -> Iterator[tuple[TestClient, Session, LocalBlobStore, Scripted]]:
    engine = make_engine(f"sqlite:///{tmp_path / 'la.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    app = create_app()
    store = LocalBlobStore(b"a")
    voice = Scripted("bodhan")

    def session() -> Iterator[Session]:
        with factory() as s:
            yield s

    app.dependency_overrides[get_session] = session
    app.dependency_overrides[get_audio_store] = lambda: store
    app.dependency_overrides[practice_api.get_speech] = lambda: Speech(voice)
    app.dependency_overrides[practice_api.get_ai_context] = lambda: CallContext(
        mode="stub",
        client=FakeClient([]),  # type: ignore[arg-type]
    )
    with factory() as db:
        published(db, store, Speech(voice), BIG)
        published(db, store, Speech(voice), SMALL)
        yield TestClient(app), db, store, voice


def h(role: str) -> dict[str, str]:
    return {"X-Role": role}


def test_coach_and_officer_list_teachers_and_mentors_cannot(api) -> None:  # type: ignore[no-untyped-def]
    client, *_ = api
    for role in ("coach", "officer"):
        rows = client.get("/api/review/lesson-audio", headers=h(role)).json()
        assert len(rows) == 12
    for role in ("teacher", "mentor"):
        assert client.get("/api/review/lesson-audio", headers=h(role)).status_code == 403


def test_a_cohort_of_fewer_than_5_classes_is_listed_without_script_or_audio(api) -> None:  # type: ignore[no-untyped-def]
    client, db, *_ = api
    small = (
        db.execute(
            select(lesson_audio.LessonAudioRecord).where(
                lesson_audio.LessonAudioRecord.cohort_id == SMALL
            )
        )
        .scalars()
        .first()
    )
    assert small is not None
    view = client.get(f"/api/review/lesson-audio/{small.id}", headers=h("coach")).json()
    assert view["hidden"] is True
    assert "sentences" not in view and "audio_url" not in view and "timing" not in view
    for path in ("regenerate", "approve"):
        r = client.post(f"/api/review/lesson-audio/{small.id}/{path}", json={}, headers=h("coach"))
        assert r.status_code == 403


def big_rec(db: Session) -> lesson_audio.LessonAudioRecord:
    rec = (
        db.execute(
            select(lesson_audio.LessonAudioRecord).where(
                lesson_audio.LessonAudioRecord.cohort_id == BIG,
                lesson_audio.LessonAudioRecord.day == 1,
            )
        )
        .scalars()
        .first()
    )
    assert rec is not None
    return rec


def test_the_coach_opens_a_lesson_with_sentences_checks_costs_and_audio(api) -> None:  # type: ignore[no-untyped-def]
    client, db, *_ = api
    rec = big_rec(db)
    view = client.get(f"/api/review/lesson-audio/{rec.id}", headers=h("coach")).json()
    assert view["hidden"] is False and view["audio_url"]
    assert len(view["sentences"]) == len(view["checks"]) == len(view["sentence_costs_inr"])
    assert view["summary"]["passed"] == len(view["sentences"])
    assert view["provider"] == "bodhan" and view["voice"] == "Kavya"


def test_regenerating_one_sentence_makes_one_chunk_and_keeps_the_published_audio(api) -> None:  # type: ignore[no-untyped-def]
    client, db, store, voice = api
    rec = big_rec(db)
    before = len(voice.said)
    m_before = db.execute(select(TrackManifest).where(TrackManifest.cohort_id == BIG)).scalar_one()
    old_key = next(p for p in m_before.body["parts"] if p["id"] == rec.part_id)["audio_key"]
    r = client.post(
        f"/api/review/lesson-audio/{rec.id}/regenerate", json={"sentence": 0}, headers=h("coach")
    )
    assert r.status_code == 200
    new = r.json()
    assert new["revision"] == rec.revision + 1 and new["status"] == "unreviewed"
    assert len(voice.said) == before + 1  # one chunk
    db.expire_all()
    m = db.execute(select(TrackManifest).where(TrackManifest.cohort_id == BIG)).scalar_one()
    assert next(p for p in m.body["parts"] if p["id"] == rec.part_id)["audio_key"] == old_key
    audit = db.execute(
        select(ContentAudit).where(ContentAudit.action == "regen_sentence")
    ).scalar_one()
    assert audit.role == "coach" and audit.detail["sentence"] == 0 and "script" not in audit.detail


def test_approving_points_the_manifest_to_the_new_revision_and_deletes_the_old_file(api) -> None:  # type: ignore[no-untyped-def]
    client, db, store, voice = api
    rec = big_rec(db)
    old_key = rec.audio_key
    new = client.post(
        f"/api/review/lesson-audio/{rec.id}/regenerate", json={}, headers=h("coach")
    ).json()
    assert (
        client.post(
            f"/api/review/lesson-audio/{new['id']}/approve", headers=h("officer")
        ).status_code
        == 403
    )
    done = client.post(f"/api/review/lesson-audio/{new['id']}/approve", headers=h("coach"))
    assert done.status_code == 200 and done.json()["status"] == "approved"
    db.expire_all()
    m = db.execute(select(TrackManifest).where(TrackManifest.cohort_id == BIG)).scalar_one()
    part = next(p for p in m.body["parts"] if p["id"] == rec.part_id)
    assert part["audio_id"] == new["id"] and part["audio_review"] == "approved"
    assert store.size(old_key) is None and store.size(part["audio_key"]) is not None
    assert db.get(lesson_audio.LessonAudioRecord, rec.id).status == "superseded"  # type: ignore[union-attr]
    small_manifest = db.execute(
        select(TrackManifest).where(TrackManifest.cohort_id == SMALL)
    ).scalar_one()
    assert all(
        p.get("audio_id") != new["id"] for p in small_manifest.body["parts"]
    )  # other cohort untouched
    actions = {a.action for a in db.execute(select(ContentAudit)).scalars()}
    assert {"regen_lesson", "approve_audio"} <= actions


def test_a_failed_regeneration_says_the_service_is_down_and_changes_nothing(api) -> None:  # type: ignore[no-untyped-def]
    client, db, store, voice = api
    rec = big_rec(db)
    voice.fail_on = set(range(1, 999))
    voice.calls = 0
    r = client.post(f"/api/review/lesson-audio/{rec.id}/regenerate", json={}, headers=h("coach"))
    assert r.status_code == 503
    db.expire_all()
    assert db.get(lesson_audio.LessonAudioRecord, rec.id).status == "unreviewed"  # type: ignore[union-attr]
