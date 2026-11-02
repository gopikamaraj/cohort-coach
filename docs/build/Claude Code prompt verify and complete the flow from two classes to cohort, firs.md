# Claude Code prompt: verify and complete the flow from two classes to cohort, first lesson, feedback, chat and the coach view

Paste everything below the line into Claude Code at the repo root.

---

**Task.** Check five connected flows end to end, write down what works and what does not, then build what is missing and check again:

1. After the **second class's pre-test sheets** are entered, a **cohort forms** from the two classes' data.
2. The **first audio lesson** is generated for the cohort.
3. After the first lesson, the teacher can give **feedback** and there is a **Generate next lesson** option.
4. The **cohort chat** works between the two teachers, with the AI drafting and a person in control.
5. A **coach** can see the cohorts and what is happening in each.

The lessons are audio lessons. Where this prompt says "lesson", it means the audio lesson with its script.

## Rules

- **Verify first, then change.** Before editing any code, run the checks in Step 2 and write the results into the report. Do not hide a failure by changing a test.
- **No real child data in the repository or in tests.** Automated tests use a synthetic two-class scenario that copies the pilot's patterns (Step 1). The real pilot sheets are used only in the manual run, locally, with `PILOT_DEMO=1`, and nothing from them is committed, including screenshots.
- **No paid calls in tests.** Use recorded AI answers and a fake voice provider. A manual demo run may make real calls within the cost caps.
- **Policy changes are explicit.** If a rule (the minimum number of classes in a cohort, or how single-question probes count) blocks the flow, do not silently change the default. Add a setting, turn it on only for pilot and demo, label what it produces on screen, and record the decision in DECISIONS.md.
- **Keep the existing guardrails:** code decides, the AI words, names are masked before any model call, a person approves content (or the demo shows the "Demo: pre-approved" badge), silence is never scored, and coaches and officers see counts, not children.
- Follow DESIGN.md. English, Hindi and Tamil text must fit.

**Step 0. Read first.** Read CLAUDE.md, DECISIONS.md, PROGRESS.md, AI\_USAGE.md, docs/RUBRIC\_MAP.md, and the code for: Enter the check and the pilot and synthetic data sources, the error finder and its two-item rule, cohort formation and mentor suggestion, the track rule, call 5 (lesson drafting) and the Sarvam voice service, the lesson player, any feedback screen, the review queue, the cohort chat (call 13), its gating and timeouts, the coach screens, roles and the demo accounts, and the end-to-end tests.

## Step 1. Scenario and accounts

1. **Two teachers and a coach.** Make sure the demo has teacher **T1** (class 3A), teacher **T2** (class 3B), a **coach C1** in the same block, and optionally a mentor. Judge mode can view as each.
2. **A synthetic two-class scenario** (`demo/scenarios/two_classes_pilot_like.yaml`), generated with no real children, that copies the pilot's class-level patterns:
   - 3A, strength 21, 16 sheets: 4 children wrong on borrowing across a zero (703 − 468), 3 wrong on the three-digit sum with two carries (246 + 178), 3 writing numbers with a zero wrongly, 1 subtracting wrongly after borrowing, 2 confusing signs; 5 fully correct.
   - 3B, strength 19, 18 sheets plus one absent: 5 wrong across a zero, 4 wrong on two carries, 2 subtracting wrongly after borrowing, 1 confusing signs; 11 fully correct. It uses the pilot's Form A paper (15 items, dictation numbers 305 and 496 for 3A, and 346 and 728 for 3B).
3. **A manual pilot run** for later: the steps in `docs/pilot/PILOT-DEMO.md` with the real sheets, entered as 3A by T1 and 3B by T2.

## Step 2. Verify the five flows (before changing anything)

For each check, record **Pass, Partial or Fail**, with evidence: the test name, the log line, or a screenshot of synthetic data.

**Flow 1: a cohort forms from two classes**

1. After T1 submits 3A's check, the Papers page and the teacher's screen show cohort status **"waiting for other classes"**, or the existing equivalent.
2. After T2 submits 3B's check, cohort formation runs, either automatically or from a coach button. Record which, and how long it takes.
3. Cohorts appear for the errors both classes share under the existing rule. Each shows the error, the member classes, flagged counts per class, and why each class is in or out.
4. **Check the rules that could block it, and report the actual values:**
   - the **minimum number of classes** for a cohort;
   - the **two-item rule**: Form A probes borrowing across a zero (item 14) and the three-digit sum with two carries (item 11) with **one question each**, so these may only count as "possible" and not flag anyone;
   - whether **every Form A item** (including 11 to 15) has error probes in the engine;
   - the **class threshold** (share of flagged children) for joining a cohort. Write down which cohorts form with the synthetic scenario under the current rules, and which do not, and why.
5. A mentor suggestion appears when a class did better on that error, or a plain "no mentor suggestion" with the reason.
6. Each teacher sees her class's cohorts.

**Flow 2: the first audio lesson is generated**

1. When a cohort forms (or its track starts), the track rule records which error and why.
2. Lesson 1's script is drafted by call 5 from approved strategy content, with sources.
3. It is voiced in each teacher's language by the voice service, stored privately, and shown with its script, duration and play controls.
4. It goes to the coach's review queue, or carries the demo badge in judge mode. After approval it appears for both teachers.
5. It can be downloaded for offline play.
6. A voice failure leaves a text-only lesson with a retry, and logs it.

**Flow 3: feedback, and Generate next lesson**

