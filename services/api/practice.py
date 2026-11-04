# ruff: noqa: E501
"""Practice Class API: create a session, take turns, end it for feedback.

Session state lives in memory with a time limit and is never persisted. The full transcript
comes back to the client, which keeps it on the teacher's phone. The server stores only the
metadata-only audit rows written by the AI calls.
"""

from __future__ import annotations

import base64
import logging
import os
import time
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, replace
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from ai import config
from ai.client import BudgetExceeded, CallContext
from ai.config import ai_mode
from engine.model import ErrorCode
from services.api.identity import user_of
from services.api.ratelimit import RateLimiter
from services.api.roles import judge_session, require
from services.api.sprite_media import tray_items
from services.practice.content import LANGS, load_personas, load_scenario
from services.practice.hints import hints
from services.practice.session import (
    PracticeSession,
    SessionFinished,
    end_session,
    seating,
    start_session,
    take_turn,
)
from services.practice.stub_client import StubClient
from services.practice.watch import (
    LiveMeter,
    WatchFallback,
    load_recorded,
    run_watch,
    tag,
)
from services.speech import cast
from services.speech.sarvam import SpeechError
from services.speech.service import SpeechService, default_service
from services.speech.voices import voice_for
from services.spoken.adapters.practice import prepare_utterance
from services.usage import context as usage_context

# Per connection, per minute; every one of these starts a paid call (docs/privacy.md).
_LIMIT_SESSION = RateLimiter("practice_session", 20)
_LIMIT_TURN = RateLimiter("practice_turn", 40)
_LIMIT_VOICE = RateLimiter("practice_voice", 12)
_LIMIT_WATCH = RateLimiter("practice_watch", 6)

router = APIRouter(
    prefix="/api/practice",
    tags=["practice"],
    dependencies=[Depends(require("practice.rehearse"))],
)

SESSION_TTL_S = 2 * 60 * 60
MAX_SESSIONS = 500
_SESSIONS: dict[str, tuple[PracticeSession, float]] = {}


def get_ai_context() -> CallContext:
    """The AI mode from the environment (recorded, live, record, or stub for offline demos)."""
    mode = config.ai_mode()
    if mode == "stub":
        return CallContext(mode="stub", client=StubClient())
    return CallContext(mode=mode)


AI_CONTEXT = Depends(get_ai_context)


def get_speech() -> SpeechService:
    return default_service()


SPEECH = Depends(get_speech)
MAX_AUDIO_BYTES = 2_000_000
_POOL = ThreadPoolExecutor(max_workers=4)
log = logging.getLogger(__name__)


class CreateSession(BaseModel):
    scenario: str = "SUB-SFL"
    language: str = "en"
    judge: bool = False
    counts: dict[str, int] | None = (
        None  # class-level error counts, to seat children like her class
    )
    checked: int = Field(0, ge=0, le=200)
    seed: int | None = None


class TurnRequest(BaseModel):
    text: str | None = Field(None, max_length=1000)
    material: str | None = None
    stt_confidence: float | None = Field(None, ge=0, le=1)


def _sweep() -> None:
    now = time.time()
    for sid in [k for k, (_, at) in _SESSIONS.items() if now - at > SESSION_TTL_S]:
        del _SESSIONS[sid]
        _OWNERS.pop(sid, None)
    while len(_SESSIONS) >= MAX_SESSIONS:
        gone = min(_SESSIONS, key=lambda k: _SESSIONS[k][1])
        del _SESSIONS[gone]
        _OWNERS.pop(gone, None)


_OWNERS: dict[str, str] = {}  # session id -> the user who started it (transcripts are never stored)


def _get(session_id: str, uid: str) -> PracticeSession:
    entry = _SESSIONS.get(session_id)
    if entry is None or time.time() - entry[1] > SESSION_TTL_S:
        raise HTTPException(404, "This practice session has expired. Start a new one.")
    if _OWNERS.get(session_id) != uid:  # another user's session looks like no session at all
        raise HTTPException(404, "This practice session has expired. Start a new one.")
    _SESSIONS[session_id] = (entry[0], time.time())
    return entry[0]


