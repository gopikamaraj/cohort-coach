"""P09 T12: the model run. About three minutes of the track's move done well with five simulated
children: teacher lines come only from the approved model-lesson script, children's lines from the
engine and call 1. Rendered with a fixed seed and frozen; the coach approves it (gate 3); only then
is it voiced and published, labelled simulated. A new render needs a new approved script version."""

from __future__ import annotations

import re
import shutil

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.calls.c05_track_draft import draft_part
from ai.client import CallContext
from ai.schemas import TrackPart
from services.api.db import ContentAudit, ReviewItem
from services.content import drafting, model_run, publish, review, versions
from services.content.track import load_track
from services.pilot.storage import LocalBlobStore
from services.practice.stub_client import StubClient
from services.speech import audio as speech_audio
from tests.ai.test_c05_track_draft import PASS
from tests.support_ai import FakeClient

COACH = ("coach-demo", "coach")
OFFICER = ("officer-demo", "officer")

SCRIPT = (
    "Teacher says: Today we will take 52 - 29 with bundles of ten. "
    "Child says: I take the smaller digit from the bigger one. "
    "Teacher says: Tell me how you got your answer. What did you do first? "
    "Teacher says: Show me with the bundles. We have 5 bundles and 2 loose sticks. "
    "Teacher says: We cannot take 9 sticks from 2. Open a bundle to get ten loose sticks. "
    "Teacher says: Now take away 9 loose sticks. Then take away 2 bundles. "
    "Teacher says: Check it by adding back. 23 + 29 = 52. "
    "Teacher says: Well done. You checked your own answer."
)


def ctx() -> CallContext:
    return CallContext(mode="stub", client=StubClient())


def approved_script(db: Session, script: str = SCRIPT, language: str = "en") -> ReviewItem:
    track = load_track("sub-sfl.v1")
    part = TrackPart(kind="model_lesson", day=0, script=script)
    c = CallContext(mode="stub", client=FakeClient([part, PASS]))  # type: ignore[arg-type]
    item = drafting.store_draft(
        db, draft_part(track, "model_lesson", 0, language, context=c), track
    )
    assert item is not None
    review.approve(db, item.item_id, *COACH)
    row = db.get(ReviewItem, item.item_id)
    assert row is not None
    return row


def test_a_script_is_split_into_teacher_and_child_lines() -> None:
    lines = model_run.parse_script(SCRIPT)
    assert [x.speaker for x in lines].count("teacher") == 7
    assert [x.speaker for x in lines].count("child") == 1
    assert lines[0].text.startswith("Today we will take")


def test_moves_are_assigned_by_code_from_the_tracks_strategy_order() -> None:
    track = load_track("sub-sfl.v1")
    moves = model_run.assign_moves(7, track.model_strategies)
    assert moves[0] == "pose_problem" and moves[-1] == "praise"
    assert moves[1:-1] == [
        "show_bundles",
        "exchange_ten",
        "check_back",
        "show_bundles",
        "exchange_ten",
    ]
    assert len(model_run.assign_moves(2, track.model_strategies)) == 2


def test_a_run_renders_from_an_approved_script_with_teacher_lines_only_from_it(db: Session) -> None:
    item = approved_script(db)
    run = model_run.render(db, item.item_id, seed=7, context=ctx())
    assert run.content["kind"] == "model_run" and run.content["simulated"] is True
    teacher = [t["teacher"]["line"] for t in run.content["turns"]]
    expected = [x.text for x in model_run.parse_script(SCRIPT) if x.speaker == "teacher"]
    assert len(teacher) == 7 and teacher == expected  # not one word of her own
    assert run.status == "pending" and run.content_type == "model_run"
    assert "simulated" in run.content["caption"].lower()


def test_five_simulated_children_and_every_number_is_the_engines(db: Session) -> None:
    item = approved_script(db)
    run = model_run.render(db, item.item_id, seed=7, context=ctx())
    turns = run.content["turns"]
    assert len(run.content["children"]) == 5
    for t in turns:
        child = t["child"]
        digits = {int(n) for n in re.findall(r"\d+", child["text"])}
        assert digits <= set(t["engine_numbers"]), (child["text"], t["engine_numbers"])


def test_the_same_seed_gives_the_same_frozen_run(db: Session, tmp_path) -> None:  # type: ignore[no-untyped-def]
    first = model_run.render(db, approved_script(db).item_id, seed=7, context=ctx())
    second = model_run.render_dry(db, approved_script(db).item_id, seed=7, context=ctx())
    assert first.content["turns"] == second["turns"]


def test_only_an_approved_script_can_be_rendered(db: Session) -> None:
    track = load_track("sub-sfl.v1")
    part = TrackPart(kind="model_lesson", day=0, script=SCRIPT)
    c = CallContext(mode="stub", client=FakeClient([part, PASS]))  # type: ignore[arg-type]
    item = drafting.store_draft(db, draft_part(track, "model_lesson", 0, "en", context=c), track)
    assert item is not None  # still waiting for the coach
    with pytest.raises(versions.BadState):
        model_run.render(db, item.item_id, seed=7, context=ctx())
    review.approve(db, item.item_id, *COACH)
    row = db.get(ReviewItem, item.item_id)
    assert row is not None
    row.content = {**row.content, "kind": "lesson"}  # a voice lesson is not a model-lesson script
    db.commit()
    with pytest.raises(versions.BadState):
        model_run.render(db, item.item_id, seed=7, context=ctx())


def test_a_new_render_needs_a_new_approved_script_version(db: Session) -> None:
    item = approved_script(db)
    model_run.render(db, item.item_id, seed=7, context=ctx())
    with pytest.raises(versions.BadState) as err:
        model_run.render(db, item.item_id, seed=8, context=ctx())  # same words, same version
    assert "new approved script version" in str(err.value)
    newer = approved_script(db, script=SCRIPT + " Teacher says: Thank you, everyone.")
    assert model_run.render(db, newer.item_id, seed=7, context=ctx()).status == "pending"


