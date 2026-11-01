# Claude Code prompt: redesign the Enter check page, one last time (every feature, option and state)

Paste everything below the line into Claude Code at the repo root. It is the full specification of the **Enter check** page (`#/check`): what it does, every control on it, every state, and what changes from today. Build it, test it, and report. Do not add features that are not in this file.

---

**Task.** Rebuild the Enter check page so a teacher can enter a whole class's answers quickly and safely, on a phone first, in Tamil, Hindi or English, with or without signal, with the AI on or off. Today's page works, but it is spread over three components that behave differently (`StartCheck`, `Check`, and the pilot/demo `DemoEntry` with its review drawer). The redesign gives them **one page with one roll list**, one status model, and one way to finish.

## Rules (non-negotiable, from `CLAUDE.md`)

- **No child names, faces or voices.** Children are **roll numbers** only ("Roll no 7"). Only the teacher can link a roll number to a child.
- **Photos are read and dropped.** A sheet photo is shrunk on the phone, sent for reading, and never stored on the phone's disk or the server. Per-sheet reads stay in memory until she confirms; then only class counts are kept.
- **Counts, never percentages** for the teacher ("11 of 28 children"). Simulated data is labelled "simulated", demo data "Demo", pilot data "Pilot data".
- **Code computes every number.** The page never calculates a result; it sends answers to the same `finishCheck` as today.
- **Honest labels.** Every answer that came from a reader says how: *Read by AI*, *Recorded AI answer* (when the server replays recordings), *Read from demo answer file*, *Read from pilot answer file*, *Typed*. A planned feature is never shown as working.
- **Design:** `docs/design/stitch/DESIGN.md` (Calm Institutional, Material 3, teal). Colours only from `theme.css`. 44 px touch targets (48 px for the primary button), sentence case, plain verbs. One primary action per screen state. Every string has `en`, `hi`, `ta`; text must fit in Hindi and Tamil without cut-off.
- **The title bar already shows the page name and one-line subtitle** ("Enter check: Enter each child's answers from the paper, by roll number."). Do not repeat a page `h1` that says the same; the page keeps one `h1` for its current state (see 3).
- **Never delete or weaken a test.** Existing browser tests for this page (`e2e/check.spec.ts`, `photo.spec.ts`, `app.spec.ts`, `stages.spec.ts`, `paper-flow.spec.ts`, `pilot-demo.spec.ts`, `demo.spec.ts` step 4 and 5) may be updated for new test ids, but every behaviour they prove must still be proved.

## 1. Read first

`CLAUDE.md` (sections 4, 5, 9), `docs/design/stitch/DESIGN.md`, `docs/design/stitch/INVENTORY.md` (T2, X7, X37, X39), `docs/build/qa/WIDGETS.md`, and the code: `apps/pwa/src/screens/Check.tsx`, `components/StartCheck.tsx`, `components/PaperHubParts.tsx` (`PaperChooser`, `AssignedToYou`), `components/PilotDataCard.tsx`, `components/DemoEntry.tsx` (the roll list and the review drawer), `components/SheetPreview.tsx`, `lib/check.ts`, `lib/checks.ts`, `lib/sheets.ts`, `lib/sampleSheets.ts`, `lib/paperKeys.ts`, `lib/demoStudio.ts`, `lib/aiMode.ts`, and the strings `check.*`, `demo.entry.*`, `demo.drawer.*`, `pilot.*`.

## 2. What exists today (keep the behaviour, change the shape)

