# Claude Code prompt: the end-to-end demo flow (Demo Studio)

Paste everything below the line into Claude Code at the repo root. It builds on the prompts for checks, Paper Studio, the role-based assistant, tester stats and the UI re-skin. Reuse what exists. Where a piece it needs does not exist yet, build the smallest version that satisfies the interface named here.

---

**Task.** Build the judge's **demo flow**: one guided path of 11 steps, from generating a paper to the SCERT dashboard, running on synthetic data that is clearly labelled. A judge must be able to complete it in about 15 minutes, using real code paths, with real AI calls where the product uses them and clear labels where it does not.

**Defaults chosen (follow them):**

- The review drawer is a bottom drawer: 40% of the available width on desktop (anchored bottom right), and 40% of the height on phones (full width).
- In step 4 the teacher uploads sheet 1 and the AI reads it (a real AI call). **Auto-fill the other sheets** then loads the other sheets' data from the demo answer file made with the sheets, with no AI calls, and says so on screen.
- The first audio carries a visible "Demo: pre-approved" badge. Later content still goes through the coach in step 10.
- In judge mode the chat timeout is 60 seconds, with a "Skip the wait" button.
- Only sheet 1 is read live by the AI (cached by image hash). Any sheet can be re-read with the AI on request, within the cost cap.
- Each judge gets an isolated demo class, and a Reset button restarts the demo.
- An optional step 12 simulates the post-test.

**Rules.**

- **Honesty first.** Every synthetic sheet, simulated class, cohort member and chart built from them shows a visible **Demo** or **Simulated** label. Synthetic sheets also carry it in their file metadata and in a small footer on the image. Reading accuracy on synthetic sheets is reported separately and is never presented as evidence of real-world accuracy. A sheet whose data came from the demo answer file is labelled Read from demo answer file, and is never presented as an AI read.
- **No child data and no names.** Synthetic sheets use roll numbers only.
- **Real code paths.** The demo drives the same generator, error finder, cohort logic, track picker, chat and dashboards that real use does. The reader is live for sheet 1 and for any sheet re-read on request. The other sheets use the demo answer file, and the screens say so. No hard-coded screens.
- **Isolation.** Each judge session has its own demo class and data. Nothing leaks between sessions, and the demo never touches pilot data.
- **Cost and speed.** AI sheet reads (sheet 1, and any re-read) are cached by image hash and count against a per-session cost cap, with a plain message when it is hit.
- Follow DESIGN.md. Tag every demo event for tester stats.

**Step 0. Read first.** Read CLAUDE.md, DECISIONS.md, PROGRESS.md, docs/design/stitch/DESIGN.md, docs/RUBRIC\_MAP.md, and the existing code for: judge mode and view-as, the check record and Start a check, Paper Studio and its PDF, the sheet reader and the Enter the check screen, the Bayesian child model and the simulated block generator, the error finder, cohort formation and mentor matching, the track picker and audio generation, Practice Class, the cohort chat and AI drafts, the coach inbox, the officer dashboard, the knowledge base, the guided tour, and the role-based assistant.

## The 11 steps

1. **Start:** sign in as a judge, view as **Teacher**, language **English**.
2. **Generate a paper:** with no past data, the teacher enters the class details and the short intake form in Paper Studio, and generates a **pre-test paper**.
3. **Generate demo sheets:** Paper Studio offers **Generate 20 filled sheets for this paper**. Download the paper and the sheets. Each sheet file is named with the class code and roll number, for example `3A-roll07.png`, and a ZIP is offered. The ZIP also holds reads.json, the demo answer file with each sheet's answers, confidences and flags.
4. **Enter the check:** upload sheet 1 and the AI reads it. Then choose **Auto-fill the other sheets** to load the rest from the demo answer file.
5. **Review:** each roll number shows its status. A preview icon opens the drawer with the sheet image beside the data the AI read. She verifies and approves each sheet.
6. **Submit the check:** after Finish entering, offer **Simulate other classes' results** (demo only).
7. **Form cohorts:** the simulated classes and her class form **3 cohorts**, and her class is in **2** of them.
8. **First audio:** generate the first audio intervention with the tip, strategy and script.
9. **Practice Class:** try the intervention content with the simulated children.
10. **Cohort chat:** ask a question, and the AI answers from the approved guidelines.
11. **Coach and SCERT views:** the coach sees the cohorts and the review queue and approves content. A SCERT officer sees the cohort situation on a dashboard.
12. **Optional:** simulate the post-test and show before and after.

