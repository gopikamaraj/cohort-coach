# Speech evaluation, gates and rollout (Prompt 4)

Built on 1 Nov 2026 on branch `speech-bodhan`, from Prompt 4 of `docs/build/bodhan-speech-prompts.md`. Live scripts were run because you chose that. No slide was edited; the deck sentences to change are listed below.

## Where things stand

- **Both gates `pending`** (`docs/evidence/speech_gates.md`). The listening pack is made live and is ready for raters. The speech-to-text test needs team members' recordings. Rollout is at **stage 1, development only** (`docs/build/SPEECH-ROLLOUT.md`).
- **Bodhan is cheaper but slower.** At unverified prices a lesson costs about ₹2.1 to ₹2.4 with Bodhan and ₹10.5 to ₹11.8 with Sarvam (`docs/evidence/speech_cost.md`).
- **Bodhan's speed and limit rule it out for live use today.** Its text to speech is 4 to 6 times slower than Sarvam's in a 120-call live run, and its default limit is about 8 requests a minute. It shouldn't be first in any deployment teachers use until it passes both gates and the limit is raised.

## What was built

| Step | What | Where |
| --- | --- | --- |
| 1 Listening pack | `python tasks.py speech-eval-pack`. Per language, 20 scripts (10 lesson sentences with numbers, sums and the maths words borrow and regroup; 10 child lines, two per mood), each voiced by 2 Bodhan and 2 Sarvam voices. Blinded file names; the key in its own file; a self-contained offline rating page (embedded clips; four 1 to 5 scores and a comment per clip; saves a CSV). `scripts/speech_eval_aggregate.py` gives the means per provider, voice and language, the "numbers wrong" share and the gate | `content/speech_eval/scripts.yaml`, `scripts/speech_eval_pack.py`, `scripts/speech_eval_aggregate.py`, `services/speech/evaluation.py` |
| 2 Speech-to-text test | A recording protocol (team members only, real phones, tags for phone and noise) and `python tasks.py speech-eval-stt`. It reports character and word error rates after normalising digits and number words, number accuracy and key-term accuracy, per language and tag, plus the worst items. Raw transcripts stay in the git-ignored `data/speech-eval/`; only numbers go to `evals/results/` | `docs/evidence/speech-eval/PROTOCOL.md`, `scripts/speech_eval_stt.py` |
| 3 Latency and cost | `python tasks.py speech-latency`: 30 calls per function and provider, median and p95 by input size, Bodhan paced outside the timing. `scripts/speech_cost.py` writes the cost per lesson and per session from measured inputs | `scripts/speech_latency.py`, `scripts/speech_cost.py`, `docs/evidence/speech_cost.md` |
| 4 Gates | The front matter `bodhan_tts` / `bodhan_stt` (pending, pass or fail), the date and who decided. Thresholds in config (`TODO-HUMAN(Gopi, Seema)`). The scripts always print each gate against its threshold, and write it only with `--record NAME`, never a pending result. The startup warning reads the file | `docs/evidence/speech_gates.md`, `content/speech_gates.yaml` |
| 5 Shadow mode | `SPEECH_SHADOW_PROVIDER` (off by default): after the main transcript, the same audio goes to the other provider in the background. Only a similarity score and the latency are logged. Rate-limited (`SPEECH_SHADOW_PER_MINUTE`), and counted in the session's speech allowance | `services/speech/service.py` |
| 6 Privacy, consent, licence | The consent text and privacy page now say a teacher's recording goes to a third-party speech service (Bodhan AI or Sarvam) and is not kept by us (en, hi, ta). `docs/vendors/bodhan/TERMS-CHECK.md` is the template for you to fill in. The attribution "Voices and speech recognition: Bodhan AI / AI4Bharat (Indic-Speak, Indic-Transcribe)" is in the README and the About tab, and "The children's voices are AI-generated" sits by the Practice Class voice controls | `strings/*.json`, `docs/privacy.md`, `apps/pwa/src/screens/Assistant.tsx`, `Practice.tsx` |
| 7 Outage and rollout | A test with both providers down: published lessons and cached template lines still play, and the text always shows. Five rollout stages, each with its check | `tests/speech/test_outage_privacy.py`, `docs/build/SPEECH-ROLLOUT.md` |
| 8 Docs | README, `.env.example`, `docs/help/coach.md`, `docs/RUBRIC_MAP.md` (E3.3), `docs/build/DECISIONS.md` | |

## Tests

| | Result |
| --- | --- |
| `tests/speech/test_evaluation.py` (new) | 10 passed: blinding and its key, aggregation arithmetic on fixed ratings (including rejected rows), the TTS gate (pass, fail, pending), number normalisation in speech-to-text items, the STT summary and gate, `record` (only pass or fail, needs a name) and the startup warning, the aggregate script recording only with `--record`, the STT script with no recordings, the pack plan and the page's labels, and shadow mode (off by default; logs similarity and latency only, never text; rate-limited; counted in the cap) |
| `tests/speech/test_outage_privacy.py` (new) | 2 passed: the outage test, and no audio, transcript or key in any log, metadata row or stored record |
| All of `tests/speech`, plus tasks, rule-11 wording and `AI_USAGE.md` checks | **159 passed** |
| Browser `e2e/speech-rating.spec.ts` (new) | 1 passed: a rater scores clips and saves a CSV; nothing is fetched; axe passes |
| Browser practice-voice, voice, lesson-voice, speech-rating, assistant, practice | 39 of 40 in one batch. `practice.spec.ts` "a class's own counts seat the children…" failed in the batch and passed alone twice: an order-dependent flake |

