# Cohort Coach pilot: Grade 3 maths pre-test and post-test

> Source: the team's pilot test pack (Claude Doc, as of 2026-10-16). Machine-readable answer key: `pilot_forms.golden.json` (same folder). If this file and the JSON ever disagree, stop and ask.

## What's in this pack

Two parallel 10-item papers: Form A before training, Form B after it. Both have the same item types in the same order with different numbers, so a fall in errors reflects learning, not memory of the paper.

| Items | What the child does | Error it detects |
| --- | --- | --- |
| 1–2 | Writes a number the tester says aloud | PV-HEARD: writes it as heard (346 → 30046). PV-REVERSE: swaps the last two digits (346 → 364) |
| 3–5 | Adds two 2-digit numbers, with carrying | ADD-NOCARRY: forgets the carried ten |
| 6 | Subtracts without borrowing | None. Anchor item: shows the child can subtract at all |
| 7–10 | Subtracts with borrowing | SUB-SFL: takes the smaller digit from the larger. SUB-NODEC: borrows a ten but doesn't reduce the tens |

**What to print.** Pre-test · Form A: one per child plus 5 spares per class. Post-test · Form B: the same, kept with Seema until post-test day. Each sheet exports to a one-page A4 PDF. This guide, including the answer key, stays with Seema — she briefs each class teacher on how to run the test, but teachers don't see the key; sheets are scored blind from photos afterward.

**Design choices that matter**

- Answer boxes are wide and undivided. A box split into 3 digit cells tells the child the answer has 3 digits, which hides PV-HEARD.
- Sums are set in columns, the way Grade 3 children practise carrying and borrowing, so the procedural errors show.
- Items 1–2 also catch PV-REVERSE, so the pre-test answers whether Hindi-medium classes need a fifth error.
- No names. Children write only their roll number, so each child's pre and post sheets can be paired. Remove the box if you want fully anonymous sheets; you lose the paired analysis in *Measuring impact*.
- Open: Seema checks all 20 items against the NCERT Grade 3 textbook before printing.

## Running the test

The child's own class teacher runs both tests, word for word the same script each time, so any change in the results comes from the training. Allow 30 minutes; most Grade 3 children finish within 20.

**Who and when**

- The tester is the class's own teacher, not a hackathon team member. Seema talks to the school's HM and teachers directly to arrange this, and hands over the printed sheets and this guide; the same teacher runs the pre-test and the post-test for her class.
- Pre-test before cohorting. Post-test after the track's last lesson, at the same time of day as the pre-test.

**Before the class**

- [ ] Write the class code on every sheet: school plus section, e.g. S1-3A.
- [ ] Seat children apart, each with a pencil and eraser.
- [ ] Clear the board, with no worked examples in view.

**What to say**

| Say in Hindi | Meaning |
| --- | --- |
| आज हम गणित के 10 सवाल करेंगे। यह परीक्षा नहीं है, इसके नंबर नहीं मिलेंगे। | Today we'll do 10 maths questions. It isn't an exam, and there are no marks. |
| सबसे ऊपर अपना रोल नंबर लिखो। नाम मत लिखना। | Write your roll number at the top. Don't write your name. |
| हर सवाल अपने तरीके से करो और उत्तर उसके डिब्बे में लिखो। | Do each question your own way and write the answer in its box. |
| कोई सवाल न आए तो उसे छोड़कर अगला करो। | If you can't do one, leave it and do the next. |

**Items 1–2: dictation**

