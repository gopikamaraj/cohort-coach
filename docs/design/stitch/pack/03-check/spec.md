# 03 · Check entry (start a check and print a paper)

_Written for Stitch: what this screen is, what each part does, and what to keep. Tables are generated from the live page; the purpose and behaviour lines are written from the component source._

## 1. Screen

- **Route:** `#/check`
- **Roles shown:** teacher
- **Languages captured:** en, hi
- **Inventory id:** T2, X35
- **When a user sees it:** A teacher starts the termly 10-item check for her class.
- **What they are trying to do:** Choose which paper to print (the pilot paper or a new one for this class), then enter the children's answers from sheet photos or by hand.
- **Source:** apps/pwa/src/screens/Check.tsx, apps/pwa/src/components/StartCheck.tsx, apps/pwa/src/components/PaperMaker.tsx
- **Data:** simulated demo data (judge mode, recorded AI answers). Every capture of data was checked for a Demo or Simulated label.

## 2. Images

| File | What it shows | Viewport | Scroll | State |
| --- | --- | --- | --- | --- |
| 01-check_default_teacher_en_phone.png | First viewport, clean | 390 x 844 @2x | top | default · teacher · en |
| 01-check_default_teacher_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | default · teacher · en |
| 01-check_default_teacher_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | default · teacher · en |
| 01-check_default_teacher_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 573 px | default · teacher · en |
| 01-check_default_teacher_en_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1146 px | default · teacher · en |
| 01-check_default_teacher_en_phone-s04.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1148 px | default · teacher · en |
| 01-check_default_teacher_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · teacher · en |
| 01-check_default_teacher_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · teacher · en |
| 01-check_default_teacher_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · teacher · en |
| 01-check_default_teacher_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · teacher · en |
| 02-check_paper-details_teacher_en_phone.png | First viewport, clean | 390 x 844 @2x | top | paper-details · teacher · en |
| 02-check_paper-details_teacher_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | paper-details · teacher · en |
| 02-check_paper-details_teacher_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | paper-details · teacher · en |
| 02-check_paper-details_teacher_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 573 px | paper-details · teacher · en |
| 02-check_paper-details_teacher_en_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 908 px | paper-details · teacher · en |
| 02-check_paper-details_teacher_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | paper-details · teacher · en |
| 02-check_paper-details_teacher_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | paper-details · teacher · en |
| 02-check_paper-details_teacher_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | paper-details · teacher · en |
| 02-check_paper-details_teacher_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | paper-details · teacher · en |
| 03-check_paper-new_teacher_en_phone.png | First viewport, clean | 390 x 844 @2x | top | paper-new · teacher · en |
| 03-check_paper-new_teacher_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | paper-new · teacher · en |
| 03-check_paper-new_teacher_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | paper-new · teacher · en |
| 03-check_paper-new_teacher_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 573 px | paper-new · teacher · en |
| 03-check_paper-new_teacher_en_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1082 px | paper-new · teacher · en |
| 03-check_paper-new_teacher_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | paper-new · teacher · en |
| 03-check_paper-new_teacher_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | paper-new · teacher · en |
| 03-check_paper-new_teacher_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | paper-new · teacher · en |
| 03-check_paper-new_teacher_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | paper-new · teacher · en |
| 04-check_default_teacher_hi_phone.png | First viewport, clean | 390 x 844 @2x | top | default · teacher · hi |
| 04-check_default_teacher_hi_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | default · teacher · hi |
| 04-check_default_teacher_hi_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | default · teacher · hi |
| 04-check_default_teacher_hi_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 597 px | default · teacher · hi |
| 04-check_default_teacher_hi_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1118 px | default · teacher · hi |
| 04-check_default_teacher_hi_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · teacher · hi |
| 04-check_default_teacher_hi_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · teacher · hi |
| 04-check_default_teacher_hi_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · teacher · hi |
| 04-check_default_teacher_hi_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · teacher · hi |
| check-sheet.png | Contact sheet of the main states | — | — | all |

## 3. Layout

