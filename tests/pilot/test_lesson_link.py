"""The lesson link: approved words first, the voice paid for once, on a teacher's first tap.

A teacher opens an unguessable, expiring link with no sign-in. It shows one approved lesson's
text. Tapping Download audio voices that script (one Sarvam call), keeps the file, and every later
tap reuses it. A daily cap stops a leaked link from spending credit.
"""

from __future__ import annotations

import threading

import pytest
from sqlalchemy import select

from services.api.db import PilotAudio, PilotAudit
from services.pilot import audio as audio_mod
from services.speech.sarvam import SpeechError
from tests.pilot.conftest import Env
from tests.pilot.test_audio import approve, cards, generate

ORIGIN = "https://cohort-coach-pwa.example"


@pytest.fixture
def spoken(seeded: Env, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Every script the voice was asked to say (the stand-in costs nothing)."""
    said: list[str] = []
    monkeypatch.setenv("PWA_ORIGIN", ORIGIN)
    monkeypatch.setattr(
        seeded.speech, "synthesize", lambda text, lang, voice: said.append(text) or b"clip"
    )
    return said


def approved_card(env: Env, slot: int = 0) -> dict:  # type: ignore[type-arg]
    generate(env)
    card = cards(env)[slot]
    assert approve(env, card["id"]).status_code == 200
    return card


def link_token(env: Env, card_id: str) -> str:
    res = env.client.get(f"/api/pilot/audio/{card_id}/lesson-link", headers=env.h("ops"))
    assert res.status_code == 200, res.text
    url = res.json()["url"]
    assert url.startswith(f"{ORIGIN}/#/lesson/")
    return url.rsplit("/", 1)[-1]


def test_a_lesson_link_needs_an_approved_lesson(seeded: Env, spoken: list[str]) -> None:
    generate(seeded)
    first = cards(seeded)[0]["id"]
    res = seeded.client.get(f"/api/pilot/audio/{first}/lesson-link", headers=seeded.h("ops"))
    assert res.status_code == 409
    approve(seeded, first)
    assert (
        seeded.client.get(
            f"/api/pilot/audio/{first}/lesson-link", headers=seeded.h("ops")
        ).status_code
        == 200
    )


def test_only_the_share_role_can_make_a_lesson_link(seeded: Env, spoken: list[str]) -> None:
    card = approved_card(seeded)
    for who, code in (("ops", 200), ("rev", 403), ("off", 403)):
        res = seeded.client.get(f"/api/pilot/audio/{card['id']}/lesson-link", headers=seeded.h(who))
        assert res.status_code == code, who


def test_the_link_shows_the_approved_words_without_signing_in_or_voicing(
    seeded: Env, spoken: list[str]
) -> None:
    card = approved_card(seeded)
    token = link_token(seeded, card["id"])
    res = seeded.client.get(f"/api/pilot/lesson/{token}")  # no Authorization header
    assert res.status_code == 200
    body = res.json()
    assert body["script"] == card["script"] and body["title"] == card["title"]
    assert body["audio_ready"] is False
    assert spoken == []  # opening the page spends nothing
    # nothing about a school, a teacher or a child is in what a teacher is sent
    text = str(body)
    for banned in ("SCH-01", "T-101", "3A", "ops", "seema"):
        assert banned not in text


def test_the_first_tap_voices_once_and_later_taps_reuse_the_file(
    seeded: Env, spoken: list[str]
) -> None:
    card = approved_card(seeded)
    token = link_token(seeded, card["id"])
    first = seeded.client.post(f"/api/pilot/lesson/{token}/audio")
    assert first.status_code == 200, first.text
    made = len(spoken)
    assert made > 0
    assert seeded.audio.keys() == [f"pilot-audio/{card['id']}.m4a"]
    assert seeded.client.get(first.json()["url"]).status_code == 200
    again = seeded.client.post(f"/api/pilot/lesson/{token}/audio")
    assert again.status_code == 200 and len(spoken) == made  # no second call
    assert seeded.client.get(f"/api/pilot/lesson/{token}").json()["audio_ready"] is True
    with seeded.factory() as db:
        who = {
            a.actor
            for a in db.execute(select(PilotAudit)).scalars()
            if a.action == "audio.published"
        }
    assert who == {audio_mod.LINK_ACTOR}


def test_two_taps_at_once_make_the_audio_once(seeded: Env, spoken: list[str]) -> None:
    card = approved_card(seeded)
    token = link_token(seeded, card["id"])
    codes: list[int] = []
    gate = threading.Barrier(2)

    def tap() -> None:
        gate.wait()
        codes.append(seeded.client.post(f"/api/pilot/lesson/{token}/audio").status_code)

    threads = [threading.Thread(target=tap) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert codes == [200, 200]
    assert len(spoken) == len(audio_mod.chunks(card["script"]))  # one voicing, not two


def test_a_made_audio_is_served_when_the_coordinator_made_it_first(
    seeded: Env, spoken: list[str]
) -> None:
    card = approved_card(seeded)
    seeded.client.post(f"/api/pilot/audio/{card['id']}/render", headers=seeded.h("ops"))
    made = len(spoken)
    token = link_token(seeded, card["id"])
    assert seeded.client.post(f"/api/pilot/lesson/{token}/audio").status_code == 200
    assert len(spoken) == made


def test_the_daily_cap_stops_new_voicings_but_not_the_text_or_made_audio(
    seeded: Env, spoken: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PILOT_VOICE_DAILY_MAX", "1")
    generate(seeded)
    for c in cards(seeded)[:2]:
        approve(seeded, c["id"])
    one, two = (link_token(seeded, c["id"]) for c in cards(seeded)[:2])
    assert seeded.client.post(f"/api/pilot/lesson/{one}/audio").status_code == 200
    capped = seeded.client.post(f"/api/pilot/lesson/{two}/audio")
    assert capped.status_code == 429 and "tomorrow" in capped.json()["detail"]
    assert seeded.client.get(f"/api/pilot/lesson/{two}").status_code == 200  # still readable
    assert seeded.client.post(f"/api/pilot/lesson/{one}/audio").status_code == 200  # already made


def test_when_the_voice_is_down_the_text_still_opens(
    seeded: Env, spoken: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    card = approved_card(seeded)
    token = link_token(seeded, card["id"])

    def down(*a: object, **k: object) -> bytes:
        raise SpeechError("unavailable", 503, "down")

    monkeypatch.setattr(seeded.speech, "synthesize", down)
    res = seeded.client.post(f"/api/pilot/lesson/{token}/audio")
    assert res.status_code == 503 and "Read the lesson" in res.json()["detail"]
    assert seeded.client.get(f"/api/pilot/lesson/{token}").status_code == 200
    # the voice comes back: the next tap makes it
    monkeypatch.setattr(seeded.speech, "synthesize", lambda t, lang, v: b"clip")
    assert seeded.client.post(f"/api/pilot/lesson/{token}/audio").status_code == 200


@pytest.mark.parametrize("bad", ["", "x", "a.b", "not-a-token.at-all"])
def test_a_wrong_link_opens_nothing(seeded: Env, spoken: list[str], bad: str) -> None:
    assert seeded.client.get(f"/api/pilot/lesson/{bad or 'x'}").status_code == 404
    assert seeded.client.post(f"/api/pilot/lesson/{bad or 'x'}/audio").status_code == 404
    assert spoken == []


def test_an_edited_or_staff_token_is_not_a_lesson_link(seeded: Env, spoken: list[str]) -> None:
    card = approved_card(seeded)
    token = link_token(seeded, card["id"])
    body, _, sig = token.partition(".")
    assert seeded.client.get(f"/api/pilot/lesson/{body}x.{sig}").status_code == 404
    staff = seeded.h("ops")["Authorization"].split(" ", 1)[1]
    assert seeded.client.get(f"/api/pilot/lesson/{staff}").status_code == 404


def test_a_link_expires(seeded: Env, spoken: list[str]) -> None:
    card = approved_card(seeded)
    token = link_token(seeded, card["id"])
    assert seeded.client.get(f"/api/pilot/lesson/{token}").status_code == 200
    seeded.clock.now += (audio_mod.LESSON_LINK_DAYS * 86400) + 5
    res = seeded.client.get(f"/api/pilot/lesson/{token}")
    assert res.status_code == 404 and "ended" in res.json()["detail"]


def test_a_lesson_switched_off_stops_opening(seeded: Env, spoken: list[str]) -> None:
    card = approved_card(seeded, slot=2)
    token = link_token(seeded, card["id"])
    res = seeded.client.put(
        "/api/pilot/config/audio-count", json={"audio_count": 1}, headers=seeded.h("ops")
    )
    assert res.status_code == 200
    assert seeded.client.get(f"/api/pilot/lesson/{token}").status_code == 404


def test_a_returned_lesson_cannot_be_opened_from_an_old_link(
    seeded: Env, spoken: list[str]
) -> None:
    generate(seeded)
    first = cards(seeded)[0]["id"]
    approve(seeded, first)
    token = link_token(seeded, first)
    with seeded.factory() as db:
        row = db.get(PilotAudio, first)
        assert row is not None
        row.status, row.note = "failed", "rejected:tone_issue"
        db.commit()
    assert seeded.client.get(f"/api/pilot/lesson/{token}").status_code == 404


def test_the_link_without_a_web_address_is_refused_not_guessed(
    seeded: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    generate(seeded)
    first = cards(seeded)[0]["id"]
    approve(seeded, first)
    monkeypatch.delenv("PWA_ORIGIN", raising=False)
    res = seeded.client.get(f"/api/pilot/audio/{first}/lesson-link", headers=seeded.h("ops"))
    assert res.status_code == 503


def test_sharing_the_text_is_recorded_before_any_audio_exists(
    seeded: Env, spoken: list[str]
) -> None:
    card = approved_card(seeded)
    res = seeded.client.post(
        f"/api/pilot/audio/{card['id']}/shares",
        json={"teacher_refs": ["T-101"]},
        headers=seeded.h("ops"),
    )
    assert res.status_code == 200 and res.json() == {"recorded": 1}
    assert spoken == []


def test_the_only_open_routes_are_sign_in_the_lesson_page_and_its_audio(env: Env) -> None:
    """Every other pilot route still needs a token; the lesson routes are the one new exception."""
    from fastapi.routing import APIRoute

    from services.pilot.routes import router

    open_routes = {
        ("POST", "/api/pilot/auth/signin"),
        ("GET", "/api/pilot/lesson/{token}"),
        ("POST", "/api/pilot/lesson/{token}/audio"),
        ("GET", "/api/pilot/blob/{token}"),  # signed, expiring local-store links (dev only)
        ("PUT", "/api/pilot/blob/{token}"),
    }
    seen = set()
    for route in router.routes:
        assert isinstance(route, APIRoute)
        for method in route.methods:
            seen.add((method, route.path))
            if (method, route.path) in open_routes:
                continue
            probe = route.path
            for name in ("token", "audio_id", "sheet_id", "school_code"):
                probe = probe.replace("{" + name + "}", "x")
            res = env.client.request(method, probe)
            assert res.status_code == 401, (method, route.path, res.status_code)
    assert open_routes <= seen
