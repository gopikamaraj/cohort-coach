# Claude Code prompt: full demo QA with the AI offline (every step, every widget, checked against the latest requirements)

Paste everything below the line into Claude Code at the repo root.

---

**Task.** The app's Claude API is unreachable right now (monthly limit). Test **everything else**:

1. Walk every demo step, on phone and desktop, in every role the demo uses.
2. Check **every widget** on every screen of that path: present, labelled, working, in every state.
3. Check that the **content matches the latest requirements and design** (listed below).
4. **Fix** what is wrong and **build** what is missing. Then run it all again.

AI features are tested with **recorded answers**, and the app's behaviour when the AI is **unavailable** is tested as a feature in its own right.

## Rules

- **No live AI calls.** Every AI call runs in `recorded` or `off` mode (Step 1). Never call the Claude API in this session, because the app's key is unavailable. Automated tests also use recorded voice. If the Sarvam key works, one manual run may voice the recorded scripts live (VOICE\_MODE=live), labelled as usual.
- **Honest labels everywhere.** Whatever the screen shows from a recording, a demo file, a simulation or the pilot is labelled as such. A recorded answer is never shown as a live one.
- **Verify first, then fix.** Write the findings (Step 5) before changing code. Do not weaken a test to make it pass.
- **Planned is not built.** A feature the requirements mark as planned or roadmap must not appear as working. If it appears, label it or remove it.
- **No real child data** in the repository, fixtures or screenshots. Synthetic data only, apart from the local pilot run, which stays in the git-ignored folder.
- **Smallest correct change.** Follow the requirements and DESIGN.md. Do not add features the requirements don't ask for. Every behaviour change gets a test.

## The latest requirements (source of truth, together with the repo docs)