def test_the_coach_approves_or_returns_it_and_each_step_is_audited(db: Session, tmp_path) -> None:  # type: ignore[no-untyped-def]
    run = model_run.render(db, approved_script(db).item_id, seed=7, context=ctx())
    with pytest.raises(versions.NotAllowed):
        model_run.approve(db, run.item_id, *OFFICER)
    done = model_run.approve(db, run.item_id, *COACH)
    assert done.status == "approved" and done.badge == "checked_reviewed"
    other = model_run.render(
        db,
        approved_script(db, script=SCRIPT + " Teacher says: Goodbye.").item_id,
        seed=7,
        context=ctx(),
    )
    model_run.reject(db, other.item_id, *COACH, reason="tone_issue", pending_dir=tmp_path)
    actions = [
        a.action
        for a in db.execute(
            select(ContentAudit).where(ContentAudit.content_type == "model_run")
        ).scalars()
    ]
    assert actions == ["render", "approve", "render", "reject"]


class Spy:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def synthesize(self, text: str, lang: str, voice: object) -> bytes:
        self.calls.append((text, lang, getattr(voice, "speaker", "?")))
        return speech_audio.tone(0.4, 260)


def fake_join(clips: list[bytes], *, fmt: str = "ogg", kbps: int = 16, gap_s: float = 0.6):  # type: ignore[no-untyped-def]
    return b"OggS" + b"x" * 900 * len(clips), 2.0 * len(clips)


def approved_run(db: Session) -> ReviewItem:
    run = model_run.render(db, approved_script(db).item_id, seed=7, context=ctx())
    model_run.approve(db, run.item_id, *COACH)
    row = db.get(ReviewItem, run.item_id)
    assert row is not None
    return row


def test_an_unapproved_run_is_never_voiced(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(model_run, "join_to_file", fake_join)
    run = model_run.render(db, approved_script(db).item_id, seed=7, context=ctx())
    spy = Spy()
    with pytest.raises(versions.BadState):
        model_run.voice(db, run.item_id, store=LocalBlobStore(b"s"), speech=spy)  # type: ignore[arg-type]
    assert spy.calls == []


def test_an_approved_run_is_voiced_with_an_adult_teacher_and_five_child_voices(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(model_run, "join_to_file", fake_join)
    run = approved_run(db)
    spy, store = Spy(), LocalBlobStore(b"s")
    out = model_run.voice(db, run.item_id, store=store, speech=spy)  # type: ignore[arg-type]
    speakers = {s for _, _, s in spy.calls}
    assert "ritu" in speakers  # the adult teacher voice
    assert len(speakers - {"ritu"}) >= 2  # the children sound different from her and each other
    assert all("[child" not in t and "{{" not in t for t, _, _ in spy.calls)
    assert out["audio"]["key"] in store.keys() and out["audio"]["bytes"] > 0
    again = model_run.voice(db, run.item_id, store=store, speech=spy)  # type: ignore[arg-type]
    assert again["audio"]["sha256"] == out["audio"]["sha256"] and len(spy.calls) == len(
        [c for c in spy.calls]
    )


def test_a_run_is_voiced_once(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(model_run, "join_to_file", fake_join)
    run = approved_run(db)
    spy, store = Spy(), LocalBlobStore(b"s")
    model_run.voice(db, run.item_id, store=store, speech=spy)  # type: ignore[arg-type]
    said = len(spy.calls)
    model_run.voice(db, run.item_id, store=store, speech=spy)  # type: ignore[arg-type]
    assert len(spy.calls) == said


def test_the_track_manifest_lists_the_voiced_run_labelled_simulated(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.content.test_publish import approve_all, switched_on

    monkeypatch.setattr(model_run, "join_to_file", fake_join)
    monkeypatch.setattr(publish, "join_to_file", fake_join)
    v = switched_on(db)
    track = load_track("sub-sfl.v1")
    manifest = publish.publish_version(
        db,
        v.id,
        publish.cohorts_for_error("SUB-SFL")[0],
        store=LocalBlobStore(b"s"),
        speech=Spy(),  # type: ignore[arg-type]
    )
    assert not [p for p in manifest["parts"] if p["kind"] == "model_run"]  # none approved yet
    # the script in the version is the one the run must be built from
    script_id = next(p["id"] for p in manifest["parts"] if p["kind"] == "model_lesson")
    run = model_run.render(db, script_id, seed=7, context=ctx())
    model_run.approve(db, run.item_id, *COACH)
    store = LocalBlobStore(b"s")
    model_run.voice(db, run.item_id, store=store, speech=Spy())  # type: ignore[arg-type]
    again = publish.publish_version(
        db,
        v.id,
        publish.cohorts_for_error("SUB-SFL")[0],
        store=store,
        speech=Spy(),  # type: ignore[arg-type]
    )
    entry = next(p for p in again["parts"] if p["kind"] == "model_run")
    assert entry["audio_key"] and entry["caption"].lower().startswith("simulated")
    assert entry["language"] == "en" and entry["badge"] == "checked_reviewed"
    assert track.id == again["track_id"] and approve_all  # imported helpers are in use


@pytest.mark.real_audio
@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_a_three_minute_run_stays_within_the_data_budget() -> None:
    clip = speech_audio.tone(12.0, 220)
    data, seconds = model_run.encode([clip] * 15)  # about 3 minutes with the pauses
    assert seconds > 170
    per_three_minutes = len(data) / seconds * 180
    assert per_three_minutes <= 350_000, per_three_minutes  # ~0.35 MB per 3 minutes
