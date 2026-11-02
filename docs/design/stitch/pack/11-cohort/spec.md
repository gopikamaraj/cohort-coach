# 11 · Cohort chat

_Written for Stitch: what this screen is, what each part does, and what to keep. Tables are generated from the live page; the purpose and behaviour lines are written from the component source._

## 1. Screen

- **Route:** `#/cohort`
- **Roles shown:** teacher
- **Languages captured:** en
- **Inventory id:** X13
- **When a user sees it:** A teacher in a cohort talks with other teachers, her mentor and her coach.
- **What they are trying to do:** Read the weekly prompt and the posts, and post without names or numbers about a child.
- **Source:** apps/pwa/src/screens/Cohort.tsx
- **Data:** simulated demo data (judge mode, recorded AI answers). Every capture of data was checked for a Demo or Simulated label.

## 2. Images

| File | What it shows | Viewport | Scroll | State |
| --- | --- | --- | --- | --- |
| 01-cohort_default_teacher_en_phone.png | First viewport, clean | 390 x 844 @2x | top | default · teacher · en |
| 01-cohort_default_teacher_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | default · teacher · en |
| cohort-sheet.png | Contact sheet of the main states | — | — | all |

## 3. Layout

Top to bottom in the first state ("default"), by region, with the numbered elements in each:

- **header**: E1 to E5 (5 elements)
- **main**: E6 to E9 (4 elements)
- **bottom bar**: E10 to E14 (5 elements)
- The page does not scroll inside a container.

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
| E6 | heading | Cohort chat | main | 4.1%, 14.8% · 358 x 31 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E7 | heading | Cohorts you can join | main | 8.5%, 41.9% · 324 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E8 | label | I agree to share my posts with my cohort under a label. | main | 8.5%, 50.1% · 324 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Label for the field next to it. |
| E9 | checkbox | I agree to share my posts with my cohort under a label. | main | 9.5%, 51.9% · 16 x 24 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 0px | Tick box: turns an option on or off. |
| E10 | link | Home | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E11 | link | Enter check | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E12 | link | My class | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to What my class gets wrong. |
| E13 | link | Practice | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the Practice Class. |
| E14 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

## 5. Content and data

Joining needs a separate consent. The thread shows pseudonymous posts, a compose box with a privacy notice, a Report button on each post and a read-only note when the cohort is closed.

The text on screen, copied exactly from the page in the first state:

```text
Cohort Coach
Assistant

Online
Good signal ·
9.2 Mbps

 Cohort chat

Simulated data: this class and these children are made up for the demo.

A small space for teachers working on the same mistake. You appear as a label, never a name.

Cohorts you can join

No cohort is open yet.

I agree to share my posts with my cohort under a label.
Home
Enter check
My class
Practice
More
```

Dynamic parts: counts, dates, names of the demo class and every number come from the demo class loaded in Judge mode or from the 12-step demo session; the code computes them.

## 6. States and transitions

- **default**: open the route.
- Empty, loading, error and offline states were not captured in this pack (core scope). The loaders and messages are listed in the product's own strings (`strings/en.json`).

## 7. What works and what to change

Measured from the numbered elements (touch targets, font sizes, sideways scroll, labels). There is no current UI audit of this app: `docs/design/audit/AUDIT.md` describes the original front end before the re-skin, so it is not used here.

- Touch target under 44 px: "I agree to share my posts with my cohort" (default/en: 16 x 24 px).

## 8. Constraints

- Phone first at 390 px; desktop for coach, officer, judge and mentor screens.
- Touch targets at least 44 px, primary buttons 48 px.
- English, Hindi and Tamil text must fit without cutting.
- Use the tokens in `../00-tokens.md`: Material 3, Calm Institutional palette (teal primary), no new colours.
- Teacher-facing numbers are counts, never percentages. Simulated data stays labelled.
- No new features: redesign what exists.
