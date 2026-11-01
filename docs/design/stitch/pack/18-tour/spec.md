# 18 · Guided tour

_Written for Stitch: what this screen is, what each part does, and what to keep. Tables are generated from the live page; the purpose and behaviour lines are written from the component source._

## 1. Screen

- **Route:** `#/tour`
- **Roles shown:** judge
- **Languages captured:** en
- **Inventory id:** X2
- **When a user sees it:** A judge starts the 5-minute tour.
- **What they are trying to do:** Follow six steps, each showing what to notice, with a banner when the role switches.
- **Source:** apps/pwa/src/screens/Tour.tsx

## 2. Images

| File | What it shows | Viewport | Scroll | State |
| --- | --- | --- | --- | --- |
| 01-tour_default_judge_en_desktop.png | First viewport, clean | 1280 x 800 @1x | top | default · judge · en |
| 01-tour_default_judge_en_desktop-annotated.png | Same, with numbered boxes E1, E2, E3… | 1280 x 800 @1x | top | default · judge · en |
| 01-tour_default_judge_en_desktop-s01.png | Scroll slice (80 px overlap) | 1280 x 800 @1x | 0 px | default · judge · en |
| 01-tour_default_judge_en_desktop-s02.png | Scroll slice (80 px overlap) | 1280 x 800 @1x | 659 px | default · judge · en |
| 01-tour_default_judge_en_desktop-s03.png | Scroll slice (80 px overlap) | 1280 x 800 @1x | 1318 px | default · judge · en |
| 01-tour_default_judge_en_desktop-s04.png | Scroll slice (80 px overlap) | 1280 x 800 @1x | 1354 px | default · judge · en |
| 01-tour_default_judge_en_desktop-long.png | Stitched long image (fixed header and bottom bar kept once) | 1280 x 800 @1x | full page | default · judge · en |
| 01-tour_default_judge_en_desktop-long-annotated.png | Long image with numbered boxes | 1280 x 800 @1x | full page | default · judge · en |
| 02-tour_step-2_judge_en_desktop.png | First viewport, clean | 1280 x 800 @1x | top | step-2 · judge · en |
| 02-tour_step-2_judge_en_desktop-annotated.png | Same, with numbered boxes E1, E2, E3… | 1280 x 800 @1x | top | step-2 · judge · en |
| tour-sheet.png | Contact sheet of the main states | — | — | all |

## 3. Layout

Top to bottom in the first state ("default"), by region, with the numbered elements in each:

- **header**: E1 to E5 (5 elements)
- **main**: E6 to E60 (55 elements)
- The page scrolls inside one container: 739 px visible of 2093 px (the header and bottom bar stay fixed).

## 4. Elements

Position is the box's top-left as a share of the viewport, then its size in CSS pixels. Style is the font size / weight, text colour, background, radius; a design token name in brackets means the value matches that token.