Top to bottom in the first state ("default"), by region, with the numbered elements in each:

- **header**: E1 to E5 (5 elements)
- **main**: E6 to E55 (50 elements)
- **bottom bar**: E56 to E60 (5 elements)
- The page scrolls inside one container: 653 px visible of 1801 px (the header and bottom bar stay fixed).

## 4. Elements

Position is the box's top-left as a share of the viewport, then its size in CSS pixels. Style is the font size / weight, text colour, background, radius; a design token name in brackets means the value matches that token.

### State "default" · teacher · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | Online Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | heading | Enter the check | main | 4.1%, 14.8% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E7 | element | Pre-test · Form A · Class 3B (simulated) · 31 Oct 2026 | main | 7.2%, 29.7% · 334 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 0px | Shows text or a value. |
| E8 | button | Change | main | 53.5%, 36.6% · 95 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Changes which check (kind, date, form) the papers belong to. |
| E9 | element | 28 of 28 papers entered | main | 7.2%, 37.8% · 169 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(204, 232, 231) (--tonal); radius 0px | Shows text or a value. |
| E10 | heading | Child 1 | main | 4.1%, 51.3% · 358 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E11 | label | Choose a child's sheet Child 1 · entered Child 2 · entered Child 3 · e | main | 4.1%, 55.2% · 358 x 79 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E12 | combobox | Choose a child's sheet Child 1 · entered Child 2 · entered Child 3 · e | main | 4.1%, 58.9% · 358 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Chooses which child's sheet to enter. |
| E13 | label | Absent today: skip this roll number | main | 4.1%, 66% · 358 x 48 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E14 | checkbox | Absent today: skip this roll number | main | 5.1%, 67.4% · 24 x 24 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(247, 250, 250) (--paper); radius 0px | Marks the roll number absent so it is skipped. |
| E15 | label | Question 2 | main | 54.4%, 73.2% · 149 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E16 | label | Question 1 | main | 7.7%, 73.3% · 147 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E17 | textbox | Question 2 | main | 54.4%, 76.5% · 149 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E18 | textbox | Question 1 | main | 7.7%, 76.7% · 147 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E19 | button | Mark question 2 as left blank | main | 54.4%, 82.7% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 2 as left blank. |
| E20 | button | Mark question 2 as can't read | main | 74%, 82.7% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 2 as can't read. |
| E21 | button | Mark question 1 as left blank | main | 7.7%, 82.8% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 1 as left blank. |
| E22 | button | Mark question 1 as can't read | main | 27.1%, 82.8% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 1 as can't read. |
| E23 | label | Question 3 | main | 7.4%, 23.8% · 149 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E24 | label | Question 4 | main | 54.4%, 23.8% · 149 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E25 | textbox | Question 3 | main | 7.4%, 27.1% · 149 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E26 | textbox | Question 4 | main | 54.4%, 27.1% · 149 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E27 | button | Mark question 3 as left blank | main | 7.4%, 33.3% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 3 as left blank. |
| E28 | button | Mark question 3 as can't read | main | 27.1%, 33.3% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 3 as can't read. |
| E29 | button | Mark question 4 as left blank | main | 54.4%, 33.3% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 4 as left blank. |
| E30 | button | Mark question 4 as can't read | main | 74%, 33.3% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 4 as can't read. |
| E31 | textbox | Question 5 | main | 7.4%, 45.4% · 149 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E32 | textbox | Question 6 | main | 54.4%, 45.4% · 149 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E33 | button | Mark question 5 as left blank | main | 7.4%, 51.5% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 5 as left blank. |
| E34 | button | Mark question 5 as can't read | main | 27.1%, 51.5% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 5 as can't read. |
| E35 | button | Mark question 6 as left blank | main | 54.4%, 51.5% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 6 as left blank. |
| E36 | button | Mark question 6 as can't read | main | 74%, 51.5% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 6 as can't read. |
| E37 | textbox | Question 7 | main | 7.4%, 63.6% · 149 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E38 | textbox | Question 8 | main | 54.4%, 63.6% · 149 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E39 | button | Mark question 7 as left blank | main | 7.4%, 69.8% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 7 as left blank. |
| E40 | button | Mark question 7 as can't read | main | 27.1%, 69.8% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 7 as can't read. |
| E41 | button | Mark question 8 as left blank | main | 54.4%, 69.8% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 8 as left blank. |
| E42 | button | Mark question 8 as can't read | main | 74%, 69.8% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 8 as can't read. |
| E43 | textbox | Question 9 | main | 7.4%, 81.9% · 149 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E44 | textbox | Question 10 | main | 54.4%, 81.9% · 149 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E45 | button | Mark question 9 as left blank | main | 7.4%, 20.1% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 9 as left blank. |
| E46 | button | Mark question 9 as can't read | main | 27.1%, 20.1% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 9 as can't read. |
| E47 | button | Mark question 10 as left blank | main | 54.4%, 20.1% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 10 as left blank. |
| E48 | button | Mark question 10 as can't read | main | 74%, 20.1% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to mark question 10 as can't read. |
| E49 | checkbox | Missed the teaching on addition with carrying (questions 3–5) | main | 5.1%, 35.2% · 16 x 24 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(247, 250, 250) (--paper); radius 0px | Tick box: turns an option on or off. |
| E50 | checkbox | Missed the teaching on place value (questions 1–2) | main | 5.1%, 44.9% · 19 x 24 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(247, 250, 250) (--paper); radius 0px | Tick box: turns an option on or off. |
| E51 | checkbox | Missed the teaching on subtraction with borrowing (questions 7–10) | main | 5.1%, 54.6% · 15 x 24 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(247, 250, 250) (--paper); radius 0px | Tick box: turns an option on or off. |
| E52 | button | Use a sample sheet | main | 51%, 61.6% · 175 x 72 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Shows a sample answer sheet. |
| E53 | button | Previous child [disabled] | main | 4.1%, 71.6% · 175 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to previous child. |
| E54 | button | Next child | main | 51%, 71.6% · 175 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Saves this child's answers and moves to the next roll number. |
| E55 | button | Finish and see results | main | 4.1%, 82.9% · 358 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Finishes the check and works out the class's errors on this phone. |
| E56 | link | Home | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E57 | link | Enter check [current] | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E58 | link | My class | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to What my class gets wrong. |
| E59 | link | Practice | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the Practice Class. |
| E60 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

