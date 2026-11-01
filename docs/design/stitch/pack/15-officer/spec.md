# 15 · Programme officer home

_Written for Stitch: what this screen is, what each part does, and what to keep. Tables are generated from the live page; the purpose and behaviour lines are written from the component source._

## 1. Screen

- **Route:** `#/officer`
- **Roles shown:** officer
- **Languages captured:** en
- **Inventory id:** P1, P2, P4
- **When a user sees it:** A programme officer opens the app.
- **What they are trying to do:** See the error map, cohorts (this term and next), the funnel and the track results as aggregates. Cells under 5 classes are hidden.
- **Source:** apps/pwa/src/screens/OfficerHome.tsx
- **Data:** simulated demo data (judge mode, recorded AI answers). Every capture of data was checked for a Demo or Simulated label.

## 2. Images

| File | What it shows | Viewport | Scroll | State |
| --- | --- | --- | --- | --- |
| 01-officer_default_officer_en_desktop.png | First viewport, clean | 1280 x 800 @1x | top | default · officer · en |
| 01-officer_default_officer_en_desktop-annotated.png | Same, with numbered boxes E1, E2, E3… | 1280 x 800 @1x | top | default · officer · en |
| 01-officer_default_officer_en_desktop-s01.png | Scroll slice (80 px overlap) | 1280 x 800 @1x | 0 px | default · officer · en |
| 01-officer_default_officer_en_desktop-s02.png | Scroll slice (80 px overlap) | 1280 x 800 @1x | 659 px | default · officer · en |
| 01-officer_default_officer_en_desktop-s03.png | Scroll slice (80 px overlap) | 1280 x 800 @1x | 1318 px | default · officer · en |
| 01-officer_default_officer_en_desktop-s04.png | Scroll slice (80 px overlap) | 1280 x 800 @1x | 1977 px | default · officer · en |
| 01-officer_default_officer_en_desktop-s05.png | Scroll slice (80 px overlap) | 1280 x 800 @1x | 2260 px | default · officer · en |
| 01-officer_default_officer_en_desktop-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 1280 x 800 @1x | full page | default · officer · en |
| 01-officer_default_officer_en_desktop-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 1280 x 800 @1x | full page | default · officer · en |
| 01-officer_default_officer_en_desktop-long-annotated-p1.png | Long image with numbered boxes | 1280 x 800 @1x | full page | default · officer · en |
| 01-officer_default_officer_en_desktop-long-annotated-p2.png | Long image with numbered boxes | 1280 x 800 @1x | full page | default · officer · en |
| 02-officer_default_officer_en_phone.png | First viewport, clean | 390 x 844 @2x | top | default · officer · en |
| 02-officer_default_officer_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | default · officer · en |
| 02-officer_default_officer_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | default · officer · en |
| 02-officer_default_officer_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 597 px | default · officer · en |
| 02-officer_default_officer_en_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1194 px | default · officer · en |
| 02-officer_default_officer_en_phone-s04.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1791 px | default · officer · en |
| 02-officer_default_officer_en_phone-s05.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 2388 px | default · officer · en |
| 02-officer_default_officer_en_phone-s06.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 2985 px | default · officer · en |
| 02-officer_default_officer_en_phone-s07.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 3582 px | default · officer · en |
| 02-officer_default_officer_en_phone-s08.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 3691 px | default · officer · en |
| 02-officer_default_officer_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · officer · en |
| 02-officer_default_officer_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · officer · en |
| 02-officer_default_officer_en_phone-long-p3.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · officer · en |
| 02-officer_default_officer_en_phone-long-p4.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · officer · en |
| 02-officer_default_officer_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · officer · en |
| 02-officer_default_officer_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · officer · en |
| 02-officer_default_officer_en_phone-long-annotated-p3.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · officer · en |
| 02-officer_default_officer_en_phone-long-annotated-p4.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · officer · en |
| officer-sheet.png | Contact sheet of the main states | — | — | all |

## 3. Layout

Top to bottom in the first state ("default"), by region, with the numbered elements in each:

