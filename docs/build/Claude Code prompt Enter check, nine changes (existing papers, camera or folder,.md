# Claude Code prompt: Enter check, nine changes (existing papers, camera or folder, roll dropdown with approval, image drawer, finish rule)

Paste everything below the line into Claude Code at the repo root. It changes the **Enter check** page (`#/check`). The earlier redesign specification for this page (if it is saved in `docs/build/`) is the base. **Where this prompt differs from it, this prompt wins.** The differences are listed in Step 10.

---

**Task.** Make the nine changes below. Do not add anything that is not here.

1. The page does not mention synthetic, pilot, demo data or any data source.
2. The teacher selects a question paper that was already generated.
3. Two ways to add the attempted sheets: the camera, and a folder of pictures. Check that folder selection works in the browser and the installed web app, and fall back where it does not.
4. The roll-number dropdown shows each roll's **data state** (Entered, Not entered, Absent) and its **approval state** (Approved, Not approved). The teacher marks absent with the existing checkbox, and marking a roll absent approves it automatically.
5. Remove the upload-the-first-sheet step and the auto-fill of the rest.
6. A small image icon beside the roll dropdown opens that roll's sheet picture in a drawer (40 percent of the height at the bottom on a phone, 40 percent of the width at the side on a laptop). The teacher uses it to check what the AI read, and approves.
7. **Finish entering** is enabled only when every roll is approved or absent. When it is disabled, a note on the page says why.
8. Remove **Use a sample sheet**. The team will publish a Google Drive link to a folder of test sheets in the deck, and testers will use that folder.
9. Show the three Missed the teaching checkboxes exactly as in the reference image.

## Rules that stay

- **No child names, faces or voices.** Roll numbers only.
- **Pictures are held in memory only.** Never write a sheet picture to IndexedDB, CacheStorage, localStorage, the phone's disk or the server. Revoke each object URL when it is no longer needed.
- **Code computes every number.** The page sends approved answers to the same `finishCheck` as today.
- **Honest source labels** on each roll: *Typed*, *Read by AI*, and *Recorded AI answer* when the server replays recordings. A feature that is not built is never shown as working.
- **Counts, not percentages,** for the teacher.
- **Design:** `docs/design/stitch/DESIGN.md` (Calm Institutional, teal), colours only from `theme.css`, 44 px touch targets (48 px for the primary button), sentence case, one primary action per state. Every string in `en`, `hi` and `ta`, and fitting without cut-off in Hindi and Tamil.
- **No AI call is added** beyond what a picture read already makes (call 8, blind to the answers), except the small extension in 3.2.

**Step 0. Read first.** `CLAUDE.md`, `DECISIONS.md`, `docs/design/stitch/DESIGN.md`, `docs/design/stitch/INVENTORY.md`, `docs/build/qa/WIDGETS.md`, and the code: `apps/pwa/src/screens/Check.tsx`, `components/StartCheck.tsx`, `components/PaperHubParts.tsx` (`PaperChooser`), `components/DemoEntry.tsx`, `components/PilotDataCard.tsx`, `components/SheetPreview.tsx`, `lib/check.ts`, `lib/checks.ts`, `lib/sheets.ts`, `lib/sampleSheets.ts`, `lib/paperKeys.ts`, `lib/demoStudio.ts`, `lib/aiMode.ts`, the call 8 reader and its recorded fixtures, and the strings `check.*`, `demo.entry.*`, `demo.drawer.*`, `pilot.*`.

## Step 1. Remove (changes 1, 5 and 8)

Remove from the Enter check page and from anything it renders, in every language:

- the **Data source** control (Synthetic, Pilot), the Pilot data and Simulated data banners, and the pilot folder probe;
- **Use the sample paper**, **Use a sample sheet**, and `lib/sampleSheets.ts` if nothing else uses it;
- the upload-the-first-sheet step and **Auto-fill the other sheets**, the labels *Read from demo answer file* and *Read from pilot answer file*, and the *verified* and *unverified* chips;
- the `DemoEntry` bulk path and its separate drawer, and the roll list and Finish behaviour that belonged to it.

If other pages still use any of this code (the demo stepper, Papers), keep the code and cut only the Enter check page's use of it. List in the report each file you removed or left, and why. After this step the page's text contains none of the words *synthetic*, *pilot*, *demo*, *simulated* or *sample*, except where the AI mode legitimately says *Recorded AI answer*.

## Step 2. Choose a paper that already exists (change 2)

- The setup card has **Choose a paper**: a radio list of the papers for this class that are already generated and usable (approved, or teacher-confirmed). Each row shows its code, kind, number of questions and source. **Assigned to you** papers come first and are marked, and one is pre-selected (the one assigned for the chosen kind, else the only paper).
- The kind and form come from the chosen paper. Changing the kind refilters the list. The existing post-test note (with *Make it a termly check*) stays.
- Date (not in the future), and **How many papers?**, now pre-filled from the class's strength and required (a whole number from 1 to 100). Remove its optional wording.
- A **Create a paper** link goes to Papers and returns here. Empty state: No paper for this class yet, with the link. Creating a paper is never done on this page.
- **Start the check** is disabled with the reason on screen until a paper is chosen. The paper's answer key is fetched to the phone, or its error is shown with Retry, as today. A paper is locked once any answer is entered.
- The hosted test deployment must have at least one generated paper for each test class that **matches the Drive test folder's sheets** (same form, items and dictation numbers), so the flow can be tried. Add it to the seed data and list it in the report.

## Step 3. Add the sheets: camera or a folder (change 3)

In the entering state, an **Add the sheets** card holds two actions. Both need a connection and the AI on. When the AI is off or the phone is offline, both are disabled with the reason beside them, and typing stays fully available.

### 3.1 The camera

**Take a photo of this sheet** applies to the selected roll, as today: `input type=file accept=image/* capture=environment` (on a laptop it opens the file chooser). The picture is shrunk on the phone, read by call 8, and the boxes fill in. Replacing typed answers asks first. The result is *Entered* and *Not approved*, labelled *Read by AI*.

### 3.2 A folder of pictures

**Select a folder of pictures** reads many sheets at once. Build and check it as follows.

1. **Feature detection, not browser sniffing.** Use `'webkitdirectory' in HTMLInputElement.prototype`. Where it is available, use `input type=file multiple accept=image/* webkitdirectory` and label the button **Select a folder of pictures**. Where it is not, show **Choose pictures** and use `input type=file multiple accept=image/*`, so the teacher selects many pictures from the gallery instead. Do not use `showDirectoryPicker`.
2. **What we know about support** (from browser compatibility data; confirm it yourself): `webkitdirectory` works in desktop Chrome, Edge, Firefox and Safari, and in recent Chrome for Android. It works in Safari on iOS only from version 18.4. Samsung Internet, Opera Mini and UC Browser do not support it, and some mobile pickers cannot choose a folder at all. Mobile Safari can also **scramble original file names**, so **never rely on file names** to identify a roll.
3. **Match each picture to a roll number**, in this order: (a) a file name like `3A-roll07` when present; (b) the class code and roll number **printed or written in the sheet's header**, read by the same call 8. If call 8's output does not already include them, extend its schema with a `header` object holding `class_code`, `roll_number` and `confidence`, and add the recorded fixtures; (c) otherwise ask the teacher: show the picture as a thumbnail and a roll chooser. Keep a matching summary she can see, for example: 24 pictures found, 20 matched to roll numbers, 3 need a roll number, 1 is not a picture and was skipped.
4. **Conflicts, handled in the open:** a picture whose class code differs from this check's class shows a warning and is not used until she confirms; two pictures for one roll show both and she picks one; a roll that already has answers asks **Replace** or **Keep mine** per roll (with Replace all and Keep all choices).
5. **Reading queue.** Read at most 3 pictures at a time, show Reading 7 of 20 with a progress bar (an `aria-live` region), allow **Cancel**, and keep going when one fails. A failed picture shows its reason and a **Try again** for that picture. Respect the per-session cost cap, and say plainly when it is hit.
6. **Shrink on the phone** (long edge about 1600 px, JPEG) and keep the shrunk copy in memory for the drawer. Compute a SHA-256 of the **original file bytes** before shrinking and send it with the read request, so recorded mode can replay the right answer by file hash, and so the same picture selected twice is read once.
7. **Recorded mode.** When the server replays recordings, a picture with no recording gets the plain existing message and the roll is left for typing. Create recordings for every sheet in the test folder (the team supplies it, for example `demo/test-sheets/`) and list the count in the report.
8. **Result.** Every roll filled this way becomes *Entered* and *Not approved*, labelled *Read by AI* (or *Recorded AI answer*), with unsure boxes marked. Nothing is approved automatically.

### 3.3 Prove that folder selection works

Automated (desktop Chromium, Playwright): `setInputFiles` with a folder path on the folder input, then assert matching, conflicts, the queue and the result. Also run the same test with `webkitdirectory` removed from the prototype (by an init script) and assert that the button says **Choose pictures** and that selecting several files works.

Manual (a checklist file for the team, `docs/build/qa/FOLDER-PICKER-DEVICES.md`): for each of Chrome on Android (in the browser and as the installed web app), Samsung Internet, Safari on iOS (and the home-screen app), and desktop Chrome, Edge, Firefox and Safari, record: the browser version, whether the picker offers a folder or only pictures, whether all pictures arrive, whether file names are kept, and how long reading 20 pictures takes. Leave the table for the team to fill, with the instructions to do it. In the report, state what was proved in automation and what still needs a phone.

## Step 4. The roll dropdown (change 4)

Keep a single dropdown (a labelled `select`), one option per roll number, 1 to the class size. Each option reads, in the user's language:

| Data state | Approval | Option text (English) |
| --- | --- | --- |
| Not entered | not applicable | Roll no 7 · Not entered |
| Entered | Not approved | Roll no 7 · Entered · Not approved |
| Entered | Approved | Roll no 7 · Entered · Approved |
| Absent | Approved (automatic) | Roll no 7 · Absent · Approved |

Beside the dropdown show a chip for the selected roll with an **icon and words** (never colour alone), the roll's **source** label, and the image icon of Step 6. Above the dropdown, one line of counts, `aria-live=polite`, for example: **18 entered · 12 approved · 3 absent · 7 not entered**.

- **Absent today: skip this roll number** stays as a checkbox for the selected roll, and **only the teacher sets it**. Setting it on a roll that has answers asks first and clears them. **Setting a roll absent approves it automatically.** Unticking returns the roll to *Not entered*.
- **Approve** is a primary button for a roll that is *Entered* and *Not approved*. It sets *Approved* and then moves to the next roll that is entered and not approved, or, when none is left, to the next *Not entered* roll.
- **Any change to an approved roll's answers, marks or tags sets it back to Not approved.** It must be approved again.
- Typed answers need approving too, with the same button. A roll with no picture can be approved after a confirmation: There is no picture to check against. Approve anyway?
- Buttons: **Previous roll no**, **Next roll no**, **Next not entered**, and **Next to approve** (disabled with Nothing to approve when none).
- Answers, marks and approval are saved on the phone after every change, as today.

## Step 5. The entry panel and the three checkboxes (change 9)

For the selected roll, in this order: the **Add the sheets** actions (camera), the boxes, the checkboxes, then Approve.

- **The boxes:** one per question of the chosen paper. Digits only (digits typed in Hindi or Tamil script are converted to 0 to 9), at most 9 digits, Enter moves to the next box. **Blank** and **Can't read** marks, and the **unsure** flag from the reader. An *adaptive* item carries a small tag: extra.
- **The checkboxes.** Always visible, never inside a disclosure, directly under the boxes. The heading is **Missed the teaching (from my register)**. Under it three checkboxes, in this order, with these labels (English), each a real `input type=checkbox` with its label, a 44 px target, and wrapping text:
  1. Missed the teaching on addition with carrying (questions 3–5)
  2. Missed the teaching on place value (questions 1–2)
  3. Missed the teaching on subtraction with borrowing (questions 7–10)

  **The question numbers must come from the chosen paper's own items**, by concept, formatted as ranges and lists (for a 15-item paper the carrying label may read questions 3–5 and 11, and the borrowing label questions 7–10 and 14–15). Do not hard-code them. If a concept has no items in the paper, omit its checkbox. The state is **per roll**, stays on the phone, is never sent, and changing it sets an approved roll back to *Not approved*. Provide the same labels in Hindi and Tamil.

## Step 6. The image icon and the drawer (change 6)

- A **small image icon button** (44 px, accessible name: Show the sheet for roll no N) sits next to the roll dropdown. It is disabled, with the reason No picture for this roll, when the roll has none in memory (after a reload the pictures are gone, by design; say so, and offer **Add a picture** for that roll).
- Clicking it opens the sheet picture in a drawer:
  - **phone (under 900 px):** a **bottom drawer, 40 percent of the viewport height**, full width;
  - **laptop (900 px and above):** a **side drawer on the right, 40 percent of the viewport width**, full height below the title bar.
- **The drawer is not modal.** The page stays visible, scrollable and editable in the remaining 60 percent, so she can compare the picture with the boxes. Add padding to the page so nothing is hidden behind the drawer.
- It holds: the picture (zoom in, zoom out, rotate, fit to width), the roll number and source, **Approve**, **Re-read with AI** (shown only when the roll was read and the picture is still in memory, disabled with a reason when the AI is off or offline), and **Close**.
- **It follows the dropdown.** Changing the roll updates the picture while the drawer stays open. Approve moves to the next roll to approve and shows its picture.
- Escape closes it and returns focus to the image icon. It is a labelled region (`role=complementary` with a heading), opened and closed without animation when the user prefers reduced motion. The picture's alt text is: The answer sheet for roll no N.
- Remove the old modal review drawer and its own Approve, Next unreviewed and Mark absent buttons. Their jobs now live on the page.

## Step 7. Finish entering (change 7)

- **Finish entering** is a primary 48 px button in a sticky bar with the counts. It is **enabled only when every roll is either Approved or Absent**, and at least one roll is *Entered and Approved*.
- **When it is disabled, a visible note directly above it says why** (not a tooltip). It is linked with `aria-describedby`, and it names rolls, capped at 8 with and N more:
  - nothing entered: Enter at least one child's answers first.
  - not entered: Roll no 4, 9 and 12 are not entered. Enter them, or mark them absent.
  - not approved: Roll no 2, 7 and 8 are not approved. Open the sheet, check the answers, and approve.
  - both: show both lines. When it is enabled the note reads: All N roll numbers are approved or absent.
- **No roll is marked absent automatically any more.** Only the teacher marks absent.
- Pressing it asks first: Finish entering? A children entered, B marked absent. You can reopen the check later. **Confirm** saves the answers, runs `finishCheck` on the phone (only approved answers feed it, absent rolls are excluded), closes the check, **drops every picture from memory**, and shows the finished state.
- The finished state, **See results** and **Reopen** are as today. After Reopen, approval states are as they were, and the pictures are gone.

## Step 8. States

| Part | Offline | AI off | Recorded AI |
| --- | --- | --- | --- |
| Choose a paper, start | works with papers and keys already on the phone | works | works |
| Typing, absent, checkboxes, approve | works | works | works |
| Camera and Re-read | disabled: needs a connection, typing offered | disabled: needs the AI, which is off right now; type the answers, nothing is lost | works; source says *Recorded AI answer*; a picture with no recording says so and leaves the roll for typing |
| Folder or pictures | disabled as above | disabled as above | works the same |
| Image drawer | works for pictures already in memory | works | works |
| Finish | works (the finder runs on the phone), and results sync later | works | works |

Every loading, empty and error message already in the page is kept or improved. Nothing is lost when a read fails.

## Step 9. Roles, strings and privacy

- **Roles:** teacher and mentor use the page. Coach and officer see: This page is for teachers. The judge sees it as a teacher.
- **Strings:** add or change keys in `en.json`, `hi.json` and `ta.json`, and list any placeholder translations in `docs/build/i18n-todo.md` for review. Remove only strings no test uses.
- **Privacy, to prove in a test:** after a full run, IndexedDB, CacheStorage and localStorage contain no image data. The network log shows the checkbox state and marks are never sent. Only approved class counts leave the phone at Finish.

## Step 10. What this prompt changes from the earlier redesign specification

| Earlier specification | This prompt |
| --- | --- |
| A grid of roll chips | A single dropdown with data and approval states |
| A modal bottom review drawer, 40 percent width on a laptop | A non-modal drawer: bottom, 40 percent height on a phone, and a side drawer, 40 percent width on a laptop |
| Finish marks empty rolls absent | Only the teacher marks absent. Finish is blocked until all rolls are approved or absent, with a visible reason |
| Typed rolls are approved by moving on | Every entered roll is approved with a button |
| Data source field, sample paper, sample sheet, auto-fill | All removed |
| The Missed the teaching tags collapsed under a disclosure | Always visible checkboxes, with question numbers from the paper |
| One way to read a photo | Camera, or a folder (or multiple pictures where folders are unsupported) |

## Step 11. Tests

Write the pure logic first, then browser tests.

- **Unit (Vitest):** the roll state function and the option text for every row of the Step 4 table; the counts line; absent sets approved; any edit to an approved roll resets it; the Finish gating and each note message (including the cap of 8); picture matching by file name, by header and by manual choice; digit conversion; the checkbox labels built from a paper's items (for the 10-item and 15-item papers).
- **Browser (Playwright):**
  - removal: no page text contains *synthetic*, *pilot*, *demo*, *simulated* or *sample* in English, Hindi or Tamil, and the removed buttons are gone;
  - choosing an existing paper: assigned first and pre-selected, the filter by kind, the Create a paper round trip, start disabled with a reason;
  - the roll dropdown: every option's text, the counts line, absent auto-approves, an edit reverts approval;
  - camera read with a recorded answer, then Approve moves to the next roll to approve;
  - folder: with the directory input, matching and the summary, a class mismatch, a duplicate, a replace conflict, the queue (3 at a time), cancel, a failed picture with retry, and the fallback **Choose pictures** when `webkitdirectory` is absent;
  - the drawer: bottom and 40 percent of the height at 390 by 844, side and 40 percent of the width at 1280 by 800, non-modal (the boxes stay editable), follows the dropdown, Escape and focus return, the disabled icon with its reason;
  - Finish: disabled with each reason, enabled when all are approved or absent, the confirm text, the finished state, Reopen then Finish again;
  - the three checkboxes: always visible, the labels and order, question numbers from the paper, per roll, not sent anywhere;
  - offline, AI off and recorded modes as in Step 8; Hindi and Tamil at 360 px with no cut-off;
  - privacy: no image data in any browser storage after a run.
- **Accessibility:** axe (WCAG 2 A and AA) clean in every state, a full keyboard path, 44 px targets, and reduced motion.
- **Existing suites:** update the specs for this page (`check.spec.ts`, `photo.spec.ts`, `app.spec.ts`, `stages.spec.ts`, `paper-flow.spec.ts`, `pilot-demo.spec.ts`, `demo.spec.ts` steps 4 and 5, `demo-path*.spec.ts`). **Tests for a feature this prompt removes** (data source, sample paper or sheet, auto-fill, answer-file labels, the old drawer) may be deleted or rewritten, but **list every one in the report with the reason**. Every other behaviour a test proved must still be proved. Report the test counts before and after.

## Step 12. Report and kit updates

- `docs/build/reports/ENTER-CHECK-NINE-CHANGES.md`: what changed per number 1 to 9, the tests that cover each, the folder-picker evidence (automated results, the device table left for the team), the removed code and tests, the seed paper for the test folder, the recordings created, and the test counts before and after.
- Update `docs/design/stitch/INVENTORY.md`, `docs/build/qa/WIDGETS.md` (`python scripts/qa_widgets.py`), `docs/help/teacher.md` (entering a check), `README.md` (the demo steps now: choose a paper, add the sheets by camera or folder, approve, finish, with the Drive test folder), and add a `DECISIONS.md` entry dated today.
- Run `python tasks.py predeploy`.

**Order:** Step 1 (removals), then Step 4 and Step 7 logic with unit tests, then Step 2, then Step 5 and Step 6, then Step 3 (look at the folder test and the fallback), then Steps 8 to 12.

**Done when** the page behaves as above in every state, the folder test passes on desktop with the fallback proven, the listed tests pass, axe is clean, nothing a test proved is lost except the removed features, and the report and docs are updated.
