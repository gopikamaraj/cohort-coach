# 21 · Watch two rehearsals

_Written for Stitch: what this screen is, what each part does, and what to keep. Tables are generated from the live page; the purpose and behaviour lines are written from the component source._

## 1. Screen

- **Route:** `#/watch`
- **Roles shown:** judge
- **Languages captured:** en
- **Inventory id:** X3
- **When a user sees it:** A judge watches the Practice Class run by an AI playing the teacher.
- **What they are trying to do:** Compare an experienced and a struggling teacher style, with playback, subtitles and a labelled "AI playing the teacher (demo only)".
- **Source:** apps/pwa/src/screens/Watch.tsx
- **Data:** simulated demo data (judge mode, recorded AI answers). Every capture of data was checked for a Demo or Simulated label.

## 2. Images

| File | What it shows | Viewport | Scroll | State |
| --- | --- | --- | --- | --- |
| 01-watch_default_judge_en_desktop.png | First viewport, clean | 1280 x 800 @1x | top | default · judge · en |
| 01-watch_default_judge_en_desktop-annotated.png | Same, with numbered boxes E1, E2, E3… | 1280 x 800 @1x | top | default · judge · en |
| 01-watch_default_judge_en_desktop-s01.png | Scroll slice (80 px overlap) | 1280 x 800 @1x | 0 px | default · judge · en |
| 01-watch_default_judge_en_desktop-s02.png | Scroll slice (80 px overlap) | 1280 x 800 @1x | 472 px | default · judge · en |
| 01-watch_default_judge_en_desktop-long.png | Stitched long image (fixed header and bottom bar kept once) | 1280 x 800 @1x | full page | default · judge · en |
| 01-watch_default_judge_en_desktop-long-annotated.png | Long image with numbered boxes | 1280 x 800 @1x | full page | default · judge · en |
| watch-sheet.png | Contact sheet of the main states | — | — | all |

## 3. Layout

Top to bottom in the first state ("default"), by region, with the numbered elements in each:

- **header**: E1 to E6 (5 elements)
- **main**: E7 to E16 (6 elements)
- **side rail**: E5 to E25 (14 elements)
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
| E5 | link | Judge | side rail | 0.6%, 2% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/judge. |
| E6 | element | Good signal · 9.2 Mbps | header | 82.8%, 2.3% · 191 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E7 | heading | Watch a rehearsal | main | 10.6%, 10.6% · 1112 x 31 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E8 | link | Demo flow | side rail | 0.6%, 12.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/demo. |
| E9 | link | Home | side rail | 0.6%, 23% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/home. |
| E10 | button | Experienced teacher | main | 10.6%, 31.6% · 1112 x 48 | 19px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Button: tap to experienced teacher. |
| E11 | link | Enter check | side rail | 0.6%, 33.5% · 87 x 100 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/check. |
| E12 | button | Struggling teacher | main | 10.6%, 39.1% · 1112 x 48 | 19px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Button: tap to struggling teacher. |
| E13 | link | My class | side rail | 0.6%, 47% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/cards. |
| E14 | label | Run it live (limited each hour) | main | 10.6%, 48.1% · 1112 x 48 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E15 | checkbox | Run it live (limited each hour) | main | 10.9%, 49.6% · 24 x 24 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(247, 250, 250) (--paper); radius 0px | Tick box: turns an option on or off. |
| E16 | element | Live runs this hour: 0 of 6. Cost so far: USD 0.000 | main | 10.6%, 56.1% · 1112 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E17 | link | Practice | side rail | 0.6%, 57.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/practice. |
| E18 | link | My programme | side rail | 0.6%, 68% · 87 x 124 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/programme. |
| E19 | link | History | side rail | 0.6%, 84.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/history. |
| E20 | link | Coach | side rail | 0.6%, 95% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/coach. |
| E21 | link | Review | side rail | 0.6%, 46.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/review. |
| E22 | link | Papers | side rail | 0.6%, 57% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/papers. |
| E23 | link | Cohort | side rail | 0.6%, 67.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/cohort. |
| E24 | link | Admin | side rail | 0.6%, 78% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/admin. |
| E25 | link | My profile | side rail | 0.6%, 88.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/profile. |

## 5. Content and data

A run-type choice, play and step controls, a speed button, subtitles and a meter. Labelled as a demo.

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
- Empty, loading, error and offline states were not captured in this pack (core scope). The loaders and messages are listed in the product's own strings (`strings/en.json`).

## 7. What works and what to change

Measured from the numbered elements (touch targets, font sizes, sideways scroll, labels). There is no current UI audit of this app: `docs/design/audit/AUDIT.md` describes the original front end before the re-skin, so it is not used here.

- Touch target under 44 px: "Run it live (limited each hour)" (default/en: 24 x 24 px).

## 8. Constraints

- Phone first at 390 px; desktop for coach, officer, judge and mentor screens.
- Touch targets at least 44 px, primary buttons 48 px.
- English, Hindi and Tamil text must fit without cutting.
- Use the tokens in `../00-tokens.md`: Material 3, Calm Institutional palette (teal primary), no new colours.
- Teacher-facing numbers are counts, never percentages. Simulated data stays labelled.
- No new features: redesign what exists.