- **header**: E1 to E6 (5 elements)
- **main**: E7 to E30 (22 elements)
- **side rail**: E5 to E9 (3 elements)
- The page scrolls inside one container: 739 px visible of 2999 px (the header and bottom bar stay fixed).

## 4. Elements

Position is the box's top-left as a share of the viewport, then its size in CSS pixels. Style is the font size / weight, text colour, background, radius; a design token name in brackets means the value matches that token.

### State "default" · officer · en · desktop

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 9.4%, 1% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | button | Assistant | header | 64.8%, 1% · 129 x 44 | 19px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E3 | status | Online Good signal · 9.2 Mbps | header | 75.5%, 1.6% · 297 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E4 | image |  | header | 9.4%, 1.8% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E5 | link | Officer [current] | side rail | 0.6%, 2% · 87 x 76 | 16px / 700; rgb(0, 32, 31) (--on-pen-container); bg rgb(204, 232, 231) (--tonal); radius 16px (--s4) | Opens #/officer. |
| E6 | element | Good signal · 9.2 Mbps | header | 82.8%, 2.3% · 191 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E7 | heading | Officer | main | 10.6%, 10.6% · 1112 x 31 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E8 | link | Review | side rail | 0.6%, 12.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/review. |
| E9 | link | My profile | side rail | 0.6%, 23% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/profile. |
| E10 | heading | Cohorts | main | 12%, 31.7% · 1078 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E11 | element | Start a cohort Error PV-HEARD ADD-NOCARRY SUB-SFL SUB-NODEC Coach idSc | main | 12%, 41.6% · 1078 x 133 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Shows text or a value. |
| E12 | heading | Start a cohort | main | 12%, 41.6% · 1078 x 33 | 22.23px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E13 | label | Error PV-HEARD ADD-NOCARRY SUB-SFL SUB-NODEC | main | 12%, 48.7% · 162 x 26 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Label for the field next to it. |
| E14 | label | Coach id | main | 24.6%, 48.7% · 250 x 26 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Label for the field next to it. |
| E15 | label | Schools | main | 44.1%, 48.7% · 138 x 26 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Label for the field next to it. |
| E16 | textbox | Coach id | main | 30.3%, 49.4% · 177 x 21 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 0px | Field: she types or chooses a value. |
| E17 | textbox | Schools | main | 49.2%, 49.4% · 73 x 21 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 0px | Field: she types or chooses a value. |
| E18 | combobox | Error PV-HEARD ADD-NOCARRY SUB-SFL SUB-NODEC | main | 15.1%, 49.5% · 121 x 19 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 0px | Dropdown: she chooses one value. |
| E19 | button | Propose cohort | main | 12%, 52.1% · 1078 x 48 | 19px / 600; rgb(0, 0, 0); bg rgb(240, 240, 240); radius 8px (--s2) | Button: tap to propose cohort. |
| E20 | heading | Funnel | main | 12%, 68.9% · 1078 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E21 | element | No content is waiting for review. (system: review queue ages; gates ne | main | 12%, 77.5% · 1078 x 28 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Shows text or a value. |
| E22 | heading | Track results | main | 12%, 44.4% · 1078 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E23 | element | Inconclusive | main | 26.7%, 55.2% · 114 x 32 | 16.15px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E24 | img | ADD-NOCARRY v1: -15.7 (-23.0 to -8.8) | main | 13.3%, 67.8% · 420 x 50 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Shows text or a value. |
| E25 | element | Inconclusive | main | 23.3%, 90.2% · 114 x 32 | 16.15px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E26 | element | Not working | main | 24.3%, 31.6% · 116 x 32 | 16.15px / 600; rgb(25, 28, 28) (--ink); bg rgb(255, 218, 214) (--margin-container); radius 999px (--r-pill) | Shows text or a value. |
| E27 | img | SUB-NODEC v1: -0.3 (-3.3 to 2.8) | main | 13.3%, 44.2% · 420 x 50 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Shows text or a value. |
| E28 | element | Working | main | 21.6%, 62.1% · 87 x 32 | 16.15px / 600; rgb(25, 28, 28) (--ink); bg rgb(180, 242, 188) (--good-container); radius 999px (--r-pill) | Shows text or a value. |
| E29 | img | SUB-SFL v1: -19.5 (-24.1 to -15.1) | main | 13.3%, 74.8% · 420 x 50 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Shows text or a value. |
| E30 | heading | Error map (grade 3, term 1) | main | 12%, 96.7% · 1078 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |

### State "default" · officer · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | Online Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | heading | Officer | main | 4.1%, 14.8% · 358 x 31 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E7 | heading | Cohorts | main | 8.5%, 43.8% · 324 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E8 | element | Start a cohort Error PV-HEARD ADD-NOCARRY SUB-SFL SUB-NODEC Coach idSc | main | 8.5%, 58.8% · 324 x 155 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Shows text or a value. |
| E9 | heading | Start a cohort | main | 8.5%, 58.8% · 324 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E10 | label | Error PV-HEARD ADD-NOCARRY SUB-SFL SUB-NODEC | main | 8.5%, 65.1% · 159 x 24 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Label for the field next to it. |
| E11 | combobox | Error PV-HEARD ADD-NOCARRY SUB-SFL SUB-NODEC | main | 18.3%, 65.7% · 121 x 19 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 0px | Dropdown: she chooses one value. |
| E12 | label | Schools | main | 53.8%, 68.3% · 119 x 24 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Label for the field next to it. |
| E13 | textbox | Coach id | main | 8.5%, 68.8% · 177 x 21 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 0px | Field: she types or chooses a value. |
| E14 | textbox | Schools | main | 69.5%, 68.8% · 58 x 21 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 0px | Field: she types or chooses a value. |
| E15 | button | Propose cohort | main | 8.5%, 71.4% · 324 x 48 | 18px / 600; rgb(0, 0, 0); bg rgb(240, 240, 240); radius 8px (--s2) | Button: tap to propose cohort. |
| E16 | heading | Funnel | main | 8.5%, 87.3% · 324 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E17 | element | No content is waiting for review. (system: review queue ages; gates ne | main | 8.5%, 30.4% · 324 x 81 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Shows text or a value. |
| E18 | heading | Track results | main | 8.5%, 40.7% · 324 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E19 | element | Inconclusive | main | 54.5%, 53.8% · 109 x 31 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E20 | img | ADD-NOCARRY v1: -15.7 (-23.0 to -8.8) | main | 12.8%, 71.6% · 290 x 35 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Shows text or a value. |
| E21 | element | Inconclusive | main | 44%, 91% · 109 x 31 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E22 | element | Not working | main | 47.2%, 42.7% · 111 x 31 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(255, 218, 214) (--margin-container); radius 999px (--r-pill) | Shows text or a value. |
| E23 | img | SUB-NODEC v1: -0.3 (-3.3 to 2.8) | main | 12.8%, 60.6% · 290 x 35 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Shows text or a value. |
| E24 | element | Working | main | 38.6%, 81.4% · 83 x 31 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(180, 242, 188) (--good-container); radius 999px (--r-pill) | Shows text or a value. |
| E25 | img | SUB-SFL v1: -19.5 (-24.1 to -15.1) | main | 12.8%, 28.6% · 290 x 35 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Shows text or a value. |
| E26 | heading | Error map (grade 3, term 1) | main | 8.5%, 50.5% · 324 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E27 | link | Officer [current] | bottom bar | 0%, 93.1% · 130 x 58 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/officer. |
| E28 | link | Review | bottom bar | 33.3%, 93.1% · 130 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/review. |
| E29 | link | My profile | bottom bar | 66.7%, 93.1% · 130 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/profile. |

## 5. Content and data

Charts and tables with their text versions, a cohort form, the funnel with a source label on each line (system or self-report). No teacher or child is shown.

The text on screen, copied exactly from the page in the first state:

```text
Officer

Simulated data: this class and these children are made up for the demo.

 Aggregates only. Nothing covering fewer than 5 classes or 5 teachers is shown.

Cohorts

Start a cohort for one error, then move it forward. Each change is recorded. Counts under 5 are hidden.

Start a cohort
Error
PV-HEARD
ADD-NOCARRY
SUB-SFL
SUB-NODEC
Coach idSchools
Propose cohort

No cohorts yet.

Funnel

From delivery to change. Each step says where its number comes from. Practice Class sessions are not counted here.

No content is waiting for review. (system: review queue ages; gates never auto-approve)

PV-HEARD
Delivered: fewer than 5 teachers (system: lessons sent)
Tried it in class: fewer than 5 teachers (self-report: tapped Tried it in class)
Practised: not counted per cohort (system: not counted per cohort (sessions are metadata only))
Changed: see track results (next check, blind-scored counts)
PV-REVERSE
Delivered: fewer than 5 teachers (system: lessons sent)
Tried it in class: fewer than 5 teachers (self-report: tapped Tried it in class)
Practised: not counted per cohort (system: not counted per cohort (sessions are metadata only))
Changed: awaiting next check (next check, blind-scored counts)
ADD-NOCARRY
Delivered: fewer than 5 teachers (system: lessons sent)
Tried it in class: fewer than 5 teachers (self-report: tapped Tried it in class)
Practised: not counted per cohort (system: not counted per cohort (sessions are metadata only))
Changed: see track results (next check, blind-scored counts)
SUB-SFL
Delivered: fewer than 5 teachers (system: lessons sent)
Tried it in class: fewer than 5 teachers (self-report: tapped Tried it in class)
Practised: not counted per cohort (system: not counted per cohort (sessions are metadata only))
Changed: see track results (next check, blind-scored counts)
SUB-NODEC
Delivered: fewer than 5 teachers (system: lessons sent)
Tried it in class: fewer than 5 teachers (self-report: tapped Tried it in class)
Practised: not counted per cohort (system: not counted per cohort (sessions are metadata only))
Changed: see track results (next check, blind-scored counts)
Track results

A failed track counts against the track, not the teacher.

ADD-NOCARRY v1 Inconclusive

Change against the waitlist group: -15.7 points (likely range -23.0 to -8.8, 95 times in 100). 8 classes on the track, 7 on the waitlist.

from 7 classes, read as directional

Not enough evidence either way yet.

PV-HEARD v1 Inconclusive

fewer than 5 classes

from 3 classes,
…(shortened)
```

Dynamic parts: counts, dates, names of the demo class and every number come from the demo class loaded in Judge mode or from the 12-step demo session; the code computes them.

## 6. States and transitions

- **default**: open the route.
- Empty, loading, error and offline states were not captured in this pack (core scope). The loaders and messages are listed in the product's own strings (`strings/en.json`).

## 7. What works and what to change

Measured from the numbered elements (touch targets, font sizes, sideways scroll, labels). There is no current UI audit of this app: `docs/design/audit/AUDIT.md` describes the original front end before the re-skin, so it is not used here.

- Touch target under 44 px: "Coach id" (default/en: 177 x 21 px).
- Touch target under 44 px: "Schools" (default/en: 58 x 21 px).
- Touch target under 44 px: "Error PV-HEARD ADD-NOCARRY SUB-SFL SUB-N" (default/en: 121 x 19 px).
- 7 distinct font sizes among the numbered elements in default, en, desktop: 13.3333px, 16.15px, 16px, 19px, 20px, 22.23px, 24px.

## 8. Constraints

- Phone first at 390 px; desktop for coach, officer, judge and mentor screens.
- Touch targets at least 44 px, primary buttons 48 px.
- English, Hindi and Tamil text must fit without cutting.
- Use the tokens in `../00-tokens.md`: Material 3, Calm Institutional palette (teal primary), no new colours.
- Teacher-facing numbers are counts, never percentages. Simulated data stays labelled.
- No new features: redesign what exists.
