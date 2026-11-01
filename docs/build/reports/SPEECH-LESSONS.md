# Lesson audio with Bodhan (Prompt 2)

Built on 1 Nov 2026 on branch `speech-bodhan`, from Prompt 2 of `docs/build/bodhan-speech-prompts.md`. Your answers before the run: lessons are **MP3 mono 48 kbps**; **coach audio review comes after publishing and is optional**; **run the live scripts**; **one commit per prompt**.

## What changed

Lessons are now voiced by `services/speech/lessons.py`:

1. **Split.** Sentences end at `.` `?` `!` `।` or a line break, and a blank line starts a new section. A full stop between digits (3.5) and the signs in a sum (703 − 468) never split.
2. **Chunk.** Each chunk holds one or two sentences of one section: 220 characters as the target, 300 at most. A longer sentence is cut at commas or spaces.
3. **Voice.** Chunks are voiced in parallel, up to 3 at once, with one retry per chunk. If a chunk still fails, the *whole lesson* is made again with the next provider and its voice, so a lesson never changes voice part-way. If every provider fails, the lesson is published as text only (`audio_status: text_only`).
4. **Re-split.** A chunk whose audio is over 28 seconds is split into its sentences and voiced again.
5. **Cache.** Each chunk is stored in private storage under sha256(provider, model, voice, language, style, normalised text, pipeline version). A repeated lesson makes no provider call, and a fully cached lesson plays even with every provider down.
6. **Round-trip check.** Each chunk is transcribed back and compared with its text, by character error rate after normalising punctuation and numbers (`services/speech/textnorm.py`). Above 0.25, the chunk is made once more and then flagged. The check never blocks a lesson.
7. **Stitch.** Chunks are joined with 250 ms between sentences and 500 ms between sections, normalised to about −16 LUFS, and encoded as MP3 mono at 48 kbps. A timing map records each sentence's start and end. Inside a two-sentence chunk the split is by characters, an estimate.

`services/content/publish.py` now voices lessons through this pipeline and keeps one record per lesson revision in a new table, `lesson_audio` (`services/content/lesson_audio.py`). The manifest part carries the MP3 key, size, length, sentences, timing map, provider, review status and `ai_voice: true`.

**Coach review** (`/api/review/lesson-audio`, panel `LessonAudioReview` on the review screen):
- **Who can do what:** the coach and the officer can list and listen. Only the coach can regenerate or approve.
- **What the coach sees:** the script highlighted as it plays, a warning mark on each flagged sentence, and the provider, voice, size and length.
- **Regenerate this sentence** shows its estimated cost and makes only that chunk again on the same provider; the rest comes from the cache.
- **Regenerate the lesson** makes the whole lesson again from scratch.
- **Approve** points the manifest to the new revision and deletes older revisions' files. Until then, teachers keep hearing the approved or published version.
- **Audit:** every action writes a `ContentAudit` row (`voice_lesson`, `regen_sentence`, `regen_lesson`, `approve_audio`), with ids and counts only.
- **Small cohorts:** a lesson whose cohort has fewer than 5 classes is listed as hidden, with no script, no audio and no actions. Its script and audio carry the pooled counts of those classes (CLAUDE.md rules 3 and 15).

**Teacher player** (`LessonAudio.tsx`):
- an "AI-generated voice" label;
- the file size on the Save button (for example "(1.2 MB)");
- the script highlighted sentence by sentence as it plays, from the timing map carried in the step's new optional `audio_info`.

**Scripts:**
- `python tasks.py lessons-pregen`: plan and cost first; `--yes` to spend.
- `scripts/calibrate_chunks.py`: live; plan and cost first; `--yes` to spend.

**Rate limit (found live, fixed).** Bodhan's default is about 8 requests per minute per model. Requests are now paced to `BODHAN_REQUESTS_PER_MINUTE` and Retry-After is honoured. A wait longer than `BODHAN_PACE_MAX_WAIT_S` fails at once, so the chain falls back.

## Files

New:
- `services/speech/lessons.py`, `services/speech/textnorm.py`
- `services/content/lesson_audio.py`, `services/api/lesson_audio_api.py`
- `content/voices.yaml`
- `scripts/lessons_pregen.py`, `scripts/calibrate_chunks.py`
- `apps/pwa/src/components/LessonAudioReview.tsx`, `apps/pwa/e2e/lesson-voice.spec.ts`, `apps/pwa/e2e/fixtures/tone-lesson.mp3` (a generated tone)
- `tests/speech/test_lessons.py`, `tests/speech/test_pregen.py`, `tests/content/test_lesson_audio.py`

