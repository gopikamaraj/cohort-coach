# P09 · Content pipeline, versions and the two keys — report

**Status:** 🟡 · **Dates:** 2026-10-26 → 2026-10-27 · **Commits:** `7eeba33` (plan) … `4592d23` (T10), then T11 and this report · **Gate:** none for this phase

## Summary

A SUB-SFL track can now go from a model draft to a published manifest: call 5 drafts it part by part, code fills the class numbers and checks every sum, the existing gates run, a coach reviews it in a queue screen, and a track version reaches teachers only after the coach's key and then the officer's key. The first live run drafted all 14 parts (six lessons and a model-lesson script, Hindi and English); all passed the code gates, but call 7 held 12 of the 14. The judge review traced that to our gate showing call 7 sample numbers in place of the slots; after telling it so, a clean re-run sent 12 of 14 to the coach (finding below). Not done: the model run (T12), Tamil, the citations second pass and stage routines (all cut up front), a live Batches run, and anything on a staging URL.

## What was built

| Area | Files | Notes |
| --- | --- | --- |
| Track data | `content/tracks/sub-sfl.v1/track.yaml`, `content/strategies/strategies.v1.yaml`, `content/templates/*.md` | Loaders and a content scan: no Form A or B item in any content file |
| Slots | `services/content/slots.py` | Class numbers only as slots, filled at delivery by code; the child-wrong tag |
| Call 5 | `ai/calls/c05_track_draft.py`, `ai/prompts/c05_track_draft.v2.md` | One part per request; gates 1, 1b and call 7 before the queue |
| Drafting | `services/content/drafting.py`, `scripts/batch_draft.py` | Estimate first; `--sync` live; batch request builder tested on recorded data |
| Versions and two keys | `services/content/versions.py`, `configurable.py`, `services/api/db.py` | draft, in review, approved, active, retired; both keys in the audit row |
| Review queue | `services/content/review.py`, `rejections.py`, `services/api/review.py` | Edits re-gated, structured reasons, rejection loop into call 7 |
| Publish | `services/content/publish.py` | Voice once per language by hash, size budget, manifest |
| Screen | `apps/pwa/src/screens/Review.tsx`, `lib/queue.ts`, route `#/review`, strings `queue.*` | Coach, officer and judge; en, hi, ta |
| Docs | `docs/content-pipeline.md`, `docs/guardrails.md`, `AI_USAGE.md` | Call 5 is "Built", not "Verified" |

## Acceptance

