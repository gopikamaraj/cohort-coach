"""P09 T08: publishing. Only content both keys switched on is voiced; class numbers come from code
(the cohort's classes in the simulated block); each lesson is voiced once and reused; the
manifest lists what T4 and the bot need; a voice lesson stays within the data budget."""

from __future__ import annotations

import shutil

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.calls.c05_track_draft import draft_part
from ai.client import CallContext
from ai.schemas import TrackPart
from services.api.db import ContentAudit, TrackManifest
from services.content import drafting, publish, review, versions
from services.content.track import load_track
from services.pilot.storage import LocalBlobStore
from services.speech import audio as speech_audio
from tests.ai.test_c05_track_draft import GOOD, PASS
from tests.support_ai import FakeClient

COACH = ("coach-demo", "coach")
OFFICER = ("officer-demo", "officer")
MODEL = "Teacher says: Open a bundle. Child says: Now I have 12 loose sticks."
TAGGED = (
    GOOD
    + " Meena writes {{class.example_a}} - {{class.example_b}} = {{class.example_wrong_answer}}."
)


class Voice:
    """Counts what is said; returns a short tone so the encoder has real audio."""

    def __init__(self) -> None:
        self.said: list[str] = []

    def synthesize(self, text: str, lang: str, voice: object) -> bytes:
        self.said.append(text)
        return speech_audio.tone(0.5, 300)


def fake_join(clips: list[bytes], *, fmt: str = "ogg", kbps: int = 16, gap_s: float = 0.6):  # type: ignore[no-untyped-def]
    return b"OggS" + b"x" * 1500 * len(clips), 1.0 * len(clips)


def approve_all(
    db: Session, language: str = "en", lesson_script: str = TAGGED
) -> versions.ContentVersion:
    track = load_track("sub-sfl.v1")
    for day in range(1, 7):
        part = TrackPart(kind="lesson", day=day, script=lesson_script)
        ctx = CallContext(mode="stub", client=FakeClient([part, PASS]))  # type: ignore[arg-type]
        item = drafting.store_draft(
            db, draft_part(track, "lesson", day, language, context=ctx), track
        )
        assert item is not None
        review.approve(db, item.item_id, *COACH)
    model = TrackPart(kind="model_lesson", day=0, script=MODEL)
    ctx = CallContext(mode="stub", client=FakeClient([model, PASS]))  # type: ignore[arg-type]
    item = drafting.store_draft(
        db, draft_part(track, "model_lesson", 0, language, context=ctx), track
    )
    assert item is not None
    review.approve(db, item.item_id, *COACH)
    return review.assemble_track_version(db, track, [language], *COACH)


def switched_on(db: Session) -> versions.ContentVersion:
    v = approve_all(db)
    versions.coach_approve(db, v.id, *COACH)
    return versions.officer_activate(db, v.id, *OFFICER)


@pytest.fixture
def store() -> LocalBlobStore:
    return LocalBlobStore(b"audio-secret")


