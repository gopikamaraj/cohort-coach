"""Page 2, Intervention audio: the count, the chain, approval before publishing, sharing."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from sqlalchemy import select

from services.api.db import PilotAudio, PilotAudit, PilotShare, ReviewDecision, ReviewItem
from services.pilot import audio as audio_mod
from services.speech import audio as speech_audio
from services.speech.sarvam import SpeechError
from tests.pilot.conftest import Env

GEN = {"language": "en", "voice": "ritu"}


def generate(env: Env, **over: object) -> dict:  # type: ignore[type-arg]
    res = env.client.post("/api/pilot/audio/generate", json={**GEN, **over}, headers=env.h("ops"))
    assert res.status_code == 200, res.text
    return res.json()


def cards(env: Env, who: str = "ops", language: str | None = None) -> list[dict]:  # type: ignore[type-arg]
    url = "/api/pilot/audio" + (f"?language={language}" if language else "")
    return env.client.get(url, headers=env.h(who)).json()["cards"]


def approve(env: Env, card_id: str, who: str = "rev"):  # type: ignore[no-untyped-def]
    return env.client.post(f"/api/pilot/audio/{card_id}/approve", headers=env.h(who))


# ---- the count -------------------------------------------------------------------------------


def test_the_audio_count_defaults_to_three(env: Env) -> None:
    cfg = env.client.get("/api/pilot/config", headers=env.h("ops")).json()
    assert cfg["audio_count"] == 3 and cfg["audio_max"] == 10


@pytest.mark.parametrize("bad", [0, -1, 11, 100])
def test_counts_outside_one_to_the_maximum_are_rejected(env: Env, bad: int) -> None:
    res = env.client.put(
        "/api/pilot/config/audio-count", json={"audio_count": bad}, headers=env.h("ops")
    )
    assert res.status_code == 422
    assert env.client.get("/api/pilot/config", headers=env.h("ops")).json()["audio_count"] == 3


def test_the_maximum_comes_from_pilot_audio_max(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PILOT_AUDIO_MAX", "5")

    def put(n: int) -> int:
        res = env.client.put(
            "/api/pilot/config/audio-count", json={"audio_count": n}, headers=env.h("ops")
        )
        return res.status_code

    assert (put(5), put(6), put(1)) == (200, 422, 200)
    monkeypatch.setenv("PILOT_AUDIO_MAX", "7")
    assert put(7) == 200


def test_changing_the_count_is_audit_logged(env: Env) -> None:
    env.client.put("/api/pilot/config/audio-count", json={"audio_count": 6}, headers=env.h("ops"))
    with env.factory() as db:
        row = db.execute(
            select(PilotAudit).where(PilotAudit.action == "config.audio_count")
        ).scalar_one()
        assert row.actor == "ops" and row.detail == {"before": 3, "after": 6}


def test_lowering_the_count_deactivates_cards_and_never_deletes_them(seeded: Env) -> None:
    generate(seeded)
    assert [c["active"] for c in cards(seeded)] == [True, True, True]
    seeded.client.put(
        "/api/pilot/config/audio-count", json={"audio_count": 1}, headers=seeded.h("ops")
    )
    after = cards(seeded)
    assert [(c["slot"], c["active"]) for c in after] == [(1, True), (2, False), (3, False)]
    with seeded.factory() as db:
        assert len(db.execute(select(PilotAudio)).all()) == 3
    seeded.client.put(
        "/api/pilot/config/audio-count", json={"audio_count": 3}, headers=seeded.h("ops")
    )
    assert all(c["active"] for c in cards(seeded))  # raising it brings them back as they were


# ---- the chain -------------------------------------------------------------------------------


def test_with_no_sheets_read_generate_says_so(env: Env) -> None:
    res = env.client.post("/api/pilot/audio/generate", json=GEN, headers=env.h("ops"))
    assert res.status_code == 409 and res.json()["detail"] == {"reason": "no_sheets"}
    page = env.client.get("/api/pilot/audio", headers=env.h("ops")).json()
    assert page["cards"] == [] and page["sheets_read"] == 0


def test_generate_makes_one_checked_card_per_slot_and_waits_for_review(seeded: Env) -> None:
    assert generate(seeded)["made"] == 3
    got = cards(seeded)
    assert [c["slot"] for c in got] == [1, 2, 3]
    assert {c["status"] for c in got} == {"needs_review"}
    assert all(c["language"] == "en" and c["voice"] == "ritu" and c["version"] == 1 for c in got)
    assert "12 of 20 children" in got[0]["script"]  # the counts came from the read sheets
    assert seeded.models.checks == 3  # call 7 ran once per slot
    with seeded.factory() as db:
        items = db.execute(select(ReviewItem)).scalars().all()
        assert len(items) == 3 and {i.status for i in items} == {"pending"}
        assert {i.badge for i in items} == {"checked"}


def test_generating_again_from_the_same_counts_does_not_pay_for_the_checker_twice(
    seeded: Env,
) -> None:
    generate(seeded)
    assert generate(seeded)["made"] == 0
    assert seeded.models.checks == 3
    assert generate(seeded, force=True)["made"] == 3
    assert {c["version"] for c in cards(seeded)} == {2}


def test_a_card_whose_checker_says_no_fails_and_never_reaches_review(seeded: Env) -> None:
    seeded.models.fail_checks = True
    generate(seeded)
    got = cards(seeded)
    assert {c["status"] for c in got} == {"failed"}
    with seeded.factory() as db:
        assert db.execute(select(ReviewItem)).first() is None
    assert approve(seeded, got[0]["id"]).status_code == 409


def test_new_sheets_make_older_cards_stale(seeded: Env) -> None:
    generate(seeded)
    assert not any(c["stale"] for c in cards(seeded))
    from tests.pilot.conftest import answers, photo, upload

    upload(seeded, photo(99), read=answers(True))
    assert all(c["stale"] for c in cards(seeded))


def test_regenerate_keeps_the_old_versions(seeded: Env) -> None:
    generate(seeded)
    first = cards(seeded)[0]
    res = seeded.client.post(f"/api/pilot/audio/{first['id']}/regenerate", headers=seeded.h("ops"))
    assert res.status_code == 200
    card = cards(seeded)[0]
    assert card["version"] == 2 and card["id"] != first["id"]
    assert [v["version"] for v in card["versions"]] == [2, 1]
    with seeded.factory() as db:
        assert db.get(PilotAudio, first["id"]) is not None


def test_the_language_and_voice_must_be_listed(seeded: Env) -> None:
    for bad in ({"language": "fr"}, {"voice": "someone-else"}):
        res = seeded.client.post(
            "/api/pilot/audio/generate", json={**GEN, **bad}, headers=seeded.h("ops")
        )
        assert res.status_code == 422


def test_each_language_has_its_own_cards(seeded: Env) -> None:
    generate(seeded)
    generate(seeded, language="ta", voice="priya")
    assert len(cards(seeded)) == 6
    ta = cards(seeded, language="ta")
    assert len(ta) == 3 and ta[0]["file_name"] == "cc-pilot-slot1-ta.m4a"
    assert "குழந்தைகளில்" in ta[0]["script"]


# ---- approval before anything is published ----------------------------------------------------


def test_nothing_reaches_the_published_bucket_before_approval(seeded: Env) -> None:
    generate(seeded)
    assert seeded.audio.keys() == []
    for c in cards(seeded):
        assert c["status"] == "needs_review"
    # the coordinator and the officer cannot approve, and render refuses an unapproved card
    first = cards(seeded)[0]["id"]
    assert approve(seeded, first, "ops").status_code == 403
    assert approve(seeded, first, "off").status_code == 403
    assert (
        seeded.client.post(f"/api/pilot/audio/{first}/render", headers=seeded.h("ops")).status_code
        == 409
    )
    assert seeded.audio.keys() == []
    assert approve(seeded, first).status_code == 200
    assert seeded.audio.keys() == []  # approving the words makes no audio and spends no credit
    assert (
        seeded.client.post(f"/api/pilot/audio/{first}/render", headers=seeded.h("ops")).status_code
        == 200
    )
    assert seeded.audio.keys() == [
        f"pilot-audio/{first}.m4a"
    ]  # only the approved one, and only now
    with seeded.factory() as db:
        decision = db.execute(select(ReviewDecision)).scalar_one()
        assert decision.decision == "approve" and decision.reviewer_role == "reviewer"
        assert db.get(ReviewItem, db.get(PilotAudio, first).review_item_id).status == "approved"  # type: ignore[union-attr]


def test_approval_publishes_the_text_and_make_audio_voices_it(
    seeded: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    spoken: list[str] = []
    monkeypatch.setattr(
        seeded.speech, "synthesize", lambda text, lang, voice: spoken.append(text) or b"clip"
    )
    generate(seeded)
    first = cards(seeded)[0]
    assert approve(seeded, first["id"]).status_code == 200
    approved = cards(seeded)[0]
    assert approved["status"] == "approved" and approved["shareable"] and not approved["ready"]
    assert spoken == []  # nothing was voiced
    assert (
        seeded.client.post(
            f"/api/pilot/audio/{first['id']}/render", headers=seeded.h("ops")
        ).status_code
        == 200
    )
    assert spoken  # the voice was called only now
    ready = cards(seeded)[0]
    assert ready["status"] == "audio_ready" and ready["ready"] and ready["duration_s"] > 0
    assert 0 < ready["bytes"] < 1_000_000
    assert seeded.audio.types[f"pilot-audio/{first['id']}.m4a"] == "audio/mp4"


def test_a_failed_voice_leaves_the_lesson_approved_and_can_be_retried(
    seeded: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    generate(seeded)
    first = cards(seeded)[0]["id"]
    real = seeded.speech.synthesize

    def down(*a, **k):  # type: ignore[no-untyped-def]
        raise SpeechError("unavailable", 503, "down")

    monkeypatch.setattr(seeded.speech, "synthesize", down)
    approve(seeded, first)
    seeded.client.post(f"/api/pilot/audio/{first}/render", headers=seeded.h("ops"))
    card = cards(seeded)[0]
    assert card["status"] == "failed" and card["note"] == "audio:unavailable"
    assert seeded.audio.keys() == []
    monkeypatch.setattr(seeded.speech, "synthesize", real)
    assert (
        seeded.client.post(f"/api/pilot/audio/{first}/render", headers=seeded.h("ops")).status_code
        == 200
    )
    assert cards(seeded)[0]["status"] == "audio_ready"


def test_returning_a_lesson_records_the_reason_and_feeds_the_checker(
    seeded: Env, tmp_path: Path
) -> None:
    generate(seeded)
    first = cards(seeded)[0]["id"]
    res = seeded.client.post(
        f"/api/pilot/audio/{first}/reject", json={"reason": "tone_issue"}, headers=seeded.h("rev")
    )
    assert res.status_code == 200
    bad = seeded.client.post(
        f"/api/pilot/audio/{first}/reject", json={"reason": "because"}, headers=seeded.h("rev")
    )
    assert bad.status_code == 422
    with seeded.factory() as db:
        decision = db.execute(select(ReviewDecision)).scalar_one()
        assert decision.decision == "reject" and decision.reason == "tone_issue"
    saved = list((tmp_path / "rejections").glob("*.yaml"))
    assert len(saved) == 1 and "tone_issue" in saved[0].read_text(encoding="utf-8")
    assert cards(seeded)[0]["status"] == "failed"
    assert seeded.audio.keys() == []


# ---- download and share -----------------------------------------------------------------------


def ready_card(env: Env) -> dict:  # type: ignore[type-arg]
    generate(env)
    for c in cards(env):
        assert approve(env, c["id"]).status_code == 200
        assert (
            env.client.post(f"/api/pilot/audio/{c['id']}/render", headers=env.h("ops")).status_code
            == 200
        )
    return cards(env)[0]


def test_download_and_share_are_unavailable_for_unapproved_audio(seeded: Env) -> None:
    generate(seeded)
    first = cards(seeded)[0]
    assert first["ready"] is False
    h = seeded.h("ops")
    assert seeded.client.get(f"/api/pilot/audio/{first['id']}/file", headers=h).status_code == 409
    assert seeded.client.get(f"/api/pilot/audio/{first['id']}/link", headers=h).status_code == 409
    res = seeded.client.post(
        f"/api/pilot/audio/{first['id']}/shares", json={"teacher_refs": ["T-101"]}, headers=h
    )
    assert res.status_code == 409
    with seeded.factory() as db:
        assert db.execute(select(PilotShare)).first() is None


def test_an_approved_file_downloads_with_a_name_that_holds_only_slot_and_language(
    seeded: Env,
) -> None:
    card = ready_card(seeded)
    res = seeded.client.get(f"/api/pilot/audio/{card['id']}/file", headers=seeded.h("ops"))
    assert res.status_code == 200 and res.headers["content-type"] == "audio/mp4"
    assert 'filename="cc-pilot-slot1-en.m4a"' in res.headers["content-disposition"]
    assert res.content[4:8] == b"ftyp"  # a real MP4/M4A container
    for c in cards(seeded):
        assert c["file_name"] in {
            "cc-pilot-slot1-en.m4a",
            "cc-pilot-slot2-en.m4a",
            "cc-pilot-slot3-en.m4a",
        }
    # the coach and officer can listen too
    for who in ("rev", "off"):
        assert (
            seeded.client.get(
                f"/api/pilot/audio/{card['id']}/file", headers=seeded.h(who)
            ).status_code
            == 200
        )


def test_file_names_hold_no_school_or_teacher_name(seeded: Env) -> None:
    card = ready_card(seeded)
    for text in (card["file_name"], json.dumps(card["versions"])):
        for banned in ("SCH", "T-101", "3A", "ops", "seema"):
            assert banned not in text
    assert audio_mod.file_name.__doc__ and "never a school" in audio_mod.file_name.__doc__


def test_the_mp3_option_renders_an_mp3(seeded: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PILOT_AUDIO_FORMAT", "mp3")
    card = ready_card(seeded)
    assert card["file_name"].endswith(".mp3") and card["mime"] == "audio/mpeg"
    res = seeded.client.get(f"/api/pilot/audio/{card['id']}/file", headers=seeded.h("ops"))
    assert res.content[:3] == b"ID3" or res.content[0] == 0xFF


def test_a_signed_link_expires(seeded: Env) -> None:
    card = ready_card(seeded)
    link = seeded.client.get(f"/api/pilot/audio/{card['id']}/link", headers=seeded.h("ops")).json()
    assert link["expires_in"] == 24 * 3600
    assert seeded.client.get(link["url"]).status_code == 200
    # only the share role can mint one
    assert (
        seeded.client.get(
            f"/api/pilot/audio/{card['id']}/link", headers=seeded.h("rev")
        ).status_code
        == 403
    )
    seeded.clock.now += link["expires_in"] + 1
    assert seeded.client.get(link["url"]).status_code == 403


def test_marking_a_share_writes_rows_and_is_audit_logged(seeded: Env) -> None:
    card = ready_card(seeded)
    res = seeded.client.post(
        f"/api/pilot/audio/{card['id']}/shares",
        json={"teacher_refs": ["T-101", "T-102", "T-101"]},
        headers=seeded.h("ops"),
    )
    assert res.json() == {"recorded": 2}
    with seeded.factory() as db:
        rows = db.execute(select(PilotShare)).scalars().all()
        assert {r.teacher_ref for r in rows} == {"T-101", "T-102"}
        assert all(r.audio_id == card["id"] and r.shared_by == "ops" and r.shared_at for r in rows)
        audit = db.execute(
            select(PilotAudit).where(PilotAudit.action == "audio.shared")
        ).scalar_one()
        assert audit.actor == "ops" and audit.detail["teachers"] == 2
    assert cards(seeded)[0]["shared_with"] == ["T-101", "T-102"]
    for bad in (["Mrs Lakshmi"], [], ["x"]):
        res = seeded.client.post(
            f"/api/pilot/audio/{card['id']}/shares",
            json={"teacher_refs": bad},
            headers=seeded.h("ops"),
        )
        assert res.status_code == 422, bad


def test_an_officer_sees_no_share_log_and_no_small_class_figures(seeded: Env) -> None:
    card = ready_card(seeded)
    seeded.client.post(
        f"/api/pilot/audio/{card['id']}/shares",
        json={"teacher_refs": ["T-101"]},
        headers=seeded.h("ops"),
    )
    page = seeded.client.get("/api/pilot/audio", headers=seeded.h("off")).json()
    assert page["sheets_read"] == 0 and page["classes_read"] == 0  # one class: hidden
    assert all(c["shared_with"] == [] and c["script"] == "" for c in page["cards"])
    coach = seeded.client.get("/api/pilot/audio", headers=seeded.h("rev")).json()
    assert coach["cards"][0]["script"] and coach["cards"][0]["shared_with"] == []
    own = seeded.client.get("/api/pilot/audio", headers=seeded.h("ops")).json()
    assert own["cards"][0]["shared_with"] == ["T-101"]


def test_audio_past_a_lowered_count_cannot_be_downloaded_or_shared(seeded: Env) -> None:
    ready_card(seeded)
    seeded.client.put(
        "/api/pilot/config/audio-count", json={"audio_count": 1}, headers=seeded.h("ops")
    )
    off = next(c for c in cards(seeded) if c["slot"] == 3)
    assert off["active"] is False
    assert (
        seeded.client.get(f"/api/pilot/audio/{off['id']}/file", headers=seeded.h("ops")).status_code
        == 409
    )


def test_a_script_never_carries_a_school_teacher_or_child(seeded: Env) -> None:
    generate(seeded)
    for lang in ("en", "ta"):
        generate(seeded, language=lang, voice="ritu")
    for c in cards(seeded):
        for banned in ("SCH-01", "T-101", "3A"):
            assert banned not in c["script"] and banned not in c["title"]


# ---- the file itself ----------------------------------------------------------------------------


def _noise(seconds: float) -> bytes:
    rng = np.random.default_rng(1)
    samples = (
        (rng.normal(0, 0.3, int(seconds * 24000)) * 32767).clip(-32768, 32767).astype(np.int16)
    )
    return speech_audio._wav_bytes(samples, 24000)


@pytest.mark.parametrize("fmt", ["m4a", "mp3"])
def test_a_three_minute_note_is_mono_and_under_the_size_target(fmt: str) -> None:
    clips = [_noise(60), _noise(60), _noise(60)]  # the worst case for a speech codec: white noise
    data, seconds = speech_audio.join_to_file(clips, fmt=fmt)
    assert 180 < seconds < 184
    assert len(data) < 1_000_000  # the target; WhatsApp's own limit is 16 MB
    assert len(data) < 16 * 1024 * 1024 // 10


def test_a_long_script_is_encoded_smaller_to_stay_under_the_target(
    seeded: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    sizes: list[int] = []
    real = audio_mod.join_to_file

    def spy(clips, *, fmt="m4a", kbps=32, gap_s=0.6):  # type: ignore[no-untyped-def]
        data, seconds = real(clips, fmt=fmt, kbps=kbps, gap_s=gap_s)
        sizes.append(kbps)
        return (data + b"\0" * 1_100_000, seconds) if kbps == 32 else (data, seconds)

    monkeypatch.setattr(audio_mod, "join_to_file", spy)
    generate(seeded)
    card = cards(seeded)[0]
    approve(seeded, card["id"])
    seeded.client.post(f"/api/pilot/audio/{card['id']}/render", headers=seeded.h("ops"))
    assert sizes == [32, 24] and cards(seeded)[0]["bytes"] < 1_000_000


def test_scripts_are_split_at_sentences_for_the_voice() -> None:
    text = "One sentence here. " * 200
    parts = audio_mod.chunks(text, limit=300)
    assert all(len(p) <= 300 for p in parts) and len(parts) > 5
    assert "".join(parts).replace(" ", "") == text.replace(" ", "")