def _to_dict(obj: Any) -> dict[str, Any]:
    out = asdict(obj)
    for k, v in list(out.items()):
        if hasattr(v, "value"):
            out[k] = v.value
    return out


@router.post("/sessions", dependencies=[Depends(_LIMIT_SESSION)])
def create_session(body: CreateSession, uid: str = Depends(user_of), speech: SpeechService = SPEECH) -> dict[str, Any]:
    if body.language not in LANGS:
        raise HTTPException(422, f"language must be one of {', '.join(LANGS)}")
    try:
        load_scenario(body.scenario)
        counts = {ErrorCode(k): v for k, v in (body.counts or {}).items()}
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(422, "Unknown scenario or error code.") from exc
    _sweep()
    session = start_session(
        body.scenario,
        body.language,
        counts=counts,
        checked=body.checked,
        seed=body.seed,
        judge=body.judge and judge_session(),
    )
    _SESSIONS[session.id] = (session, time.time())
    _OWNERS[session.id] = uid
    loaded = session.loaded
    return {
        "session_id": session.id,
        "seed": session.seed,  # lets her retry with the same children
        "language": session.language,
        "judge": session.judge,
        # who is sitting where. Not who has the error: the first faces are all calm (the shy
        # child looks shy), and the confusion meter appears only after a turn.
        "children": seating(session),
        "materials": loaded.scenario.materials,
        "material_items": tray_items(loaded.scenario.materials),
        "turn_cap": loaded.config.max_turns,
        # what she is practising: the rubric's "try next" lines, in her language (content, not AI)
        "goal": {
            "error": session.error,
            "tips": [p.try_next[session.language] for p in loaded.rubric.points],
        },
        "voice": {"available": speech.available, "mode": speech.mode},
        "moves": _moves_with_cues(session),
    }


@router.post("/sessions/{session_id}/turns", dependencies=[Depends(_LIMIT_TURN)])
def post_turn(  # noqa: E501
    session_id: str, body: TurnRequest, uid: str = Depends(user_of), ctx: CallContext = AI_CONTEXT
) -> dict[str, Any]:
    session = _get(session_id, uid)
    try:
        result = take_turn(
            session,
            text=body.text,
            material=body.material,
            stt_confidence=body.stt_confidence,
            context=ctx,
        )
    except SessionFinished as exc:
        raise HTTPException(409, "This rehearsal has finished. Ask for feedback.") from exc
    except BudgetExceeded as exc:
        raise HTTPException(503, "Practice is paused for today. Try again later.") from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {**_to_dict(result), "turns_left": session.loaded.config.max_turns - session.state.turn}


VOICE_OFF = "Voice is off for the rest of this practice. The text continues."
SWITCH_AFTER = 2  # synthesis failures in a row before the session moves to the next provider


def _seat_voices(session: PracticeSession) -> dict[str, str]:
    """Each child's voice for the whole session: by seat and the persona's gender (voices.yaml)."""
    kids = session.state.children
    genders = [session.personas[c.name].gender if c.name in session.personas else "f" for c in kids]
    return dict(
        zip([c.name for c in kids], cast.seat_voices(session.language, genders), strict=True)
    )


def _synth_ex(
    speech: SpeechService, text: str, session: PracticeSession, speaker: str
) -> tuple[bytes, str]:
    """A child's line as audio, and who made it. Her voice is fixed for the session; her mood (the
    engine's) sets the style by code; the session's speech allowance and provider pin apply."""
    persona = session.personas.get(speaker)
    voice = voice_for(persona.id if persona else "")
    # the spoken layer: the line is made ready for the ear here; the line on the screen is unchanged
    text = prepare_utterance(text, session.language, "simulated_child")
    if type(speech).synthesize is not SpeechService.synthesize or not hasattr(
        speech, "synthesize_ex"
    ):
        return speech.synthesize(text, session.language, voice), "speech"  # a stand-in service
    return speech.synthesize_ex(
        text,
        session.language,
        voice,
        budget=session.speech_budget,
        style=cast.mood_style(session.moods.get(speaker)),
        bodhan_voice=_seat_voices(session).get(speaker),
        order=session.tts_order,
    )


