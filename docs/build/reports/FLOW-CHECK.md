# Flow check: two classes to cohort, first lesson, feedback, chat and the coach view (31 Oct – 1 Nov 2026)

Prompt: `docs/build/Claude Code prompt verify and complete the flow from two classes to cohort, firs.md`.
All automated checks use the synthetic scenario `demo/scenarios/two_classes_pilot_like.yaml` (no real
child). The real pilot sheets were used only in the local run (Step 5), and only counts and pass or
fail lines are copied here.

## Step 2: what was there before any change (verified on the committed code, 31 Oct)

Pass, Partial or Fail, with the evidence. "Demo Studio" is the judge's single-class path
(`services/demo/`, `#/demo`), where her class joins about 24 simulated block classes.

### Flow 1: a cohort forms from two classes

| # | Check | Before | Evidence |
| --- | --- | --- | --- |
| 1.1 | After T1's check, a "waiting for other classes" status | **Fail** | No two-class flow. A check's counts go to `POST /api/classes/{id}/profile` (`services/api/profiles.py`), which stores them and forms nothing. Demo Studio has one teacher. |
| 1.2 | After T2's check, formation runs (automatic or coach button) | **Fail** | Formation runs only in Demo Studio step 6 (`POST /api/demo/{sid}/simulate-classes`), for one real class plus simulated ones. Nothing runs when a second real class arrives. |
| 1.3 | Cohorts for shared errors, with members, counts per class and why each is in or out | **Partial** | Demo Studio step 7 lists cohorts with class counts and "you are in / next term" (`services/demo/cohorts.py::plan`). No per-class reason for every class. |
| 1.4 | Blocking rules and their values | see below | `engine/grouping.py`, `engine/diagnosis.py`, `engine/bugs.py` |
| 1.5 | Mentor suggestion or "no mentor suggestion" with a reason | **Partial** | Same-term candidate rule (`engine/mentors.py::check_candidate`) runs on simulated classes only; when none qualifies the demo shows nothing, with no reason. |
| 1.6 | Each teacher sees her class's cohorts | **Partial** | One teacher only (Demo Studio). |

**Rule values found (Flow 1, step 4).**

- **Minimum classes for a cohort:** `COHORT_MIN = 15`, `COHORT_MAX = 20` (`engine/grouping.py`). A
  pool under 15 still forms **one undersized cohort** (`undersized: true`), so in the engine the real
  floor is 1 class. But before forming, `split_waitlist` sends about half of each group to next term
  (the comparison group). With two classes on one error, one goes to next term, so **a two-class
  cohort never forms this term**.
- **Two-item rule:** `MIN_HITS = 2` (`engine/diagnosis.py`). On the pilot's 15-item paper, borrowing
  across a zero (item 14), the three-digit sum with two carries (item 11), the three-digit
  borrow-twice item (item 15) and 3A's dictated 305 are each the paper's only question of their
  kind. A child wrong on one of them alone never shows the error.
- **Probes for every item:** **Fail** for items 1 (305), 11, 14 and 15. The error functions handled
  two-digit sums and numbers with no zero only. On the committed code: 305 had no probe; 246 + 178
  gave 414 (should be 314); 703 − 468 gave 245 for both subtraction errors (a collision; should be
  365 and 345); 542 − 179 gave 377 and 373 (should be 437 and 473). Items 12 and 13 are anchors (no
  probes, by design).
- **Class threshold:** p ≥ 1 in 4 with at least 10 children checked
  (`MIN_PREVALENCE_NUMERATOR/DENOMINATOR = 1/4`, `MIN_CHILDREN_CHECKED = 10`). One track per class:
  PV-HEARD first, else the highest share.
- **Under these rules, the synthetic scenario forms no cohort.** 3A: borrowing across a zero (4 of
  16), two carries (3 of 16) and 305 (3 of 16) are all single-question, so they count 0. SUB-NODEC
  shows for 1 of 16. 3B: SUB-NODEC 2 of 18, all else single-question. No error reaches 1 in 4, so
  neither class gets a track. Even with a track, the waitlist split would send one class to next term.

