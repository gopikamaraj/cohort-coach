# Speech: voice in the Practice Class (v1, after P07)

A teacher can hold a button and speak to the five pretend children, and hear each child answer in a different voice. Speech is the second AI layer on top of the text pipeline, not a separate path: speech-to-text produces her words, the same pipeline (label, engine, child line, gates) produces the child's line, and text-to-speech reads it. If any speech step fails, she is moved to typing and nothing is lost.

**Status, stated plainly.** Built and tested against mocked HTTP, real ffmpeg and a stub speech service, and since the key was replaced (2026-10-17) run live once: all 36 clips (twelve children in en, hi, ta) synthesised, so the twelve speaker names are accepted by Sarvam, and 24 live voice turns were timed (`evals/results/voice_latency.json`). The voice median is **over** the 5 s target (below). Whether the five children sound distinct is still for a person to confirm: `scripts/check_voices.py` saves the clips for listening.

## The path of one voice turn

```text
phone: hold button -> MediaRecorder (WebM/Opus, 24 kbps) -> POST /voice-turn (multipart, <= 2 MB)
server: ffmpeg -> 16 kHz mono WAV -> cut at silences into chunks <= 28 s -> Sarvam speech-to-text
        -> text turn: call 2 label, engine, call 1 child line, gate 1/1b validators
        -> candidate line known -> text-to-speech STARTS (in parallel) while call 7 checks the line
        -> check passes: release that audio.  check fails: the template line is voiced instead
        -> reply: what she said (heard), the child's line, OGG/Opus audio as base64, stage timings
phone: shows her words and the child's line, plays the audio, then is ready again
```

The audio is never stored by us: it exists only in process memory (and the framework's transient upload buffer while the request is read); the recording is decoded, transcribed and dropped; the reply audio is returned inline and cached in memory only by a hash of the line. A real child's voice is never recorded or used. What she said comes back to her phone as text, like a typed turn, and the transcript stays on the phone.

## Which voice is which child

`content/voices/children.v1.yaml` gives each of the twelve fictional children one stock Bulbul v3 speaker and a pitch ratio (configured, between 1.18 and 1.40). Raising the pitch is done by ffmpeg (`asetrate`, `aresample`, `atempo`), which raises the pitch and keeps the speed; a test measures the shift with an FFT and checks the duration is kept. A child therefore sounds the same in every session, and the five seats of a session are configured with different speakers (a test checks the twelve speaker names differ; that they sound different is not yet verified).

- Bulbul v3 has no pitch control (`pitch` and `loudness` are v2 only), so the shift is ours.
- Cloned voices are built behind `SARVAM_CLONES=1`, off by default and not tested live: Sarvam's docs do not list the clone request fields and publish no licence terms. Policy if switched on: licence-cleared AI-designed voices or a consenting adult, never a real child.
- Speaker names were taken from Sarvam's documentation and are unverified. `check_voices.py` reports any speaker the service refuses.

## When voice is on, and when it turns itself off

| Situation | What happens |
| --- | --- |
| The server has speech, this phone can record, the link is not 2g, and she has not chosen typing before | Hold-to-speak is the main action |
| `effectiveType` is `2g` or `slow-2g` | Starts in typing mode; "Use voice" is one tap away |
| One voice request fails | A notice; she can try again |
| Two in a row fail | Typing takes over by itself with a plain notice; "Use voice" brings it back |
| Server circuit breaker: 3 speech failures in a row | Speech is skipped for 30 s (503 with `text_mode`), then one trial request is let through |
| Microphone blocked | Notice that says how to allow it, and typing |
| She taps for under 0.4 s, or nothing is heard | Nothing is sent or she is asked to hold and speak again; not counted as a failure |
| She chooses "Type instead" | Remembered on this phone |

Only the Practice Class needs a connection, and voice is its heaviest form. This is the stated trade-off: voice needs a good signal, typing needs less, and the offline practice cards are the last resort (P14).

## Check-then-release

Text-to-speech starts as soon as the candidate line passes the code validators, in parallel with call 7 (the checker), so the checker's time is hidden behind synthesis. The audio is released only if the line passes the checker. If the checker holds the line back, or the model call falls back, the line that is voiced is the safe template line, never the held candidate. The held candidate was already sent to Sarvam for synthesis (that is what running in parallel means); it is a fictional child's line, the result is discarded, and an unstarted job is cancelled. `tests/speech/test_voice_turn.py::test_audio_is_released_only_when_the_line_passes_the_checker` checks that the audio sent back is the template line's and not the AI candidate's.

## What is logged

One row per speech request in `speech_calls`: stage (stt or tts), mode, language, latency, byte counts, characters, seconds, cost in INR (prices in `services/speech/pricing.yaml`, copied from Sarvam's pricing page on 2026-10-17), cache hit, and the error kind. Never the audio and never the text (a test checks the row against the turn's words). `python scripts/budget.py` shows it. The per-turn trace in judge mode gains `layers.evaluation.stages` (`stt_ms`, `tts_wait_ms`), shown in the AI-layers overlay.

## Limits on the public endpoint

A recording is refused above 2 MB (and by `Content-Length` before it is read) or above 30 s of audio after decoding (the phone stops at 25 s); a finished rehearsal is refused (409) before any paid speech call, so the 40-turn judge cap also caps speech spend. Speech has its own daily budget, `SPEECH_BUDGET_INR_DAILY` (default 200, counted in memory per server process from the same cost estimate as `speech_calls`); when it is spent, voice reports `text_mode` and everyone types. Any unexpected error in the speech path becomes `text_mode`, never a 500. A per-IP rate limit is still parked (`docs/build/PARKING.md`) and is needed before the public staging URL. Sending a teacher's voice to Sarvam is the one place audio leaves our server: the hold-to-speak screen should carry a one-line notice and the consent text to be written with Seema (TODO-HUMAN).

## Pronunciation

`content/pronunciation/{hi,ta}.yaml` list the maths words to check. Every `say` is empty: nobody has listened yet, and the build does not guess. Words that are filled in become the dictionary file (`services/speech/pronunciation.py`); the id Sarvam returns goes in `SARVAM_DICT_HI` and `SARVAM_DICT_TA`. TODO-HUMAN(Shivani for Hindi, Gopi for Tamil).

## Stub speech (tests and demos)

`SPEECH_MODE=stub` (the screen shows "Simulated voice" when it is on) returns scripted teacher lines (the same four lines in each language, in turn) as the "transcript" and a generated tone as the voice. It is not speech recognition, and `speech_mode` in the response says `stub`. The Playwright tests use it with Chromium's fake microphone; they prove the hold-to-speak flow and the fallback, not recognition.

## Measured and not yet measured

| Item | Status |
| --- | --- |
| Voice turn median under 5 s | **Not met**: 24 live turns, median 7515 ms, p90 9938 ms (en 9055, hi 7358, ta 6218), from `evals/results/voice_latency.json` (one network and machine: directional). Speech-to-text median 1109 ms and the wait for the child's audio median 1523 ms, so most of the time is the text pipeline (Claude calls), the gap already reported in `docs/practice-class.md`. Mitigation plan: fix the text pipeline first (smaller prompts, parallel label and engine work), then stream the reply audio; the typing path is the fallback |
| Reply audio size | Mean 19916 bytes per reply over those 24 turns (same file); per rehearsal and per track still to compute |
| Five audibly distinct children, three languages, on a phone | Needs a person: `python scripts/check_voices.py`, then listen (Gopi, Shivani) |
| Text-turn latency target (3 s) | Still over, see `docs/practice-class.md`; voice adds the speech stages on top |