Changed:
- `services/content/publish.py`, `services/speech/bodhan.py` (pacing)
- `services/api/flows/steps.py`, `services/api/flows/t4.py`, `services/api/channels/base.py` (`audio_info`)
- `services/api/main.py`, `services/api/db.py`
- `apps/pwa/src/components/LessonAudio.tsx`, `src/screens/Flow.tsx`, `src/screens/Review.tsx`, `src/lib/flow.ts`, `src/lib/lessonAudio.ts` (+ test), `src/styles.css`, `strings/{en,hi,ta}.json` (Hindi and Tamil are drafts for Seema)
- `scripts/data_budget.py` (the model run now counted at its own 16 kbps), `docs/evidence/data_budget.json` (regenerated)
- `tasks.py`, `.env.example`, `README.md`, `CLAUDE.md` (section 9 row), `docs/RUBRIC_MAP.md` (E3.2), `docs/help/coach.md`, `docs/build/DECISIONS.md`

## Tests

| | Result |
| --- | --- |
| `tests/speech/` (90 after Prompt 1) | **117 passed**: 21 lesson pipeline, 2 pre-generation, 4 new Bodhan pacing and Retry-After |
| `tests/content/` | **144 + 9 passed** (9 new lesson-audio review tests) |
| `tests/flows`, `tests/channels`, `tests/api` | 157 passed |
| vitest | 449 passed (2 new: sentence at a time, size label) |
| Browser `e2e/lesson-voice.spec.ts` (new) | **5 passed**: coach review (highlight, flag, regenerate one sentence, approve, axe), hidden small cohort, officer read-only, teacher player (label, size, highlight, axe), Hindi and Tamil at 360 px |
| `e2e/review-queue.spec.ts`, `e2e/app.spec.ts` | 15 passed |
| `tests/test_data_budget.py` | **1 failed, 2 passed**. The failure is the 10 MB target at the lesson cap (see Decisions). Left failing on purpose |

### Tests changed, and why

- **`tests/content/test_publish.py`**
  - The speed shim now patches `lessons.encode_mp3` instead of `publish.join_to_file`, which publish no longer calls.
  - The budget test checks the new budget: at most 1.85 MB per 5 minutes and an MP3 file, instead of 0.6 MB and an OGG file. That follows your MP3 decision. Every other assertion is unchanged.
- **`tests/content/test_review_api.py`, `test_seed_demo.py`, `test_model_run.py`:** the same speed-shim change, on one line each. No assertion changed.
- **`tests/speech/test_bodhan.py`:** the two Retry-After tests now use a fake clock that their sleep advances, which pacing needs. Their expected waits (3.0 s and 8.0 s) are unchanged.

## Live runs (1 Nov, your choice: run everything)

| Run | Result | Estimated cost (unverified prices) |
| --- | --- | --- |
| `scripts/calibrate_chunks.py --yes` | 20 of 21 requests (one 429). Characters per second: en Kavya 11.8, Amit 11.2; hi Kavya 10.9, Suhani 10.6, Amit 8.9; ta Anitha 12.7, Arun 13.0. At the 220-character target every narrator stays under 28 s. `evals/results/chunk_calibration.json` | INR 0.94 |
| `scripts/seed_demo_track.py` (publish the demo track) | **Nothing published**: all 14 lesson drafts in the local database were held by the output checker (call 7). Re-drafting would spend Claude (call 5), which is outside this prompt; not done | 0 |
| Two lesson texts through the pipeline, before the pacing fix (day 1 en and hi, local store only, not published) | Bodhan hit its rate limit; **both lessons were remade with Sarvam** (whole-lesson fallback): 37 and 38 chunks, 218 s and 227 s, 1.31 MB and 1.36 MB MP3, every sentence passed the round trip | about INR 21.7 |
| First section of day 1 en, after the pacing fix | **Bodhan, no fallback**: 13 chunks, 101 s, 605 KB, 24 of 26 sentences passed the round trip (one chunk flagged at a character error rate of 0.31 after its one remake), 150 s wall time | INR 0.90 |
| `python tasks.py lessons-pregen --yes` | Not run: there is no published lesson in the local database (see above) | 0 |

Small probe calls to measure the rate limit (about 30 requests of "Ten.") cost a fraction of a rupee.

## "Done when"

- **A lesson in each language can be generated with the mock, stitched, checked, reviewed and played with highlighting:** yes for en and hi in the pipeline and API tests; Tamil splitting and normalising are covered too. The browser tests cover review and highlighting.
- **The demo lessons play from the cache with providers off:** yes, `test_the_demo_lessons_play_from_the_cache_with_every_provider_disabled`.
- **The live calibration script works with your keys:** yes, run above.

## Not done, or open

- **Bodhan's rate limit** (8 a minute per model) makes a whole lesson take about 10 minutes, and rules Bodhan out of live Practice Class turns until Bodhan raises it. Ask them.
- **The 10 MB per-track target** is missed at the lesson cap with MP3 48 kbps. It needs a new target number from you.
- **Demo lessons can't be pre-generated locally** until a track is published, which needs drafts that pass the checker.
- **Telegram** would need `sendAudio` for MP3 lessons (roadmap).
- **Hindi and Tamil number words** in `textnorm.py`, and every voice in `content/voices.yaml`, are `TODO-HUMAN` for Seema and Gopi.