### State "paper-details" · teacher · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | Online Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | heading | Start a check | main | 4.1%, 14.8% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E7 | element | Class 3B (simulated) · Term 1 | main | 4.1%, 30.8% · 358 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E8 | radio | Pre-test · suggested | main | 4.1%, 39.7% · 192 x 44 | 18px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Choice: selects this option. |
| E9 | radio | Post-test | main | 55.4%, 39.7% · 104 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Choice: selects this option. |
| E10 | radio | Termly check | main | 4.1%, 45.9% · 136 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Choice: selects this option. |
| E11 | label | Date of the check | main | 4.1%, 53.9% · 166 x 79 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E12 | textbox | Date of the check | main | 4.1%, 57.6% · 166 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E13 | label | How many papers? (optional) | main | 4.1%, 65.6% · 233 x 79 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E14 | textbox | How many papers? (optional) | main | 4.1%, 69.3% · 233 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E15 | heading | Saved for this class | main | 4.1%, 78.3% · 358 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E16 | element | Print a paper for this check Which paper? The pilot paper (Form A): an | main | 4.1%, 85.4% · 358 x 682 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 16px (--s4) | Opens the panel for printing a paper for this check. |
| E17 | button | Print a paper for this check | main | 8.5%, 87% · 324 x 44 | 18px / 600; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Button: tap to print a paper for this check. |
| E18 | label | The pilot paper (Form A): answers can be entered on this phone | main | 8.5%, 31.3% · 324 x 62 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E19 | radio | The pilot paper (Form A): answers can be entered on this phone [checked] | main | 9.7%, 32% · 24 x 24 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(247, 250, 250) (--paper); radius 50% | Choice: selects this option. |
| E20 | label | A new paper for this class: print it and mark it by hand with its answ | main | 8.5%, 40% · 324 x 89 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E21 | radio | A new paper for this class: print it and mark it by hand with its answ | main | 9.7%, 40.8% · 24 x 24 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(247, 250, 250) (--paper); radius 50% | Choice: selects this option. |
| E22 | label | Language of the paper English हिन्दी (Hindi) தமிழ் (Tamil) | main | 8.5%, 55.3% · 180 x 79 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E23 | combobox | Language of the paper English हिन्दी (Hindi) தமிழ் (Tamil) | main | 8.5%, 59% · 180 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Dropdown: she chooses one value. |
| E24 | label | Second language (optional) None हिन्दी (Hindi) தமிழ் (Tamil) | main | 8.5%, 67.1% · 219 x 79 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E25 | combobox | Second language (optional) None हिन्दी (Hindi) தமிழ் (Tamil) | main | 8.5%, 70.7% · 219 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Dropdown: she chooses one value. |
| E26 | button | Make the paper | main | 8.5%, 49.5% · 324 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Makes the paper by code from the approved rules. |
| E27 | button | Paper A | main | 4.1%, 63.7% · 358 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to paper a. |
| E28 | button | Close | main | 4.1%, 82.7% · 358 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to close. |
| E29 | link | Home | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E30 | link | Enter check [current] | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E31 | link | My class | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to What my class gets wrong. |
| E32 | link | Practice | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the Practice Class. |
| E33 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