@pytest.fixture(autouse=True)
def quick_join(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("real_audio") is None:
        monkeypatch.setattr(publish, "join_to_file", fake_join)


def sub_sfl_cohort() -> str:
    return publish.cohorts_for_error("SUB-SFL")[0]


def test_class_numbers_come_from_the_cohorts_classes_by_code() -> None:
    cohort = sub_sfl_cohort()
    values = publish.cohort_values(cohort, "SUB-SFL", example=(52, 29))
    block = publish.block()
    classes = next(c for c in block["cohorts"] if c["cohort_id"] == cohort)["class_ids"]
    rows = [a for a in block["assignments"] if a["class_id"] in classes and a["track"] == "SUB-SFL"]
    assert values["class.count_showing"] == str(sum(r["children_showing"] for r in rows))
    assert values["class.children_checked"] == str(sum(r["children_checked"] for r in rows))
    assert values["class.example_wrong_answer"] == "37"


def test_a_cohort_for_another_error_is_refused() -> None:
    other = publish.cohorts_for_error("ADD-NOCARRY")[0]
    with pytest.raises(versions.BadState):
        publish.cohort_values(other, "SUB-SFL", example=(52, 29))


def test_content_that_is_not_switched_on_is_never_published(
    db: Session, store: LocalBlobStore
) -> None:
    v = approve_all(db)  # assembled and in review: neither key turned yet
    voice = Voice()
    with pytest.raises(versions.BadState):
        publish.publish_version(db, v.id, sub_sfl_cohort(), store=store, speech=voice)  # type: ignore[arg-type]
    versions.coach_approve(db, v.id, *COACH)  # one key is still not enough
    with pytest.raises(versions.BadState):
        publish.publish_version(db, v.id, sub_sfl_cohort(), store=store, speech=voice)  # type: ignore[arg-type]
    assert voice.said == [] and store.keys() == []


def test_an_active_version_is_voiced_once_per_lesson_and_reused(
    db: Session, store: LocalBlobStore
) -> None:
    v = switched_on(db)
    voice = Voice()
    first = publish.publish_version(db, v.id, sub_sfl_cohort(), store=store, speech=voice)  # type: ignore[arg-type]
    lessons = [p for p in first["parts"] if p["kind"] == "lesson"]
    assert len(lessons) == 6 and all(p["audio_key"] for p in lessons)
    said = len(voice.said)
    assert said > 0
    again = publish.publish_version(db, v.id, sub_sfl_cohort(), store=store, speech=voice)  # type: ignore[arg-type]
    assert len(voice.said) == said  # same words, same voice: nothing is voiced twice
    assert [p["audio_key"] for p in again["parts"]] == [p["audio_key"] for p in first["parts"]]


def test_the_spoken_text_has_the_cohorts_numbers_and_no_tags_or_slots(
    db: Session, store: LocalBlobStore
) -> None:
    v = switched_on(db)
    voice = Voice()
    manifest = publish.publish_version(db, v.id, sub_sfl_cohort(), store=store, speech=voice)  # type: ignore[arg-type]
    values = publish.cohort_values(sub_sfl_cohort(), "SUB-SFL", example=(52, 29))
    text = manifest["parts"][0]["script"]
    assert f"{values['class.count_showing']} of {values['class.children_checked']} children" in text
    assert "{{" not in text and "[child" not in text
    assert "52 - 29 = 37" in text  # the child's mistake, said as she says it
    assert all("[child" not in s and "{{" not in s for s in voice.said)


def test_the_manifest_lists_what_the_lesson_screens_and_the_bot_need(
    db: Session, store: LocalBlobStore
) -> None:
    v = switched_on(db)
    manifest = publish.publish_version(db, v.id, sub_sfl_cohort(), store=store, speech=Voice())  # type: ignore[arg-type]
    assert manifest["track_id"] == "sub-sfl.v1" and manifest["version"] == v.version
    assert manifest["simulated"] is True
    lesson = manifest["parts"][0]
    for key in (
        "id",
        "kind",
        "day",
        "language",
        "audio_key",
        "bytes",
        "seconds",
        "sha256",
        "script",
        "badge",
    ):
        assert key in lesson, key
    assert lesson["badge"] == "checked_reviewed"
    assert manifest["reviewed"]["role"] == "coach" and manifest["reviewed"]["at"]
    assert manifest["activated"]["role"] == "officer" and manifest["activated"]["at"]
    model = next(p for p in manifest["parts"] if p["kind"] == "model_lesson")
    assert model["audio_key"] is None and model["script"]  # a script she reads; no audio
    stored = db.execute(select(TrackManifest)).scalar_one()
    assert stored.cohort_id == sub_sfl_cohort() and stored.body["parts"] == manifest["parts"]
    assert db.execute(select(ContentAudit).where(ContentAudit.action == "publish")).scalar_one()


def test_a_filled_lesson_that_breaks_the_arithmetic_is_not_published(
    db: Session, store: LocalBlobStore
) -> None:
    # The model did the class arithmetic itself: right for the sample numbers the draft gate used,
    # wrong for this cohort. Once the real numbers are in, code catches it before any voicing.
    values = publish.cohort_values(sub_sfl_cohort(), "SUB-SFL", example=(52, 29))
    assert int(values["class.children_checked"]) - int(values["class.count_showing"]) != 17
    sneaky = GOOD + " So {{class.children_checked}} - {{class.count_showing}} = 17 got it right."
    v = approve_all(db, lesson_script=sneaky)
    versions.coach_approve(db, v.id, *COACH)
    versions.officer_activate(db, v.id, *OFFICER)
    voice = Voice()
    with pytest.raises(publish.PublishBlocked):
        publish.publish_version(db, v.id, sub_sfl_cohort(), store=store, speech=voice)  # type: ignore[arg-type]
    assert voice.said == [] and store.keys() == []


@pytest.mark.real_audio
@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_a_voice_lesson_stays_within_the_data_budget() -> None:
    clip = speech_audio.tone(30.0, 220)  # 30 seconds of sound, as one lesson chunk
    data, seconds = publish.encode([clip] * 10)  # about 5 minutes with the pauses
    assert seconds > 280
    per_five_minutes = len(data) / seconds * 300
    assert per_five_minutes <= 600_000, per_five_minutes  # ~0.6 MB per 5 minutes (OGG/Opus)
    assert data[:4] == b"OggS"