| Area | Today | Where |
| --- | --- | --- |
| Start a check | Kind (pre-test, post-test, termly; one marked *suggested*), date (not in the future), expected number of papers (optional), the list of checks already saved for the class, the paper chooser (papers for this class and kind that are approved or confirmed; one pre-selected: the one *assigned to you*, else the only one), a **Create a paper** link to Papers, Start the check, a judge-only *Use the sample paper* | `StartCheck.tsx`, `PaperChooser` |
| Paper key | Starting fetches the paper's own answer key to the phone (all usable papers are prefetched so a check can start offline). If the key cannot be fetched: an error that says check the connection | `lib/paperKeys.ts` |
| Entering | Header with the check label, progress ("12 of 28 papers entered"), the attached paper code, *Change*; a roll picker ("Roll no 3 - not entered"); **Absent today**; one box per question (native numeric keyboard, Enter moves on), **Blank** and **Can't read** marks per box; the *missed the teaching* tags per concept (stay on the phone); Previous, Next roll no, **Next not entered**; a running count; **Finish entering** | `Check.tsx` |
| Photo | **Take a photo of this sheet** (needs a connection and the privacy choice): the photo is shrunk, read by the AI (call 8) *without being told the answers*, the boxes fill in, unsure boxes are marked, the original is shown in a tile that opens larger, replacing typed answers asks first; offline, a clear message; a judge-only *Use a sample sheet* | `Check.tsx`, `lib/sheets.ts`, `SheetPreview.tsx` |
| Bulk path (pilot machine and demo) | Sheet 1 read by the AI, the rest filled from the **demo / pilot answer file** with no AI call, a roll list with status per roll number, a bottom **review drawer** (sheet beside the reads, unsure boxes marked, Approve, Next unreviewed, Mark absent, Re-read with AI), data source Synthetic or Pilot (Pilot only on a machine that has the folder) | `DemoEntry.tsx`, `PilotDataCard.tsx` |
| Finish | Finish entering asks first, marks the empty roll numbers absent, runs the on-phone error finder (`finishCheck`), and opens My class. A finished check shows *See results* and **Reopen** | `Check.tsx` |
| Offline / AI off | Answers are saved on the phone after every key. Photo reading needs a connection; with the AI off the photo and Re-read buttons are disabled with the reason on screen; typing and the answer file still work | `Check.tsx`, `lib/aiMode.ts` |

**What is wrong with it today** (the reasons for this redesign):

1. Three different screens for one job: the typed path, the photo path and the bulk path have different lists, labels and finish buttons.
2. The roll picker is a dropdown: she cannot *see* which of 28 rolls are done, absent or need a look.
3. The paper, kind, date and count are asked in a long form before any answer, and are not visible once she is entering.
4. Entering is one child at a time with no overview and no way to jump to "the ones that need a look".
5. The review drawer exists only on the pilot/demo path; a photo read in the normal path has no drawer and no Approve step.

## 3. The new page: one page, four zones

The page has one `h1` that names its state ("Set up the check", "Enter answers", "Check is finished"). Zones appear in this order on a phone; on a laptop (from 900 px) the roll list sits on the left and the entry panel on the right.

```text
PHONE (390 px)                                  LAPTOP (1280 px)
+------------------------------------+          +--------------+---------------------------------+
| (title bar: page, status, EN/हिं/தமி) |          | ROLL LIST    |  ENTRY PANEL                    |
+------------------------------------+          |  (zone 2)    |   (zone 3)                      |
| ZONE 1  Check summary (one line)   |          |              |                                 |
|  Pre-test · 3A · 12 Oct · paper P-…|          | 1 ✓ 2 ✓ 3 ! |  Roll no 3        [Absent]      |
|  [Change]                          |          | 4 · 5 · 6 · |  [sheet photo]   Q1 [ 346 ]     |
+------------------------------------+          | ...          |                  Q2 [ 728 ]     |
| ZONE 2  Roll list (chips)          |          |              |   ...                           |
|  12 of 28 entered · 2 need a look  |          | 12 of 28     |  [Take a photo] [Previous][Next]|
|  [1✓][2✓][3!][4 ][5 ] ... [Absent] |          | [Next not    |                                 |
|  [Next not entered] [Next to review]|          |  entered]    |                                 |
+------------------------------------+          +--------------+---------------------------------+
| ZONE 3  Entry panel (selected roll)|          | ZONE 4  Sticky bar:  12 of 28 · [Finish entering]|
|  boxes, photo, marks, tags         |          +------------------------------------------------+
+------------------------------------+
| ZONE 4  Sticky bar: [Finish entering]|
+------------------------------------+
```

### Zone 0. Set up the check (state `setup`: before any answer)

A single card, not a long form. Order of fields, each with its label and what it does:

| Field | Label (en) | Options and rules | Notes |
| --- | --- | --- | --- |
| Paper | **Choose a paper** | Radio list of usable papers for this class: code, kind, number of questions, source (*Made by the rules*, *Imported, awaiting review*, *Teacher-confirmed*), cohort status. **Assigned to you** papers first and marked; one is pre-selected (the one assigned for this kind, else the only paper). Link **Create a paper** (to `#/papers`). Empty state: "No paper for this class yet" with the link | Existing `PaperChooser`; keys are prefetched; a paper whose key cannot be fetched shows the error and a Retry |
| Kind | **What kind of check is this?** | Pre-test, Post-test, Termly check; the suggested one marked. Changing kind refilters the papers. A post-test with no pre-test shows the existing note with *Make it a termly check* | Existing |
| Date | **Date of the check** | Not in the future | Existing |
| Class size | **How many papers? (optional)** | Digits only; becomes the roll list's length when given. If left empty the list grows as she goes (see Zone 2) | Existing |
| Data source | **Data source** | *Synthetic* (demo), *Pilot* | **Shown only where allowed:** *Pilot* appears only on a machine that has the pilot folder (`pilotProbe` ready) and is disabled with a reason when the folder is not ready; the hosted demo never offers it. Synthetic is shown only in demo/judge mode. A teacher in a normal deployment sees no data-source field |
| Saved checks | **Saved for this class** | A read-only list of the class's other checks (kind, paper, date, number of papers, *please confirm* chip) | Existing; collapsed by default |
| Start | **Start the check** (primary) | Disabled with the reason on screen until a paper is chosen: "Choose a paper above to start." | Fetches the paper's key, then opens zone 1 to 4 |
| Sample paper | **Use the sample paper (made-up class)** | **Judge only** | Existing |