### State "default" · judge · en · desktop

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 1.3%, 1% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | button | Assistant | header | 64.8%, 1% · 129 x 44 | 19px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E3 | status | Online Good signal · 9.2 Mbps | header | 75.5%, 1.6% · 297 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E4 | image |  | header | 1.3%, 1.8% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E5 | element | Good signal · 9.2 Mbps | header | 82.8%, 2.3% · 191 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | heading | Guided tour | main | 2.5%, 10.6% · 1216 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E7 | element | Step 1 of 7 | main | 2.5%, 23.2% · 190 x 19 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E8 | element | Step 1 of 7 · budgeted at about 45 s (the whole tour is budgeted at ab | main | 2.5%, 25.9% · 1216 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E9 | status | Now you're the Teacher | main | 2.5%, 30.4% · 196 x 32 | 16.15px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Message shown to the user (read out by a screen reader). |
| E10 | heading | Check a class | main | 2.5%, 38% · 1216 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E11 | element | What to notice: Start a check says which paper this is (pre-test, post | main | 2.5%, 42.1% · 1216 x 86 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E12 | heading | Enter the check | main | 2.5%, 54.3% · 1216 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E13 | button | Change | main | 88.9%, 67% · 98 x 44 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Changes which check (kind, date, form) the papers belong to. |
| E14 | element | Pre-test · Form A · Class 3B (simulated) · 31 Oct 2026 | main | 3.4%, 68% · 901 x 28 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 0px | Shows text or a value. |
| E15 | element | 28 of 28 papers entered | main | 74.8%, 68.3% · 169 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(204, 232, 231) (--tonal); radius 0px | Shows text or a value. |
| E16 | heading | Child 1 | main | 2.5%, 79.5% · 1216 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E17 | label | Choose a child's sheet Child 1 · entered Child 2 · entered Child 3 · e | main | 2.5%, 83.7% · 1216 x 80 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E18 | combobox | Choose a child's sheet Child 1 · entered Child 2 · entered Child 3 · e | main | 2.5%, 87.7% · 1216 x 48 | 19px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Chooses which child's sheet to enter. |
| E19 | label | Absent today: skip this roll number | main | 2.5%, 95.2% · 1216 x 48 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E20 | checkbox | Absent today: skip this roll number | main | 2.8%, 96.7% · 24 x 24 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(247, 250, 250) (--paper); radius 0px | Marks the roll number absent so it is skipped. |
| E21 | textbox | Question 2 | main | 51.3%, 24% · 578 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E22 | textbox | Question 1 | main | 3.6%, 24.1% · 576 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E23 | button | Mark question 2 as left blank | main | 51.3%, 30.5% · 287 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 2 as left blank. |
| E24 | button | Mark question 2 as can't read | main | 74.1%, 30.5% · 287 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 2 as can't read. |
| E25 | button | Mark question 1 as left blank | main | 3.6%, 30.6% · 286 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 1 as left blank. |
| E26 | button | Mark question 1 as can't read | main | 26.3%, 30.6% · 286 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 1 as can't read. |
| E27 | textbox | Question 3 | main | 3.5%, 43.5% · 578 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E28 | textbox | Question 4 | main | 51.3%, 43.5% · 578 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E29 | button | Mark question 3 as left blank | main | 3.5%, 50% · 287 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 3 as left blank. |
| E30 | button | Mark question 3 as can't read | main | 26.3%, 50% · 287 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 3 as can't read. |
| E31 | button | Mark question 4 as left blank | main | 51.3%, 50% · 287 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 4 as left blank. |
| E32 | button | Mark question 4 as can't read | main | 74.1%, 50% · 287 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 4 as can't read. |
| E33 | textbox | Question 5 | main | 3.5%, 62.7% · 578 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E34 | textbox | Question 6 | main | 51.3%, 62.7% · 578 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E35 | button | Mark question 5 as left blank | main | 3.5%, 69.2% · 287 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 5 as left blank. |
| E36 | button | Mark question 5 as can't read | main | 26.3%, 69.2% · 287 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 5 as can't read. |
| E37 | button | Mark question 6 as left blank | main | 51.3%, 69.2% · 287 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 6 as left blank. |
| E38 | button | Mark question 6 as can't read | main | 74.1%, 69.2% · 287 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 6 as can't read. |
| E39 | textbox | Question 7 | main | 3.5%, 82% · 578 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E40 | textbox | Question 8 | main | 51.3%, 82% · 578 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E41 | button | Mark question 7 as left blank | main | 3.5%, 88.5% · 287 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 7 as left blank. |
| E42 | button | Mark question 7 as can't read | main | 26.3%, 88.5% · 287 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 7 as can't read. |
| E43 | button | Mark question 8 as left blank | main | 51.3%, 88.5% · 287 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 8 as left blank. |
| E44 | button | Mark question 8 as can't read | main | 74.1%, 88.5% · 287 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 8 as can't read. |
| E45 | textbox | Question 9 | main | 3.5%, 18.8% · 578 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E46 | textbox | Question 10 | main | 51.3%, 18.8% · 578 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E47 | button | Mark question 9 as left blank | main | 3.5%, 25.3% · 287 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 9 as left blank. |
| E48 | button | Mark question 9 as can't read | main | 26.3%, 25.3% · 287 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 9 as can't read. |
| E49 | button | Mark question 10 as left blank | main | 51.3%, 25.3% · 287 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 10 as left blank. |
| E50 | button | Mark question 10 as can't read | main | 74.1%, 25.3% · 287 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 10 as can't read. |
| E51 | checkbox | Missed the teaching on addition with carrying (questions 3–5) | main | 2.8%, 41% · 24 x 24 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(247, 250, 250) (--paper); radius 0px | Tick box: turns an option on or off. |
| E52 | checkbox | Missed the teaching on place value (questions 1–2) | main | 2.8%, 50.5% · 24 x 24 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(247, 250, 250) (--paper); radius 0px | Tick box: turns an option on or off. |
| E53 | checkbox | Missed the teaching on subtraction with borrowing (questions 7–10) | main | 2.8%, 60% · 24 x 24 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(247, 250, 250) (--paper); radius 0px | Tick box: turns an option on or off. |
| E54 | button | Use a sample sheet | main | 50.3%, 67% · 604 x 48 | 19px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Shows a sample answer sheet. |
| E55 | button | Previous child [disabled] | main | 2.5%, 74.5% · 604 x 48 | 19px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to previous child. |
| E56 | button | Next child | main | 50.3%, 74.5% · 604 x 48 | 19px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Saves this child's answers and moves to the next roll number. |
| E57 | button | Finish and see results | main | 2.5%, 86.5% · 1216 x 48 | 19px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Finishes the check and works out the class's errors on this phone. |
| E58 | button | Back [disabled] | main | 2.5%, 94% · 400 x 48 | 19px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to back. |
| E59 | button | Skip to the next step | main | 34.4%, 94% · 400 x 48 | 19px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Button: tap to skip to the next step. |
| E60 | link | Leave the tour | main | 66.3%, 94% · 400 x 48 | 19px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Opens #/roles. |

### State "step-2" · judge · en · desktop

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 1.3%, 1% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | button | Assistant | header | 64.8%, 1% · 129 x 44 | 19px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E3 | status | Online Good signal · 9.2 Mbps | header | 75.5%, 1.6% · 297 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E4 | image |  | header | 1.3%, 1.8% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E5 | element | Good signal · 9.2 Mbps | header | 82.8%, 2.3% · 191 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | heading | Guided tour | main | 2.5%, 10.6% · 1216 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E7 | element | Step 2 of 7 | main | 2.5%, 23.2% · 190 x 19 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E8 | element | Step 2 of 7 · budgeted at about 20 s (the whole tour is budgeted at ab | main | 2.5%, 25.9% · 1216 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E9 | status | Now you're the Officer | main | 2.5%, 30.4% · 190 x 32 | 16.15px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Message shown to the user (read out by a screen reader). |
| E10 | heading | Approve a proposed cohort | main | 2.5%, 38% · 1216 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E11 | element | What to notice: Guardrails: a person approves; nothing is approved by  | main | 2.5%, 42.1% · 1216 x 28 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E12 | button | Back | main | 2.5%, 58.5% · 400 x 48 | 19px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to back. |
| E13 | button | Skip to the next step | main | 34.4%, 58.5% · 400 x 48 | 19px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Button: tap to skip to the next step. |
| E14 | link | Leave the tour | main | 66.3%, 58.5% · 400 x 48 | 19px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Opens #/roles. |

## 5. Content and data

A progress bar, the step's text and what to notice, Back, Next and Leave. A banner says when the tour has switched the role.

The text on screen, copied exactly from the page in the first state:

```text
Guided tour

Simulated data: this class and these children are made up for the demo.

Step 1 of 7 · budgeted at about 45 s (the whole tour is budgeted at about 5 minutes; not yet timed on a phone)

Now you're the Teacher

Check a class

What to notice: Start a check says which paper this is (pre-test, post-test or termly check, Form A or B, date), and the header shows it on every screen. Guardrails: you confirm the boxes the reader was unsure of; the error card gives counts only and says where it most likely went wrong. Simulated.

Enter the check

Simulated data: this class and these children are made up for the demo.

Pre-test · Form A · Class 3B (simulated) · 31 Oct 2026

28 of 28 papers entered

Change

Enter the papers in roll order. Only your phone knows which paper is which child.

Child 1
Choose a child's sheet
Child 1 · entered
Child 2 · entered
Child 3 · entered
Child 4 · entered
Child 5 · entered
Child 6 · entered
Child 7 · entered
Child 8 · entered
Child 9 · entered
Child 10 · entered
Child 11 · entered
Child 12 · entered
Child 13 · entered
Child 14 · entered
Child 15 · entered
Child 16 · entered
Child 17 · entered
Child 18 · entered
Child 19 · entered
Child 20 · entered
Child 21 · entered
Child 22 · entered
Child 23 · entered
Child 24 · entered
Child 25 · entered
Child 26 · entered
Child 27 · entered
Child 28 · entered
Absent today: skip this roll number
Question 1
Blank
?
Question 2
Blank
?
Question 3
Blank
?
Question 4
Blank
?
Question 5
Blank
?
Question 6
Blank
?
Question 7
Blank
?
Question 8
Blank
?
Question 9
Blank
?
Question 10
Blank
?
Missed the teaching (from my register)
Missed the teaching on addition with carrying (questions 3–5)
Missed the teaching on place value (questions 1–2)
Missed the teaching on subtraction with borrowing (questions 7–10)
Take a photo of this sheet
Use a sample sheet
Previous child
Next child

28 children entered

Finish and see results
Back
Skip to the next step
Leave the tour
```

Dynamic parts: counts, dates, names of the demo class and every number come from the demo class loaded in Judge mode or from the 12-step demo session; the code computes them.

## 6. States and transitions

- **default**: open the route.
- **step-2**: go to #/tour/2.
- Empty, loading, error and offline states were not captured in this pack (core scope). The loaders and messages are listed in the product's own strings (`strings/en.json`).

## 7. What works and what to change

Measured from the numbered elements (touch targets, font sizes, sideways scroll, labels). There is no current UI audit of this app: `docs/design/audit/AUDIT.md` describes the original front end before the re-skin, so it is not used here.

- Touch target under 44 px: "Absent today: skip this roll number" (default/en: 24 x 24 px).
- Touch target under 44 px: "Missed the teaching on addition with car" (default/en: 24 x 24 px).
- Touch target under 44 px: "Missed the teaching on place value (ques" (default/en: 24 x 24 px).
- Touch target under 44 px: "Missed the teaching on subtraction with " (default/en: 24 x 24 px).
- 6 distinct font sizes among the numbered elements in default, en, desktop: 13.3333px, 16.15px, 16px, 19px, 20px, 24px.

## 8. Constraints

- Phone first at 390 px; desktop for coach, officer, judge and mentor screens.
- Touch targets at least 44 px, primary buttons 48 px.
- English, Hindi and Tamil text must fit without cutting.
- Use the tokens in `../00-tokens.md`: Material 3, Calm Institutional palette (teal primary), no new colours.
- Teacher-facing numbers are counts, never percentages. Simulated data stays labelled.
- No new features: redesign what exists.