## Step A. Demo scenario and synthetic class

1. A **scenario file** (`demo/scenarios/class_3a.yaml`) sets the class code, strength (20), the language, the error mix to plant, and a seed. Tune the mix so the class has two main error patterns (borrowing across a zero, and a three-digit sum with two carries) and a small third pattern (numbers with a zero) below the cohort threshold. Use the existing cohort rule, and adjust the planted counts until her class lands in exactly two of the three cohorts.
2. **Generate the children from the Bayesian child model.** Draw each child's hidden state from the scenario, then each child's answers to the generated paper from the model's answer table. This gives plausible errors and a known truth. Save the truth as JSON (never shown to the teacher) for the reading check.
3. The scenario is deterministic from its seed. A **Regenerate** option uses a new seed.

## Step B. Synthetic sheet images

1. Render each child's paper as an image from the paper's layout map: the printed form, a roll number, and handwriting-style answers written into the answer boxes, including small borrow and carry marks for some children.
2. Use handwriting-style fonts and add realistic noise: small rotations, shadows, uneven ink, paper texture, slight blur, and perspective.
3. Include a few hard cases (about 2 or 3 of 20): a smudged answer, a crossed-out answer, and a blank. These should produce low-confidence reads, so the judge sees the review step matter.
4. Footer text on every image: **"Demo sheet"**. Add the same flag in the PNG metadata, and mark the sheet **Demo** in the app after upload.
5. **Look at the images.** Render samples and view them before moving on. Fix clipping, unreadable digits and unrealistic noise.
6. Name files `{classcode}-roll{NN}.png`, and offer a ZIP and a printable PDF of the blank paper. Also write the demo answer file (reads.json), which holds what a reader would return for each sheet, with low confidence on the hard cases, and a separate truth.json that the app never shows.

## Step C. Auto-fill and review

1. **Sheet 1 is read by the AI.** The teacher uploads sheet 1 and the AI reads it (a real call, cached by image hash). Show the image beside the read data, labelled Read by AI.
2. **Auto-fill:** upload the other images at once. Recognise each demo sheet from its metadata, match it to a roll number (by file name, or by the printed roll box if the name is missing), and load its data from reads.json. No AI call is made, and the screen says so: Read from demo answer file. The load is instant, with no fake progress. The printed check code is compared with the open check, with a warning on a mismatch. If an uploaded image is not a demo sheet, read it with the AI instead. If the session has lost its answer file, offer to upload reads.json.
3. **Status per roll number**, as in the check prompt: not entered, entered, absent. Auto-filled sheets show **Read, needs review** until she approves them.
4. **The drawer.** A preview icon on each roll number opens a bottom drawer: 40% of the available width on desktop (anchored bottom right), and 40% of the height on phones (full width). It shows the sheet image (with zoom and rotate), and the read data beside it with low-confidence answers highlighted and editable. Buttons: Approve, Next unreviewed, Mark absent, and Re-read with AI (a live call within the cost cap, which replaces the data and relabels it Read by AI). Keyboard and screen reader accessible.
5. Only approved reads move on to the error finder. **Finish entering** marks unentered roll numbers absent, as in the check prompt.
6. A **demo reading summary** (demo mode only) compares the AI reads (sheet 1, and any sheet re-read with the AI) with the known truth and shows how many were read correctly, leaving out sheets loaded from the demo answer file, labelled **Synthetic sheets**. Save it to `docs/evidence/demo_synthetic_reading.md`. It is not evidence of real handwriting accuracy.

## Step D. Simulate other classes, and form cohorts

1. After the check is submitted, a demo-only button **Simulate other classes' results** creates about 24 classes in 8 schools from the simulated block generator, with class-level counts only, all labelled **Simulated**.
2. Run the real cohort formation on those classes and her class. Show the **3 cohorts**, the rule that put each class in, the member count, and a suggested **mentor** (a class that did better on the same error). Her class is a member of 2, shown clearly.
3. A visible **Simulated** label on every simulated class and on each cohort count.

## Step E. First audio, Practice Class and chat

