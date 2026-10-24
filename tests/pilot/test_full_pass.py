"""One pass over a synthetic class, end to end: upload, read, three scripts, approval, audio,
download, share. Speech is the stub and the models are stand-ins; a live speech check is behind a
flag (PILOT_LIVE_SPEECH=1) because it spends Sarvam credit and needs a working key."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import select

from services.api.db import (
    PilotAudio,
    PilotAudit,
    PilotClassCount,
    PilotShare,
    PilotSheet,
    SpeechCall,
)
from tests.pilot.conftest import Env, answers, photo, synthetic_class, upload


@pytest.mark.real_audio  # the one end-to-end test that voices and encodes with ffmpeg for real
def test_a_coordinator_can_go_from_photos_to_shared_audio(env: Env) -> None:
    # 1. the coordinator signs in and uploads 20 sheets (12 children make the SUB-SFL mistake)
    rows = synthetic_class(20, 12)
    for i, row in enumerate(rows):
        assert upload(env, photo(i), read=row)["status"] == "read"
    summary = env.client.get("/api/pilot/sheets/summary", headers=env.h("ops")).json()
    assert (summary["uploaded"], summary["read"], summary["needs_look"]) == (20, 20, 0)

    # 2. the counts the engine got from those reads
    with env.factory() as db:
        counts = db.execute(select(PilotClassCount)).scalar_one()
        assert (counts.children_checked, counts.counts) == (20, {"SUB-SFL": 12})

    # 3. she asks for three English lessons (the default) in the default voice
    cfg = env.client.get("/api/pilot/config", headers=env.h("ops")).json()
    assert cfg["audio_count"] == 3
    made = env.client.post(
        "/api/pilot/audio/generate",
        json={"language": "en", "voice": cfg["voice_default"]},
        headers=env.h("ops"),
    ).json()
    assert made == {"made": 3}
    page = env.client.get("/api/pilot/audio", headers=env.h("ops")).json()
    assert [c["status"] for c in page["cards"]] == ["needs_review"] * 3
    assert env.audio.keys() == []  # nothing published yet

    # 4. the coach reads each script and approves it; the lessons are voiced and published
    for card in page["cards"]:
        assert env.client.get("/api/pilot/audio", headers=env.h("rev")).status_code == 200
        res = env.client.post(f"/api/pilot/audio/{card['id']}/approve", headers=env.h("rev"))
        assert res.status_code == 200
    ready = env.client.get("/api/pilot/audio", headers=env.h("ops")).json()["cards"]
    assert [c["status"] for c in ready] == ["audio_ready"] * 3
    assert len(env.audio.keys()) == 3 and env.sheets.keys() != env.audio.keys()

    # 5. she downloads each file and records who she sent it to
    for card in ready:
        res = env.client.get(f"/api/pilot/audio/{card['id']}/file", headers=env.h("ops"))
        assert res.status_code == 200 and len(res.content) < 1_000_000
        env.client.post(
            f"/api/pilot/audio/{card['id']}/shares",
            json={"teacher_refs": summary["teachers"]},
            headers=env.h("ops"),
        )
    with env.factory() as db:
        assert len(db.execute(select(PilotShare)).all()) == 3
        actions = {a.action for a in db.execute(select(PilotAudit)).scalars()}
        assert {"audio.drafted", "audio.approved", "audio.published", "audio.shared"} <= actions
        assert all(a.status == "audio_ready" for a in db.execute(select(PilotAudio)).scalars())
        # speech spend is logged as metadata only
        assert all(r.characters >= 0 for r in db.execute(select(SpeechCall)).scalars())


def test_a_mixed_class_makes_lessons_for_the_commonest_error_only(env: Env) -> None:
    from engine.bugs import add_nocarry
    from engine.forms import FORM_A

    def add_child() -> list[str]:
        row = answers(False)
        for i in FORM_A.items[2:5]:
            row[i.n - 1] = str(min(add_nocarry(i.a, i.b)))
        return row

    for i in range(16):
        upload(env, photo(i), read=add_child() if i < 10 else answers(False))
    env.client.post(
        "/api/pilot/audio/generate", json={"language": "en", "voice": "ritu"}, headers=env.h("ops")
    )
    cards = env.client.get("/api/pilot/audio", headers=env.h("ops")).json()["cards"]
    assert {c["status"] for c in cards} == {"needs_review"}
    assert "10 of 16 children" in cards[0]["script"] and "carried ten" in cards[0]["script"]


def test_uploads_do_not_touch_the_unrelated_tables(env: Env) -> None:
    upload(env, photo(1), read=answers(True))
    with env.factory() as db:
        assert db.execute(select(PilotSheet)).scalar_one().status == "read"
        assert db.execute(select(PilotAudio)).first() is None


@pytest.mark.skipif(
    os.environ.get("PILOT_LIVE_SPEECH") != "1", reason="live Sarvam check: set PILOT_LIVE_SPEECH=1"
)
def test_live_speech_voices_one_short_line() -> None:  # pragma: no cover - needs a working key
    from services.speech.audio import join_to_file
    from services.speech.service import default_service
    from services.speech.voices import Voice

    svc = default_service()
    clip = svc.synthesize("Lesson one. A short check of the voice.", "en", Voice("ritu", 1.0, 1.0))
    data, seconds = join_to_file([clip])
    assert seconds > 1 and 0 < len(data) < 200_000