### State "paper-new" · teacher · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | Online Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | heading | Start a check | main | 4.1%, 14.8% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E7 | element | Class 3B (simulated) · Term 1 | main | 4.1%, 30.8% · 358 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E8 | radio | Pre-test · suggested | main | 4.1%, 39.7% · 192 x 44 | 18px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Choice: selects this option. |
| E9 | radio | Post-test | main | 55.4%, 39.7% · 104 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Choice: selects this option. |
| E10 | radio | Termly check | main | 4.1%, 45.9% · 136 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Choice: selects this option. |
| E11 | label | Date of the check | main | 4.1%, 53.9% · 166 x 79 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E12 | textbox | Date of the check | main | 4.1%, 57.6% · 166 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E13 | label | How many papers? (optional) | main | 4.1%, 65.6% · 233 x 79 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E14 | textbox | How many papers? (optional) | main | 4.1%, 69.3% · 233 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E15 | heading | Saved for this class | main | 4.1%, 78.3% · 358 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E16 | element | Print a paper for this check Which paper? The pilot paper (Form A): an | main | 4.1%, 85.4% · 358 x 856 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 16px (--s4) | Opens the panel for printing a paper for this check. |
| E17 | button | Print a paper for this check | main | 8.5%, 87% · 324 x 44 | 18px / 600; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Button: tap to print a paper for this check. |
| E18 | label | The pilot paper (Form A): answers can be entered on this phone | main | 8.5%, 31.3% · 324 x 62 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E19 | radio | The pilot paper (Form A): answers can be entered on this phone | main | 9.7%, 32% · 24 x 24 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(247, 250, 250) (--paper); radius 50% | Choice: selects this option. |
| E20 | label | A new paper for this class: print it and mark it by hand with its answ | main | 8.5%, 40% · 324 x 89 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E21 | radio | A new paper for this class: print it and mark it by hand with its answ [checked] | main | 9.7%, 40.8% · 24 x 24 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(247, 250, 250) (--paper); radius 50% | Choice: selects this option. |
| E22 | element | Entering the answers of a new paper on this phone comes later. Mark it | main | 8.5%, 53.9% · 324 x 72 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E23 | element | From this class's last check · 28 children were checked | main | 8.5%, 65.3% · 324 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E24 | label | Language of the paper English हिन्दी (Hindi) தமிழ் (Tamil) | main | 8.5%, 75.9% · 180 x 79 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E25 | combobox | Language of the paper English हिन्दी (Hindi) தமிழ் (Tamil) | main | 8.5%, 79.6% · 180 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Dropdown: she chooses one value. |
| E26 | label | Second language (optional) None हिन्दी (Hindi) தமிழ் (Tamil) | main | 8.5%, 87.7% · 219 x 79 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E27 | combobox | Second language (optional) None हिन्दी (Hindi) தமிழ் (Tamil) | main | 8.5%, 31% · 219 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Dropdown: she chooses one value. |
| E28 | button | Make the paper | main | 8.5%, 49.5% · 324 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Makes the paper by code from the approved rules. |
| E29 | button | Paper A | main | 4.1%, 63.7% · 358 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to paper a. |
| E30 | button | Close | main | 4.1%, 82.7% · 358 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to close. |
| E31 | link | Home | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E32 | link | Enter check [current] | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E33 | link | My class | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to What my class gets wrong. |
| E34 | link | Practice | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the Practice Class. |
| E35 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

