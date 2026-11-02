"""Practice Class speech through the provider chain: each child's fixed voice and her mood's style
(decided by code), the chorus with a partial failure, the session cap, the cached template lines,
the two-failure provider switch, the 120-character line limit, silence, and the per-stage timing.
Mock providers only; no network, no paid call."""

from __future__ import annotations

import shutil
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ai.client import CallContext
from ai.guard.gates import CHILD_LINE_MAX_CHARS
from ai.validators.length import check_length
from services.api import practice as api
from services.api.main import app
from services.media.storage import LocalBlobStore
from services.practice.stub_client import StubClient
from services.speech import audio, cast, costs, tts
from services.speech.chain import ProviderChain
from services.speech.provider import Audio, Capabilities, Transcript
from services.speech.sarvam import SpeechError
from services.speech.service import SpeechService, default_chain
from services.speech.voices import Voice

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not on PATH")
WAV = audio.tone(1.5, 300, rate=24000)


class Voiced:
    """A provider that records every (text, voice, style) it is asked for. `fail_text` makes the
    lines containing it fail; `fail_all` fails everything."""

    def __init__(
        self,
        name: str,
        *,
        heard: str = "Show me with the bundles",
        fail_text: str | None = None,
        fail_all: bool = False,
    ) -> None:
        self.name = name
        self.heard = heard
        self.fail_text = fail_text
        self.fail_all = fail_all
        self.down: str | None = None
        self.asked: list[tuple[str, str, str | None]] = []

    def configured_for(self, function: str) -> bool:
        return True

    @property
    def capabilities(self) -> Capabilities:
        return Capabilities(30.0, frozenset({"wav"}), 300)

    def transcribe(self, wav: bytes, language: str) -> Transcript:
        return Transcript(self.heard, audio.wav_seconds(wav), self.name)

    def synthesize(self, text: str, language: str, voice: str, style: str | None) -> Audio:
        self.asked.append((text, voice, style))
        if self.fail_all or (self.fail_text and self.fail_text in text):
            raise SpeechError("unavailable", 503)
        return Audio(audio.tone(0.3, 440, rate=24000), "wav", 24000, 0.3, len(text), self.name)


def service(*providers: Voiced, store: object = None) -> SpeechService:
    names = [p.name for p in providers]
    chain = ProviderChain({p.name: p for p in providers}, order=lambda f, lang: names)
    return SpeechService("live", log=lambda **kw: None, providers=chain, cache_store=store)


@pytest.fixture
def client() -> Iterator[TestClient]:
    app.dependency_overrides[api.get_ai_context] = lambda: CallContext(
        mode="stub", client=StubClient()
    )
    api._SESSIONS.clear()
    tts.CACHE._items.clear()
    yield TestClient(app)
    app.dependency_overrides.clear()
    api._SESSIONS.clear()


def use(svc: SpeechService) -> None:
    app.dependency_overrides[api.get_speech] = lambda: svc


def start(client: TestClient, lang: str = "en") -> str:
    res = client.post(
        "/api/practice/sessions", json={"scenario": "SUB-SFL", "language": lang, "seed": 5}
    )
    return str(res.json()["session_id"])


def speak(client: TestClient, sid: str, wav: bytes = WAV):  # type: ignore[no-untyped-def]
    return client.post(
        f"/api/practice/sessions/{sid}/voice-turn", files={"audio": ("c.wav", wav, "audio/wav")}
    )


# --- mood and voice, by code ----------------------------------------------------------------------


def test_the_mood_sets_the_style_and_never_the_ai() -> None:
    assert cast.mood_style("bright") == "happy" and cast.mood_style("small") == "sad"
    assert [cast.mood_style(m) for m in ("calm", "flat", "doubtful", "unknown", None)] == [None] * 5


def test_each_child_gets_a_voice_of_her_gender_distinct_from_the_narrator() -> None:
    from services.speech.lessons import lesson_voices

    for lang in ("en", "hi", "ta"):
        voices = cast.seat_voices(lang, ["f", "m", "f", "m", "f"])
        assert len(set(voices)) == 5
        assert lesson_voices()[lang]["bodhan"] not in voices
        data = cast._data()["children"][lang]
        assert voices[0] in data["f"] and voices[1] in data["m"]


