# Improvement-track modules (2 Nov 2026)

Branch `autopilot/results-cohort-audio`, uncommitted. Prompt: `docs/build/Claude Code prompt improvement track with several modules, due dates, feedback a.md`.

## 0. Why there was only one module before (Step 0)

The "Improvement track" of a cohort of one class was one *pack*, not a plan. Nothing in the data, the content or the code could have made a second one:

| Question | Answer, with evidence |
| --- | --- |
| Was it the content library? | In part. `content/errors/intervention.v1.yaml` holds **one set of sections per error** (`errors.<CODE>.two_minute_check`, `ten_minute_activity`, …, lines 13–82) and `strategy_details` per approach (line 83). There was no ordered list of modules. The strategy library (`content/strategies/strategies.v1.yaml`) did have 3 to 7 approaches per error, but nothing sequenced them for a class-only cohort. |
| Was it the track start? | Yes. `ClassCohort` (`services/api/db.py:417`) stores the errors and counts only: no plan, no start date, no due dates. `services/api/cohorts/class_only.py:57` creates the cohort and stops. |
| A missing plan or trigger? | Yes. No `track`, `module` or `due date` table existed, and no scheduler touched cohorts: the only scheduler (`services/chat/scheduler.py`) sweeps the cohort *chat*. `tasks.py` had no daily job. |
| The UI? | Yes. `apps/pwa/src/lib/pack.ts:buildPack` builds the whole pack on the phone once per error; `InterventionPack.tsx` shows it with one Download audio. No timeline, no feedback card, no "next". |
| The audio? | No. `POST /api/audio/pack` voices any text it is sent (`services/api/pack_audio.py:118`) and caches by text and voice; it could voice any number of modules. |

**What already existed and was reused.**

- The two-class demo run (`services/cohort_run/`) has a six-lesson track (`content/tracks/sub-sfl.v1/track.yaml`), feedback (tried, partly, not yet) and `next_lesson.decide` (tried → next, partly → same approach smaller, not yet → another approach, silence → planned next, never counted). `generate_next` and `tick` do it by code, with call 5 wording and coach review. That flow is demo-only, keyed to the run's JSON state, so it could not serve a real class-only cohort. **Its rules were copied into a pure function, not called.**
- Strategy library, intervention text and the Hindi/Tamil drafts (`services/content/error_content.py`) for the module text.
- Mask and pre-filter (`ai/validators/mask.py`, `prefilter.py`) for the feedback note.
- The Download audio endpoint and its cache, the speech layer, the role guard (`cohort.chat`, `coach.moderate`), the usage footer (the new calls go through the same `fetch`).

## 1. What was built

| Part | Where |
| --- | --- |
| States and legal moves (one table) | `services/modules/states.py` |
| Branch function (pure) | `services/modules/branch.py` — `next_module(plan, history, previous_feedback, cap)` |
| Module plans (order and alternatives) | `content/modules/modules.v1.yaml` (draft) |
| Module text, assembled by code | `services/modules/library.py` |
| Tables | `services/modules/models.py` — `tracks`, `track_modules` (unique `(track_id, number)`), `module_feedback`, `module_events` |
| Start, generate, feedback, download, coach dates, counts | `services/modules/service.py` |
| Daily job | `services/modules/jobs.py`, `scripts/modules_due.py`, `python tasks.py modules-due` |
| HTTP | `services/modules/api.py` (`/api/modules/…`; teacher routes need `cohort.chat`, coach routes `coach.moderate`) |
| Teacher screen | `apps/pwa/src/components/ModuleTrack.tsx`, `lib/modules.ts` (inside the Improvement track on My cohorts) |
| Coach screen | `apps/pwa/src/components/CoachModules.tsx` (under each class-only cohort in Cohorts) |
| Strings (72 new keys, en/hi/ta) and the lesson → module rename | `strings/*.json` |

**Migration.** The project has no migration folder; tables come from `Base.metadata.create_all`. The four tables are imported at the end of `services/api/db.py` like the other late tables.

### The branch table (code, `branch.py`; tested)

| Feedback on the previous module | Next module | Branch recorded |
| --- | --- | --- |
| none yet (the start) | first module of the plan | `first` |
| tried | next approach in the plan not used yet | `tried` |
| partly | the same approach as a smaller step (first step only), then the plan is rejoined | `partly` |
| not yet | the template's alternative, else any unused approach of that error | `not_yet` |
| none by the due date | the planned next module; the record says `no_feedback`; never read as tried | `no_feedback` |