### State "default" · teacher · hi · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | कोहॉर्ट कोच | header | 4.1%, 0.9% · 140 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | सहायक | header | 4.1%, 6.6% · 112 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | ऑनलाइन अच्छा सिग्नल · 9.2 एमबीपीएस | header | 34.8%, 7.2% · 166 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | अच्छा सिग्नल · 9.2 एमबीपीएस | header | 44.8%, 7.8% · 114 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | heading | जाँच भरें | main | 4.1%, 14.8% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E7 | element | पूर्व-परीक्षा · फ़ॉर्म A · कक्षा 3B (नकली) · 31 अक्टू॰ 2026 | main | 7.2%, 29.7% · 334 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 0px | Shows text or a value. |
| E8 | button | बदलें | main | 41.3%, 36.6% · 69 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Changes which check (kind, date, form) the papers belong to. |
| E9 | element | 28 में से 28 पर्चे दर्ज | main | 7.2%, 37.8% · 121 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(204, 232, 231) (--tonal); radius 0px | Shows text or a value. |
| E10 | heading | बच्चा 1 | main | 4.1%, 51.3% · 358 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E11 | label | बच्चे की कॉपी चुनिए बच्चा 1 · दर्ज बच्चा 2 · दर्ज बच्चा 3 · दर्ज बच्चा | main | 4.1%, 55.2% · 358 x 79 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E12 | combobox | बच्चे की कॉपी चुनिए बच्चा 1 · दर्ज बच्चा 2 · दर्ज बच्चा 3 · दर्ज बच्चा | main | 4.1%, 58.9% · 358 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Chooses which child's sheet to enter. |
| E13 | label | आज अनुपस्थित: यह रोल नंबर छोड़ें | main | 4.1%, 66% · 358 x 48 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E14 | checkbox | आज अनुपस्थित: यह रोल नंबर छोड़ें | main | 5.1%, 67.4% · 24 x 24 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(247, 250, 250) (--paper); radius 0px | Marks the roll number absent so it is skipped. |
| E15 | label | सवाल 2 | main | 54.4%, 73.2% · 149 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E16 | label | सवाल 1 | main | 7.7%, 73.3% · 147 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E17 | textbox | सवाल 2 | main | 54.4%, 76.5% · 149 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E18 | textbox | सवाल 1 | main | 7.7%, 76.7% · 147 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E19 | button | प्रश्न 2 को खाली चिह्नित करें | main | 54.4%, 82.7% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to प्रश्न 2 को खाली चिह्नित करें. |
| E20 | button | प्रश्न 2 को पढ़ा नहीं जा सकता चिह्नित करें | main | 74%, 82.7% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to प्रश्न 2 को पढ़ा नहीं जा सकता चिह्नित करें. |
| E21 | button | प्रश्न 1 को खाली चिह्नित करें | main | 7.7%, 82.8% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to प्रश्न 1 को खाली चिह्नित करें. |
| E22 | button | प्रश्न 1 को पढ़ा नहीं जा सकता चिह्नित करें | main | 27.1%, 82.8% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to प्रश्न 1 को पढ़ा नहीं जा सकता चिह्नित करें. |
| E23 | label | सवाल 3 | main | 7.4%, 21% · 149 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E24 | label | सवाल 4 | main | 54.4%, 21% · 149 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E25 | textbox | सवाल 3 | main | 7.4%, 24.3% · 149 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E26 | textbox | सवाल 4 | main | 54.4%, 24.3% · 149 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E27 | button | प्रश्न 3 को खाली चिह्नित करें | main | 7.4%, 30.5% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to प्रश्न 3 को खाली चिह्नित करें. |
| E28 | button | प्रश्न 3 को पढ़ा नहीं जा सकता चिह्नित करें | main | 27.1%, 30.5% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to प्रश्न 3 को पढ़ा नहीं जा सकता चिह्नित करें. |
| E29 | button | प्रश्न 4 को खाली चिह्नित करें | main | 54.4%, 30.5% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to प्रश्न 4 को खाली चिह्नित करें. |
| E30 | button | प्रश्न 4 को पढ़ा नहीं जा सकता चिह्नित करें | main | 74%, 30.5% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to प्रश्न 4 को पढ़ा नहीं जा सकता चिह्नित करें. |
| E31 | textbox | सवाल 5 | main | 7.4%, 42.5% · 149 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E32 | textbox | सवाल 6 | main | 54.4%, 42.5% · 149 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E33 | button | प्रश्न 5 को खाली चिह्नित करें | main | 7.4%, 48.7% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to प्रश्न 5 को खाली चिह्नित करें. |
| E34 | button | प्रश्न 5 को पढ़ा नहीं जा सकता चिह्नित करें | main | 27.1%, 48.7% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to प्रश्न 5 को पढ़ा नहीं जा सकता चिह्नित करें. |
| E35 | button | प्रश्न 6 को खाली चिह्नित करें | main | 54.4%, 48.7% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to प्रश्न 6 को खाली चिह्नित करें. |
| E36 | button | प्रश्न 6 को पढ़ा नहीं जा सकता चिह्नित करें | main | 74%, 48.7% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to प्रश्न 6 को पढ़ा नहीं जा सकता चिह्नित करें. |
| E37 | textbox | सवाल 7 | main | 7.4%, 60.8% · 149 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E38 | textbox | सवाल 8 | main | 54.4%, 60.8% · 149 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E39 | button | प्रश्न 7 को खाली चिह्नित करें | main | 7.4%, 66.9% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to प्रश्न 7 को खाली चिह्नित करें. |
| E40 | button | प्रश्न 7 को पढ़ा नहीं जा सकता चिह्नित करें | main | 27.1%, 66.9% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to प्रश्न 7 को पढ़ा नहीं जा सकता चिह्नित करें. |
| E41 | button | प्रश्न 8 को खाली चिह्नित करें | main | 54.4%, 66.9% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to प्रश्न 8 को खाली चिह्नित करें. |
| E42 | button | प्रश्न 8 को पढ़ा नहीं जा सकता चिह्नित करें | main | 74%, 66.9% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to प्रश्न 8 को पढ़ा नहीं जा सकता चिह्नित करें. |
| E43 | textbox | सवाल 9 | main | 7.4%, 79% · 149 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E44 | textbox | सवाल 10 | main | 54.4%, 79% · 149 x 48 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E45 | button | प्रश्न 9 को खाली चिह्नित करें | main | 7.4%, 85.2% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to प्रश्न 9 को खाली चिह्नित करें. |
| E46 | button | प्रश्न 9 को पढ़ा नहीं जा सकता चिह्नित करें | main | 27.1%, 85.2% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to प्रश्न 9 को पढ़ा नहीं जा सकता चिह्नित करें. |
| E47 | button | प्रश्न 10 को खाली चिह्नित करें | main | 54.4%, 85.2% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to प्रश्न 10 को खाली चिह्नित करें. |
| E48 | button | प्रश्न 10 को पढ़ा नहीं जा सकता चिह्नित करें | main | 74%, 85.2% · 72 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to प्रश्न 10 को पढ़ा नहीं जा सकता चिह्नित करें. |
| E49 | checkbox | हासिल वाला जोड़ पर सिखाना छूट गया (प्रश्न 3–5) | main | 5.1%, 38.5% · 23 x 24 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(247, 250, 250) (--paper); radius 0px | Tick box: turns an option on or off. |
| E50 | checkbox | स्थानीय मान पर सिखाना छूट गया (प्रश्न 1–2) | main | 5.1%, 47.9% · 24 x 24 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(247, 250, 250) (--paper); radius 0px | Tick box: turns an option on or off. |
| E51 | checkbox | उधार वाला घटाव पर सिखाना छूट गया (प्रश्न 7–10) | main | 5.1%, 57.2% · 22 x 24 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(247, 250, 250) (--paper); radius 0px | Tick box: turns an option on or off. |
| E52 | button | एक नमूना शीट लें | main | 51%, 64.2% · 175 x 72 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Shows a sample answer sheet. |
| E53 | button | पिछला बच्चा [disabled] | main | 4.1%, 74.2% · 175 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to पिछला बच्चा. |
| E54 | button | अगला बच्चा | main | 51%, 74.2% · 175 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Saves this child's answers and moves to the next roll number. |
| E55 | button | पूरा करें और नतीजे देखें | main | 4.1%, 85.5% · 358 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Finishes the check and works out the class's errors on this phone. |
| E56 | link | होम | bottom bar | 0%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/home. |
| E57 | link | जाँच भरें [current] | bottom bar | 20%, 93.1% · 78 x 58 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/check. |
| E58 | link | मेरी कक्षा | bottom bar | 40%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/cards. |
| E59 | link | अभ्यास | bottom bar | 60%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/practice. |
| E60 | button | और [collapsed] | bottom bar | 80%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Button: tap to और. |

