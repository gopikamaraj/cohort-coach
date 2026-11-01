# 13 · Coach home

_Written for Stitch: what this screen is, what each part does, and what to keep. Tables are generated from the live page; the purpose and behaviour lines are written from the component source._

## 1. Screen

- **Route:** `#/coach`
- **Roles shown:** coach
- **Languages captured:** en
- **Inventory id:** X21
- **When a user sees it:** A coach opens the app.
- **What they are trying to do:** See cohorts with their status, mentor status, items awaiting approval and the oldest age, and flagged posts.
- **Source:** apps/pwa/src/screens/RoleScreens.tsx
- **Data:** simulated demo data (judge mode, recorded AI answers). Every capture of data was checked for a Demo or Simulated label.

## 2. Images

| File | What it shows | Viewport | Scroll | State |
| --- | --- | --- | --- | --- |
| 01-coach_default_coach_en_desktop.png | First viewport, clean | 1280 x 800 @1x | top | default · coach · en |
| 01-coach_default_coach_en_desktop-annotated.png | Same, with numbered boxes E1, E2, E3… | 1280 x 800 @1x | top | default · coach · en |
| 02-coach_default_coach_en_phone.png | First viewport, clean | 390 x 844 @2x | top | default · coach · en |
| 02-coach_default_coach_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | default · coach · en |
| 02-coach_default_coach_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | default · coach · en |
| 02-coach_default_coach_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 438 px | default · coach · en |
| 02-coach_default_coach_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · coach · en |
| 02-coach_default_coach_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · coach · en |
| 02-coach_default_coach_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · coach · en |
| 02-coach_default_coach_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · coach · en |
| coach-sheet.png | Contact sheet of the main states | — | — | all |

## 3. Layout

Top to bottom in the first state ("default"), by region, with the numbered elements in each:

- **header**: E1 to E6 (5 elements)
- **main**: E7 to E13 (3 elements)
- **side rail**: E5 to E12 (5 elements)
- The page does not scroll inside a container.

## 4. Elements

Position is the box's top-left as a share of the viewport, then its size in CSS pixels. Style is the font size / weight, text colour, background, radius; a design token name in brackets means the value matches that token.

### State "default" · coach · en · desktop

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 9.4%, 1% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | button | Assistant | header | 64.8%, 1% · 129 x 44 | 19px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E3 | status | Online Good signal · 9.2 Mbps | header | 75.5%, 1.6% · 297 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E4 | image |  | header | 9.4%, 1.8% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E5 | link | Coach [current] | side rail | 0.6%, 2% · 87 x 76 | 16px / 700; rgb(0, 32, 31) (--on-pen-container); bg rgb(204, 232, 231) (--tonal); radius 16px (--s4) | Opens #/coach. |
| E6 | element | Good signal · 9.2 Mbps | header | 82.8%, 2.3% · 191 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E7 | heading | Coach | main | 10.6%, 10.6% · 1112 x 31 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E8 | link | Review | side rail | 0.6%, 12.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/review. |
| E9 | link | Papers | side rail | 0.6%, 23% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/papers. |
| E10 | heading | Term T1: 120 classes in 40 schools | main | 12%, 33.3% · 1078 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E11 | link | Cohort | side rail | 0.6%, 33.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/cohort. |
| E12 | link | My profile | side rail | 0.6%, 44% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/profile. |
| E13 | heading | Term T2: 120 classes in 40 schools | main | 12%, 61.4% · 1078 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |

### State "default" · coach · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | Online Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | heading | Coach | main | 4.1%, 14.8% · 358 x 31 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E7 | heading | Term T1: 120 classes in 40 schools | main | 8.5%, 45.1% · 324 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E8 | heading | Term T2: 120 classes in 40 schools | main | 8.5%, 38.3% · 324 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E9 | link | Coach [current] | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/coach. |
| E10 | link | Review | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/review. |
| E11 | link | Papers | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/papers. |
| E12 | link | Cohort | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/cohort. |
| E13 | link | My profile | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/profile. |

## 5. Content and data

A cohort table with status chips, a count of items awaiting approval and links to the review queue and cohort pages. Desktop first; it collapses to one column on a phone.

The text on screen, copied exactly from the page in the first state:

```text
Cohort Coach
Assistant

Online
Good signal · 9.2 Mbps

 Coach

Simulated data: this class and these children are made up for the demo.

A coach (for example from a DIET) sees how many children show each error across the block. Counts only; nothing about one class or teacher.

Term T1: 120 classes in 40 schools
Writes a number the way it is said: 251 of 3538 children checked
Swaps tens and ones: 58 of 3538 children checked
Forgets the carried ten: 369 of 3538 children checked
Takes the smaller digit from the larger: 805 of 3538 children checked
Borrows a ten but does not reduce the tens digit: 663 of 3538 children checked
Term T2: 120 classes in 40 schools
Writes a number the way it is said: 226 of 3530 children checked
Swaps tens and ones: 85 of 3530 children checked
Forgets the carried ten: 331 of 3530 children checked
Takes the smaller digit from the larger: 574 of 3530 children checked
Borrows a ten but does not reduce the tens digit: 599 of 3530 children checked

Approving cohorts and reviewing lessons arrive in a later step.

Coach
Review
Papers
Cohort
My profile
```

Dynamic parts: counts, dates, names of the demo class and every number come from the demo class loaded in Judge mode or from the 12-step demo session; the code computes them.

## 6. States and transitions

- **default**: open the route.
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
