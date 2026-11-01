# Claude Code prompt: identify every check (pre-test, post-test, termly) and pair them

Paste everything below the line into Claude Code at the repo root.

---

**Task.** Right now the "Enter the check" screen does not say which check the papers belong to. Add a **check** record, so every sheet, result and chart knows its class, kind (pre-test, post-test or termly check), form (A or B), term and date. Use it to pair a pre-test with its post-test and show before and after.

**Why.** The evidence for the judges and the mentors is "children flagged before, and after the track". That only works if every sheet is tied to the right check, and a Form A paper is never mixed with a Form B paper.

**Rules.**

- **Pre-test and post-test are not new machinery.** They are labels on two consecutive checks of one class with a track in between. A check is the post-test of the track before it and the pre-test of the track after it. The pilot labels them explicitly.
- **Keep the existing privacy rules.** Read how child identity is handled today ("only your phone knows which paper is which child"). Pair children across checks at the same level, on the device, and send only counts. Do not add names, and do not send per-child identifiers to the server.
- **Behaviour of existing screens must not break.** Existing sheets are migrated, not lost.
- Follow DESIGN.md. English, Hindi and Tamil text must fit.

**Step 0. Read first.** Read CLAUDE.md, DECISIONS.md, PROGRESS.md, docs/design/stitch/DESIGN.md, and the existing code for: the Enter the check screen and its sheet model, the worksheet generator and its PDF output, the sheet-photo reading flow, the class card, the verdict statistics, the cohort and track models, the pilot data scripts, and the database migrations.

## Step 1. Data model

Add a `check` table: `check_id`, `class_id`, `kind` (pre, post, termly), `form` (A, B or C), `term` (for example 2026-T3), `round` (1, 2, 3 within the term), `check_date`, `paper_version` (the generator version that made the paper), `track_id` (for a post-test, the track it evaluates; for a pre-test, the track it starts), `expected_children`, `status` (draft, entering, approved, closed), `notes`. Add `check_id` to every sheet and result table. Add indexes on `class_id` and `check_date`.

A check is unique per class, kind, form and date. Only one check can be open for entry per class at a time.

**Migration.** Create one `legacy` check per existing class from its existing sheets, with kind `pre`, form A and the earliest sheet date. Mark it "confirm" so the teacher can correct it. Do not delete anything.

## Step 2. Start a check (new first step)

Before "Enter the check", add a short **Start a check** screen:

1. Choose the class. Suggest the kind from history: no check yet means Pre-test. A finished track means Post-test. Otherwise Termly check. Let her change it.
2. Choose the form. Suggest Form B for a post-test after a Form A pre-test, and Form A for a pre-test. Show the paper's check code.
3. Term and date default to the current term and today, and can be changed.
4. Show what exists: "Pre-test, Form A, 26 Oct, 18 papers" when she is about to enter a post-test. If a post-test is chosen and no pre-test exists, say so plainly and let her continue as a termly check.

## Step 3. Make the check visible everywhere

- **A header on every Enter the check screen**, always visible: "Pre-test · Form A · Class 3A · 29 Oct 2026", plus progress such as "12 of 18 papers entered". A "Change" link returns to Start a check, with a warning if sheets are already entered.
- **The same label** on the class card, the cohort view, the track page and every chart.
- **A check switcher** on the class card: choose which two checks to compare. Default to the latest pair.

## Step 4. Print the check code on the paper, and read it back

1. The worksheet generator prints a small code in the header, for example `A · PRE · 3A · T3`, and a visible Form A or Form B title. Keep "Cohort Coach" off the child's paper, as before.
2. When she photographs a paper, the reader also returns the printed code, with a confidence.
3. Code compares it with the open check. If they differ (for example a Form B paper in a Form A check), show a clear warning on that paper, and do not accept it until she confirms or changes the check. If the code is unreadable, ask her to confirm by hand.

## Step 5. Form B mirrors Form A

The generator creates Form B from Form A, item by item: the same skill and difficulty with new numbers, one twin for every item, including the three-digit carry, the borrow across a zero and the dictation number with a zero in it. Record `twin_of` on every Form B item. A pre and a post can only be compared on twin items.

## Step 6. Pairing and the before-and-after view

1. **Pair on the device.** Match children across the two checks at the level the app already uses (roll order within the class). Children absent in either check are excluded and counted separately.
2. **Compare by competency.** For each of C1, C2 and C3, count children flagged in the pre-test who are no longer flagged in the post-test, children newly flagged, and children unchanged. Send only these counts.
3. **Show it** as a simple before and after table and bars on the class card, with the label "Pre-test Form A (26 Oct) to Post-test Form B (30 Oct)" and a plain note of the number of children paired. When fewer than 10 children are paired, say that the sample is small.
4. **Verdicts** continue to judge the track, not the teacher, and now carry the two check ids they compare.

## Step 7. Demo and judge mode

Add demo classes with a pre-test and a post-test, clearly labelled **Demo data**, so judges can see the before and after without waiting for real data. Add the Start a check step to the guided tour.

## Step 8. Evidence and tests

- `docs/evidence/pilot_results.md` is generated from the checks: flagged children per competency, before and after, with the check labels and the number paired. Counts only. Label it a small pilot.
- **Tests first:** a check cannot be closed with no sheets; a Form B paper is rejected in a Form A check until confirmed; the suggested kind and form follow the history; legacy migration creates one check per class and loses nothing; pairing excludes absent children and counts them; the before and after table shows counts only and never an identifier; every chart shows its check label; Form B has a twin for every Form A item.
- Run axe on the new screen and the header.

## Step 9. Kit updates

DECISIONS.md: an entry dated 2026-10-30 for the check record, the printed check code and the Form A and B rule. README: how to start a pre-test and a post-test. docs/RUBRIC\_MAP.md: link the user-testing and efficacy rows to the before and after view. Report: `docs/build/reports/CHECKS.md`.

**Order:** Steps 1 and 2, then 3, then 4 and 5, then 6, then 7 to 9.

**Done when** every sheet belongs to a labelled check, the header shows it on every entry screen, a wrong-form paper is caught, a pre-test and post-test pair into a before and after view with counts only, and the tests pass.
