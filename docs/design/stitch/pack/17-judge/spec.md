# 17 · Judge mode

_Written for Stitch: what this screen is, what each part does, and what to keep. Tables are generated from the live page; the purpose and behaviour lines are written from the component source._

## 1. Screen

- **Route:** `#/judge`
- **Roles shown:** judge
- **Languages captured:** en
- **Inventory id:** J1
- **When a user sees it:** A judge opens the demo.
- **What they are trying to do:** Load the simulated class, switch roles, advance to term 2, simulate offline, and reach the demo flow, the AI map and the audit trail.
- **Source:** apps/pwa/src/screens/Judge.tsx

## 2. Images

| File | What it shows | Viewport | Scroll | State |
| --- | --- | --- | --- | --- |
| 01-judge_default_judge_en_desktop.png | First viewport, clean | 1280 x 800 @1x | top | default · judge · en |
| 01-judge_default_judge_en_desktop-annotated.png | Same, with numbered boxes E1, E2, E3… | 1280 x 800 @1x | top | default · judge · en |
| 01-judge_default_judge_en_desktop-s01.png | Scroll slice (80 px overlap) | 1280 x 800 @1x | 0 px | default · judge · en |
| 01-judge_default_judge_en_desktop-s02.png | Scroll slice (80 px overlap) | 1280 x 800 @1x | 472 px | default · judge · en |
| 01-judge_default_judge_en_desktop-long.png | Stitched long image (fixed header and bottom bar kept once) | 1280 x 800 @1x | full page | default · judge · en |
| 01-judge_default_judge_en_desktop-long-annotated.png | Long image with numbered boxes | 1280 x 800 @1x | full page | default · judge · en |
| 02-judge_demo-loaded_judge_en_desktop.png | First viewport, clean | 1280 x 800 @1x | top | demo-loaded · judge · en |
| 02-judge_demo-loaded_judge_en_desktop-annotated.png | Same, with numbered boxes E1, E2, E3… | 1280 x 800 @1x | top | demo-loaded · judge · en |
| 02-judge_demo-loaded_judge_en_desktop-s01.png | Scroll slice (80 px overlap) | 1280 x 800 @1x | 0 px | demo-loaded · judge · en |
| 02-judge_demo-loaded_judge_en_desktop-s02.png | Scroll slice (80 px overlap) | 1280 x 800 @1x | 472 px | demo-loaded · judge · en |
| 02-judge_demo-loaded_judge_en_desktop-long.png | Stitched long image (fixed header and bottom bar kept once) | 1280 x 800 @1x | full page | demo-loaded · judge · en |
| 02-judge_demo-loaded_judge_en_desktop-long-annotated.png | Long image with numbered boxes | 1280 x 800 @1x | full page | demo-loaded · judge · en |
| 03-judge_default_judge_en_phone.png | First viewport, clean | 390 x 844 @2x | top | default · judge · en |
| 03-judge_default_judge_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | default · judge · en |
| 03-judge_default_judge_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | default · judge · en |
| 03-judge_default_judge_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 573 px | default · judge · en |
| 03-judge_default_judge_en_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 926 px | default · judge · en |
| 03-judge_default_judge_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · judge · en |
| 03-judge_default_judge_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · judge · en |
| 03-judge_default_judge_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · judge · en |
| 03-judge_default_judge_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · judge · en |
| judge-sheet.png | Contact sheet of the main states | — | — | all |

## 3. Layout

Top to bottom in the first state ("default"), by region, with the numbered elements in each:

- **header**: E1 to E6 (5 elements)
- **main**: E7 to E22 (8 elements)
- **side rail**: E5 to E27 (14 elements)
- The page scrolls inside one container: 800 px visible of 1272 px (the header and bottom bar stay fixed).

## 4. Elements

Position is the box's top-left as a share of the viewport, then its size in CSS pixels. Style is the font size / weight, text colour, background, radius; a design token name in brackets means the value matches that token.