If the term **already has a check** (`blocked`), the start button is disabled and the page says why and links to the open check.

### Zone 1. Check summary (state `entering`)

One line, always visible: **kind · class · date · paper code**, plus **Change** (kind, date and count only; the paper is locked once any answer is entered, with the existing explanation). *Please confirm* shows when the label was guessed from older data. A **Simulated data** or **Pilot data** banner appears above it when it applies. No form fields are shown here.

### Zone 2. The roll list (new: replaces the dropdown)

A wrapping grid of **roll chips**, one per roll number (the count is the class size, or the number entered so far plus one when the size is unknown; **Add a roll number** appends one). Each chip is a button, 44 px, showing the number and a status icon **and** a word (never colour alone):

| Status | Icon | Word | Meaning |
| --- | --- | --- | --- |
| Not entered | empty circle | not entered | nothing yet |
| Typed | pencil | entered | she typed or confirmed the answers |
| Needs a look | flag | needs a look | read from a photo or a file and **not yet approved**, or has marked boxes |
| Approved | check | approved | she approved the read (or typed it) |
| Absent | slash | absent | skipped; the roll number is kept, the child is not counted |
| No sheet | dash | no sheet | pilot or demo only: the roll number has no sheet in the folder |

Above the grid: a one-line count that says exactly this, with counts and no percentage: "**12 of 28 entered · 2 need a look · 1 absent**" (an `aria-live="polite"` region). Under it, three buttons:

- **Next not entered**: jumps to the next roll with nothing entered (wraps; when none is left, says so and offers **Finish entering**).
- **Next to review**: jumps to the next roll that *needs a look* (disabled with "Nothing to review" when none).
- **Mark absent** (on the selected chip's panel, see Zone 3) is the only way to set absent; the chip then shows it.

Keyboard: the grid is one tab stop with arrow keys moving between chips (roving tabindex); Enter selects. The selected chip is `aria-current="true"`.

### Zone 3. The entry panel (the selected roll)

Heading: **Roll no N** and its status chip with its **source**:

| Source label | When |
| --- | --- |
| *Typed* | she typed the answers |
| *Read by AI* | read from her photo by call 8 |
| *Recorded AI answer* | the same, when the server replays recordings (AI mode *recorded*) |
| *Read from demo answer file* / *Read from pilot answer file* | filled from the file with no AI call; pilot also shows *verified* or *unverified* |

Then, in this order:

1. **Absent today** toggle ("Absent today: skip this roll number"). Switching it on for a roll that has answers asks first and clears them.
2. **Sheet** (when there is a picture): the original beside the boxes on a laptop, above them on a phone, as a tile that opens larger with **zoom in, zoom out, rotate**, and **Close**. The picture is held in memory only and dropped when she leaves the roll. Alt text: "The answer sheet for roll no N".
3. **The boxes**: one per question of the chosen paper (the paper's own number, 10 anchor plus any adaptive items). Each box has the label "Question N", a numeric input (digits only, any script the keyboard offers is converted to 0 to 9; at most 9 digits), **Blank** and **Can't read** marks (toggle buttons with their own accessible names), and the **unsure** flag ("check") on boxes the reader was not sure of. Enter moves to the next box. An item that is *adaptive* carries a small tag "extra" so she knows it does not count in before and after (new; from the paper's own data).
4. **Photo**: **Take a photo of this sheet** (uses the camera; accepts a file on a laptop). Rules, all existing: needs a connection and the privacy choice (else the existing message and a link to My profile); shows "Reading the sheet…"; on success fills the boxes, marks unsure ones and says "Filled in from the photo. Check every box…" with the **source chip** above; on failure says what happened and what to do (offline, could not read, bad photo, typing is faster); replacing typed answers asks first. In AI **off** mode the button is disabled with the visible reason "Reading a photo needs the AI, which is off right now. Type the answers in the boxes; nothing you typed is lost."
5. **Re-read with AI**: shown only when the roll was read from a photo or file that is still in memory; same availability rules as the photo button; disabled with a reason in off mode. (Replaces the drawer's Re-read.)
6. **Approve** (primary for a roll that *needs a look*): marks it approved and **moves to the next roll that needs a look** (or the next not entered when none). A roll she typed is approved by moving on; she never has to press Approve for typed answers.
7. **Missed the teaching** tags, per concept, collapsed under a "From my register (optional)" disclosure; they stay on the phone and are never sent. Existing behaviour and labels.
8. **Previous roll no** and **Next roll no**; both keep what she typed (autosave on every key, "Saved on this phone").

**The review drawer.** A roll that came from a photo or a file opens in the **bottom review drawer** exactly as specified for the demo: a bottom drawer, **40 percent of the height on a phone** (full width) and **40 percent of the width on a laptop, anchored bottom right**; the sheet beside the reads; unsure boxes marked; buttons **Approve**, **Next unreviewed**, **Mark absent**, **Re-read with AI**; focus moves into it, Escape closes it and returns focus to the chip, the drawer is a labelled dialog. On a laptop the entry panel and the drawer are the same panel docked bottom right, not two copies. This unifies today's `DemoEntry` drawer and the normal path.

### Zone 4. The sticky bar

- Always visible at the bottom of the page: the count ("12 of 28 entered") and **Finish entering** (primary, 48 px).
- **Finish entering** asks first: "Finish entering? N roll numbers have nothing entered and will be marked absent. You can reopen the check later." (shown only when N is greater than 0; N counts rolls with nothing entered and not absent). If any roll still *needs a look*, the dialog says "M roll numbers still need a look" and offers **Review them** (default) or **Finish anyway** (they are counted as read).
- After confirming, the empty rolls become absent, the answers are saved, `finishCheck` runs on the phone (the same function as today), the check is closed, and the page shows the finished state.
- With **no answer entered at all**, Finish is disabled with the reason "Enter at least one child first."

### State `finished`

`h1`: "This check is finished". Shows "N children entered, A roll numbers marked absent." and two actions: **See results** (primary; opens My class) and **Reopen** (secondary). Reopen returns to `entering` with every roll as it was; **Finish entering** again re-runs the finder and updates the results. The note: "Reopen to change an answer or a roll number marked absent. Finish entering again to update the results."

## 4. Every state each part must handle

| Part | Default | Loading | Empty | Error | Offline | AI off | Recorded AI |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Paper chooser | list, assigned first | "Finding papers…" | "No paper for this class yet" + Create a paper | "Papers could not be loaded. Try again." | uses papers and keys already on the phone | n/a | n/a |
| Start | enabled with a paper | "Fetching the answer key…" | disabled with the reason | key error with Retry | starts if the key is on the phone, else the key error | n/a | n/a |
| Roll list | chips | skeleton chips | "Add a roll number" when size unknown | n/a | works (all on the phone) | works | works |
| Boxes | typing | n/a | blank boxes | n/a | works | works | works |
| Photo / Re-read | button | "Reading the sheet…" (the page stays usable) | n/a | the four existing messages | disabled, "needs a connection", typing offered | disabled, "needs the AI, which is off" | works; source says *Recorded AI answer*; a new sheet with no recording says so plainly (`demo` 503 text) and offers Auto-fill or typing |
| Answer file fill | **Auto-fill the other sheets** (demo and pilot only) | "Filling from the answer file…" | disabled with "no answer file" | "That answer file could not be used" | works (file is local or cached) | works (no AI) | works |
| Drawer | open on a read roll | n/a | n/a | n/a | works | Re-read disabled with the reason | Re-read works |
| Finish | confirm then close | "Finding the errors…" | disabled until one child is entered | "Could not finish. Your answers are safe; try again." | works (the finder runs on the phone); results sync later | works | works |

Connection pill and AI-mode badge stay in the title bar; the page never duplicates them, but an **AI off** note appears inside the photo area as above.

## 5. Roles and visibility

| Element | Teacher, Mentor | Coach, Officer | Judge |
| --- | --- | --- | --- |
| Enter check page | yes | **no** (not in their tabs; a deep link shows "This page is for teachers" with a link home) | yes (as a teacher) |
| Data source field | hidden | n/a | Synthetic always; Pilot only on a machine with the pilot folder |
| Use the sample paper, Use a sample sheet | hidden | n/a | shown |
| Auto-fill from an answer file | hidden (pilot machine only: shown for the pilot class) | n/a | shown for the demo class; shown for the pilot class on a pilot machine |
| Recorded AI answer chip | shown if the server replays recordings | n/a | shown |
| Pilot banner | only on a pilot machine | n/a | only on a pilot machine |

## 6. Data and privacy the page must keep

- Answers per roll are saved on the phone in IndexedDB after every key (as today); only class-level counts leave the phone when the check is finished.
- Picture URLs are in-memory object URLs, revoked when the roll changes or the page closes; the pilot's real images are never stored.
- Marked boxes, the *missed the teaching* tags and the source of each roll's answers (typed / AI / file) stay on the phone; the server never receives them.
- Nothing on the page shows a name, a school or a number about a single teacher's class to anyone else.
- The AI call for a photo is the existing one (call 8, blind to the answers); nothing in this redesign adds an AI call.

## 7. Strings

Add or change keys in `strings/en.json`, `hi.json`, `ta.json` (Hindi and Tamil are drafts for Seema to review; list them in `docs/build/i18n-todo.md` if the translation is a placeholder). New keys include: the setup `h1`, the roll status words (typed, needs a look, approved, absent, no sheet), the count line with three counts, **Next to review**, **Approve**, **Add a roll number**, "Nothing to review", "Review them", "Finish anyway", the roll chip accessible names ("Roll no 7, needs a look"), "extra" for adaptive items, the source labels, and the unreachable-for-this-role message. Reuse every existing `check.*`, `demo.entry.*`, `demo.drawer.*` and `pilot.*` key that still fits; remove none that a test uses.

## 8. Accessibility and performance

- axe (WCAG 2 A and AA) clean in every state of section 4 on phone and laptop.
- Full keyboard path: setup, roll list (arrow keys), boxes (Enter to next), drawer (focus in, Escape out), Finish dialog.
- Every chip, toggle and button has an accessible name that includes the roll number; status is never colour alone; `aria-live` for the count and for read results.
- Reduced motion respected (no slide animation for the drawer).
- Touch targets at least 44 px; the sticky bar never covers a box (the page pads for it).
- Usable within about 3 seconds on the throttled phone profile of `e2e/qa-screens.spec.ts`; a class of 40 rolls renders without lag.

## 9. Tests (write them first where the logic is pure)

- **Unit (Vitest):** the roll status function (inputs: typed, read, approved, absent, no sheet → status and word), the count line, *Next not entered* and *Next to review* (wrap-around, none left), the finish summary (empty rolls to absent, needs-a-look count), digit normalisation (Devanagari and Tamil digits), 9-digit limit.
- **Browser (Playwright), recorded AI mode:** setup (assigned paper first and pre-selected, Create a paper link round-trip, the kind change refilters, blocked term); typing a class of 5 with an absent roll and a blank box; photo read with a recorded answer (the *Recorded AI answer* chip, unsure boxes marked, Approve moves to the next that needs a look); the drawer sizes (40 percent height on a phone, 40 percent width bottom right on a laptop, focus, Escape); Next not entered; Finish with empty rolls (confirm, they become absent); finished state; Reopen then Finish again; offline entry then back online.
- **Browser, AI off** (`e2e/demo-path-ai-off.spec.ts` style): photo and Re-read disabled with the reason, typing and the answer file still work, nothing lost.
- **Roles:** coach and officer cannot open the page; Pilot data source is absent on the hosted build.
- **Languages:** Hindi and Tamil: the page fits at 360 px with no cut-off and no English left; digits correct.
- **Existing suites still pass.** Report the counts before and after.

## 10. Report

Write `docs/build/reports/ENTER-CHECK-REDESIGN.md`: what changed (zones 0 to 4, the unified roll list and drawer), a table of every control with its test id and the test that covers it, screenshots (phone and laptop; setup, entering, drawer, finished; English, Hindi, Tamil; synthetic data only) in `docs/build/qa/screens/`, the before and after test counts, and any open question. Update `docs/design/stitch/INVENTORY.md` (T2, X7, X37), `docs/help/teacher.md` (Entering a check), `README.md` (demo steps 4 to 6 wording), and add a `docs/build/DECISIONS.md` entry dated today. Regenerate `docs/build/qa/WIDGETS.md` (`python scripts/qa_widgets.py`) and run `python tasks.py predeploy`.

**Done when** the page matches this file in every state, the listed tests pass, axe is clean, nothing a test proved today is lost, and the report and docs are updated.
