# Autopilot report: results page, answer map, error explanations, a cohort of one class, intervention content, Download audio

Branch `autopilot/results-cohort-audio` (from `bayes-32state`). Local only: nothing pushed, nothing merged, `main` untouched. Step-by-step log: `docs/build/autopilot/LOG.md`. Decisions: `docs/build/DECISIONS.md` (2026-11-02).

## Read this first

1. **`apps/pwa/node_modules` is damaged and needs `npm ci`.** My cleanup of a temporary comparison worktree deleted `.bin` and `@playwright` (and probably more) through a Windows junction. `npm ci` fails because two leftover processes hold a file: a Vite preview on port 4199 (pids 13816, 6824, left from earlier work) and the Vite dev server (`npm run dev`, pid 41312 and its child 25612). The sandbox refused my request to stop them, so I stopped there. To fix: close those, then `cd apps/pwa && npm ci`. The source files, lockfile and package.json are untouched.
2. **Browser checks were run with Playwright**, not the Chrome extension (it was not connected in this session). Screenshots are in `data/autopilot-screens/` (git-ignored, synthetic data only).
3. **One live Bodhan call was made** (see Part F). Cost about INR 0.26 by unverified prices. No Claude call was made.
4. After the damage I could not re-run two e2e tests that failed in the full run (`practice.spec.ts` "every child who spoke is highlighted" and `papers-hub.spec.ts` "a generated paper is edited in the same paper"). I could not confirm whether they fail on the base; treat them as unverified.
5. Everything new that teachers read is a **draft** for Seema (content gaps below); Hindi and Tamil text for the explanations and the pack does not exist and was not machine-translated.

## What was found and done, by part

### Preflight
- The speech layer (Bodhan first, Sarvam fallback) existed only on branch `speech-bodhan`. I merged it into the autopilot branch (not into `main`). Conflicts in 6 files were resolved keeping both sides. **A bug from that merge**: a missing `}` in `styles.css` nested the speech and results CSS inside `.finding-lines`. Found by the no-wrap test; fixed.
- The merge made the content scan fail (`content/speech_eval/scripts.yaml` spoke Form A items 43 and 346). I changed two example numbers in that file (to 62 and 527). The test bar is unchanged.
- Fixed 3 lint failures that were already on the base so lint is green.

### Part A: results page review (blocker 0, wrong content 0, polish 3)
Checked on a made-up class of 16 (`apps/pwa/e2e/fixtures/results16.json`, written from the Python engine by `scripts/make_results16.py`, and a test that fails if it drifts). Counts on the class cards equal the engine's; no `%`, `undefined`, `NaN`; two absent rolls are left out of the map and the count; the page is identical after a reload and offline; with no check it says so. Coach, mentor and officer see counts but never the roll-level map, explanations or the cohort maker (new, tested). Findings fixed: (1) a hidden-text rule let screen-reader text escape the table's scroll box and widen the whole page on a phone (566 px) — fixed; (2) the detail clipped at the right edge on a phone (grid `min-width`) — fixed, with a "nothing cut off" test; (3) the Hindi screen showed the English code ADD-WHOLE-ONES — removed.

### Part B: answer map
`AnswerMap.tsx`, `lib/results.ts`. Real `table` with `th scope`, one button per cell with a name like "Roll 4, question 7: wrong: Takes the smaller digit from the larger", roving arrow-key movement, legend chips that highlight and clear, sort by roll or by wrong answers, a total row, a popover with the answer, the correct answer, the mistake, confirmed or possible, a line on what the child likely did and a link to the explanation, and "This table stays on this phone." Colours are new `--heat-*` tokens in `theme.css` (Okabe-Ito); every mistake also has two letters and a pattern. Tests: 14 unit tests; `results.spec.ts` compares all 160 cells with the engine, five cells by eye, column totals, legend counts, sort, highlight both ways, popover, keyboard, axe, Hindi and Tamil at 360 px, laptop. The design-token test now checks contrast with ink (at least 4.5:1), colour-blind separation (at least 15 CIE76 under protan, deutan and tritan) and one pattern and two letters per mistake.

