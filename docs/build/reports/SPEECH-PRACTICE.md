# Practice Class speech with Bodhan (Prompt 3)

Built on 1 Nov 2026 on branch `speech-bodhan`, from Prompt 3 of `docs/build/bodhan-speech-prompts.md`. Live scripts were run because you chose that before the run.

## What I found already in place

Much of the prompt was already built in the Practice Class voice path. I verified these, kept them, and say here what each relies on:

- **Recording limit:** the app already stopped recording at 25 s (`MAX_RECORD_MS`) and chose the format with `MediaRecorder.isTypeSupported` (`apps/pwa/src/lib/voice.ts`).
- **Too short:** a recording under 400 ms was not sent.
- **Typing fallback:** after two voice failures the app switched to typing by itself.
- **Release on pass:** the child's speech started in parallel with call 7 and was released only on pass. Chorus lines were voiced in parallel, and a failed line kept its text.
- **Masking (Step 3):** the transcript and typed lines are masked before calls 1 to 3. `take_turn` masks with `mask_personal` (keeping the five pretend children's names) before call 2. Call 1 gets the masked line, and call 3 reads the masked records. Tested by `tests/practice/test_session.py::test_a_real_childs_name_is_masked_before_any_model_call_but_the_pretend_children_keep_theirs`. **No change was needed.** The 31 October finding no longer applies.

## What changed

**Recording (app):**
- A visible timer counts the seconds to 25.
- At 25 s the recording stops by itself and shows "That is the longest we can listen to at once. Say the rest in a second message."; what was said is still sent.
- A very short or silent clip shows "I didn't catch that. Try again: hold the button while you speak." This is the prompt's sentence plus the existing hint, so the existing voice test keeps passing unchanged.
- When the session's speech allowance is used, the server's 503 carries `voice_off`. The app switches to typing at once and says "Voice is off for the rest of this practice. The text continues." This is not counted as a failure.
- All strings are in en, hi and ta (Hindi and Tamil are drafts for Seema).

**Speech to text (server):** done in Prompt 1's chain path. Convert to 16 kHz mono WAV, trim silence, split at 28 s, pass the session language, join the pieces, drop the audio. Silence is never sent: the API answers 422 and the turn is not scored. The over-30-second refusal stays.

**Children's voices:**
- `content/voices.yaml` `children:` lists Bodhan voices per language by gender. Each child keeps one voice for the session, chosen by seat and the persona's gender, distinct from the lesson narrator.
- The Sarvam fallback is the child's existing speaker and pitch, so a switch keeps each child recognisable.
- `services/speech/cast.py` handles the cast.
- **Style from mood, by code** (`moods:` in the same file): bright to `happy`, small to `sad`, calm, flat and doubtful to the neutral reading. The AI never chooses a voice or a style.
- **Line length:** a gate check limits child lines to 120 characters (`CHILD_LINE_MAX_CHARS`). Recorded AI lines are at most 114 characters and template lines at most 120, so no replay changed.

**Failures and caps:**
- A failed line is text only, and the next turn tries again.
- After **two failures in a row**, the session moves to the next provider for the rest of it. A failure here is no audio at all, or the first provider failing so that a fallback answered. Logged by provider names only.
- Each session has its own speech allowance (`PracticeSession.speech_budget`, from Prompt 1's caps). When it's used up, voice is off for the rest of that practice.

**Rate limit, live turns:** a live turn waits at most `BODHAN_LIVE_PACE_MAX_WAIT_S` (2 s) for Bodhan's allowance before Sarvam speaks. Batch work (lessons, pre-generation) still waits up to 90 s. `default_chain(live=...)` sets which.

**Cache:**
- Lines are cached in memory and in the private audio store (`line-cache/`), so a line said once is free even after a restart.
- `python tasks.py practice-pregen` finds the engine's template lines by playing seeded sessions of every scenario and language. It prints how many lines, voices, styles and languages, with characters, cost and time at Bodhan's limit, and needs `--yes`; `--limit N` voices only some.
- `scripts/voice_audition.py` makes a listening page (`audition/<lang>/index.html`, git-ignored) for choosing the cast.

**Timing:** every voice turn records `layers.evaluation.timing`: speech to text, call 2, engine, call 1, call 7, text to speech, time to first audio, and the provider that spoke. These sit under a new key, so the existing `stages` keys (and their test) are unchanged. `scripts/practice_voice_latency.py` reports medians and 95th percentiles per provider. My first draft of it was written over the existing text-turn latency script, `scripts/practice_latency.py`, by mistake. That script was restored from git unchanged, and the new one has its own name.

## Files

New:
- `services/speech/cast.py`
- `scripts/practice_pregen.py`, `scripts/voice_audition.py`, `scripts/practice_voice_latency.py`
- `tests/speech/test_practice_voice.py` (13 tests)
- `apps/pwa/e2e/practice-voice.spec.ts` (4 tests), `apps/pwa/e2e/fixtures/tone-mic.wav` (a generated tone)

Changed:
- `content/voices.yaml`, `services/speech/service.py` (per-child voice, style, order, persistent cache, `synthesize_ex`, `default_chain(live=)`), `services/speech/chain.py` (order override; style for Bodhan only)
- `services/practice/session.py` (session speech state, moods, engine time), `services/api/practice.py`, `ai/guard/gates.py` (120 characters)
- `scripts/lessons_pregen.py` (patient chain), `tasks.py` (`practice-pregen`), `.gitignore` (`audition/`)
- `apps/pwa/src/screens/Practice.tsx`, `src/lib/voice.ts`, `src/lib/practice.ts`, `src/styles.css`, `strings/{en,hi,ta}.json`
- `docs/help/teacher.md`, `docs/practice-class.md`, `.env.example`, `docs/build/DECISIONS.md`

## Tests

| | Result |
| --- | --- |
| `tests/speech/test_practice_voice.py` (new) | 13 passed: mood to style, seat to voice, a turn with the seat voice and mood style, one chorus child failing (text kept, others voiced), session cap (voice off, text continues), characters cap, store cache across a restart, practice-pregen (finds lines, voices them, serves them with the provider down), two-failure provider switch, 120 characters, silence not scored, timing with the provider, live versus batch pacing |
| `tests/speech`, `tests/practice`, `tests/api`, gates, tasks | **450 passed** |
| Browser `e2e/practice-voice.spec.ts` (new) | 4 passed: the timer and the 25 s auto-stop (Playwright clock), the microphone fed from a tone WAV with the upload's type checked against the supported format, voice off switching to typing at once, axe and Hindi and Tamil at 360 px with the timer showing |
| Browser `e2e/voice.spec.ts` (existing) | 5 passed, unchanged |

No existing test was changed for Prompt 3.

## Live runs (1 Nov)

| Run | Result | Estimated cost (unverified prices) |
| --- | --- | --- |
| `scripts/voice_audition.py --lang hi --yes` | 54 of 54 clips (6 voices × 3 styles × 3 lines), `audition/hi/index.html`, about 7 minutes because of pacing | INR 1.16 |
| `scripts/practice_voice_latency.py --live --yes --turns 3` (9 turns, en, hi, ta) | All 9 turns answered. **Bodhan** (6 turns): text to speech median 7 758 ms, p95 12 812 ms; first audio median 14 742 ms, p95 17 780 ms. **Sarvam** (3 turns): text to speech median 2 202 ms; first audio median 7 905 ms. Speech to text about 1.3 s with both. Call 2 about 1.2 s, call 1 about 2.2 s. Bodhan was paced and its breaker opened; one session moved itself to Sarvam after two failures. Call 7 has no time because your local `.env` has `PRACTICE_SKIP_CHECKER=1` (and `PRACTICE_AI_INTENTS=explain,work_aloud`). `evals/results/practice_voice_latency_live.json` | Claude about USD 0.03, speech about INR 1.8 |
| `python tasks.py practice-pregen --yes --limit 16`, then again | 16 voiced, then **16 served from the store** (a new process: the cache survives a restart). The full set is 981 lines (3 sessions per scenario and language), INR 19.71, about 2 hours at Bodhan's limit: not run | INR 0.33 |

The mock latency run (`evals/results/practice_voice_latency_mock.json`) shows about 1 s of our own ffmpeg conversion in each of speech to text and text to speech on this machine, on top of the provider's time.

## "Done when"

- **Tests pass:** yes.
- **A turn works by voice and by typing with the mock provider:** yes, server and browser.
- **Children speak in distinct voices with moods mapped to styles:** yes, tested.
- **A failure never loses the text:** yes, tested, including a chorus child failing.
- **The audition script and the live latency run work with your keys:** yes, both run.

## Not done, or open

- **Bodhan isn't fit for live Practice Class turns today.** First audio took about 15 s, against Sarvam's 8 s and the 5 s voice target. Its default allowance (8 a minute) runs out within two or three turns. Ask Bodhan to raise the limit, then measure again. Until then the chain falls back to Sarvam.
- **The full template-line pre-generation** (981 lines, about 2 hours at the current limit) and **the Tamil and English auditions** were not run. Run them when the limit is higher: `python tasks.py practice-pregen --yes` and `python scripts/voice_audition.py --lang ta --yes`.
- **Every voice and the mood map** are `TODO-HUMAN(Seema)`: listen on `audition/hi/index.html`.