Say "मैं एक संख्या दो बार बोलूँगी। ध्यान से सुनो और उसे डिब्बा 1 में लिखो।" (I'll say a number twice; write it in box 1.) Say the number, pause 3 seconds, say it again, then wait about 15 seconds. Repeat for box 2.

| Form | Box | Say in Hindi | Say in English |
| --- | --- | --- | --- |
| A (pre) | 1 | तीन सौ छियालीस | three hundred and forty-six |
| A (pre) | 2 | सात सौ अट्ठाईस | seven hundred and twenty-eight |
| B (post) | 1 | दो सौ चौंसठ | two hundred and sixty-four |
| B (post) | 2 | आठ सौ तिरेपन | eight hundred and fifty-three |

Say the number name the normal way, in the class's medium. Never say it digit by digit, write it on the board or show it on fingers: each gives the answer away and hides PV-HEARD.

**Items 3–10: children work alone**

- Give no hints, not even "remember to carry". If a child asks, say "जैसे तुम्हें ठीक लगे, वैसे करो" (do it the way you think is right).
- Rough work in the margin is fine; only the answer in the box counts.

**After the test**

- [ ] Collect the sheets in roll-number order and count them.
- [ ] Don't mark the sheets: no ticks, crosses or corrections. Unmarked sheets are scored blind and become the photo-reading test set.
- [ ] Log the class code, date, tester, children present, minutes taken and dictation language. Seema collects this when she picks up the completed sheets, and Shivani enters it in the feedback log the same day.

## Answer key

Every error gives a different answer on every item, so each wrong answer points to one error. Each Form B item tests the same thing as its Form A item: the same ones total in items 3–5 and the same borrowing gap in items 7–10.

### Form A (pre-test)

| Item | Question | Correct | Error answers |
| --- | --- | --- | --- |
| 1 | Dictation | 346 | PV-HEARD: 30046, 3046, 300406 · PV-REVERSE: 364 |
| 2 | Dictation | 728 | PV-HEARD: 70028, 7028, 700208 · PV-REVERSE: 782 |
| 3 | 38 + 47 | 85 | ADD-NOCARRY: 75 |
| 4 | 46 + 28 | 74 | ADD-NOCARRY: 64 |
| 5 | 59 + 23 | 82 | ADD-NOCARRY: 72 |
| 6 | 87 − 52 | 35 | None (anchor) |
| 7 | 74 − 36 | 38 | SUB-SFL: 42 · SUB-NODEC: 48 |
| 8 | 45 − 19 | 26 | SUB-SFL: 34 · SUB-NODEC: 36 |
| 9 | 82 − 39 | 43 | SUB-SFL: 57 · SUB-NODEC: 53 |
| 10 | 81 − 27 | 54 | SUB-SFL: 66 · SUB-NODEC: 64 |

### Form B (post-test)

| Item | Question | Correct | Error answers |
| --- | --- | --- | --- |
| 1 | Dictation | 264 | PV-HEARD: 20064, 2064, 200604 · PV-REVERSE: 246 |
| 2 | Dictation | 853 | PV-HEARD: 80053, 8053, 800503 · PV-REVERSE: 835 |
| 3 | 29 + 46 | 75 | ADD-NOCARRY: 65 |
| 4 | 35 + 49 | 84 | ADD-NOCARRY: 74 |
| 5 | 18 + 54 | 72 | ADD-NOCARRY: 62 |
| 6 | 86 − 41 | 45 | None (anchor) |
| 7 | 83 − 35 | 48 | SUB-SFL: 52 · SUB-NODEC: 58 |
| 8 | 64 − 28 | 36 | SUB-SFL: 44 · SUB-NODEC: 46 |
| 9 | 71 − 18 | 53 | SUB-SFL: 67 · SUB-NODEC: 63 |
| 10 | 93 − 29 | 64 | SUB-SFL: 76 · SUB-NODEC: 74 |

Also watch items 3–5 for the whole ones total written in (38 + 47 → 715). It isn't a tracked error, so score it "other", but count it: it may be worth a track.

## Scoring and cohorting

A child counts as showing an error only when it appears on at least 2 of the items that test it; one slip isn't a pattern.

**Reading each sheet**

1. Read only what is in the box. If the child crossed out and rewrote, use the last answer.
2. Devanagari digits count the same: ३४६ is 346.
3. Mark each answer correct, an error code from the key, other, or blank. Mark unreadable answers "?" and have a second person check them.
4. Apply the 2-item rule: both items 1–2 for PV-HEARD or PV-REVERSE, 2 of items 3–5 for ADD-NOCARRY, 2 of items 7–10 for SUB-SFL or SUB-NODEC. An answer both heard and reversed (30064) counts for both.
5. A wrong anchor (item 6) means the child struggles with subtraction itself. Note it, but still score items 7–10.

**Class tally.** One per class: fill the pre-test columns now and the post-test columns later. Write the class code and the number of children checked at each test above it. p = children showing it ÷ children checked.

| Error | Pre-test: children showing it | Pre-test p | Post-test: children showing it | Post-test p |
| --- | --- | --- | --- | --- |
| PV-HEARD | | | | |
| PV-REVERSE | | | | |
| ADD-NOCARRY | | | | |
| SUB-SFL | | | | |
| SUB-NODEC | | | | |

**Forming cohorts from the pre-test**

- A class qualifies for a track when its pre-test p is at least 25% and at least 10 children were checked.
- Each class takes one track. PV-HEARD comes first because the other errors build on it; otherwise the class takes its highest-p error.
- A cohort is every teacher whose class takes the same track. Expect small cohorts with 2 schools; the 15–20 size and 2-per-school cap apply at block scale.
- PV-REVERSE has no track yet. If it qualifies in several classes, that is the evidence for adding one.

## Measuring impact

Impact is how far the trained error falls from pre-test to post-test, beyond the fall in errors the class wasn't trained on.

Two checks run side by side: a class-level comparison against a natural baseline, worked out under Per class as the extra fall. A child-level test of whether individual flips look like more than chance follows, worked out under Child by child with an exact McNemar test. A track counts as working only when both agree.

*[Diagram in the original doc: measuring impact · two checks, one verdict — Per class: Baseline → Extra fall; Child by child: Paired by roll number → McNemar exact test; both feed Working / Not working / Inconclusive.]*

Untrained errors are the comparison because children also improve from regular teaching and from seeing the paper a second time. Average only the untrained errors that at least 10% of the class showed at pre-test. A class that qualifies for an error by prevalence but isn't put on that error's track this term also counts: its own natural change on that error becomes a second data point for the baseline.

**Per class.** Extra fall = the trained error's fall minus the untrained errors' average fall, in percentage points.

| Class code | Track | Trained error: pre p → post p | Untrained errors (average): pre p → post p | Extra fall (points) |
| --- | --- | --- | --- | --- |
| | | | | |

**Child by child.** Only for the trained error, and only children present at both tests, paired by roll number.

| Children at both tests | Post-test: shows it | Post-test: doesn't show it |
| --- | --- | --- |
| Pre-test: showed it | Still | Fixed |
| Pre-test: didn't show it | New | Never |

Compare Fixed against New with an exact McNemar test — it checks whether more children moved from error to no-error than the reverse, more than chance alone would produce. Twelve Fixed against two New, for example, gives p = 0.013, well under the 0.05 cutoff used below.

**Verdict per track**

- Working: an extra fall of at least 10 points, and McNemar p below 0.05.
- Not working: an extra fall of under 5 points, or a rise.
- Inconclusive: anything else. Likely with this few classes; report the numbers anyway.

Results count against the track, not the teacher.