### Part B2: Why an error is flagged
The paper page's matrix is now one shared component (`CoverageMatrix`) used by both pages, so they cannot differ. Fixed the rendering: header cells do not wrap, error codes stay whole, names beside codes, the error column stays fixed while the table scrolls inside its own box, items tagged "extra". Added: a column of this class's counts (confirmed and possible, 0 shown too), the rule in words (reads the engine's `min_hits`), the shared-items note, linking in both directions, accessible dot text. Data check: the matrix is built from the answer key's own probes; a test proves it equals the paper's coverage for Form A and that the key's wrong answers equal the engine's bug functions on every item of both forms.

### Part C: What each error means
`content/errors/explanations.v1.yaml` → `error_content.json` (exported by `python tasks.py export-keys`, which now also checks it). A test fails if any error the engine can produce has no explanation. The worked example is read from the key of the class's own question (the question most children made the mistake on, and the answer most wrote); counts equal the class card. Marked Draft.

### Part D: a cohort of one class
New table `class_cohorts` and `/api/cohorts/class-only` (teacher make and list, coach list). One per check; counts only; name goes through the existing posting check (a phone number in the name is refused); no teacher id in any reply. `COHORT_MIN_CLASSES` is unchanged (tested). Phone side: kept in `localStorage` first, sent when online, retried on reload; labelled "Just my class: no other teachers yet" on the form, the made card, the cohort page, My programme and the coach's list. 6 server tests and 4 browser tests (create with the most common error pre-selected, request body has no child data, reload, offline then online, coach view, role hiding).

### Part E: intervention content (text first)
`lib/pack.ts` builds nine sections per error from content only (no AI): what you are seeing (class counts and example), why, a two-minute check, up to three strategies with steps, materials and source, a ten-minute activity, common teaching mistakes, how to know it is working (the engine's rule and the class's count), ideas for home, and if it does not improve. A section with no content is left out and logged (tested). Sections collapse; the pack prints; nothing plays by itself. 7 unit tests.

### Part F: Download audio
`POST /api/audio/pack` (+ `GET /api/audio/pack/cap`) through the existing speech layer: sentences kept whole (sums, decimals, the Hindi danda), chunks, parallel generation with retries, one narrator per file, whole file regenerated on the fallback provider, loudness and MP3 encoding, chunk and file cache, a per-phone character cap (`AUDIO_DOWNLOAD_CHARS_PER_DEVICE`, else `AUTOPILOT_MAX_TTS_CHARS`, else 20000). Button: "Preparing the audio...", download named like `intervention-sub-sfl-en.mp3` (a section adds its id), size shown, "AI-generated voice", disabled with a reason offline, plain messages for the cap and for failure with Try again. 9 server tests with a scripted provider (success, cache, cap, whole-file fallback, all-fail 503 with nothing stored, no text in logs, bad input) and 7 browser tests with the mock voice (no call before pressing, file name, section file, offline). Bodhan's request body, 422, 429, 5xx and timeout are covered by the existing `tests/speech/test_bodhan.py`.
**Live check** (`python scripts/verify_pack_audio_live.py --go`): one English section, 368 characters, estimated INR 0.26 (unverified prices). Result: provider bodhan, 31.4 s MP3 (expected about 25 s), mean volume -16.3 dB (not silent), repeat press served from the cache, round trip through Bodhan speech to text CER 0.004 and WER 0.013. Characters used 368 of 20000; STT 31 s of 300; Claude calls 0. **Hindi and Tamil audio was not run**: there is no Hindi or Tamil pack content.

## Tests, before and after

| Suite | Before | After |
| --- | --- | --- |
| vitest | 447 passed | 470 passed (last full run, before the node_modules damage) |
| pytest (whole repo) | 8 failed (already on the base) | 9 failed, 2691 passed: the same 8 plus `test_data_budget` (14.7 MB against a 10 MB target, from the speech branch, a known pending decision) |
| Playwright (whole repo) | 4 failed (checks.spec) | full run 19 failed, 234 passed, 7 skipped; after fixes below, see next lines |

Of the 19: 4 `checks.spec` (already on the base); 6 enter-check camera, drawer, keyboard, photo and AI-off tests and 5 PDF-import tests (papers-hub ×3, demo-path ×2): I ran these on a clean checkout of the base commit and **they fail the same way there**; 2 `qa-screens` Hindi/Tamil and the demo-path 566 px overflow were **mine and are fixed** (re-run green); 2 (practice highlight, papers-hub same-paper) not re-confirmed (see top). The new specs (`results.spec.ts` 11, `cohort-pack.spec.ts` 10) passed on the last build.

## Content gaps and new text for Seema to review
All in `content/errors/explanations.v1.yaml` and `content/errors/intervention.v1.yaml`, all `status: draft`, English only, all marked `TODO-HUMAN(Seema): review`: the explanation of six errors (what, why, spot, first); for five errors a two-minute check, ten-minute activity, teaching mistakes, home ideas and an if-not-improving line; steps and materials for the seven library strategies; and one new strategy "Say it, build it, write it" for PV-REVERSE, which the library did not cover. Hindi (Shivani) and Tamil (Gopi) text is missing. The interface strings I added (about 200 keys) have Hindi and Tamil written by me and need a native read.

## Not done or open
- Hindi and Tamil audio and content; a server-side rebuild of the pack text (the endpoint trusts the text it is sent, limited by the cap); merging a class-only cohort into a real cohort (not built, as asked).
- The speech gates for Bodhan are still pending (startup warning remains).
- Decide whether `autopilot/results-cohort-audio` should merge into anything.