Rules: an approach is never repeated except after "partly"; cap 6 modules (`MODULE_CAP`); at the cap, or when the plan and alternatives run out, it **stops** with "Talk to your mentor or coach" and a `coach_notified` event; a plan that simply finishes completes the track ("It is time for the next check"); nothing is planned after the track's end date. Reasons are fixed sentences in en/hi/ta (`module.reason.*`).

### Starting, generating, triggers

- `start_track` plans every module with a title and a due date (7 days apart, `MODULE_GAP_DAYS`) and generates **only Module 1**. Later modules stay `planned` with no text.
- One function, `generate_module(track, number, trigger)`, for all four triggers (`start`, `teacher`, `due_date`, `coach`). The row is claimed with `UPDATE … WHERE status='planned'`; the loser returns the existing module. A double press, a repeated job and a retry make one module (tested, including two threads).
- The teacher's **Get the next module** is refused until she has answered the newest module (409 `needs_feedback`); the screen shows "Give feedback on Module 2 to get Module 3, or it will arrive on 17 Nov".
- The daily job (06:00 Indian time; the day changes at 06:00, so 05:59 still belongs to the day before): makes every due module in order, catches up missed days, retries a failure three times with a growing wait, marks it and records `coach_notified` if it still fails, and flags a module not downloaded after 5 days (`MODULE_NO_DOWNLOAD_DAYS`) once. Clock and sleep are injected.

**Scheduler setup.** Locally: `python tasks.py modules-due` once, or `python tasks.py modules-due --loop` (a development fallback that wakes at 06:00 IST). In production call `POST /api/modules/jobs/due` every day at 06:00 `Asia/Kolkata` with header `X-Job-Token: $MODULES_JOB_TOKEN` (the route is off unless the token is set). Cloud Scheduler example:

```
gcloud scheduler jobs create http modules-due --schedule="0 6 * * *" --time-zone="Asia/Kolkata" \
  --uri="https://<api>/api/modules/jobs/due" --http-method=POST --headers="X-Job-Token=<token>"
```

The project had no scheduler of its own for this (the chat sweep is called from the chat flow), so this is new.

## 2. Content gaps (for Seema)

- `content/modules/modules.v1.yaml` is `status: draft`: the **order** of each plan and the "not yet" alternatives are my choice from the strategy library. SUB-SFL and SUB-NODEC 4 modules; ADD-NOCARRY 3; PV-HEARD 2 (two approaches in the library, no alternatives); PV-REVERSE 1 (one approach). Short plans end in "talk to your mentor or coach" on "not yet". An error with no plan (ADD-WHOLE-ONES) gets one module and a log line.
- All module text is the strategy library's and intervention file's, still `draft` (they say so on screen). Strategy **descriptions, steps and worked examples** have Hindi/Tamil only where `hindi.draft.v1.yaml` / `tamil.draft.v1.yaml` give them; the rest shows English with a note. Worked examples are never translated, so the spoken Hindi and Tamil skip them.
- **No AI words the modules.** The optional call 5 wording with coach review is not built. `AI_USAGE.md` is unchanged and claims nothing new.

### Every new text for review (Claude drafts, en first)

- All `module.*` keys in `strings/{en,hi,ta}.json` (72): reasons (`module.reason.*`), the timeline, statuses, the feedback card, banners, the coach table. Hindi and Tamil are drafts for Seema and Shivani; Hindi *मॉड्यूल* and Tamil *தொகுதி* are the words in the prompt.
- The smaller-step sentence in `modules.v1.yaml` (`smaller_step.intro`, en/hi/ta).
- The renamed strings (72 keys that said lesson). The separate *model lesson* / *model-lesson script* keeps its name: say if you want it renamed too.

## 3. The rename (Step 10)

- App strings: `strings/en.json`, `hi.json`, `ta.json` (72 keys). Slot names were kept (`{lesson}` in `run.ev.voice_failed` is a slot, not a word).
- Help: `docs/help/{teacher,coach,mentor,officer,product,judge}.md`, `docs/judge-test-script.md`, the non-generated lines of `README.md`. New sections on modules in `teacher.md` and `coach.md`.
- Not changed on purpose: README's generated *Where AI is used* block (it comes from `ai/registry.py`, whose descriptions still say lesson), code and file names (`LessonAudio`, `lessons.py`, `track.lessons`), `docs/build/*` history.
- **Still say "lesson" (decks and video script; not edited):** `docs/submission/slides.md` and the deck source it builds, `docs/submission/` video script and shot list, `docs/YOU_SAID_WE_CHANGED.md`, `docs/roadmap.md`, `docs/practice-class.md`, `docs/content-pipeline.md`, `docs/offline.md`, `docs/channels.md`, `docs/guardrails.md`, `docs/deploy.md`, `docs/ux-gaps.md`, `docs/RUBRIC_MAP.md` (existing rows), `AI_USAGE.md`, `CLAUDE.md`. (`grep -il lesson` on these.)