1. **First audio.** The track picker chooses the approach for her first cohort from the error and what she has tried (nothing yet). The AI drafts the script (tip, strategy, short steps, a closing line) from the knowledge base. Voice it (server voice) and show the script as text. Show the **Demo: pre-approved** badge. Audio is generated once per scenario and cached, with a regeneration option.
2. **Practice Class.** A button on the audio takes her to Practice Class with the suggested next step set from this lesson. The five simulated children's levels come from her class's data.
3. **Cohort chat.** She asks a question. The AI drafts an answer from the approved guidelines with citations, or says it has no source. In judge mode the timeout is 60 seconds, with a countdown and a **Skip the wait** button. The reply is labelled as AI-generated from approved material, and a mentor or coach can correct it.

## Step F. Coach and SCERT views

1. **Coach (and mentor).** The coach sees the three cohorts, each member count and mentor, plus a **review queue** holding: the demo teacher's chat question with its AI reply, a mentor method card draft (seed one from a fixed simulated mentor transcript), and the AI-drafted second audio. Approve, edit or reject each, with a reason.
2. **SCERT officer dashboard.** The cohort situation: classes per cohort, shares of classes by error, tracks started, approvals pending, and, after the optional step 12, before and after by cohort. Counts only, never fewer than 5 in any cell, every number labelled **Simulated** where it is. No individual teachers or children.

## Step G. The demo stepper and reset

1. A persistent **Demo step n of 11** panel with a one-line description, a **Next** button that opens the right screen with the right data, and a **Back**. It uses the guided tour and links each step to the judge guide's question for that screen.
2. A **Reset demo** button restarts with a fresh class and clears the session's demo data after a confirmation.
3. **Isolation:** every judge session gets its own demo class code and data, keyed to the device profile.
4. **Optional step 12:** simulate the post-test results for her class (a labelled twin paper and simulated sheets, or class-level counts) and show the before and after view with a **Simulated** label.

## Step H. Tests first

- **End to end (Playwright):** run all 11 steps as a judge in English, and assert each screen and label. Run it in Hindi for the main screens.
- **Determinism:** the same scenario seed gives the same sheets and the same cohorts. Her class is in exactly 2 of 3 cohorts.
- **Labels:** every synthetic sheet, simulated class, cohort count and dashboard number is labelled. A test fails if any demo data appears without a label.
- **Files:** names follow `{classcode}-roll{NN}.png`, and the metadata flag is present.
- **Auto-fill:** demo sheets load from reads.json with zero AI calls and the label Read from demo answer file; sheet 1 is read by the AI and cached by hash (a second run makes no AI call); a non-demo image falls back to the AI; roll matching by file name and by printed roll box; code mismatch warning; hard cases carry low confidence; Re-read with AI works within the cost cap.
- **Drawer:** opens as a bottom drawer at 40% width on desktop and 40% height on phones, shows the image and read data, and is keyboard accessible.
- **Isolation:** two sessions never see each other's data. Reset clears only the session's own data. The demo never touches pilot data.
- **Chat:** an answer without a source abstains. The skip-the-wait button sends the labelled reply. The coach can correct it.
- **Privacy:** minimum-5 rule on the dashboard, and no names anywhere.
- **Cost cap:** the per-session cap stops AI calls with a clear message.
- Axe accessibility checks on every new screen.

## Step I. Evidence and kit updates

- `docs/evidence/demo_synthetic_reading.md` (synthetic only, labelled), and a measured time and cost for one full demo run.
- RUBRIC\_MAP.md: rows for the demo flow and what is simulated, with status Simulated where it applies.
- AI\_USAGE.md: note that in the demo sheet 1 is read by a real AI call on synthetic input (cached), and the other sheets load from a demo answer file.
- DECISIONS.md: an entry dated 2026-10-31 with the defaults chosen above.
- README: the demo steps, the judge credentials, and how to reset.
- The role-based assistant's judge documents: add the demo steps and the Simulated labels.
- docs/design/stitch/INVENTORY.md updated. Report: `docs/build/reports/DEMO-FLOW.md`.

**Order:** A and B (look at the images), then C, then D, then E, then F, then G, then H and I.

**Done when** a judge can run all 11 steps in one sitting, every demo number is labelled, the end-to-end test passes, sheets are named by class and roll number, and the synthetic reading summary exists.
