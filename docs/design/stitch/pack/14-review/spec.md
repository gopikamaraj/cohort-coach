# 14 · Review queue

_Written for Stitch: what this screen is, what each part does, and what to keep. Tables are generated from the live page; the purpose and behaviour lines are written from the component source._

## 1. Screen

- **Route:** `#/review`
- **Roles shown:** coach
- **Languages captured:** en
- **Inventory id:** P3, X23
- **When a user sees it:** A coach or officer approves AI-drafted content.
- **What they are trying to do:** Read a draft with its check results, then approve, edit or reject it with a reason. Two keys: the coach, then the mentor.
- **Source:** apps/pwa/src/screens/Review.tsx
- **Data:** simulated demo data (judge mode, recorded AI answers). Every capture of data was checked for a Demo or Simulated label.

## 2. Images

| File | What it shows | Viewport | Scroll | State |
| --- | --- | --- | --- | --- |
| 01-review_default_coach_en_desktop.png | First viewport, clean | 1280 x 800 @1x | top | default · coach · en |
| 01-review_default_coach_en_desktop-annotated.png | Same, with numbered boxes E1, E2, E3… | 1280 x 800 @1x | top | default · coach · en |
| review-sheet.png | Contact sheet of the main states | — | — | all |

## 3. Layout

Top to bottom in the first state ("default"), by region, with the numbered elements in each:

- **header**: E1 to E6 (5 elements)
- **main**: E7 to E19 (9 elements)
- **side rail**: E5 to E17 (5 elements)
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
| E5 | link | Coach | side rail | 0.6%, 2% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/coach. |
| E6 | element | Good signal · 9.2 Mbps | header | 82.8%, 2.3% · 191 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E7 | heading | Review queue | main | 10.6%, 10.6% · 1112 x 31 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E8 | link | Review [current] | side rail | 0.6%, 12.5% · 87 x 76 | 16px / 700; rgb(0, 32, 31) (--on-pen-container); bg rgb(204, 232, 231) (--tonal); radius 16px (--s4) | Opens #/review. |
| E9 | link | Papers | side rail | 0.6%, 23% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/papers. |
| E10 | element | Neither key alone publishes. Each change makes a new version. | main | 10.6%, 27.6% · 1112 x 44 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E11 | link | Cohort | side rail | 0.6%, 33.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/cohort. |
| E12 | button | Awaiting coach [pressed] | main | 10.6%, 39.1% · 222 x 48 | 19px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 0px | Button: tap to awaiting coach. |
| E13 | button | Awaiting mentor | main | 28%, 39.1% · 222 x 48 | 19px / 600; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Button: tap to awaiting mentor. |
| E14 | button | Approved | main | 45.4%, 39.1% · 222 x 48 | 19px / 600; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Button: tap to approved. |
| E15 | button | Returned | main | 62.7%, 39.1% · 222 x 48 | 19px / 600; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Button: tap to returned. |
| E16 | button | All | main | 80.1%, 39.1% · 222 x 48 | 19px / 600; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Button: tap to all. |
| E17 | link | My profile | side rail | 0.6%, 44% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/profile. |
| E18 | heading | Track versions | main | 12%, 59.6% · 1078 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E19 | heading | Audit | main | 12%, 74.5% · 1078 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |

## 5. Content and data

A queue list with the age of each item, a panel for the chosen item with its automatic checks, an editable script, approve and reject buttons (reject needs a structured reason), versions and the audit trail.

The text on screen, copied exactly from the page in the first state:

```text
Cohort Coach
Assistant

Online
Good signal · 9.2 Mbps

 Review queue

Simulated data: this class and these children are made up for the demo.

Content waits here for a person. The coach approves it, then the programme officer switches it on for the block.

 Neither key alone publishes. Each change makes a new version.

Acting as Coach

Awaiting coach
Awaiting mentor
Approved
Returned
All

Nothing is waiting here.

Track versions

No track versions yet.

Audit

Nothing recorded yet.

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