### State "default" · judge · en · desktop

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 9.4%, 1% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | button | Assistant | header | 64.8%, 1% · 129 x 44 | 19px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E3 | status | Online Good signal · 9.2 Mbps | header | 75.5%, 1.6% · 297 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E4 | image |  | header | 9.4%, 1.8% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E5 | link | Judge [current] | side rail | 0.6%, 2% · 87 x 76 | 16px / 700; rgb(0, 32, 31) (--on-pen-container); bg rgb(204, 232, 231) (--tonal); radius 16px (--s4) | Opens #/judge. |
| E6 | element | Good signal · 9.2 Mbps | header | 82.8%, 2.3% · 191 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E7 | heading | Judge mode | main | 10.6%, 10.6% · 1112 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E8 | link | Demo flow | side rail | 0.6%, 12.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/demo. |
| E9 | link | Run the demo flow (about 15 minutes) | main | 10.6%, 20.9% · 1112 x 48 | 19px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Opens #/demo?step=1. |
| E10 | link | Home | side rail | 0.6%, 23% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/home. |
| E11 | heading | Test script | main | 10.6%, 28.9% · 1112 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E12 | link | Enter check | side rail | 0.6%, 33.5% · 87 x 100 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/check. |
| E13 | link | Open | main | 12.5%, 42.7% · 1088 x 48 | 19px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Opens #/home. |
| E14 | link | My class | side rail | 0.6%, 47% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/cards. |
| E15 | link | Open | main | 12.5%, 54.8% · 1088 x 48 | 19px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Opens #/check. |
| E16 | link | Practice | side rail | 0.6%, 57.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/practice. |
| E17 | link | Open | main | 12.5%, 66.8% · 1088 x 48 | 19px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Opens #/cards. |
| E18 | link | My programme | side rail | 0.6%, 68% · 87 x 124 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/programme. |
| E19 | link | Open | main | 12.5%, 83.9% · 1088 x 48 | 19px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Opens #/cards. |
| E20 | link | History | side rail | 0.6%, 84.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/history. |
| E21 | link | Coach | side rail | 0.6%, 95% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/coach. |
| E22 | link | Open | main | 12.5%, 96% · 1088 x 48 | 19px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Opens #/practice. |
| E23 | link | Review | side rail | 0.6%, 46.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/review. |
| E24 | link | Papers | side rail | 0.6%, 57% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/papers. |
| E25 | link | Cohort | side rail | 0.6%, 67.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/cohort. |
| E26 | link | Admin | side rail | 0.6%, 78% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/admin. |
| E27 | link | My profile | side rail | 0.6%, 88.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/profile. |

### State "demo-loaded" · judge · en · desktop

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 9.4%, 1% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | button | Assistant | header | 64.8%, 1% · 129 x 44 | 19px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E3 | status | Online Good signal · 9.2 Mbps | header | 75.5%, 1.6% · 297 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E4 | image |  | header | 9.4%, 1.8% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E5 | link | Judge [current] | side rail | 0.6%, 2% · 87 x 76 | 16px / 700; rgb(0, 32, 31) (--on-pen-container); bg rgb(204, 232, 231) (--tonal); radius 16px (--s4) | Opens #/judge. |
| E6 | element | Good signal · 9.2 Mbps | header | 82.8%, 2.3% · 191 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E7 | link | Open | main | 12.5%, 6.6% · 1088 x 48 | 19px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Opens #/cards. |
| E8 | link | Demo flow | side rail | 0.6%, 12.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/demo. |
| E9 | link | Open | main | 12.5%, 18.6% · 1088 x 48 | 19px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Opens #/practice. |
| E10 | link | Home | side rail | 0.6%, 23% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/home. |
| E11 | link | Open | main | 12.5%, 30.7% · 1088 x 48 | 19px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Opens #/practice. |
| E12 | link | Enter check | side rail | 0.6%, 33.5% · 87 x 100 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/check. |
| E13 | link | Open | main | 12.5%, 42.8% · 1088 x 48 | 19px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Opens #/aimap. |
| E14 | link | My class | side rail | 0.6%, 47% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/cards. |
| E15 | button | Load a simulated class | main | 10.6%, 50.7% · 1112 x 48 | 19px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Loads the simulated class into this phone. |
| E16 | link | Practice | side rail | 0.6%, 57.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/practice. |
| E17 | status | Simulated class loaded: 28 children. | main | 10.6%, 58.3% · 1112 x 28 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Message shown to the user (read out by a screen reader). |
| E18 | link | My programme | side rail | 0.6%, 68% · 87 x 124 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/programme. |
| E19 | button | Advance to Term 2 | main | 10.6%, 71.4% · 1112 x 48 | 19px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Moves the demo to term 2. |
| E20 | button | Simulate offline | main | 10.6%, 78.9% · 1112 x 48 | 19px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Pretends the phone is offline to show what still works. |
| E21 | link | History | side rail | 0.6%, 84.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/history. |
| E22 | button | Clear this phone | main | 10.6%, 86.4% · 1112 x 48 | 19px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Clears the demo data. |
| E23 | heading | For judges | main | 10.6%, 94.4% · 1112 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E24 | link | Coach | side rail | 0.6%, 95% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/coach. |
| E25 | link | AI map | main | 10.6%, 98.5% · 60 x 44 | 19px / 400; rgb(0, 0, 238); bg rgb(247, 250, 250) (--paper); radius 0px | Opens #/aimap. |
| E26 | link | Review | side rail | 0.6%, 46.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/review. |
| E27 | link | Papers | side rail | 0.6%, 57% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/papers. |
| E28 | link | Cohort | side rail | 0.6%, 67.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/cohort. |
| E29 | link | Admin | side rail | 0.6%, 78% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/admin. |
| E30 | link | My profile | side rail | 0.6%, 88.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/profile. |