def _synth(speech: SpeechService, text: str, session: PracticeSession, speaker: str) -> bytes:
    return _synth_ex(speech, text, session, speaker)[0]


def _note_tts(session: PracticeSession, ok: bool, provider: str, speech: SpeechService) -> None:
    """Two failures in a row (no audio, or the first provider failing so a fallback answered) move
    the session to the providers after the first one for the rest of it. Logged by names only."""
    chain = getattr(speech, "chain", None)
    first = (
        chain.candidates("tts", session.language)[0].name
        if chain is not None and chain.candidates("tts", session.language)
        else None
    )
    primary_failed = (not ok) or (first is not None and provider not in (first, "cache"))
    session.tts_failures = session.tts_failures + 1 if primary_failed else 0
    if session.tts_failures >= SWITCH_AFTER and session.tts_order is None and chain is not None:
        rest = [p.name for p in chain.candidates("tts", session.language)][1:]
        if rest:
            session.tts_order = rest
            log.warning(
                "practice voice: session moved from %s to %s after %d failures",
                first,
                rest,
                SWITCH_AFTER,
            )


def _moves_with_cues(session: PracticeSession) -> list[dict[str, Any]]:
    """Each move with things she could say, in her language, using the children in this class.

    The example lines are content (content/movelists), written with an example child's name; the
    name is swapped for one of her five children so the cue can be used as it stands. A move that
    makes children go quiet (scolding) is never offered as a cue.
    """
    lang = session.language
    kids = [c.name for c in session.state.children if not c.shy] or [
        c.name for c in session.state.children
    ]
    example_names = sorted({k.names[lang] for k in load_personas().children}, key=len, reverse=True)
    out: list[dict[str, Any]] = []
    for i, m in enumerate(session.loaded.movelist.moves):
        entry: dict[str, Any] = {"id": m.id, "label": m.label[lang], "examples": []}
        if not m.quiet and m.engagement >= 0:
            for j, line in enumerate(m.examples[lang]):
                name = kids[(i + j) % len(kids)]
                for example in example_names:
                    if example in line and example not in kids:
                        line = line.replace(example, name)
                        break
                entry["examples"].append(line)
        out.append(entry)
    return out


def _text_mode(why: str, voice_off: bool = False) -> HTTPException:
    return HTTPException(503, {"text_mode": True, "message": why, "voice_off": voice_off})