## 4. Tests

Pure logic, state machine, the library, reasons in three languages, idempotency (also two threads), the job on a frozen clock (the 05:59 / 06:00 boundary, catch-up, retry, a persistent failure, one failing track not stopping others, the no-download flag, the end date), coach dates (single, shift, cannot move a made module), roles, the whole three-module track from start to the coach's counts, and the API.

| Suite | Result |
| --- | --- |
| `tests/modules/` (new) | 84 passed |
| `apps/pwa/src/lib/modules.test.ts` (new) | 11 passed |
| `apps/pwa/e2e/modules.spec.ts` (new) | written, **not run** (you are doing the browser tests): timeline, closed button and reason, feedback and next, audio file name, axe, Hindi and Tamil at 360 px, offline, coach counts |
| Whole Python suite | see the final message for the counts and the failures that were already there |

Existing failures that are not from this work (seen again, unchanged): `src/lib/flow.test.ts` (2) and `profile.test.ts` (1) expect the old 25% rule and "nothing on by default"; `pack.test.ts` (1) expects English fallback where a Hindi draft now exists; `tests/test_design_tokens.py::test_the_tap_target_and_font_floors_are_in_the_css` (a 14 px font in the CSS); `tests/speech/test_pack_audio.py::test_a_sum_is_never_split_inside` (the spoken layer). One failure was mine and is fixed: the rename had changed a `{lesson}` slot name.

## 5. What I did not do / limits

- Only class-only cohorts get modules; the two-class demo run is unchanged.
- Not run in a browser; only type-checked and unit-tested. No push, no merge, no commit.
- "Notify the coach" is a recorded event shown as counts, not a push message.
- A coach sees per-module counts for a cohort of one teacher, which is that teacher's progress; no id, no name.

---

# Part A: four answers and the not-tried hold (2 Nov 2026)

**What existed (Step 0).** Answers `tried`, `partly`, `not_yet`; the pure branch function (`branch.next_module`); the daily job (`jobs.run_due`); the feedback card in `ModuleTrack.tsx`; the cohort chat is a separate system (`ThreadPost` in `services/api/cohorts/thread.py` for a cohort space, and `ChatMessage` for the question and AI-draft flow), which a class-only cohort does not have. **What differed from the brief:** three answers, no hold, no deferral, no migration.

**Changed.**

| Item | Where |
| --- | --- |
| Answers `worked / partly / not_yet / not_tried`; `tried` removed everywhere (code, branch names, reason codes, strings, tests, docs) | `services/modules/states.py`, `branch.py`, `models.py`, `strings/*.json`, `tests/modules/` |
| Hold: module stays open; dates move by `MODULE_DEFER_DAYS`, at most `MODULE_MAX_DEFERRALS`; coach event after the second; the job defers again before making a held module's successor | `service.py` (`_defer`, `maybe_defer`), `jobs.py` |
| Why not yet? chips; shorter version (first step only); link to ask the mentor or coach | `POST /api/modules/tracks/{id}/modules/{n}/why`, `ModuleTrack.tsx` (`HoldPanel`) |
| Migration `tried` -> `worked` (answer, branch, reason code, event details), idempotent; Postgres column widened | `services/modules/migrate.py`, called from `services/api/profiles.py` and `scripts/modules_due.py` |
| Coach table: Worked, Partly, Not yet, Not tried (own column; never a result) | `CoachModules.tsx` |
| Reason strings for the new case (en, hi, ta) | `module.reason.worked`, `module.reason.not_tried` |

**Tests.** `tests/modules/test_not_tried.py` (26): the four answers and refusals, branch for not tried and worked, the hold (open module, +7 days, end date, no coach event yet), the shorter version, Get next always works, a repeated press defers once, a real answer closes the hold, the job's second deferral with the coach event then the module as `no_feedback` with a frozen clock and a repeat run, the env settings, counts, a held last module is not finished, chips, the migration (and a second run changes nothing), the endpoint over HTTP, strings in three languages. `modules.spec.ts` gains the four-option card, the hold (chips, shorter version, 44 px, axe, Hindi and Tamil fit at 360 px); **written, not run**. Module suites: 84 before, 110 after.

**Not changed.** The two-class demo flow (`TwoClasses.tsx`, `cohort_run`) still has its own "Tried it" answer; it is a different flow.