1. After lesson 1 is played, or marked as listened, a feedback card offers **tried, partly, not yet**, and an optional note (text or voice). Names are masked.
2. The feedback is saved, and the coach and mentor see it as counts plus masked notes.
3. A **Generate next lesson** option exists after feedback. Record who can press it, and what it does.
4. If no feedback arrives by the set date, the planned lesson 2 goes out, and silence is not counted as a result.

**Flow 4: the cohort chat**

1. T1 and T2 both see their cohort's chat. A teacher outside the cohort cannot.
2. T1 posts a question that includes a made-up child's name. The name is masked before any model call and stored masked.
3. An AI draft appears from approved material with its sources, or the AI abstains.
4. The coach sees it in the inbox and can send, edit or replace it.
5. If no one acts before the timeout (60 seconds in judge mode), a labelled AI reply goes out, and the coach can correct it afterwards.
6. T2 sees the thread. A question typed offline queues and sends later.

**Flow 5: the coach sees the cohorts and what is happening**

1. A coach screen lists the cohorts, each with:
   - the error, member classes and teachers as counts, and the mentor suggestion;
   - lesson 1's status (drafted, approved, released), plays, and feedback counts (tried, partly, not yet);
   - lesson 2's status, chat activity (open questions, drafts waiting, auto-sent replies), and the next check's status.
2. Opening a cohort shows a timeline of these events, with links to the review queue and the chat.
3. Counts only, and no child-level data. A mentor sees only her cohort. An officer sees totals only.

## Step 3. Build what is missing

Build only what Step 2 found missing or broken, following these designs. Reuse existing code.

**Flow 1.**

- Make the minimum number of classes a setting (`COHORT_MIN_CLASSES`). Keep the production default. Allow 2 for pilot and demo, labelled **Pilot cohort, two classes** on screen.
- If the two-item rule stops the pilot's main patterns from forming cohorts, add a setting (`COHORT_ALLOW_SINGLE_ITEM_PROBES`), off by default and on for pilot and demo. Cohorts formed this way carry the label **Based on one question per child**. Note in the paper record that Form B must add a second item for each, so this stops being needed.
- Add any missing error probes for Form A items 11 to 15 from the existing bug functions.
- Make formation run automatically when a check is submitted (and keep a coach button). Show the reason when no cohort forms.

**Flow 2.**

- Connect cohort formation, the track rule, call 5, the voice service, the review queue, and release to the teachers.
- One lesson per cohort and language, with each teacher getting her language's version.
- Store the script text. Store audio privately and offer it for offline download.

**Flow 3.**

- A feedback card under the lesson player, shown once the lesson has been played or marked as listened.
- **Generate next lesson**, available to the teacher after she gives feedback (and to the coach for the cohort). **Code picks the next step within the cohort's track**:
  - *tried*: the next step in the track's sequence;
  - *partly*: the same approach, with a smaller step and more practice;
  - *not yet*: another approach from the strategy library for the same error, skipping what she already tried. The AI words lesson 2 from approved content with sources. It goes to review, or carries the demo badge. Record the decision and its reason.
- If there is no feedback by the set date, release the planned lesson 2.

**Flow 4.** Fix any gap in membership, masking, drafting with sources, abstaining, the inbox, the timeout with its label, correction afterwards, and the offline queue.

**Flow 5.** Build the coach's **Cohorts** screen and a per-cohort timeline from existing records, with the counts above, links to the review queue and chat, and role limits for mentor and officer.

Add any missing screens to the demo stepper, and to the role-based assistant's help documents and suggested questions (for example "Why did no cohort form?" and "How is the next lesson chosen?").

## Step 4. Tests

- **One end-to-end test** across roles, with recorded AI answers and the fake voice provider: T1 enters 3A, T2 enters 3B, cohorts form, the coach approves lesson 1, T1 plays it and answers "not yet", T1 presses Generate next lesson, the coach approves lesson 2, T2 asks in the chat with a made-up name, the AI drafts, the coach sends, T1 sees it, and the coach's Cohorts screen shows the right counts.
- **Unit and API tests** for each flow: the cohort rules and both settings, labels shown when settings are on, Form A probes present, the lesson pipeline and voice failure, feedback saved and counted, the next-lesson decision for each answer (tried, partly, not yet, and silence), chat membership, masking, abstaining, the timeout, correction, the coach view's counts, and role limits.
- **Privacy:** no names in logs, drafts or the coach view. No real pilot data in fixtures.
- Axe accessibility checks on any new screen.

## Step 5. The manual pilot run

With `PILOT_DEMO=1` and the real sheets, enter 3A as T1 (first sheet read by the AI, the rest auto-filled) and 3B as T2, then walk through all five flows. Record results in `data/pilot/evidence/flow-run.md`, which is ignored by git. Commit only the counts and the pass or fail lines to the report.

## Step 6. Report and kit updates

- `docs/build/reports/FLOW-CHECK.md`: a table with flow, check, result before, what was missing, what was built, test name and result after. Add the rule values found in Flow 1, step 4.
- DECISIONS.md: an entry dated 2026-11-01 for any setting added, its default, where it is on, and its label.
- RUBRIC\_MAP.md, README and the demo stepper updated for the five flows.
- AI\_USAGE.md: note how call 5 is used for lesson 2.

**Order:** Step 1, then Step 2 in full with the report written, then Step 3 flow by flow (1, 2, 3, 4, 5) with its tests, then Steps 4 to 6.

**Done when** the report shows every check passing, or a clearly explained Partial, the end-to-end test passes, and the manual pilot run walks from the second class's sheets to the coach's view of the cohorts.