@router.post("/sessions/{session_id}/voice-turn", dependencies=[Depends(_LIMIT_VOICE)])
def post_voice_turn(
    session_id: str,
    request: Request,
    uid: str = Depends(user_of),
    audio: UploadFile = File(...),  # noqa: B008
    ctx: CallContext = AI_CONTEXT,
    speech: SpeechService = SPEECH,
) -> dict[str, Any]:
    """Speech in, speech out. Order: speech-to-text, the text pipeline, then synthesis started
    in parallel with call 7 and released only if the line passes (check-then-release). On any
    speech failure the client gets 503 with `text_mode` and carries on by typing."""
    session = _get(session_id, uid)
    if session.state.finished or session.ended:  # before any paid speech call
        raise HTTPException(409, "This rehearsal has finished. Ask for feedback.")
    if not speech.available:
        raise _text_mode("Voice is not available right now. Type instead.")
    if session.voice_off:
        raise _text_mode(VOICE_OFF, voice_off=True)
    if int(request.headers.get("content-length") or 0) > MAX_AUDIO_BYTES + 100_000:
        raise HTTPException(413, "That recording is too large. Hold the button for less time.")
    recording = audio.file.read(MAX_AUDIO_BYTES + 1)
    if not recording or len(recording) > MAX_AUDIO_BYTES:
        raise HTTPException(422, "That recording was empty or too long. Try again.")
    t0 = time.monotonic()
    try:
        if type(speech).transcribe is SpeechService.transcribe:
            heard = speech.transcribe(recording, session.language, budget=session.speech_budget)
        else:
            heard = speech.transcribe(recording, session.language)
    except SpeechError as exc:
        if exc.code == "session_cap":  # this session's speech allowance is used: text from now on
            session.voice_off = True
            raise _text_mode(VOICE_OFF, voice_off=True) from exc
        if exc.kind == "bad_request":  # too long or unreadable: not a service failure
            raise HTTPException(422, "That recording was too long or unclear. Try again.") from exc
        raise _text_mode("Could not hear that. Type instead.") from exc
    except Exception as exc:  # odd audio must never become a 500: she carries on by typing
        raise _text_mode("Could not hear that. Type instead.") from exc
    stt_ms = int((time.monotonic() - t0) * 1000)
    if not heard.strip():
        raise HTTPException(422, "I didn't catch that. Try again: hold the button while you speak.")
    pending: dict[str, Future[tuple[bytes, str]]] = {}

    def start_audio(candidate: str, speaker: str) -> None:
        pending["f"] = usage_context.submit(_POOL, _synth_ex, speech, candidate, session, speaker)

    try:
        result = take_turn(session, text=heard[:1000], context=ctx, on_candidate=start_audio)
    except SessionFinished as exc:
        raise HTTPException(409, "This rehearsal has finished. Ask for feedback.") from exc
    except BudgetExceeded as exc:
        raise HTTPException(503, "Practice is paused for today. Try again later.") from exc
    out: dict[str, Any] = {
        **_to_dict(result),
        "turns_left": session.loaded.config.max_turns - session.state.turn,
        "heard": heard,
    }
    audio_b64, tts_wait_ms, tts_provider = None, 0, None
    voice_off_now = False
    if result.child_text:
        t1 = time.monotonic()
        # An AI line that was released (it passed gates 1 and 2, or call 7 is switched off): its
        # speech was started in parallel and can be used. Template lines are spoken from here.
        released = result.source == "ai"
        try:
            if released and "f" in pending:
                data, tts_provider = pending["f"].result(timeout=20)
            else:
                data, tts_provider = _synth_ex(
                    speech, result.child_text, session, result.speaker or ""
                )
            audio_b64 = base64.b64encode(data).decode()
            _note_tts(session, True, tts_provider, speech)
        except SpeechError as exc:
            voice_off_now = exc.code == "session_cap"
            if not voice_off_now:
                _note_tts(session, False, "", speech)
        except Exception:  # noqa: BLE001 - the text is already there; audio is a bonus
            _note_tts(session, False, "", speech)
        tts_wait_ms = int((time.monotonic() - t1) * 1000)
    first_audio_ms = int((time.monotonic() - t0) * 1000) if audio_b64 else None
    # The other children who spoke: their template lines are spoken in parallel, one clip each.
    spoken = [
        (o, usage_context.submit(_POOL, _synth_ex, speech, o["child_text"], session, o["speaker"]))
        for o in out.get("others", [])
        if o["child_text"] and not voice_off_now
    ]
    for o in out.get("others", []):
        o["audio"], o["audio_mime"] = None, None
    for o, fut in spoken:
        try:
            o["audio"] = base64.b64encode(fut.result(timeout=20)[0]).decode()
            o["audio_mime"] = "audio/ogg"
        except SpeechError as exc:  # the text is there; audio is a bonus
            voice_off_now = voice_off_now or exc.code == "session_cap"
        except Exception:  # noqa: BLE001 - the text is there; audio is a bonus
            pass
    if voice_off_now:
        session.voice_off = True
    for f in pending.values():  # a candidate that was not released is dropped
        if not f.done():
            f.cancel()
    stages = {"stt_ms": stt_ms, "tts_wait_ms": tts_wait_ms}
    out["layers"]["evaluation"]["stages"] = stages
    calls = out["layers"]["evaluation"].get("call_ms", {})
    # every stage of the turn, and who spoke it (for the latency results per provider)
    out["layers"]["evaluation"]["timing"] = {
        "stt_ms": stt_ms,
        "label_ms": calls.get("label"),
        "engine_ms": out["layers"]["evaluation"].get("engine_ms"),
        "child_ms": calls.get("child"),
        "check_ms": calls.get("check"),
        "tts_ms": tts_wait_ms,
        "first_audio_ms": first_audio_ms,
        "tts_provider": tts_provider,
        "speech_mode": speech.mode,
    }
    out["voice_off"] = session.voice_off
    if session.voice_off:
        out["voice_message"] = VOICE_OFF
    out["audio"] = audio_b64
    out["audio_mime"] = "audio/ogg" if audio_b64 else None
    out["speech_mode"] = speech.mode
    return out


