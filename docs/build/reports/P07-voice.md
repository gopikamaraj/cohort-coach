# P07 · Voice (speech service and child voices): report

**Status: 🟡 built and tested without the network; nothing has run against Sarvam.** The Sarvam key in `.env` is rejected (403 `invalid_api_key_error`, checked again with `scripts/check_voices.py`). Everything that needs a live call is ready and waiting for a working key.

## What was built

| Task | Result | Where |
| --- | --- | --- |
| T01 Sarvam facts and pricing | Read from Sarvam's docs on 2026-10-17 and logged in DECISIONS; prices with source and date | `docs/build/DECISIONS.md`, `services/speech/pricing.yaml` |
| T02 Speech clients | HTTP client (errors mapped, bounded retries), ffmpeg helpers (decode, cut at silences, pitch shift, OGG/Opus), speech-to-text, text-to-speech with a cache, voices, circuit breaker | `services/speech/` |
| T03 Stub speech | `SPEECH_MODE=stub`: scripted transcripts and a tone; the screen says "Simulated voice" | `services/speech/service.py` |
| T04 Voice turn | `POST /api/practice/sessions/{id}/voice-turn`; synthesis starts in parallel with call 7 and is released only on pass; stage timings in `layers`; `speech_calls` table; `scripts/budget.py` section | `services/api/practice.py`, `ai/calls/c01_child_voice.py` (`on_candidate`) |
| T05 Client | Hold to speak, listening / thinking / speaking states, automatic text after 2 failures or on 2g, remembered choice, mic released on leave, three languages | `apps/pwa/src/screens/Practice.tsx`, `lib/voice.ts` |
| T06 Pronunciation | Word lists (all `say` empty: nobody has listened) and a dictionary builder | `content/pronunciation/`, `services/speech/pronunciation.py` |
| T07 Live scripts | `check_voices.py` (key and twelve voices, clips for listening) and `voice_latency.py --live` | `scripts/` |
| T08 Docs and review | `docs/speech.md`, offline matrix row, evidence hook, parking notes | `docs/` |

## Acceptance

| Criterion | Evidence | Status |
| --- | --- | --- |
| Live voice rehearsal in hi, ta, en on a phone with five audibly distinct children | Not run: needs a working key and a person to listen | ⛔ human |
| Median voice turn under 5 s, or the gap documented | Not measured. `python scripts/voice_latency.py --live` writes `evals/results/voice_latency.json`; the evidence page shows it only when it exists. A stub run prints "STUB RUN" and is not a measurement | ⛔ key |
| Automatic text fallback demonstrated | Playwright with a fake microphone and stub speech (`apps/pwa/e2e/voice.spec.ts`: two failures to typing, 2g, remembered choice); API tests for 503 `text_mode`, the breaker, over-long audio, odd errors. Staging demonstration still to do | 🟡 |

## Evidence of the checks

- Python: 26 speech tests (mocked HTTP, real ffmpeg: chunk limit, pitch measured by FFT with duration kept, cache hit, breaker, request shape, key header, retries) plus 8 voice-turn tests (check-then-release, budget, finished session, length limit, odd errors, no text in `speech_calls`). The full suite passed in the pre-commit hook.
- Playwright: 5 voice tests and the existing 18, all passing on a production build.
- Eval and evidence numbers: none new. Nothing was hand-written.

## Reviews

- **integrity-auditor:** honest with fixes. Fixed: the check-then-release test now compares the audio bytes with the template line and not the AI candidate; the stub run no longer prints a verdict; the evidence hook requires a live run and shows how many turns had no audio; the task file's evidence path and statuses were aligned; the "distinct voices" wording now says speaker names are configured and the sound is unverified.
- **judge-reviewer:** pass with fixes. Fixed: stub speech is labelled on screen in three languages; stage timings now show in the AI-layers overlay; the held-candidate behaviour and the one-line consent notice are written in `docs/speech.md`.
- **privacy-guardian:** no leak found; two blocking items about abuse and cost on the public endpoint. Fixed: finished sessions refuse before any speech call, 2 MB and 30 s limits, a daily speech budget, unexpected errors become text mode; the microphone is released on leaving the screen and when the recorder fails. Still open: a per-IP rate limit (parked, needed before the public URL).
- **A bug found while fixing:** ffmpeg's piped WAV has no length in its header, so audio length is now computed from the samples (test added).

## Open and for people

1. Gopi: fix or replace the Sarvam key on Sarvam's dashboard (still 403). Then run `python scripts/check_voices.py`, listen to the clips, run `python scripts/voice_latency.py --live`, and run `python tasks.py evidence`. The twelve speaker names are from the docs and unverified.
2. Gopi and Shivani: listen for five audibly distinct children in hi, ta and en; fill `content/pronunciation/*.yaml` only where a word sounds wrong.
3. Seema and Gopi: the consent line for sending a teacher's voice to Sarvam, and Hindi and Tamil review of the new strings (`docs/build/i18n-todo.md`).
4. Per-IP rate limit and the staging demonstration of the fallback (P15).
5. Gopi's confirmation of the P07 DECISIONS entries stays open, as for P03 to P06.

## Numbers and honesty

No voice latency, audio size or cost figure is claimed anywhere: each waits for a live run. The text-turn latency (3 s target) is still over, as reported in P04.