### Flow 2: the first audio lesson

| # | Check | Before | Evidence |
| --- | --- | --- | --- |
| 2.1 | The track rule records which error and why | **Partial** | `assign_tracks` records `reason` (`pv_heard_first` or `highest_p`). Demo Studio only. |
| 2.2 | Lesson 1 drafted by call 5 from approved strategies, with sources | **Partial** | `services/demo/live.py::first_audio` calls `draft_part` (call 5) on `content/tracks/sub-sfl.v1`. Template fallback when no draft. The strategies are named in the review item, not on the lesson screen. |
| 2.3 | Voiced in each teacher's language, stored privately, script, duration, play | **Partial** | English only, one class. Audio is cached in the demo folder and served by the session route. |
| 2.4 | Coach review queue, or the demo badge; then shown to both teachers | **Partial** | Lesson 1 skips review with "Demo: pre-approved" (DECISIONS 2026-10-31). There is no second teacher. |
| 2.5 | Download for offline play | **Partial** | `LessonAudio` has "Save for offline" for flow lessons. The Demo Studio lesson has no download. |
| 2.6 | A voice failure leaves text with a retry, and logs it | **Partial** | Text only on failure (`_voice` returns the error name). Regenerate exists. Nothing is logged. |

### Flow 3: feedback and Generate next lesson

