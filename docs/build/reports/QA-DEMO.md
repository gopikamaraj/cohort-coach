# QA: the full demo with the AI offline

Run on 1 Nov 2026, while the Claude API key was unavailable (the workspace's monthly limit). No live AI call was made: the browser tests use `AI_MODE=recorded` (answers replayed from `ai/fixtures/recorded/`) and `AI_MODE=off` (every call fails as if the service were unreachable), with `SPEECH_MODE=stub`. Synthetic data only.

Status: **findings written (Step 5); fixes in progress (Step 6).** This file is updated after the fixes and the second run.

## How it was run

| What | How |
| --- | --- |
| Demo path, recorded AI answers | `apps/pwa/e2e/demo-path.spec.ts`: all demo steps on a phone (390 × 844) and a desktop (1280 × 800), with axe, a layout check, a raw-text check, a tap-target check and a screenshot on every screen |
| Demo path, AI off | `apps/pwa/e2e/demo-path-ai-off.spec.ts`, against a second API with `AI_MODE=off` (port 8012) and a second preview (port 4174) |
| Roles, every screen, languages, speed | `apps/pwa/e2e/qa-screens.spec.ts`: the tabs of each role in order, axe on every screen each role reaches, Hindi and Tamil on the main screens, a throttled-phone timing |
| Widget checklist | `docs/build/qa/WIDGETS.md`, generated from the code by `python scripts/qa_widgets.py` (23 screens, 574 widgets with a test id) |
| Screenshots | `docs/build/qa/screens/` (`phone-*`, `desktop-*`, `off-*`, `lang-hi-*`, `lang-ta-*`) |

## Disagreements between the requirement list and the repo docs

The requirement list in the QA prompt is newer than the repo docs; where they differ it wins, except where it conflicts with a non-negotiable in `CLAUDE.md`, which is listed under Open questions.

| Requirement list | Repo docs | What was done |
| --- | --- | --- |
| Demo stepper "Demo step n of 12" | `DemoPanel.tsx`, README, INVENTORY X36: "n of 11", step 12 optional | Changed to 12 steps; the two-classes step (13) is labelled Optional |
| The demo forms 3 cohorts, the teacher's class in 2 | `CLAUDE.md` §5: one track per class per term | Kept one track a term; the screen now says her class is in 2 of the 3 cohorts, one this term and one next term (Open question 2) |
| A Recorded AI answer label and an AI mode badge | Not in any doc | Built (Step 1) |
| Masking on Practice Class input | Masking existed for the cohort chat only | Built |
| Roll list "Roll no N - status", Next not entered, Finish entering marks the rest absent, Reopen | Check screen: "Child N · state", Next child, Finish and see results | Built (see M1, M2) |

## Findings

Severity: 1 Blocker, 2 Honesty or privacy, 3 Wrong content, 4 Missing, 5 Polish. Result: Pass, Fail, Missing, Wrong content, Not built and correctly labelled.

### Step results (first run, before fixes)

| Step | Phone | Desktop | Notes |
| --- | --- | --- | --- |
| 1 Start | Pass, with W1 | Pass, with W1 | Badge missing before Step 1 (H2) |
| 2 Home | M4 | M4 | Navigation order passes |
| 3 Papers, create | Pass | Pass, P1 | Twin note, paper code |
| 4 Files and demo sheets | Pass | Pass | 20 sheets, `3A-roll07.png`, label, `reads.json` |
| 5 Import from a PDF | Pass, with P7 | Pass, with P7 | Recorded read labelled after Step 1 |
| 6 Enter check | W2, W3, M1, M2, M3, H5 | same | Sheet 1 has no recording to replay (Open question 3) |
| 7 Review drawer | Pass | Pass | 40% of the height (phone), 40% of the width bottom right (desktop), focus, Escape, unsure cell |
| 8 Submit and class card | Pass | Pass | |
| 9 Other classes, cohorts | W7 | W7 | 3 cohorts, all Simulated |
| 10 First audio lesson | M5 (fixed in Step 1) | same | Badge was server English (W5) |
| 11 Feedback, Generate next lesson | Pass (two-classes step, `e2e/two-classes.spec.ts`) | | |
| 12 Practice Class | H1 | H1 | Five children, text always shown |
| 13 Cohort chat | M7 | M7 | Abstention shown; no approved material for a sourced draft |
| 14 Coach | W4 (fixed in Step 1), H4 (fixed in Step 1) | same | |
| 15 SCERT officer | Pass | Pass | Under 5 hidden, Simulated, no names |
| 16 Post-test | Pass | Pass | Labelled Demo data |
| 16b Two classes (optional) | W1 (no demo bar) | same | |
| 17 Judge extras | H3, P4 | same | Testing evidence, assistant, AI map open |

### All findings, in severity order

| # | Step and widget | Expected | Found | Result | Severity | Screenshot |
| --- | --- | --- | --- | --- | --- | --- |
| — | Whole demo path | No step stops the demo | Both viewports reach the end in recorded mode | Pass | — | `phone-*.jpg`, `desktop-*.jpg` |
| H1 | 12 Practice Class, the teacher's typed or spoken line | Names masked before any model call (requirement 15) | The line goes to calls 2 and 1 as typed; masking exists only in the cohort chat | Fail | 2 Privacy | `phone-12-practice-turn.jpg` |
| H2 | Every AI answer; the header | "Recorded AI answer" on replayed answers; "AI: recorded answers" badge | Neither existed; nothing said an answer was replayed | Missing | 2 Honesty | `phone-01-start.jpg` (after) |
| H3 | 17 AI map (`#/aimap`); README "Where AI is used" | Planned calls never shown as working (requirement 14) | Calls 4 (method card) and 6 (digest) are listed like built calls; they have a prompt but no code; `AI_USAGE.md` says Specified | Fail | 2 Honesty | `desktop-17-ai-map.jpg` |
| H4 | 14 Coach, mentor method card | Not shown as working | A pre-written card from `demo/scenarios/mentor_card.yaml`, labelled Simulated mentor, with nothing saying call 4 is planned | Fail | 2 Honesty | `phone-14-coach.jpg` |
| H5 | 6 Enter check, Use sheet 1 (recorded mode) | Says honestly what happened | A newly made demo sheet can have no recording (its paper fingerprint is new), and the screen showed "demo 503" | Fail | 2 Honesty | `phone-06-entry.jpg` |
| W1 | 1 to 13, the demo bar | "Demo step n of 12" | "of 11"; on the optional step 13 the bar disappears (the stored step is capped at 12) | Wrong content | 3 | `phone-16b-two-classes.jpg` |
| W2 | Every demo step's error message | The server's plain message | "demo 503" for every server error: the error class's own `message` hid the server's text | Wrong content | 3 | `phone-06-entry.jpg` |
| W3 | 6 Enter check, roll list and dropdown | "Roll no N - status" | "Roll 1" (demo entry) and "Child 1 · not entered" (Enter check) | Wrong content | 3 | `phone-06-entry.jpg` |
| W4 | 14 Coach, status chips | Words | Raw codes `awaiting_coach`, `pending` | Wrong content | 3 | `phone-14-coach.jpg` |
| W5 | 10 Lesson badge (Hindi, Tamil) | In the chosen language | "Demo: pre-approved" came from the server in English | Wrong content | 3 | |
| W6 | README "Where AI is used" | Counts that match the table | "Eight Claude calls" over a table of 15 | Wrong content | 3 | |
| W7 | 9 Cohorts | Her class in 2 of the 3 cohorts, with reasons | "Your class is in this cohort" on one card and "next term" on another; no line says 2 of 3 | Wrong content | 3 | `phone-09-cohorts.jpg` |
| M1 | 6 Enter check and demo entry | Next not entered | Only Next child (Enter check); nothing in the demo entry | Missing | 4 | |
| M2 | 6 Finish entering | A confirm dialog; the rest marked absent; Reopen afterwards | No dialog; Enter check's Finish does not mark the rest absent; no Reopen | Missing | 4 | |
| M3 | 6 Demo entry, roll list | Absent for a roll number with no sheet | Mark absent only inside the drawer, for a sheet already read | Missing | 4 | |
| M4 | 2 Home | Assigned to you card | Not on Home (it is in Enter check) | Missing | 4 | `phone-02-home.jpg` |
| M5 | 10 Lesson | Offline download | No download link | Missing | 4 | `phone-10-lesson.jpg` |
| M6 | AI widgets, off mode | A message, the work kept, the non-AI path | No message anywhere; buttons stayed enabled and failed | Missing | 4 | `off-*.jpg` |
| M7 | 13 Chat | A recorded draft with sources, and an abstention | Only the abstention: no teaching strategy is approved yet, so nothing can be drafted from approved material | Missing | 4 | `phone-13-chat.jpg` |
| M8 | Profile, backup file input (every role) | A label (axe `label`) | No accessible name | Missing | 4 | |
| M9 | Coach, mentor, audit, AI map | Scrollable regions reachable by keyboard (axe `scrollable-region-focusable`) | `main` and the AI map table scroll but take no focus | Missing | 4 | |
| P1 | Desktop side rail | Labels whole | "My programme" breaks inside the word ("programm / e") | Polish | 5 | `desktop-05-import-review.jpg` |
| P2 | Phone header | One row | Assistant, AI badge and connection pill take two rows | Polish | 5 | `phone-01-start.jpg` |
| P3 | Papers, paper rules (Hindi, Tamil) | No English left | The rules section is rule data in English (templates, ids) | Polish | 5 | `lang-hi-papers.jpg` |
| P4 | Judge view on a judge deployment | | The For judges tab shows in every view-as role, labelled "Judge view. Not shown to teachers." | Pass (by design, Open question 1) | — | |
| P7 | 5 Import review | The table beside the image | The image sits above the table | Polish | 5 | `desktop-05-import-review.jpg` |

## Fixes (Step 6), in severity order

| # | Change | Requirement | Proof |
| --- | --- | --- | --- |
| H1 | The Practice Class masks the teacher's line (names, roll numbers, phone numbers) before calls 1, 2 and 3 and before the server record; the five pretend children's names are kept (`mask_personal(..., keep=...)`) | 15 | `tests/practice/test_session.py::test_a_real_childs_name_is_masked_before_any_model_call_but_the_pretend_children_keep_theirs`, `tests/chat/test_mask.py::test_names_in_keep_are_left_and_every_other_name_is_still_masked` |
| H2, M6 | `AI_MODE=off`; `/api/health` reports the mode; header badge (AI: recorded answers, AI: off); Recorded AI answer on each AI answer (sheet reads, the drawer, Practice child lines, lesson 1 and lesson 2 drafts, chat answers, the PDF import, the photo read); in off mode a note and the non-AI path on each AI widget, with Read sheet 1, Re-read, the photo read and the PDF upload disabled with the reason on screen | 1, Step 1 | `tests/ai/test_client.py` (off mode), `tests/api/test_health.py`, `e2e/demo-path.spec.ts`, `e2e/demo-path-ai-off.spec.ts` |
| H3, W6 | The registry's `built` flag; the AI map shows "Planned, not built" on calls 4 and 6; the README counts 13 built calls and marks 4 and 6 | 14 | `tests/ai/test_registry_built.py` (built means code calls it) |
| H4 | The mentor card says it was written for the demo and that call 4 is planned | 14 | `e2e/demo-path.spec.ts` (`demo-mentor-planned`) |
| H5 | The demo read says why nothing came back: recorded mode (no recording of a new sheet) or off; Auto-fill and typing named; nothing is counted | 1 | `tests/demo/test_demo_api.py::test_without_a_live_model_the_read_says_why_and_counts_nothing` |
| W1 | Demo step n of 12; step 13 Optional and keeps the bar | Step 3.1 | `src/lib/demoStudio.test.ts`, `e2e/demo.spec.ts`, `e2e/demo-path.spec.ts` |
| W2 | Demo errors show the server's words | Step 4 (errors) | `src/lib/demoStudio.test.ts` |
| W3, M1, M2, M3 | Roll no N - status; Next not entered; Finish entering asks and marks the rest absent; the finished check shows See results and Reopen; the demo entry has Absent per roll number, Next not entered, the confirm and Reopen the check | 4 | `e2e/demo-path.spec.ts`, `e2e/check.spec.ts`, `e2e/app.spec.ts` |
| W4 | Status codes shown as words (`item.st.*`) | 16 | `e2e/demo-path.spec.ts` (`demo-mentor-status`), `e2e/demo.spec.ts` |
| W5 | The pre-approved badge is translated on the phone | 16 | `e2e/demo-path.spec.ts` |
| W7 | "Your class is in 2 of the 3 cohorts: SUB-SFL this term and ADD-NOCARRY next term (one track a term)" | 7 | `e2e/demo-path.spec.ts` (`demo-in-two`) |
| M4 | Assigned to you on Home, with an empty state and a Create a paper link | 2 | `e2e/demo-path.spec.ts` (`assigned-home`) |
| M5 | Lesson 1: Download for offline | 8 | `e2e/demo-path.spec.ts` |
| M8 | The backup file input has a label | 16 | `e2e/qa-screens.spec.ts` (axe) |
| M9 | `main` and the AI map table take keyboard focus so they can be scrolled | 16 | `e2e/qa-screens.spec.ts` (axe) |
| P1 | The side rail breaks only between words | 16 | `desktop-*.jpg` |
| P3 | Rule details fold for a teacher under a translated "(written in English)" summary; open for a coach | 16 | `e2e/qa-screens.spec.ts` (Hindi, Tamil) |
| P7 | The import page sits beside the review table on a wide screen | 5 | `desktop-05-import-review.jpg` |
| — | When the move labeller fails, code finds the one child she named, so that child answers (found while reviewing the screenshots the user sent) | 9 | `tests/practice/test_calls_1_2.py::test_a_failed_call_still_finds_the_one_child_she_named_by_code` |

Not fixed, with a reason: **M7** (a sourced chat draft needs approved strategies: a human gate, not code); **P2** (the phone header takes two rows with the AI badge; the badge stays visible because it is the honesty label).

### Checks that passed

- **Roles:** the tabs of teacher, mentor, coach, officer and judge match the requirements in order; officers have no Papers page and no Create a paper.
- **Accessibility:** axe found nothing on any demo-path screen on either viewport; the only violations on the role sweep are M8 and M9.
- **Layout:** no horizontal scroll on any screen at 390 px or 1280 px; no raw string key or error text on any screen.
- **Tap targets:** no visible button or field under 44 px on the demo path.
- **Not built, never shown:** no Bayesian model, belief engine, pulse check, progress view, next-step policy or phone voice is named anywhere in the app, README, help pages or rubric map.
- **Pilot:** the Pilot data source is hidden on a machine without the pilot folder (the hosted demo), so it is never offered there.

## Open questions

1. **Judge tools in view-as.** On the judge deployment (`JUDGE_MODE=1`) the Practice Class's For judges tab shows in every role a judge views as. It is labelled "Judge view. Not shown to teachers." and never appears on a teacher deployment. Kept.
2. **Her class in 2 cohorts.** `CLAUDE.md` says one track per class per term. Kept that rule and changed the wording: her class is in 2 of the 3 cohorts, one this term and one next term. Changing the rule needs a human decision.
3. **Recorded mode and new demo sheets.** Every demo paper prints its fingerprint, which is new on every device, so a freshly made sheet can never match a recorded read. In recorded mode the read now says so plainly and the user goes on with Auto-fill or typing; the sheet read is replayed only where the image is fixed (tests). Changing how papers are fingerprinted was out of scope.
4. **Hand-made fixtures.** Some recorded answers were written for tests, not recorded from the model (each file says so in a `note`). They still show "Recorded AI answer", the label the requirements name, and no evidence number is ever computed from them.
5. **Server messages in English.** Messages the server writes (errors, a few labels) are English only; the screens translate the ones on the demo path.