| Criterion | Proof | Key output | Status |
| --- | --- | --- | --- |
| One lesson goes draft, checks, review, approve, audio, manifest, in hi and en | `tests/content/test_publish.py`, `test_review_api.py`, `test_versions.py` (stubbed model and speech) | A version both keys switched on is published, each lesson voiced once per language, manifest complete | 🟡 proven in tests and by the live drafts; **not run on a staging URL** |
| P3 shows the automated check results; a rejected example appears in the next call 7 prompt | `apps/pwa/e2e/review-queue.spec.ts` (API mocked), `tests/content/test_rejection_loop.py` | Checks shown per item; promote moves a rejection into the next call 7 system prompt; the audit row records the example-set version | ✅ |
| Audio at most about 0.6 MB per 5 minutes | `tests/content/test_publish.py` (real ffmpeg OGG/Opus at 16 kbps) | Under 600 KB per 5 minutes | ✅ |
| The SUB-SFL model run goes render, review, approve, audio, manifest, at about 0.35 MB | none | T12 not started | ❌ cut (last on the phase's own list; P10 to P16 are untouched with 4 days left) |

## Tests and evals

Run `python tasks.py check` (Python, vitest, eval smoke) and `npx playwright test e2e/review-queue.spec.ts`. The per-task counts are in `docs/build/tasks/P09.md`. No eval number is claimed for call 5: its bar (at least 80% accepted with minor edits, arithmetic 100%) needs the coach's decisions and has not been measured; `review.stats` computes it from decisions once there are some.

## AI calls touched

| Call | Model | Prompt version | Validators | Eval | Live runs |
| --- | --- | --- | --- | --- | --- |
| 5 track drafting | `claude-opus-5-5` | v2 | arithmetic, slots only, no check items, reading level, pre-filter | pending (needs coach decisions) | 2 (one stopped after part 1 on a console encoding error); see `docs/evidence/p09_live_draft_run.txt` |
| 7 output checker | `claude-haiku-5-5` | unchanged | n/a | unchanged | 14 calls inside the run |

## Cost and latency measured

| Measure | Value | Sample | Source |
| --- | --- | --- | --- |
| Script estimate before a full run | USD 0.60 | 14 requests | printed by `scripts/batch_draft.py` |
| Measured per full run | about twice the estimate | 14 parts, two runs | `docs/evidence/p09_live_draft_run.txt`, `docs/evidence/p09_live_draft_run_after_slots_note.txt` |
| Cumulative spend to date | `python tasks.py budget` (includes earlier work) | all calls | the budget table |

The first run's "queued" marks cover only parts that were new: the local database already held drafts of most parts from earlier work, which the script skips as duplicates.

## Deviations and decisions

| What changed from the brief | Why | Entry |
| --- | --- | --- |
| Drafting is synchronous, not a waited-for batch | 5 days to submission | task file "Cuts taken up front" |
| Tamil, citations second pass, stage routines, model run cut | time | same; also add to PROGRESS "Cuts taken" |
| `PILOT_MODE=0` forced in the test and e2e environments | a developer's `.env` with pilot mode on turned 39 unrelated tests and the browser tests into pilot-mode runs | `tests/conftest.py`, `apps/pwa/playwright.config.ts` |

## Finding fixed in this phase: call 7 and slots

In slot mode the gate shows call 7 the draft with sample numbers where the `{class.*}` slots are, so a lesson reads "7 of 20 children". Call 7's rule is that it states no statistic, so it held 12 of 14 drafts. The fix is in input shaping, not the prompt file: the checker is told in its trusted input (`slots_note`) that the numbers stand in for slots code fills at delivery (`ai/calls/c07_checker.py`, `ai/guard/gates.py`, test `test_the_checker_is_told_that_sample_numbers_stand_in_for_slots`). Before: 2 of 14 reached the coach. After (clean database, same track and languages): 12 of 14, 2 held with reasons. P13's call 7 eval should include a slot-mode case.

## Reviews

| Reviewer | Verdict | Blocking findings fixed | Open non-blocking items |
| --- | --- | --- | --- |
| judge-reviewer | pass with fixes | Call 7 held 12 of 14 drafts (fixed, re-run: 12 of 14 pass); cuts now logged in PROGRESS and PARKING; Tamil flagged "not drafted" in `track.yaml` | No end-to-end run on a staging URL with real voice; the model run is cut; the `roadmap.md` file does not exist yet (P16) |
| privacy-guardian | clear with fixes | F1: the manifest view (coach, officer) returned filled scripts holding a cohort's pooled counts, so for a one-class cohort one teacher's class: scripts are now left out of that view (`test_the_manifest_view_carries_no_filled_script_for_a_coach_or_officer`). F2: a promoted example is screened for phone numbers, emails and ID numbers. F3: the reject note is screened the same way and `content/rejections/pending/` is git-ignored | Examples are not wrapped in delimiter tags in call 7's prompt; in the judge deployment an example is written to the server's repository folder and persists across judges; reviewer ids are one per role until P12; audit `detail` is free JSON (ids and codes today) |
| integrity-auditor | honest with fixes | The evidence line for the first run now explains that earlier drafts already sat in the database; the estimate-versus-actual gap is stated; the stale test path in T04 is corrected | Reported spend rests on the script's own measure; `python tasks.py budget` is the ledger |

## Waiting on people

| Owner | Item | Placeholder in place | Needed by |
| --- | --- | --- | --- |
| Seema | Review the Hindi and English SUB-SFL v1 drafts in the queue and the strategy wording | Drafts labelled `TODO-HUMAN(Seema)` | before real teachers hear them |
| Shivani | Hindi and Tamil wording of the `queue.*` strings | First drafts | no |
| Gopi | Confirm that a coach reading a filled script for a cohort of fewer than 5 classes is acceptable in the pilot (scripts are hidden from the manifest view; the coach still reads drafts with sample numbers only) | Logged | before real cohorts |
