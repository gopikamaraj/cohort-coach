# Demo audit: the 12 demo steps, run in a browser

Run on 30 Oct 2026 against the built app (`npm run build`, `vite preview`) and the real API, on a fresh database. Every number below comes from `docs/build/reports/demo-audit/audit.json`, written by the audit script during the run. Screenshots of each step are in the same folder.

## How it was run

| Setting | Value | What it means for the result |
| --- | --- | --- |
| Browser | Chromium, Pixel 5 phone size (393 × 851), touch | Phone layout is what was tested. Desktop was only checked for horizontal scroll. |
| Role | Judge mode, English | Hindi and Tamil were checked for raw string keys and native text only, not for wording. |
| `AI_MODE` | `recorded` | The AI answers are recorded fixtures. **No live AI call was made, so this does not show that live AI works.** |
| `SPEECH_MODE` | `stub` | No real voice was made. The lesson page shows the script and an audio element, but not a Sarvam voice. |
| Database | Fresh SQLite file, deleted afterwards | No leftover state from earlier runs. |
| Checks | 73 browser checks across the 12 steps and an extras group | A step passes only when every check passed. |

## Result

**72 of 73 checks passed in the run. The one failure was a mistake in my check, not in the app, and a separate re-run passed.** All 12 steps work in this setup. The whole run took 72 seconds.

| Step | What it does | Checks | Result | Loader message seen |
| --- | --- | --- | --- | --- |
| 1 | Start as a teacher with a made-up class 3A | 4 of 4 | Working | none needed |
| 2 | Generate a paper (pilot paper, Form A) | 4 of 4 | Working | yes: "Making the paper…" |
| 3 | Generate 20 demo sheets and download the zip | 5 of 5 | Working | yes: "Writing 20 children's answers…" |
| 4 | Sheet 1 read by the AI, 19 filled from the answer file | 5 of 5 | Working | yes, a different message for each action |
| 5 | Review drawer, smudged sheet marked unsure, approve all 20 | 7 of 7 | Working | none needed |
| 6 | Submit the check, find errors on the phone, simulate other classes | 4 of 4 | Working | yes: "Simulating 24 other classes…" |
| 7 | Three cohorts, her class in one now and eligible for a second next term | 4 of 4 | Working | none seen (loads fast) |
| 8 | First audio lesson, "Demo: pre-approved" badge | 3 of 3 | Working, voice not tested | yes: "The AI is drafting lesson 1…" |
| 9 | Practice Class with the lesson's next step | 2 of 2 | Working | none needed |
| 10 | Cohort chat: ask, wait or skip | 4 of 4 | Working | yes: "Sending your question…" |
| 11 | Coach queue (mentor card, lesson 2 draft) and officer dashboard | 7 of 7 | Working | not seen (see below) |
| 12 | Optional post-test, before and after | 3 of 3 | Working | not seen (see below) |

## What is working

- **The full path runs end to end.** One judge device goes from step 1 to step 12 with no dead end.
- **Paper and sheets.** The paper code reads `A · PRE · 3A · T1`. Twenty sheets appear, sheet 7 is named `3A-roll07.png`, they are labelled "Not real children's work", and the zip downloads as `3A-demo-sheets.zip`.
- **Reading and review.** The AI read of sheet 1 matched what the code drew (10 of 10 boxes on 1 synthetic sheet, labelled as not evidence of accuracy on real handwriting). The other 19 sheets say "Read from demo answer file" and no AI call is made. The drawer is exactly 40% of the phone height, holds focus, closes on Escape, and the smudged sheet has one unsure cell.
- **Class counts.** Her class shows PV-HEARD 2, ADD-NOCARRY 7, SUB-SFL 9 of 20 children (simulated). Code computed these.
- **Cohorts.** Three cohorts, each labelled Simulated. Her class is in the SUB-SFL cohort this term and the ADD-NOCARRY cohort says "next term".
- **Lesson.** Lesson 1 shows the "Demo: pre-approved" badge and a script with her class's numbers filled in by code (9 of 20 children).
- **Practice Class** shows the lesson's next step.
- **Chat.** The question appears in the thread and the skip button works.
- **Coach and officer.** The simulated mentor card is shown, the coach can write an answer and approve the card, and the officer dashboard says simulated, hides the PV-HEARD cell ("Hidden (under 5)") and shows no teacher or child.
- **Post-test.** Before and after shows, labelled "Demo data".
- **Accessibility.** The automated check (axe, WCAG 2 A and AA) found no violations on any of the 12 steps.
- **Languages.** Hindi and Tamil: 16 of 16 screen checks found no raw string keys and real native text.
- **Layout.** No horizontal scroll at 1280 px wide or at 360 px wide.
- **Session.** Reloading keeps the step and the session, and a deep link to step 7 still shows the cohorts. Reset worked when re-tested on its own: the server session returned 404 afterwards, a new session id was created, and the page went to step 1.

## What is not working or needs attention