| # | Check | Before | Evidence |
| --- | --- | --- | --- |
| 3.1 | A feedback card (tried, partly, not yet) and an optional note | **Partial** | The T4 flow asks "Tried it in class?" (yes / not yet) and "How did it go?" (worked / partly / didn't) (`services/api/flows/t4.py`, `LessonTap`). No note. Not in the Demo Studio lesson. |
| 3.2 | Saved; coach and mentor see counts and masked notes | **Partial** | Officer funnel counts taps (`services/api/officer.py`). There is no coach or mentor view of feedback. |
| 3.3 | Generate next lesson | **Fail** | Not built. Demo Studio queues lesson 2 for review regardless of feedback. |
| 3.4 | No feedback by the set date: the planned lesson goes out, silence not scored | **Fail** | No set date and no release rule. |

### Flow 4: the cohort chat

| # | Check | Before | Evidence |
| --- | --- | --- | --- |
| 4.1 | T1 and T2 see the cohort's chat; an outsider cannot | **Partial** | Membership is enforced (`services/chat/service.py::_member`). Each teacher sees only her own questions (`my_questions`), so T2 never sees T1's question. |
| 4.2 | A made-up name is masked before any model call and stored masked | **Pass** | `mask_personal` runs before `classify` and drafting; only the masked text is stored (`tests/chat/`). |
| 4.3 | An AI draft from approved material with sources, or the AI abstains | **Pass** | Call 13 drafts with citations or abstains (`services/chat/draft.py`, `retrieve.py`). |
| 4.4 | The coach can send, edit or replace it | **Pass** | `chat.reply` modes `as_is`, `edit`, `own`. Demo Studio step 11. |
| 4.5 | Timeout (60 s in the demo), then a labelled AI reply; the coach corrects afterwards | **Pass** | `live.ask` sets a 60 s due time. "Skip the wait" runs the real `scheduler.tick`. `chat.correct` exists. |
| 4.6 | T2 sees the thread; a question typed offline queues and sends later | **Fail** | No second teacher's view (4.1). The chat has no offline queue. |

### Flow 5: the coach's view of cohorts

| # | Check | Before | Evidence |
| --- | --- | --- | --- |
| 5.1 | A Cohorts screen: error, classes, teachers, mentor, lesson 1 and 2 status, plays, feedback counts, chat activity, next check | **Fail** | `#/coach` shows block totals only (`RoleScreens.tsx`). `GET /api/cohorts/coach/cohorts` gives status and member counts (hidden under 5). Demo Studio step 11 shows one cohort's chat and queue. No lesson, feedback or play counts. |
| 5.2 | A per-cohort timeline with links to the queue and chat | **Fail** | Not built. |
| 5.3 | Counts only; a mentor sees her cohort; an officer sees totals | **Partial** | Counts only, with a 5-class floor (`lifecycle.summary`). There is no per-cohort coach screen to limit. |

## Step 3 and 4: what was built, and the result after (1 Nov)

Code: `services/cohort_run/` (scenario, formation, next lesson, service, API under `/api/cohort-run`, judge deployment
only), `apps/pwa/src/screens/TwoClasses.tsx` (`#/two-classes`, demo step 13, **View as** T1, T2, a teacher outside
the cohort, the coach, the cohort's mentor, another mentor, the officer), `engine/bugs.py` and `engine/diagnosis.py`
(three-digit answers, single-question skills), call 5's optional `variant` (`ai/calls/c05_track_draft.py`),
`content/templates/lesson_fallback.yaml`, and help, questions and rubric row E1.6.

Tests: `tests/cohort_run/test_rules.py` (15), `tests/cohort_run/test_api.py` (21), `tests/engine/test_three_digit.py`
(10), `apps/pwa/e2e/two-classes.spec.ts` (one test across every role, with axe on four screens). No paid call: the stub or
recorded AI client and a fake or stub voice.

| Flow | Check | Before | What was missing | What was built | Test | After |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 1.1 Waiting status after T1 | Fail | No two-class flow | Formation runs on every submit; "Waiting for other classes: 1 of 2 so far" | `test_the_first_class_waits_and_sees_only_her_class`, e2e | **Pass** |
| 1 | 1.2 Formation after T2 (automatic, or a coach button) | Fail | No trigger | Automatic on submit (about 7 s, because it drafts and voices lesson 1 in each language); **Form cohorts now** for the coach | `test_the_second_class_forms_the_cohort_automatically`, `test_the_coach_button_runs_formation` | **Pass** |
| 1 | 1.3 Cohort, members, counts, why in or out | Partial | Per-class reasons | Every class and error: in, under 1 in 4, another track, too few checked, no track yet, plus "on one question only" | `test_pilot_settings_form_one_labelled_cohort`, e2e | **Pass** |
| 1 | 1.4 Blocking rules | see values | Two settings; probes for items 1, 11, 14, 15 | `COHORT_MIN_CLASSES`, `COHORT_ALLOW_SINGLE_ITEM_PROBES`, three-digit error answers | `test_settings_come_from_the_environment_in_production`, `test_three_digit.py` | **Pass** (values below) |
| 1 | 1.5 Mentor suggestion or a reason | Partial | The reason | Same-term candidate rule over the run's classes, or "No mentor suggestion" with why | `test_a_better_class_is_suggested_as_mentor` | **Pass** |
| 1 | 1.6 Each teacher sees her class's cohorts | Partial | A second teacher | Teacher view shows her own class only, and her cohort | `test_the_first_class_waits_and_sees_only_her_class` | **Pass** |
| 2 | 2.1 The track rule records the error and why | Partial | — | `track_reason` per class (PV-HEARD first, or the highest share) | `test_pilot_settings_form_one_labelled_cohort` | **Pass** |
| 2 | 2.2 Lesson 1 by call 5 from approved content, with sources | Partial | Sources on screen | Call 5 per language; code writes it from the same topic and strategies when no draft comes back; sources listed | `test_lesson_one_is_worded_by_call_5_when_its_draft_comes_back` | **Partial**: the strategy library is still status *draft* awaiting Seema; recorded call 5 answers exist for English lessons 1 and 2 only, so Hindi and later lessons are code-written in tests |
| 2 | 2.3 Voiced in each teacher's language, private, script, duration, play | Partial | Per teacher and language | One lesson per cohort and language; voiced per teacher with her class's numbers; served only to her | `test_lesson_one_per_language_goes_to_review_then_out` | **Pass** |
| 2 | 2.4 Review queue, then both teachers | Partial | Review in this flow | A real review item per lesson; released on the coach's approval; T1 gets English, T2 Hindi | same, e2e | **Pass** |
| 2 | 2.5 Download for offline | Partial | Download | **Download for offline** (attachment) | same | **Pass** |
| 2 | 2.6 Voice failure: text, retry, logged | Partial | Log and retry | Text stays; warning with ids only; **Try the voice again** | `test_a_voice_failure_leaves_text_logs_it_and_can_be_retried` | **Pass** |
| 3 | 3.1 Feedback card after play or "heard"; optional note, masked | Partial | Card and note | Tried it, Partly, Not yet, and a note (names and roll numbers masked); only after play or **I've heard it** (self-report) | `test_feedback_only_after_playing_and_the_note_is_masked`, `test_marked_heard_also_opens_feedback` | **Pass** |
| 3 | 3.2 Saved; coach and mentor see counts and masked notes | Partial | Coach and mentor view | Counts (self-report) and masked notes, by pseudonym | same | **Pass** |
| 3 | 3.3 Generate next lesson | Fail | All | The teacher after her feedback, or the coach for her. Code decides; call 5 words it; review | `test_generate_next_lesson_follows_her_answer[tried, partly, not_yet]`, `test_generate_next_needs_feedback_first_and_the_coach_may_press_it` | **Pass** |
| 3 | 3.4 No feedback by the set date | Fail | All | **Skip to the set date** (simulated clock): the planned lesson is queued; silence is recorded as "no answer" and never counted | `test_silence_releases_the_planned_lesson_and_is_not_counted` | **Pass** |
| 4 | 4.1 Both teachers see the chat; an outsider cannot | Partial | A shared view | **Share with my cohort** (unticked by default in the product): others see the question and released answers by pseudonym; an outsider gets 403 | `test_chat_membership_masking_abstain_coach_reply_and_sharing`, `test_an_unshared_question_stays_private`, e2e | **Pass** |
| 4 | 4.2 Name masked before any model call, stored masked | Pass | — | Reused | same, e2e | **Pass** |
| 4 | 4.3 AI draft with sources, or abstain | Pass | — | Reused; the run shows "The AI found nothing approved" when it abstains | same | **Pass** (abstain path in this run; the draft path is covered in `tests/chat/`) |
| 4 | 4.4 Coach sends, edits or replaces | Pass | — | Reused in the run's inbox | same, e2e | **Pass** |
| 4 | 4.5 Timeout, labelled AI reply, correction | Pass | — | Reused: 60 s, **Skip the wait**, correction | `tests/chat/` | **Pass** (not re-run end to end here, because the strategies are drafts, so no approved material to send) |
| 4 | 4.6 T2 sees the thread; an offline question queues | Fail | Both | Shared view (4.1); an outbox on the phone, sent when back online (retried every 3 s while anything waits) | e2e | **Pass** |
| 5 | 5.1 Cohorts screen with every count | Fail | All | Step 5 **Cohorts**: mistake, classes, teachers, children in the cohort who showed it, mentor, lesson 1 per language, plays (system), heard and feedback (self-report), no answer (not counted), next lessons, chat, next check | `test_role_limits_on_the_coach_view`, e2e | **Pass** |
| 5 | 5.2 Timeline with links | Fail | All | Timeline of every event; links to the review queue and the chat | e2e | **Pass** |
| 5 | 5.3 Counts only; mentor's own cohort; officer totals | Partial | Limits on the new view | Mentor of another cohort sees nothing; officer sees totals with any figure over fewer than 5 classes hidden | `test_role_limits_on_the_coach_view`, `test_the_coach_view_has_no_child_level_data` | **Pass** |

### Rule values (Flow 1, step 4), after

| Rule | Production | Pilot and demo | Label on screen |
| --- | --- | --- | --- |
| Minimum classes for a cohort (`COHORT_MIN_CLASSES`) | 15 | 2 (no waitlist split at pilot scale) | Pilot cohort, two classes |
| A paper's only question of a kind (`COHORT_ALLOW_SINGLE_ITEM_PROBES`) | off: "possible" only | on: counts | Based on one question per child |
| Two-item rule (`MIN_HITS`) | 2 | 2 (unchanged) | — |
| Class threshold | 1 in 4, at least 10 checked | same | — |
| Probes on the 15-item paper | items 1 to 11, 14, 15 (12 and 13 are anchors) | same | — |

**Synthetic scenario under each rule set** (`tests/cohort_run/test_rules.py`):
- **Production:** no cohort. Every main pattern is single-question.
- **Pilot and demo:** one SUB-SFL cohort of 3A and 3B, 9 of 34 children. 3A has 4 of 16; 3B has 5 of 18.
- **Left out:**
  - Two carries: under 1 in 4 (3 of 16, and 4 of 18).
  - 305: 3 of 16.
  - Subtracting wrongly after borrowing: 1 of 16, and 2 of 18.
  - Confusing signs: not a tracked mistake.
- **Mentor:** no suggestion, because both classes are in the cohort.

## Step 5: the manual pilot run (local, counts only)

`python -m tools.pilot.flow_run` on the machine with the pilot folder. Recorded AI answers, no paid call. The full
output is in `data/pilot/evidence/flow-run.md`, which is git-ignored.

**How it ran.** It is a scripted run on the real API, not a click-through in the browser. The first sheet of each
class was read by call 8 earlier, in the ingest. Here every sheet comes from the hand-keyed answer file.

- **3A** (16 checked):
  - 2-item counts: PV-HEARD 1.
  - One-question counts: PV-HEARD 2, SUB-NODEC 3.
- **3B** (18 checked):
  - 2-item counts: SUB-NODEC 1.
  - One-question counts: SUB-NODEC 2.
- **FAIL: Flow 1, a cohort forms after the second class.** With both settings on, no class reaches 1 in 4. The best
  is SUB-NODEC: 3 of 16 in 3A (4 needed) and 3 of 18 in 3B (5 needed). The coach's view says "No cohort formed", and
  each class shows its reason for each mistake. So flows 2 to 5 were not reached on real data. They pass on the
  synthetic scenario above.
- **Why the real classes differ from the synthetic scenario:**
  - On 703 − 468, the wrong answers (4 in 3A, 5 in 3B) are mostly 245: 2 of 4 and 3 of 5. That is SUB-NODEC (the tens
    is not reduced), not smaller-from-larger.
  - None of the wrong answers on 246 + 178 (3 and 4) matches an error function.

  The synthetic scenario maps "wrong across a zero" to smaller-from-larger, because SUB-SFL is the only mistake with
  approved lesson content today. **That mapping is an assumption, not the pilot's pattern.**

## What is still open

1. **The real pilot classes do not form a cohort under any setting built here.** Forming one would need a lower class
   line, or an across-a-zero track (SUB-NODEC has no approved lesson content yet). That is a human decision (Seema,
   Gopi). Parked in `docs/build/PARKING.md`.
2. **Approved strategies.** The strategy library is still a draft, so in the chat the AI abstains and a person answers.
   The auto-send path is tested in `tests/chat/`, but it cannot run in this flow until strategies are approved.
3. **The phone's own error finder** does not compute the one-question ("possible") counts yet. The synthetic classes are
   worked out on the server, and the pilot run in a local script. A check entered on a phone sends 2-item counts only.
4. **The in-browser pilot entry** (*Enter from the pilot sheets*) is not wired into the two-class run. Step 5 used the
   local script.
5. **The paper record:** the post-test must add a second item for each single-question skill (items 11, 14, 15, and
   dictation with a zero). Then `COHORT_ALLOW_SINGLE_ITEM_PROBES` is no longer needed (`docs/pilot/PILOT-DEMO.md`).
6. **Hindi and Tamil** for the new screen and the code-written lesson are first drafts by the build, not yet read by a native speaker.
7. **The run's state** (lessons, feedback, events) is kept in one JSON column per run, for the judge demo. A production
   cohort would keep feedback in `lesson_taps` and lessons in track manifests.