## 5. Content and data

"Start a check" shows the paper choice; the details panel explains the paper. "A new paper" opens a short form about the class (what it finds hard, what was taught, how many children). Printing opens the paper's PDF in Paper Studio. After the check starts the screen shows one child at a time with a number grid, a sheet photo picker, absent and missed-teaching controls.

The text on screen, copied exactly from the page in the first state:

```text
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
```

Dynamic parts: counts, dates, names of the demo class and every number come from the demo class loaded in Judge mode or from the 12-step demo session; the code computes them.

## 6. States and transitions

- **default**: open the route.
- **paper-details**: tap check-change, then tap css:[data-testid=paper-details] summary.
- **paper-new**: tap check-change, then tap css:[data-testid=paper-details] summary, then tap "A new paper for this class".
- Empty, loading, error and offline states were not captured in this pack (core scope). The loaders and messages are listed in the product's own strings (`strings/en.json`).

## 7. What works and what to change

Measured from the numbered elements (touch targets, font sizes, sideways scroll, labels). There is no current UI audit of this app: `docs/design/audit/AUDIT.md` describes the original front end before the re-skin, so it is not used here.

- Touch target under 44 px: "Absent today: skip this roll number" (default/en: 24 x 24 px).
- Touch target under 44 px: "Missed the teaching on addition with car" (default/en: 16 x 24 px).
- Touch target under 44 px: "Missed the teaching on place value (ques" (default/en: 19 x 24 px).
- Touch target under 44 px: "Missed the teaching on subtraction with " (default/en: 15 x 24 px).
- Touch target under 44 px: "The pilot paper (Form A): answers can be" (paper-new/en: 24 x 24 px).
- Touch target under 44 px: "A new paper for this class: print it and" (paper-new/en: 24 x 24 px).

## 8. Constraints

- Phone first at 390 px; desktop for coach, officer, judge and mentor screens.
- Touch targets at least 44 px, primary buttons 48 px.
- English, Hindi and Tamil text must fit without cutting.
- Use the tokens in `../00-tokens.md`: Material 3, Calm Institutional palette (teal primary), no new colours.
- Teacher-facing numbers are counts, never percentages. Simulated data stays labelled.
- No new features: redesign what exists.