def test_a_turn_speaks_with_the_speakers_seat_voice_and_mood_style(client: TestClient) -> None:
    bodhan = Voiced("bodhan")
    use(service(bodhan))
    sid = start(client)
    body = speak(client, sid).json()
    assert body["audio"] and body["heard"] == "Show me with the bundles"
    session = api._SESSIONS[sid][0]
    seats = api._seat_voices(session)
    spoken = {text: (voice, style) for text, voice, style in bodhan.asked}
    voice, style = spoken[body["child_text"]]
    assert voice == seats[body["speaker"]]
    assert style == cast.mood_style(session.moods[body["speaker"]])
    for o in body["others"]:
        assert spoken[o["child_text"]][0] == seats[o["speaker"]]  # each child her own voice


def test_one_chorus_child_failing_keeps_her_text_and_the_others_audio(client: TestClient) -> None:
    """The provider fails for one child's voice only. In a turn where she joins in, her line is
    shown with no audio, and the children around her still get theirs."""

    class OneVoiceDown(Voiced):
        def synthesize(self, text: str, language: str, voice: str, style: str | None) -> Audio:
            if voice == self.down:
                self.asked.append((text, voice, style))
                raise SpeechError("unavailable", 503)
            return super().synthesize(text, language, voice, style)

    p = OneVoiceDown("bodhan")
    use(service(p))
    sid = start(client)
    seats = api._seat_voices(api._SESSIONS[sid][0])
    seen = None
    for _ in range(12):
        tts.CACHE._items.clear()
        body = speak(client, sid).json()
        if len(body.get("others") or []) >= 1:
            target = body["others"][0]
            p.down = seats[target["speaker"]]
            tts.CACHE._items.clear()
            body = speak(client, sid).json()
            mine = [o for o in body.get("others", []) if seats[o["speaker"]] == p.down]
            if mine:
                seen = (body, mine[0])
                break
            p.down = None
    assert seen, "the seeded class should put the chosen child in a chorus within 12 turns"
    body, hers = seen
    assert hers["child_text"] and hers["audio"] is None  # her text stays, without audio
    others_ok = [o for o in body["others"] if o is not hers and o["child_text"]]
    assert all(o["audio"] for o in others_ok)
    if seats.get(body["speaker"]) != p.down:
        assert body["audio"]  # the first speaker's audio is untouched


# --- the session cap ------------------------------------------------------------------------------


def test_the_session_cap_turns_voice_off_and_the_text_continues(client: TestClient) -> None:
    use(service(Voiced("bodhan")))
    sid = start(client)
    api._SESSIONS[sid][0].speech_budget = costs.SessionSpeechBudget(
        max_stt_seconds=2.0, max_tts_chars=10_000
    )
    first = speak(client, sid)
    assert first.status_code == 200 and first.json()["voice_off"] is False
    second = speak(client, sid)
    assert second.status_code == 503
    detail = second.json()["detail"]
    assert (
        detail["voice_off"] is True
        and "Voice is off for the rest of this practice" in detail["message"]
    )
    third = speak(client, sid)  # still off: no speech call is made
    assert third.status_code == 503 and third.json()["detail"]["voice_off"] is True
    typed = client.post(f"/api/practice/sessions/{sid}/turns", json={"text": "Well done"})
    assert typed.status_code == 200 and typed.json()["child_text"]


def test_running_out_of_characters_marks_voice_off_in_the_reply(client: TestClient) -> None:
    use(service(Voiced("bodhan")))
    sid = start(client)
    api._SESSIONS[sid][0].speech_budget = costs.SessionSpeechBudget(
        max_stt_seconds=600, max_tts_chars=5
    )
    body = speak(client, sid).json()
    assert body["child_text"] and body["audio"] is None
    assert body["voice_off"] is True and body["voice_message"].startswith("Voice is off")


# --- cached template lines ------------------------------------------------------------------------