@router.post("/sessions/{session_id}/end")
def post_end(session_id: str, uid: str = Depends(user_of), ctx: CallContext = AI_CONTEXT) -> dict[str, Any]:
    session = _get(session_id, uid)
    try:
        card, layers = end_session(session, context=ctx)
    except BudgetExceeded as exc:
        raise HTTPException(503, "Feedback is paused for today. Try again later.") from exc
    out = _to_dict(replace(card, gate=None))
    out.pop("gate", None)
    return {
        "card": out,
        "layers": layers,
        "transcript": [
            {"turn": r.turn, "teacher": r.teacher_text, "child": r.child_text, "speaker": r.speaker}
            for r in session.records
        ],
        "explanation": card.gate.explanation if card.gate else "",
    }


# Watch mode (judge mode only) ---------------------------------------------------------------------


class WatchRequest(BaseModel):
    scenario: str = "SUB-SFL"
    style: Literal["experienced", "struggling"]
    language: str = "en"
    live: bool = False  # a recorded run is the default; live runs are capped per hour


WATCH_METER = LiveMeter(cap_per_hour=int(os.environ.get("WATCH_LIVE_PER_HOUR") or 6), runs=deque())


@router.post("/watch", dependencies=[Depends(_LIMIT_WATCH)])
def post_watch(body: WatchRequest, ctx: CallContext = AI_CONTEXT) -> dict[str, Any]:
    """An AI teacher runs the rehearsal. Judge mode only: a real teacher hears the model run."""
    if not judge_session():
        raise HTTPException(403, "The demo teacher is available in the demo only.")
    if body.language not in LANGS:
        raise HTTPException(422, f"language must be one of {', '.join(LANGS)}")
    try:
        load_scenario(body.scenario)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(422, "Unknown scenario.") from exc
    reason: str | None = None
    live_possible = (ctx.mode or ai_mode()) in ("live", "stub")
    if body.live and not live_possible:
        reason = "live runs are off in this deployment"
    elif body.live and not WATCH_METER.allowed():
        reason = "the hourly limit of live runs is reached"
    elif body.live:
        try:
            run = run_watch(
                scenario=body.scenario, style=body.style, language=body.language, context=ctx
            )
            WATCH_METER.record(float(run["provenance"]["cost_usd"]))
            return tag(run, kind="live run")
        except WatchFallback as exc:
            reason = f"the live run stopped: {exc}"
        except BudgetExceeded:
            reason = "practice is paused for today"
    rec = load_recorded(body.scenario, body.style, body.language)
    if rec is None:
        raise HTTPException(503, "There is no recorded run for this choice yet.")
    return tag(rec, kind="recorded run", reason=reason)


@router.get("/watch/meter")
def get_watch_meter() -> dict[str, Any]:
    """Live runs and their cost this hour, added up from the calls' own costs."""
    if not judge_session():
        raise HTTPException(403, "The demo teacher is available in the demo only.")
    return WATCH_METER.snapshot()


@router.get("/sessions/{session_id}/hints")
def get_hints(session_id: str, uid: str = Depends(user_of)) -> dict[str, Any]:
    """Three replies for the next turn (judge mode only). The quality of each is not sent."""
    if not judge_session():
        raise HTTPException(403, "Hints are available in the demo only.")
    session = _get(session_id, uid)
    return {"hints": hints(session)}