| # | Finding | Severity | Detail |
| --- | --- | --- | --- |
| 1 | The demo bar takes about 40% of a phone screen | Medium | The header plus the sticky "Demo step n of 11" bar with four buttons fills roughly the top 40% of the phone (see `04-entry.png`, `11-coach.png`). On step 5 the drawer takes the bottom 40% as well, which leaves about a fifth of the screen for the sheet list. It works, but on a small phone a judge has to scroll a lot. A shorter bar (one row, or collapsible) would help. Not fixed. |
| 2 | A 404 shows in the browser console on every first load | Low | `GET /api/tester/config` returns 404 when tester mode is off. It does no harm, but a judge who opens the console sees a red error. The call should be quiet when tester mode is off. Not fixed. |
| 3 | The chat answers nothing by itself | By design, but a judge may read it as broken | The AI finds no approved strategy for the question, so the thread says "Waiting for a mentor or coach to answer", and a person answers at step 11. Skipping the wait does not change this. Seema approving strategies for SUB-SFL would let the AI draft an answer. |
| 4 | PV-HEARD is planted on 3 children but only 2 are counted | Not a bug | Roll 15 is the blank-sheet hard case, and a blank box leaves that child with fewer than the 2 items the rule needs. The code-computed truth is 2 (`truth_profile`), and the phone finds 2. The scenario file says 3, which may confuse a reader. |
| 5 | The "of 11" counter on a 12-step flow | Low | The bar says "step 12" with no "of", because step 12 is optional. This is consistent but can look like a miscount. |

## What this run did not test

- **Live AI.** Recorded answers only. A live run (`AI_MODE=live`) is the only way to see real call 8 reads on a photo, real lesson 1 drafting, or the real chat check. Live cost is small, but I did not spend it without your say-so.
- **Real voice.** `SPEECH_MODE=stub`, so no Sarvam audio was heard, and the lesson's audio file was not played.
- **Loader on steps 7, 11 and 12.** My check polls every 150 ms and found no loader text on these steps. They finish in 70 to 1,500 ms, so the loader may simply have been too brief to catch. I cannot say it is missing.
- **Hindi and Tamil wording.** Checked only for missing keys. The wording is a draft and needs a reader.
- **A real low-end phone, Slow 3G and the installed app.**
- **Two judges at once on the same server.** An existing browser test (`demo.spec.ts`) covers two devices, and it passed earlier today.
- **Cloud deployment.** This was local. The cloud needs a redeploy for the Paper Studio and Demo Studio changes (the Dockerfile now installs Pango).

## Files

- `docs/build/reports/demo-audit/audit.json`: every check, loader text, axe result, console error and failed request.
- `docs/build/reports/demo-audit/*.png`: one or two screenshots per step.

## Second run: live AI and live voice (31 Oct 2026)

Same script, same 12 steps, with `AI_MODE=live` and `SPEECH_MODE=live` on a fresh database. Source: `docs/build/reports/demo-audit/live/audit.json`.

**Result: 73 of 73 checks passed, with no axe violations and no failed requests except the known 404 below.** The run took 102 seconds.

Which calls really ran live (from the API log):

| Step | Call | Live in this run? |
| --- | --- | --- |
| 4 | Call 8, the AI reading sheet 1 | Yes. It read 10 of 10 boxes correctly. |
| 8 | Lesson 1 (call 5) and its voice | **No, from the demo cache** (`data/demo_cache/`, made by your earlier live run). The cache is designed to do this, so a judge's first click costs nothing. |
| 10 | Call 12, classifying the chat question | Yes. It sent the question to a person, because no approved strategy exists. |
| 11 | Call 5 (lesson 2 draft) and call 7 (checker) | Yes. |

I did not read the spend from the budget report. It reads the default database, not the one this run used, so I can't give a cost figure. The live calls were one sheet read, one question classification, and one lesson draft with its check.

## Fixes made after the first run

| # | Finding | Status |
| --- | --- | --- |
| 1 | Demo bar too tall on a phone | **Reduced, not removed.** The step text is now a little smaller with tighter gaps. (My first try, a three-line limit, cut Hindi text into the buttons, as the Stitch pack screenshots showed, so it was removed on 31 Oct.) The 146 px and 255 px figures below were measured with that first try and are out of date. The bar is 146 px tall on a 393 × 851 screen, and with the header the two take 255 px (30% of the height). I did not take a before measurement in the same way, so I can't state an exact saving. On a phone it still takes a large share of the screen. Making the bar collapsible would help more, but it would hide the Reset and guide buttons from the browser tests, so I left it. |
| 2 | 404 for `/api/tester/config` in the console | **Not changed, on purpose.** The 404 is the designed way to say tester mode is off, and `tests/api/test_tester.py` asserts it. The browser prints it as a red console line. Changing it means changing a tested contract, which is your decision. |
| 3 | Chat gives no AI answer | Unchanged. Needs Seema to approve strategies for SUB-SFL. |
| 4 | PV-HEARD planted 3, counted 2 | Not a bug. Unchanged. |

After the CSS change, the demo and paper browser tests pass (12 of 12).

## Follow-up fixes (31 Oct 2026)

- **Simulated label.** History, Papers, Cohort, Review and Mentor now show the "Simulated data" banner (found by the Stitch pack run). The pack's validator now passes with no known gaps.
- **Tick boxes.** My earlier note about 16 to 28 px tick boxes was wrong as a tap-target finding: each box sits inside a label row at least 48 px tall, and the label is the target.
- **Officer cohort form.** It now uses the app's field styling (label above field, 48 px fields, primary button).
- **Browser tests.** The AI map test now expects the 13 calls the map shows. The Playwright config pins the two Practice Class speed switches to their defaults so a developer's `.env` cannot change the tests. Lint on `src` and `e2e` is clean. Full browser suite: 176 passed, 7 skipped.
- **Not changed:** the 404 for `/api/tester/config` (the designed way to say tester mode is off, asserted by a test) and the size of the demo bar.