def test_a_line_said_once_is_served_from_the_store_even_after_a_restart() -> None:
    tts.CACHE._items.clear()
    store = LocalBlobStore(b"lines")
    p = Voiced("bodhan")
    first = service(p, store=store)
    v = Voice("anushka", 1.2, 1.0)
    _, who = first.synthesize_ex("I think it is 37.", "en", v, style="happy", bodhan_voice="Suhani")
    assert who == "bodhan" and len(p.asked) == 1
    tts.CACHE._items.clear()  # a new process: memory is empty, the store is not
    again = service(p, store=store)
    _, who2 = again.synthesize_ex(
        "I think it is 37.", "en", v, style="happy", bodhan_voice="Suhani"
    )
    assert who2 == "cache" and len(p.asked) == 1
    _, who3 = again.synthesize_ex("I think it is 37.", "en", v, style="sad", bodhan_voice="Suhani")
    assert who3 == "bodhan"  # another style is another clip


def test_practice_pregen_finds_the_template_lines_and_voices_them() -> None:
    import importlib.util
    import sys
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "scripts" / "practice_pregen.py"
    spec = importlib.util.spec_from_file_location("practice_pregen", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["practice_pregen"] = mod
    spec.loader.exec_module(mod)
    lines = mod.template_lines(sessions=1)
    p = mod.plan(lines)
    assert p["lines"] > 50 and p["languages"] == 3 and p["styles"] >= 2 and p["cost_inr"] > 0
    assert all(len(x["text"]) <= CHILD_LINE_MAX_CHARS for x in lines)
    tts.CACHE._items.clear()
    store = LocalBlobStore(b"pre")
    p1 = Voiced("bodhan")
    out = mod.run(service(p1, store=store), lines[:10])
    assert out == {"made": 10, "cached": 0, "failed": 0}
    tts.CACHE._items.clear()
    again = mod.run(service(Voiced("bodhan", fail_all=True), store=store), lines[:10])
    assert again == {"made": 0, "cached": 10, "failed": 0}  # served with the provider down


# --- the two-failure switch -----------------------------------------------------------------------


def test_two_failures_in_a_row_move_the_session_to_the_next_provider(client: TestClient) -> None:
    bodhan, sarvam = Voiced("bodhan", fail_all=True), Voiced("sarvam")
    use(service(bodhan, sarvam))
    sid = start(client)
    session = api._SESSIONS[sid][0]
    speak(client, sid)
    assert session.tts_order is None and session.tts_failures >= 1
    speak(client, sid)
    assert session.tts_order == ["sarvam"]
    asked_before = len(bodhan.asked)
    tts.CACHE._items.clear()
    body = speak(client, sid).json()
    assert body["audio"] and len(bodhan.asked) == asked_before  # Bodhan is not tried again
    assert body["layers"]["evaluation"]["timing"]["tts_provider"] == "sarvam"


# --- limits, silence, timing ----------------------------------------------------------------------


def test_a_child_line_over_120_characters_fails_the_length_check() -> None:
    assert CHILD_LINE_MAX_CHARS == 120
    assert not check_length("x" * 120, max_chars=CHILD_LINE_MAX_CHARS)
    assert check_length("x" * 121, max_chars=CHILD_LINE_MAX_CHARS)[0].code == "too_many_chars"


def test_silence_is_never_sent_or_scored(client: TestClient) -> None:
    p = Voiced("bodhan")
    use(service(p))
    sid = start(client)
    res = speak(client, sid, audio.tone(2.0, 0, rate=24000))
    assert res.status_code == 422 and api._SESSIONS[sid][0].state.turn == 0


def test_every_stage_is_timed_with_the_provider(client: TestClient) -> None:
    use(service(Voiced("bodhan")))
    sid = start(client)
    timing = speak(client, sid).json()["layers"]["evaluation"]["timing"]
    for key in (
        "stt_ms",
        "label_ms",
        "engine_ms",
        "child_ms",
        "check_ms",
        "tts_ms",
        "first_audio_ms",
    ):
        assert key in timing
    assert timing["tts_provider"] in ("bodhan", "cache") and timing["engine_ms"] is not None


def test_a_live_turn_does_not_wait_long_for_bodhans_allowance_but_batch_work_does(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BODHAN_API_KEY", "k")
    live = default_chain()
    batch = default_chain(live=False)
    assert live.providers["bodhan"].client.max_wait_s == 2.0  # type: ignore[attr-defined]
    assert batch.providers["bodhan"].client.max_wait_s == 90.0  # type: ignore[attr-defined]
