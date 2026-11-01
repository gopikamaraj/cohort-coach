# 16 · Mentor dashboard

_Written for Stitch: what this screen is, what each part does, and what to keep. Tables are generated from the live page; the purpose and behaviour lines are written from the component source._

## 1. Screen

- **Route:** `#/mentor`
- **Roles shown:** mentor
- **Languages captured:** en
- **Inventory id:** X20
- **When a user sees it:** A mentor opens the app.
- **What they are trying to do:** See the cohort, the week of the track, her recordings and their approval status.
- **Source:** apps/pwa/src/screens/RoleScreens.tsx
- **Data:** simulated demo data (judge mode, recorded AI answers). Every capture of data was checked for a Demo or Simulated label.

## 2. Images

| File | What it shows | Viewport | Scroll | State |
| --- | --- | --- | --- | --- |
| 01-mentor_default_mentor_en_phone.png | First viewport, clean | 390 x 844 @2x | top | default · mentor · en |
| 01-mentor_default_mentor_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | default · mentor · en |
| 02-mentor_default_mentor_en_desktop.png | First viewport, clean | 1280 x 800 @1x | top | default · mentor · en |
| 02-mentor_default_mentor_en_desktop-annotated.png | Same, with numbered boxes E1, E2, E3… | 1280 x 800 @1x | top | default · mentor · en |
| mentor-sheet.png | Contact sheet of the main states | — | — | all |

## 3. Layout

Top to bottom in the first state ("default"), by region, with the numbered elements in each:

- **header**: E1 to E5 (5 elements)
- **main**: E6 to E6 (1 elements)
- **bottom bar**: E7 to E11 (5 elements)
- The page does not scroll inside a container.

## 4. Elements

Position is the box's top-left as a share of the viewport, then its size in CSS pixels. Style is the font size / weight, text colour, background, radius; a design token name in brackets means the value matches that token.

### State "default" · mentor · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | Online Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | heading | Mentor | main | 4.1%, 14.8% · 358 x 31 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E7 | link | Mentor [current] | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/mentor. |
| E8 | link | Home | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E9 | link | Enter check | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E10 | link | My class | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to What my class gets wrong. |
| E11 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

### State "default" · mentor · en · desktop

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 9.4%, 1% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | button | Assistant | header | 64.8%, 1% · 129 x 44 | 19px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E3 | status | Online Good signal · 9.2 Mbps | header | 75.5%, 1.6% · 297 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E4 | image |  | header | 9.4%, 1.8% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E5 | link | Mentor [current] | side rail | 0.6%, 2% · 87 x 76 | 16px / 700; rgb(0, 32, 31) (--on-pen-container); bg rgb(204, 232, 231) (--tonal); radius 16px (--s4) | Opens #/mentor. |
| E6 | element | Good signal · 9.2 Mbps | header | 82.8%, 2.3% · 191 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E7 | heading | Mentor | main | 10.6%, 10.6% · 1112 x 31 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E8 | link | Home | side rail | 0.6%, 12.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/home. |
| E9 | link | Enter check | side rail | 0.6%, 23% · 87 x 100 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/check. |
| E10 | link | My class | side rail | 0.6%, 36.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/cards. |
| E11 | link | Practice | side rail | 0.6%, 47% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/practice. |
| E12 | link | My programme | side rail | 0.6%, 57.5% · 87 x 124 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/programme. |
| E13 | link | History | side rail | 0.6%, 74% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/history. |
| E14 | link | My profile | side rail | 0.6%, 84.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/profile. |

## 5. Content and data

A cohort dropdown with a status chip, the current week, a list of her recordings with status (draft, awaiting coach, approved, in use) and the weekly digest.

The text on screen, copied exactly from the page in the first state:

```text
Cohort Coach
Assistant

Online
Good signal ·
9.2 Mbps

 Mentor

Simulated data: this class and these children are made up for the demo.

A mentor is a teacher whose class fixed an error. Your way of teaching helps the next cohort. If you are invited, you would:

 Say what you do first
 Say which materials you use and how
 Say the exact words you use
 Say how long it takes and when

Invitations come after the next check shows whose class fixed the error. Recording is built in a later step.

Mentor
Home
Enter check
My class
More
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
