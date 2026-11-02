# Bodhan speech (TTS and STT): four Claude Code prompts, run one by one

How to use this file:

1. Put it in the repo, for example `docs/build/prompts/bodhan-speech-prompts.md`.
2. Start Claude Code at the repo root and paste the **Runner prompt** below.
3. Say `run prompt 1`. When it reports back, read the report, check its "Done when", then say `run prompt 2`, and so on.
4. Do all of it on a branch (`speech-bodhan`). **Do not merge into the evaluated version after the 1 Nov 2026, 11:59 PM IST freeze.**

Before you start, do these yourself (Claude Code cannot):

- Put your two keys in `.env` (names in Prompt 1). Never paste a key into the chat.
- Top up the Bodhan account. New accounts start with a small credit only.
- Read Bodhan's terms and privacy information for the audio and text you send (retention, training use, hosting region). Prompt 4 asks you to record the answer.

---

## Runner prompt (paste first)

```text
You will work from the file docs/build/prompts/bodhan-speech-prompts.md.
It holds four prompts (Prompt 1 to Prompt 4) and a Shared facts section.

Rules for this whole job:
- Work on branch speech-bodhan. Never commit to main. Never merge.
- Run ONE prompt at a time, only the one I name. When it is finished:
  run its tests, write its report, show git status and a short summary
  (what changed, test counts before and after, anything not done and why),
  then STOP and wait for me to say "run prompt N".
- Do not start the next prompt on your own. Do not do work from a later prompt early.
- Never print, log or commit a key. Read keys only from environment variables.
- No live paid calls in automated tests. Live calls happen only in scripts
  I run on purpose, and each one prints its estimated cost first.
- Never weaken or delete a test to make it pass. If a test must change, say why.
- If something in the prompt conflicts with the code you find, tell me before choosing.
Acknowledge, then wait for "run prompt 1".
```

---

## Shared facts (every prompt reads this)

**From Bodhan's API reference** (`https://console.bodhan.ai/api-docs/`, read on 1 Nov 2026). Claude Code must re-read the page when it runs, save a dated copy to `docs/vendors/bodhan/api-reference.md`, and **trust the page over this summary**. If it cannot fetch the page, stop and ask the user to save it there.

- **Base:** `https://api.bodhan.ai`. Auth is `Authorization: Bearer <key>` on every request.
- **Speech to text:** `POST /v1/audio/transcriptions`, `multipart/form-data` with `file` (required), `model` = `indic-transcribe` (required), `language` (optional, but pass it: `hi`, `ta`, `en` and others).
  - Documented format is WAV. FLAC, OGG and MP3 are accepted. **M4A, AAC, WebM and AMR are refused with HTTP 415.**
  - **Each request takes up to 30 seconds of audio**; longer audio is rejected. Billing is per second of audio, so trim silence first.
  - Response `200`: `{ "text": "..." }`. No timestamps and no confidence.
- **Text to speech:** `POST /v1/audio/speech`, JSON with `model` = `indic-speak`, `input`, `voice` (a name), and `instructions`, **a JSON string** such as `"{\"lang\": \"hi\", \"style\": \"educational lecture\"}"`.
  - `lang` is required. `style` is optional. Styles include: `AIR style news`, `Customer Care`, `TV style news`, `advertisements`, `anger`, `children's stories`, `disgust`, `educational lecture`, `fear`, `happy`, `news`, `sad`, `single person narration audiobook`, `surprise`.
  - Voices (45), any voice can read any language. Hindi: `Kavya`, `Suhani` (female), `Amit` (male). Tamil: `Anitha` (female), `Arun` (male). Other languages have their own named voices in the page.
  - **Keep each request to a sentence or two, about 30 seconds of speech. Longer text is not split for you.**
  - Numbers, dates and currency are read out in the language given.
  - Response: `audio/wav`, PCM16, 24 kHz, mono. A bad voice, language or style gives `422`.