### State "default" · judge · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | Online Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | heading | Judge mode | main | 4.1%, 14.8% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E7 | link | Run the demo flow (about 15 minutes) | main | 4.1%, 27.6% · 358 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Opens #/demo?step=1. |
| E8 | heading | Test script | main | 4.1%, 35.2% · 358 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E9 | link | Open | main | 10.3%, 51.1% · 334 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Opens #/home. |
| E10 | link | Open | main | 10.3%, 65.5% · 334 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Opens #/check. |
| E11 | link | Open | main | 10.3%, 80% · 334 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Opens #/cards. |
| E12 | link | Open | main | 10.3%, 31.2% · 334 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Opens #/cards. |
| E13 | link | Open | main | 10.3%, 45.6% · 334 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Opens #/practice. |
| E14 | link | Open | main | 10.3%, 56.9% · 334 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Opens #/practice. |
| E15 | link | Open | main | 10.3%, 68.1% · 334 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Opens #/aimap. |
| E16 | button | Load a simulated class | main | 4.1%, 75.7% · 358 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Loads the simulated class into this phone. |
| E17 | button | Advance to Term 2 | main | 4.1%, 47% · 358 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Moves the demo to term 2. |
| E18 | button | Simulate offline | main | 4.1%, 54.1% · 358 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Pretends the phone is offline to show what still works. |
| E19 | button | Clear this phone | main | 4.1%, 61.3% · 358 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Clears the demo data. |
| E20 | heading | For judges | main | 4.1%, 68.8% · 358 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E21 | link | AI map | main | 4.1%, 72.7% · 57 x 44 | 18px / 400; rgb(0, 0, 238); bg rgb(247, 250, 250) (--paper); radius 0px | Opens #/aimap. |
| E22 | link | Audit trail | main | 4.1%, 78% · 78 x 44 | 18px / 400; rgb(0, 0, 238); bg rgb(247, 250, 250) (--paper); radius 0px | Opens #/audit. |
| E23 | link | See who has tried it (testing evidence) | main | 4.1%, 83.2% · 301 x 44 | 18px / 400; rgb(0, 0, 238); bg rgb(247, 250, 250) (--paper); radius 0px | Opens #/testing. |
| E24 | link | Judge [current] | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/judge. |
| E25 | link | Demo flow | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/demo. |
| E26 | link | Home | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E27 | link | Enter check | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E28 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

## 5. Content and data

Buttons load the demo class, advance the term, toggle offline and reset. Links open the 12-step demo flow, the testing evidence and the AI map.

The text on screen, copied exactly from the page in the first state:

```text
Judge
Demo flow
Home
Enter check
My class
Practice
My programme
History
Coach
Review
Papers
Cohort
Admin
My profile
```

Dynamic parts: counts, dates, names of the demo class and every number come from the demo class loaded in Judge mode or from the 12-step demo session; the code computes them.

## 6. States and transitions

- **default**: open the route.
- **demo-loaded**: tap load-demo, then wait for demo-loaded.
- Empty, loading, error and offline states were not captured in this pack (core scope). The loaders and messages are listed in the product's own strings (`strings/en.json`).

## 7. What works and what to change

Measured from the numbered elements (touch targets, font sizes, sideways scroll, labels). There is no current UI audit of this app: `docs/design/audit/AUDIT.md` describes the original front end before the re-skin, so it is not used here.

- No measured problem found in the numbered elements. A designer should still review hierarchy and spacing by eye.

## 8. Constraints

- Phone first at 390 px; desktop for coach, officer, judge and mentor screens.
- Touch targets at least 44 px, primary buttons 48 px.
- English, Hindi and Tamil text must fit without cutting.
- Use the tokens in `../00-tokens.md`: Material 3, Calm Institutional palette (teal primary), no new colours.
- Teacher-facing numbers are counts, never percentages. Simulated data stays labelled.
- No new features: redesign what exists.