Read DECISIONS.md, docs/RUBRIC\_MAP.md, AI\_USAGE.md, docs/design/stitch/DESIGN.md, docs/design/stitch/INVENTORY.md, README, docs/help/*.md and docs/build/reports/*.md. Where they disagree with this list, this list is newer. Record each disagreement in the report.

1. **Honest labels:** Demo, Simulated, Pilot data, Read by AI, Read from demo answer file, Read from pilot answer file, Demo: pre-approved, Recorded AI answer.
2. **Navigation order:** Home, Papers, Enter check, My class, Practice, My programme. Officers have no Papers page.
3. **Papers page:** create by rules or import from a PDF or answered sheet (AI reads printed questions, code computes keys, a person confirms). Cohort status per paper, with reasons. Assign to teachers, classes or cohorts, within scope.
4. **Enter check only chooses a paper:** Assigned to you first, with a Create a paper link. Data source Synthetic or Pilot (Pilot only when allowed). A roll list (Roll no N - status), Absent, Next not entered, and Finish entering, which marks the rest absent, then Reopen.
5. **Sheet 1 is read by the AI.** The rest auto-fill from the demo or pilot answer file, labelled.
6. **Review drawer:** a bottom drawer, 40% of the width on desktop (bottom right) and 40% of the height on phones (full width). The image sits beside the reads. Buttons: Approve, Next unreviewed, Mark absent, Re-read with AI.
7. **Cohorts:** form after submission, with reasons shown. Pilot and demo settings are labelled ("Pilot cohort, two classes", "Based on one question per child"). The demo forms 3 cohorts, with the teacher's class in 2.
8. **Lessons are audio:** lesson 1 is drafted, voiced and approved (or carries the demo badge), with the script as text and offline download. A feedback card (tried, partly, not yet, an optional note). **Generate next lesson**, where code picks the step and the AI words it. The planned lesson goes out after the set date, and silence is never scored.
9. **Practice Class:** five simulated children at different levels, seeded and rule-based. Server voice (Sarvam), and text always shown. The Bayesian model is planned and must not be claimed.
10. **Cohort chat:** names masked before any model call, drafts from approved material with sources or an abstention, the coach's inbox, a labelled AI reply after the timeout (60 seconds in judge mode, with Skip the wait), and correction afterwards.
11. **Coach view:** the cohorts and what is happening in each, as counts only, with a timeline. Mentors see their own cohort, and officers see totals (never fewer than 5).
12. **Role-based assistant:** scope enforced on the server. It asks for what is missing and fills drafts, but never confirms, approves, assigns, publishes, archives or deletes. The judge guide answers from repository documents.
13. **Tester profiles:** the first-run name prompt with consent, a feedback button, and a Testing evidence page for judges.
14. **Not built, so never shown as working:** the next-step policy, the Bayesian child model and belief engine, the phone's own voice, the method card (call 4), pulse checks and the progress view (roadmap).
15. **Privacy:** no names anywhere. Masking on Practice Class input must be added if it is still missing.
16. **Design:** Calm Institutional (Material 3, teal), 44 px touch targets, phone first, and English, Hindi and Tamil text that fits.

## Step 0. Read first

Read the documents above, the router and every screen on the demo path, the AI call wrapper and the call registry, the fixtures of recorded answers, the demo and pilot data code, and the existing Playwright, Vitest and pytest suites.

## Step 1. AI modes

Add or confirm a setting `AI_MODE` with three values:

- **`live`**: normal behaviour.
- **`recorded`**: every AI call returns a recorded answer keyed by call and input hash. Create the missing fixtures for every call on the demo path (sheet reading, move labelling, child lines, lesson drafting, chat drafts, the assistant, the PDF import read), using synthetic inputs and schema-valid outputs. Each recorded answer is labelled **Recorded AI answer** in judge mode. A header badge says **AI: recorded answers**. Voice uses recorded or generated test audio, labelled the same way.
- **`off`**: every AI call fails as it would when the service is unreachable.

In `off` mode every AI-dependent widget must show a clear message, keep the user's work, and offer the non-AI path. For example: enter the answers by hand, use the answer file, show the lesson script as text, or keep the chat question queued. Nothing crashes, and nothing pretends.

## Step 2. Widget inventory

Build `docs/build/qa/WIDGETS.md` from the code and INVENTORY.md: every screen on the demo path, every widget on it (buttons, links, inputs, tabs, chips, toggles, cards, tables, badges, banners, drawers, dialogs, players, charts), and for each widget its expected label, the roles that see it, its states (default, disabled with reason, loading, empty, error, offline) and what it does. This is the checklist for Step 4.

## Step 3. The demo script, step by step

Run each step in `recorded` mode, on phone (390 by 844) and desktop (1280 by 800), in English, with Hindi on the main screens. For each step, check every widget against the inventory and the requirements, and the content wording.

1. **Start.** First-run tester prompt (nickname, both consent choices, Use without sharing), judge sign-in, view as teacher T1 (class 3A), language switch, Assistant button, connection pill, demo stepper ("Demo step n of 12"), the AI mode badge, and Demo labels.
2. **Home (teacher).** Navigation order, the Assigned to you card, the class summary, and no working "Next step" feature unless it is labelled planned.
3. **Papers: create a pre-test.** The list (filters, status, source, cohort badge, actions), Create paper with its two routes, Generate from rules (class details, profile source, the six-question intake, language, form and kind, preview, key, coverage grid, anchor and adaptive labels, post-test twin created). The assistant's open questions: asked one at a time, filling drafts, tagged "Assistant changed this" with Undo, and Confirm disabled while a blocking question is open.
4. **Papers: files and demo sheets.** Paper PDF, key PDF, layout map, and Generate 20 demo sheets (names `{class}-roll{NN}.png`, a "Demo sheet" footer, `reads.json` in the ZIP).
5. **Papers: import from a PDF or answered sheet**, with a recorded read: the upload note, the review table beside the image, keys computed by code, a printed-key mismatch flag, unsupported items, the coverage warning, the approximate layout map label, Teacher-confirmed and Imported, awaiting review, and the file deleted on confirmation.
6. **Enter check.** Start a check, Choose a paper (Assigned to you first, the Create a paper link round-trips), Data source (Pilot hidden unless allowed), the check header and counts, the roll dropdown, Absent, Next not entered, the sheet 1 read (labelled Recorded AI answer in this mode), Auto-fill from the answer file (labelled, instant), a check code mismatch warning, Finish entering (confirm dialog, absent marking), and Reopen.
7. **Review drawer.** Sizes on desktop and phone, zoom and rotate, low-confidence highlights, Approve, Next unreviewed, Mark absent, and Re-read with AI (disabled with a reason in `off` mode). Keyboard and screen reader use.
8. **Submit and class card.** Counts and error names, the cohort status reason, and Why this? if built.
9. **Second class or simulated classes.** As teacher T2, enter 3B, or use Simulate other classes. Cohorts form, the reasons show, the pilot and demo labels appear, and the class is in 2 of 3.
10. **First audio lesson.** The lesson card, script text, player, duration, offline download, the language, the Demo: pre-approved badge, and the text-only fallback in `off` mode.
11. **Feedback and Generate next lesson.** The card's three answers and note, the next lesson's rule for each answer, review or the badge, and the set-date rule.
12. **Practice Class.** Five children, labels, child lines with the server voice (recorded) and text always shown, the suggested next step, the limit text, no Bayesian claim, masking of the teacher's input, and the `off` mode message.
13. **Cohort chat.** Membership, masking, the recorded draft with sources, an abstention case, the coach's inbox, the countdown with Skip the wait, the AI label, correction, and the offline queue.
14. **Coach.** The Cohorts screen and per-cohort timeline, the review queue (approve lesson 2), assignment from the Papers page within scope, and the mentor's narrower view.
15. **SCERT officer.** The dashboard as counts only, never fewer than 5, Simulated labels, and no names.
16. **Optional post-test.** Simulated post-test, before and after on anchors only, with the small-sample warning.
17. **Judge extras.** The Testing evidence page, the judge guide (role-scoped, citing files, slide numbers and timestamps, abstaining with no source), and the Logs and explainability page only if built, never claimed if not.

## Step 4. Cross-cutting checks

- **Roles:** every screen and widget is shown or hidden exactly as the requirements say, for teacher, mentor, coach, officer and judge, including view-as.
- **Languages:** Hindi and Tamil fit on every main screen, with no cut-off text, no English left in translated screens, and correct numerals.
- **Accessibility:** run axe on **every** screen in the inventory (not just three), plus keyboard paths, focus order, labels, 44 px touch targets, contrast and reduced motion.
- **Offline:** the photo queue, lesson playback offline, the chat queue, cached screens, and a clear connection pill.
- **AI unavailable (`off` mode):** every AI widget degrades as Step 1 says. Run the whole demo script once in `off` mode and record what a user can still do.
- **Honesty:** every recorded, demo, simulated and pilot value is labelled. Nothing planned appears as working.
- **Privacy:** no names in screens, logs or drafts. Pilot data is never in the build or the hosted config. Masking is applied to Practice Class input.
- **Hosted configuration:** the hosted build opens in demo mode with judge credentials and sample inputs, and never offers Pilot.
- **Errors and empty states:** every list has an empty state, every action has an error message, and no raw stack trace ever reaches the screen.
- **Performance:** each demo screen is usable within about 3 seconds on a throttled phone profile. Record the numbers.

## Step 5. Findings

Write `docs/build/reports/QA-DEMO.md`. For each step and widget: expected, found, the result (Pass, Fail, Missing, Wrong content, Not built and correctly labelled), the severity, and a screenshot path (synthetic only).

Severity, in this order:

1. **Blocker:** the demo path stops.
2. **Honesty or privacy:** a missing label, a planned feature shown as working, a name, a leak.
3. **Wrong content:** wording, numbers or rules that disagree with the requirements.
4. **Missing:** a widget or state the requirements ask for.
5. **Polish:** design, spacing, language fit.

## Step 6. Fix and build

Work through the findings in severity order. For each: the change, the requirement it satisfies, the test that proves it, and a short line in the report. If a requirement is unclear or two requirements conflict, choose the safer option, label it, and list it under **Open questions** in the report, never silently.

## Step 7. Tests

- `e2e/demo-path.spec.ts`: the full demo script in `recorded` mode, on phone and desktop, asserting every label and widget in the inventory.
- `e2e/demo-path-ai-off.spec.ts`: the same path in `off` mode, asserting the degradations.
- An axe check on every inventoried screen.
- A role matrix test (each role, each screen, each widget's visibility).
- Language checks for Hindi and Tamil on the main screens.
- Unit and API tests for every fix.
- All existing suites still pass. Report the counts before and after.

## Step 8. Screenshots and kit updates

- Save a screenshot of every step (phone and desktop, synthetic data only) to `docs/build/qa/screens/`, named by step, and link them from the report.
- Update INVENTORY.md, the demo stepper, docs/help/\*.md, RUBRIC\_MAP.md and README to match what the app now does.
- DECISIONS.md: an entry dated 2026-11-01 for the AI modes and any open question you resolved.

**Order:** Steps 0 to 2, then Step 3 and 4 with the report written (Step 5), then Step 6 in severity order with Step 7's tests, then Step 8, then run everything again and update the report. When the Claude API key is back, run the demo path once in live mode and add any differences to the report.

**Done when** both demo-path tests pass, axe passes on every inventoried screen, the report shows no Blocker and no Honesty or Privacy finding left open, every other finding is fixed or listed with a reason, and the screenshots exist.