- **Rate limits:** other endpoints return `x-ratelimit-limit-requests`, `x-ratelimit-limit-parallel-requests` and `x-request-id` headers. Assume the speech endpoints do too, read them if present, and count retries against the limit.
- **Other endpoints** (translation, transliteration, document OCR) are **not used** in these prompts.
- **Keys:** the page shows one variable, `BODHAN_API_KEY`. An earlier article said keys are issued per model. So use two variables that may hold the same value or different ones.
- **Prices are not on that page.** Figures seen in an article (unverified, check `https://console.bodhan.ai/#pricing`): text to speech 6 rupees per 10,000 characters, speech to text 0.10 rupees per audio minute. Sarvam, for comparison, from our cost model: about 30 rupees per 10,000 characters and 30 rupees per hour.
- **Licence note:** Bodhan's open model weights require the attribution "Built with Indic-Speak from Bodhan AI / AI4Bharat" and restrict multi-tenant hosting without approval. The hosted API's own terms may differ. Add the attribution anyway.
- Do not confuse Bodhan AI with Navana.ai's "Bodhi TTS", a different product.

**In our repo (verify, do not assume):** Sarvam is the current speech provider (speech to text on her recording, text to speech for children's voices and lessons), reached through the `services` layer (see `services/api/practice.py` and the existing speech module). Practice Class turn order: speech to text, mask, call 2 (move label), engine, call 1 (child line), call 7 (checker), text to speech started in parallel with the checker. Lessons come from call 5 (Opus). Test modes: `AI_MODE` (`live`, `recorded`, `off`) for Claude calls, and a voice mode for speech.

**Hard rules for all four prompts:** no child names or child voices; no audio stored beyond what is needed (a teacher's recording is dropped after transcription); the text is always shown; counts not percentages for teachers; every user-facing string in `en`, `hi` and `ta`; follow `docs/design/stitch/DESIGN.md`; code decides, the AI words; evidence for every statement in the reports.

---

## PROMPT 1: the speech layer, with Bodhan as the first provider

**Task.** Put all speech behind one provider interface. Add Bodhan (speech to text and text to speech) as the **first** provider, keep Sarvam as the fallback, and keep everything testable without live calls.

**Step 0. Read first.** `CLAUDE.md`, `DECISIONS.md`, `docs/design/stitch/DESIGN.md`, `AI_USAGE.md`, the existing speech and voice code and its tests, how recorded and test voice modes work, the Dockerfile and deploy config, `.env.example`, settings, the observability or call-log wrapper (if built), and `docs/vendors/` (create it). Fetch the Bodhan page and save `docs/vendors/bodhan/api-reference.md` with the date.

**Step 1. The interface.** `SpeechProvider` with:

- `transcribe(audio, language) -> Transcript(text, seconds_billed, provider, request_id)`
- `synthesize(text, language, voice, style) -> Audio(bytes, format, sample_rate, seconds, chars_billed, provider, request_id)`
- `capabilities`: max audio seconds per request (Bodhan 30), accepted formats, the speech length hint, the voices and styles it supports.

Adapters: **Bodhan** (new), **Sarvam** (wrap what exists, without changing its behaviour), **Mock** (tests), and the existing recorded mode. A language map in config: app `en`, `hi`, `ta` to each provider's codes (Sarvam uses its own codes).

**Step 2. Bodhan adapters.** Use `httpx` with explicit timeouts (connect 5 s, read: speech to text 20 s, text to speech 30 s, all configurable).

- Speech to text: send multipart with `file`, `model=indic-transcribe`, and `language` always when known. Send only accepted formats. Never send audio over 28 seconds (Step 4 splits it).
- Text to speech: build `instructions` as a JSON **string** (`json.dumps` of `{"lang": ..., "style": ...}`, omitting `style` when none). Reject empty input. Refuse input above the configured length with a clear error so callers split first (Prompt 2 does the splitting). Read the WAV header to get the real duration.
- Map responses: `401` (key problem, no retry), `415` (a bug in our conversion, no retry, log loudly), `422` (bad voice, language or style, no retry, log the unknown value), `429` and `5xx` (retry once with backoff and jitter, respecting `Retry-After`), timeouts (retry once).
- Never log a key, an audio body, or a transcript. Log provider, model, characters or seconds, latency, status and `x-request-id`.

**Step 3. Provider order and fallback.**

- Config: `SPEECH_TTS_PROVIDERS=bodhan,sarvam` and `SPEECH_STT_PROVIDERS=bodhan,sarvam`, with optional per-language overrides. A provider with no key configured is skipped automatically.
- Fallback rules: an error, timeout, `429` or open circuit moves to the next provider. A `4xx` request error does not (it is our bug). A **circuit breaker** per provider and function opens after 3 failures in 60 seconds and tries again after 30 seconds. Every fallback is logged and counted.
- **A startup warning** (log only) if Bodhan is first while `docs/evidence/speech_gates.md` does not say both gates passed (Prompt 4 writes that file). It must not block the app.

**Step 4. Audio utilities** (`services/speech/audio.py`). First check that `ffmpeg` exists in the container and in dev, and add it to the Dockerfile and the README if it does not.

- `to_wav_16k_mono(bytes) -> bytes` for speech to text. It accepts what phones produce (WebM, M4A, OGG, MP3, WAV). **This is the fix for Bodhan's 415 on WebM and M4A.**
- `trim_silence(wav)`: remove leading and trailing silence and shorten long pauses, to cut billed seconds.
- `split_for_stt(wav, max_seconds=28)`: split at silence into pieces of at most 28 seconds; if no silence is found, split at the limit. Property: no piece exceeds 28 seconds, and the pieces together keep all the speech.
- `wav_to_mp3(wav, kbps=48, mono=True)` for stored lessons and offline downloads, plus `duration_seconds`, `loudness_normalise` (about -16 LUFS), and `concat(pieces, gap_ms)`.
- All of these have unit tests with generated audio (tones and silence), never real voices.

**Step 5. Costs.** `content/speech_prices.yaml` with the price per unit for each provider and function, each marked `verified: false` and the source and date. Compute cost per call, attach it to the log, and add per-session caps (configurable) for speech to text seconds and text to speech characters. When a cap is hit, behave as text-only and say so.

**Step 6. Keys and a smoke test.**

- Environment variables: `BODHAN_SPEAK_API_KEY`, `BODHAN_TRANSCRIBE_API_KEY` (each falls back to `BODHAN_API_KEY` if unset), `BODHAN_BASE_URL` (default `https://api.bodhan.ai`), `SARVAM_API_KEY` as today. Add all to `.env.example` and the README's list of external services. Settings report only whether a key is present, never its value.
- `scripts/check_bodhan.py` (reads `.env`, standard library or `httpx` only, never prints a key beyond its first 4 characters): check each key separately. It synthesizes one short Hindi sentence, then transcribes that audio back, and prints the text, durations, sizes, request ids and the estimated cost. Exit codes tell speak-key failure, transcribe-key failure and success apart. `--no-live` checks configuration only.

**Step 7. The mock server for tests.** A small local server (or `httpx.MockTransport`) that imitates Bodhan: valid WAV output (24 kHz, mono, PCM16), a `{text}` reply, and switchable `401`, `415` (for WebM, M4A, AAC, AMR), `422`, `429` with headers, `500`, and slow replies. Contract tests encode the documented constraints (formats, 30 seconds, `instructions` as a JSON string).

**Step 8. Tests (write first where the logic is pure).** Request building (the `instructions` string, the multipart fields, the language always passed), every status mapping, retry and fallback order, the circuit breaker, key skipping, the audio utilities (including the 28-second property), cost and caps, key masking in logs, and the startup warning. Existing speech tests still pass. Report test counts before and after.

**Step 9. Report and docs.** `docs/build/reports/SPEECH-LAYER.md` (what changed, the file list, the status mapping, anything unclear in Bodhan's docs); `DECISIONS.md` (entry dated today); `AI_USAGE.md` and the README (external services, keys, `ffmpeg`).

**Done when** the tests pass with no live call, a mock-server run shows Bodhan first and Sarvam as fallback, `check_bodhan.py --no-live` works, and I can run `check_bodhan.py` live with my keys.

---

## PROMPT 2: audio lessons with Bodhan

**Task.** Generate lesson audio (from call 5's script) with the speech layer: split, voice, stitch, check, cache, and review. Everything runs offline in batch, so latency does not matter but consistency and cost do.

**Step 0. Read first.** The lesson pipeline (call 5, the review queue, the lesson player, offline download), `services/speech/`, `content/` for lessons and voices, the Dockerfile (ffmpeg), the audit trail, and Prompt 1's report.

**Step 1. Voices and style config.** `content/voices.yaml`: for each of `en`, `hi`, `ta`, a lesson narrator voice and the style (`educational lecture`), with the fallback provider's voice alongside. Defaults: Hindi `Kavya`, Tamil `Anitha`, English a voice that reads `en` well. Mark each `TODO-HUMAN(Seema): confirm by listening`. A lesson uses one voice from start to finish.

**Step 2. Sentence splitting and chunking.**

- Split the script into sentences, aware of `।`, `.`, `?`, `!`, and the script's own rules. Do **not** split inside numbers or sums (for example `703 − 468`, `3.5`). Respect paragraph and section markers in the script.
- Group sentences into chunks of one or two sentences with a configurable target (start at 220 characters, hard maximum 300). After synthesis, measure the real duration; if a chunk exceeds 28 seconds, split it again and redo it.
- Provide `scripts/calibrate_chunks.py` (live, opt-in, prints estimated cost first): synthesizes sample sentences per language and voice and reports characters per second, so the target can be set from evidence.

**Step 3. Generate, stitch, store.**

- Generate chunks in parallel with a configurable limit (start at 3, lower it when rate-limit headers say so). Retry a chunk once.
- **Lesson-level fallback:** if a chunk still fails, regenerate the **whole lesson** with the next provider and its voice, so the voice never changes mid-lesson. If every provider fails, the lesson stays text-only with a clear status and a retry.
- Stitch the chunks in order with 250 ms of silence between sentences and 500 ms between sections, normalise the loudness, and encode **MP3, mono, 48 kbps** (configurable). Keep a `timing map` (sentence index, start and end in seconds), so the player can highlight the script text as it plays.
- **Cache** each chunk by `sha256(provider, model, voice, language, style, normalised text, pipeline version)` in private storage, and store the stitched lesson with its version. A repeated lesson makes no provider call. Keep old versions until a coach approves the new one.

**Step 4. The round-trip check.** After generating a chunk, transcribe it back with speech to text (the same provider by default, configurable) and compare it with the chunk's text after normalising punctuation and numbers. Compute a character error rate per chunk. Chunks above a threshold (configurable, start at 0.25) are regenerated once, and then flagged. The lesson gets a summary ("14 of 15 sentences passed the check; 1 to listen to"). The check never blocks release by itself. A coach reviews every lesson.

**Step 5. The coach review screen.** Extend the existing lesson review screen: play the audio, see the script with sentence highlighting from the timing map, see the round-trip flag on each sentence, and the provider and voice used. Actions: **Regenerate this sentence** (shows its estimated cost, replaces only that chunk and re-stitches), **Regenerate the lesson**, **Approve**. All actions are written to the audit trail. A visible label "AI-generated voice" appears on the lesson page for teachers. In judge mode the existing demo badge stays. Offline download shows the file size.

**Step 6. Pre-generation for the demo.** `python tasks.py lessons-pregen`: prints the number of characters and the estimated cost, asks for `--yes`, then generates and caches audio for all demo lessons in every language. A test proves the demo lesson plays from the cache with every provider disabled.

**Step 7. Tests.** Sentence splitting for English, Hindi and Tamil (with sums and decimals), chunk sizes and re-splitting, stitching duration equals the sum plus the gaps, the timing map offsets, cache hits and version changes, chunk retry, **whole-lesson fallback**, the round-trip flags (the mock returns altered text), regenerate one sentence touches only that chunk, MP3 validity (`ffprobe`), audit entries, and roles (only coach and reviewer can regenerate or approve). Browser tests for the review screen and the player highlighting, with axe checks and Hindi and Tamil fit at 360 px.

**Step 8. Report and docs.** `docs/build/reports/SPEECH-LESSONS.md`; `DECISIONS.md` (entry dated today); update `docs/help` for coaches (the review screen) and the README.

**Done when** a lesson in each language can be generated with the mock, stitched, checked, reviewed and played with highlighting, the demo lessons play from the cache with providers off, and the live calibration script works with my keys.

---

## PROMPT 3: Practice Class speech with Bodhan

**Task.** Use the speech layer for the teacher's speech in and the children's voices out, within Bodhan's limits, with the engine's mood driving the voice style.

**Step 0. Read first.** The Practice Class flow (`services/api/practice.py`, `services/practice/*`, the simulator and its moods, call 1, 2 and 7), the recording component in the web app, how text and voice modes work, the cost caps, and Prompts 1 and 2's reports.

**Step 1. Recording in the browser.**

- Choose the recording format by capability (`MediaRecorder.isTypeSupported`), and send the file as recorded. The server converts it (Prompt 1), so no format is refused.
- A **visible timer** counting to 25 seconds, and auto-stop at 25 seconds with the message: "That is the longest we can listen to at once. Say the rest in a second message." Very short or silent recordings give "I didn't catch that. Try again." Silence is never scored.
- Typing stays available and unchanged. All new strings in `en`, `hi` and `ta`.

**Step 2. Speech to text on the server.** Convert to 16 kHz mono WAV, trim silence, split at 28 seconds if needed (never send more than 30), pass the session language, and join the transcripts with a space. Use the provider chain with fallback. Drop the audio as soon as the transcript exists, and store no audio.

**Step 3. Mask before the AI calls.** Check that the transcript (and typed lines) are masked **before calls 1 to 3**. The 31 October repository report said they were not. If it is still missing, add masking with the existing function (keeping the five pretend children's names), with tests. Say in the report what you found.

**Step 4. The children's voices.**

- `content/voices.yaml`: a voice cast for the five seats per language, each seat a fixed voice for the session, chosen from the voice pool (mixed female and male, distinct from the lesson narrator). Include the fallback provider's voice for each seat. Mark `TODO-HUMAN(Seema): confirm by listening`.
- **Style from mood, decided by code:** `bright` to `happy`, `small` to `sad`, and `calm`, `flat` and `doubtful` to no style (the voice's default). Put the map in config. Never let the AI choose a style.
- Child lines are one or two short sentences. Keep the existing length validator and make sure a line cannot exceed about 120 characters, so it is far below 30 seconds of speech.
- Keep the current design where speech is started in parallel with the checker and released only if the line passes. When several children speak in a turn (the chorus, up to three), generate them in parallel within the concurrency limit and play them in order. If one fails, that child's line is text only.
- The text is always shown immediately and the audio plays when ready.

**Step 5. Template lines are cached.** The engine's template lines are a finite set. `python tasks.py practice-pregen` prints how many lines, voices, styles and languages it would generate, the characters and the estimated cost, asks for `--yes`, then caches them. Dynamic lines are generated live. Add an audition script `scripts/voice_audition.py` (live, opt-in, prints the estimated cost first) that generates three sample child lines in each mood with a chosen list of voices (default: all voices for a language) into a folder with a simple HTML page, so Seema can listen and choose the cast.

**Step 6. Failure behaviour in a session.** On a failure, that turn's line is text only and the next turn tries again. After two failures in a row, switch to the next provider for the rest of the session, using the matching fallback voices. Log each switch. Respect the per-session caps from Prompt 1 and show "voice is off for the rest of this practice, the text continues" when a cap is hit.

**Step 7. Latency.** Record the time of every stage per turn (speech to text, call 2, engine, call 1, call 7, text to speech, first audio) in the existing practice latency result, per provider. Do not enforce a target. Report the medians and the 95th percentiles from a mock run, and add an opt-in live run for my keys.

**Step 8. Tests.** The recording limit and the timer; format selection; server conversion of WebM, M4A, OGG and MP3; the 30-second guarantee as a property test with long audio; silence trimming; empty and very short audio; the language passed; speech to text fallback; mood to style; the seat to voice mapping; chorus in parallel and a partial failure; the cost cap and the text-only message; template-line cache hits; masking before calls 1 to 3; the two-failure provider switch. Browser tests with a fake microphone (Chromium flags `--use-fake-device-for-media-stream` and `--use-file-for-fake-audio-capture` with a WAV file), the recorded and mock modes, axe, and Hindi and Tamil at 360 px.

**Step 9. Report and docs.** `docs/build/reports/SPEECH-PRACTICE.md`; `DECISIONS.md` (entry dated today); update `docs/help/teacher.md` (recording limit) and `docs/practice-class.md`.

**Done when** the tests pass, a Practice Class turn works by voice and by typing with the mock provider, children speak in distinct voices with moods mapped to styles, a failure never loses the text, and the audition script and live latency run work with my keys.

---

## PROMPT 4: evaluation, gates and rollout

**Task.** Decide with evidence whether Bodhan stays first, record the gates, and finish the rollout, privacy and documentation work. Make the evaluation easy for people (Seema, two teachers, Gopi) to do.

**Step 0. Read first.** The three earlier reports, `evals/`, `docs/evidence/`, the cost model notes in the docs, the consent text and privacy page, and the README.

**Step 1. The listening test pack.** `python tasks.py speech-eval-pack`: for each of `en`, `hi` and `ta`, 20 scripts (10 lesson sentences with numbers, sums such as "703 minus 468", and mixed English maths words like "borrow" and "regroup"; 10 child lines, some in each mood). Generate each script with Bodhan (two or three candidate voices) and with Sarvam (matching voices). Give each file a random blinded name, and write the key to a separate file. Produce a **self-contained offline HTML rating page**: for each clip the rater scores naturalness, clarity, correct numbers, and suitability (1 to 5), plus a free comment, and exports a CSV. A second script aggregates the CSVs with the key: means per provider, voice and language, and the rate of "numbers wrong". Print the estimated cost first (a few rupees).

**Step 2. The speech to text test.** Provide a recording protocol (`docs/evidence/speech-eval/PROTOCOL.md`) and a git-ignored folder `data/speech-eval/`: 30 short utterances per language, read by team members (no children), with math talk (numbers, "borrow", "regroup", "ten", "bundle"), recorded on real phones, with a CSV of reference transcripts and tags for phone and noise. `python tasks.py speech-eval-stt` transcribes with Bodhan and Sarvam and computes the character error rate, the word error rate, and the **accuracy of numbers and key maths terms**, per language and tag, and writes a list of the worst items for review. Normalise numbers (digits and words) before comparing. Print the estimated cost first.

**Step 3. Latency and cost.** `python tasks.py speech-latency` (live, capped, opt-in): 30 calls per function and provider, giving the median and 95th percentile by input size. Write `docs/evidence/speech_cost.md` with the measured cost per lesson and per Practice Class session for each provider, using the verified price values (ask me to confirm the prices from the Bodhan console and mark `verified: true` only then).

**Step 4. The gates.** `docs/evidence/speech_gates.md` with a front-matter block: `bodhan_tts: pending|pass|fail`, `bodhan_stt: pending|pass|fail`, the date, and who decided. Default thresholds in config, each marked `TODO-HUMAN(Gopi, Seema): confirm`: for example, text to speech: mean naturalness within 0.3 of Sarvam and "numbers wrong" under 5 percent; speech to text: character error rate no more than 5 points worse than Sarvam and key-term accuracy at least 90 percent. The aggregation scripts print each gate's result against its threshold and write the front matter only when a person passes `--record` with their name. The startup warning from Prompt 1 reads this file.

**Step 5. Shadow mode.** Add an optional setting `SPEECH_SHADOW_PROVIDER` for speech to text in Practice Class: after the primary provider answers, call the shadow provider with the same audio and log **only a similarity score and the latency** (never the texts). It is off by default, rate-limited, and counted in the session cap.

**Step 6. Privacy, consent and licence.**

- Update the consent text and privacy page: a teacher's voice recording is sent to a third-party speech service to be turned into text, and is not kept by us. Provide `en`, `hi` and `ta`.
- Add a `docs/vendors/bodhan/TERMS-CHECK.md` for me to fill in: retention, use for training, hosting region, any DPA, and whether the hosted terms require attribution. The prompt only creates the template.
- Add the attribution "Voices and speech recognition: Bodhan AI / AI4Bharat (Indic-Speak, Indic-Transcribe)" to the README and the About screen, and a small "AI-generated voice" label where the voice plays.
- Confirm in a test that no audio, transcript or key appears in any log or in any stored record.

**Step 7. Outage test and rollout stages.**

- An end-to-end test that runs the demo path with **both providers disabled** and shows lessons and template lines playing from cache, and text always shown.
- Write the rollout stages in `docs/build/SPEECH-ROLLOUT.md`: (1) development only; (2) shadow mode on speech to text; (3) Bodhan first for lesson generation, with coach review; (4) Bodhan first for Practice Class after both gates pass; (5) keep Sarvam as the fallback permanently. Each stage lists its check.

**Step 8. Documentation and the claims to change later.** Update the README's external services and configuration, `.env.example`, `docs/help`, and `RUBRIC_MAP.md`. **Do not edit any slide.** Instead write `docs/build/reports/SPEECH-ROLLOUT.md` with a list of the deck sentences that will need to change once the gates pass (the architecture and AI-use slides, and the cost per teacher), with the measured numbers to put in.

**Step 9. Tests.** Aggregation maths on fixture ratings, the blinding key, number normalisation, the gate logic and `--record`, the shadow mode logging, the outage test, the privacy test, and axe on any new screen. All existing suites still pass.

**Done when** I can run the listening and speech to text packs, the aggregation prints each gate against its threshold, the gates file and startup warning work, the outage test passes, the terms template exists, and the report lists every deck sentence to update.