Metric bugs found by the new tests and fixed: key terms were matched as prefixes ("ten" matched "tens" and "tents"), and checked after number words became digits ("ten" became "10"). Terms now match whole words, on text without the number conversion.

## Live runs (1 Nov)

| Run | Result | Estimated cost (unverified prices) |
| --- | --- | --- |
| `python tasks.py speech-eval-pack --yes` | **240 of 240 clips** (120 Bodhan, 120 Sarvam), `evals/speech-eval/pack-2026-11-01/rate.html` and `key.json` (git-ignored). This pack's page was made before the `<main>` landmark fix; packs made from now on have it | INR 19.52 |
| `python tasks.py speech-latency --yes` | **120 of 120 calls succeeded** (English; `evals/results/speech_latency.json`). Text to speech, median (p95): Bodhan short 2 750 ms (3 217), medium 7 538 ms (9 140), long 13 780 ms (14 811); Sarvam short 625 ms (907), medium 1 164 ms (1 531), long 2 242 ms (2 390). Speech to text: Bodhan 516, 640 and 821 ms; Sarvam 218, 296 and 359 ms. **Bodhan's text to speech is 4 to 6 times slower than Sarvam's**, and its speech to text about twice as slow | INR 11.73 |
| `python scripts/speech_cost.py` | `docs/evidence/speech_cost.md`. Lesson (6 measured per language): Bodhan INR 2.37 en and 2.10 hi; Sarvam INR 11.85 en and 10.49 hi. A voice practice session (31 turns, 60 child lines, simulated; teacher speech assumed at 6 s a turn): Bodhan INR 1.39, Sarvam INR 6.94 | free |
| `python tasks.py speech-eval-stt` | Not run: no recordings yet (needs people, per the protocol) | — |
| Aggregation and `--record` | Not run: no ratings yet (needs raters) | — |

## The deck sentences to change once the gates pass (no slide edited)

| File and line | Sentence today | Change once both gates pass |
| --- | --- | --- |
| `docs/submission/deck.md:33` and `slides.md:34` | "...child's line (call 1), checker (call 7), voice." | Name the speech layer: "voice (Bodhan AI first, Sarvam as the fallback, behind gates)". Cite `docs/evidence/speech_gates.md` |
| `docs/submission/deck.md:41` and `slides.md:42` | "Computed worst-case data per track: `docs/evidence/data_budget.json` (met with text practice, missed if every session uses voice)." | Now false on this branch: lessons are MP3 48 kbps and the worst case is 14.73 MB with text practice. Put in the new target and figure once you've set it (Prompt 2) |
| `docs/submission/deck.md:53` and `slides.md:58` | "Cost per teacher per track: `docs/evidence/cost_per_teacher.md` (a range; assumptions stated)." | Add the speech cost per lesson and per session from `docs/evidence/speech_cost.md`, with the prices marked verified only after you confirm them |
| `docs/submission/video-script.md:12` | "The lesson reaches her as a voice note..." | Unchanged for the web app. If the bot ships, MP3 lessons need `sendAudio`, not a voice note |
| Architecture and AI-use slides | Speech shown as Sarvam | Show the provider chain with the gates; latency per provider from `evals/results/speech_latency.json` and `practice_voice_latency_live.json` |

## "Done when"

- **The listening pack:** yes, made live. **The speech-to-text pack:** yes, the script and protocol are built; it waits for recordings.
- **The aggregation prints each gate against its threshold:** yes, tested.
- **The gates file and startup warning work:** yes, tested.
- **The outage test passes:** yes.
- **The terms template exists:** yes.
- **The report lists every deck sentence to update:** yes, above.

## For you to do

1. Send `rate.html` to raters (Seema, two teachers, Gopi). Collect their `ratings-*.csv` into the pack folder, then run `python scripts/speech_eval_aggregate.py evals/speech-eval/pack-2026-11-01 --record "Name"`.
2. Record the speech-to-text set (`docs/evidence/speech-eval/PROTOCOL.md`), then run `python tasks.py speech-eval-stt --yes --record "Name"`.
3. Confirm the prices on the Bodhan console. Mark them `verified: true` in `content/speech_prices.yaml`, then run `python scripts/speech_cost.py`.
4. Fill in `docs/vendors/bodhan/TERMS-CHECK.md`, and ask Bodhan to raise the rate limit.
5. Confirm or change the gate thresholds (`content/speech_gates.yaml`), and the Hindi and Tamil script wording (`content/speech_eval/scripts.yaml`).
