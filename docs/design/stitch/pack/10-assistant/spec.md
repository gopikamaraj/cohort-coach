# 10 · Assistant

_Written for Stitch: what this screen is, what each part does, and what to keep. Tables are generated from the live page; the purpose and behaviour lines are written from the component source._

## 1. Screen

- **Route:** `#/assistant`
- **Roles shown:** teacher
- **Languages captured:** en
- **Inventory id:** X29
- **When a user sees it:** Anyone asks how to do something in the app.
- **What they are trying to do:** Ask a question and get an answer drawn from approved help text, scoped to the user's role.
- **Source:** apps/pwa/src/screens/Assistant.tsx
- **Data:** simulated demo data (judge mode, recorded AI answers). Every capture of data was checked for a Demo or Simulated label.

## 2. Images

| File | What it shows | Viewport | Scroll | State |
| --- | --- | --- | --- | --- |
| 01-assistant_default_teacher_en_phone.png | First viewport, clean | 390 x 844 @2x | top | default · teacher · en |
| 01-assistant_default_teacher_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | default · teacher · en |
| 01-assistant_default_teacher_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | default · teacher · en |
| 01-assistant_default_teacher_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 491 px | default · teacher · en |
| 01-assistant_default_teacher_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · teacher · en |
| 01-assistant_default_teacher_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · teacher · en |
| 01-assistant_default_teacher_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · teacher · en |
| 01-assistant_default_teacher_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · teacher · en |
| assistant-sheet.png | Contact sheet of the main states | — | — | all |

## 3. Layout

Top to bottom in the first state ("default"), by region, with the numbered elements in each:

- **header**: E1 to E5 (5 elements)
- **main**: E6 to E20 (15 elements)
- **bottom bar**: E21 to E25 (5 elements)
- The page scrolls inside one container: 653 px visible of 1144 px (the header and bottom bar stay fixed).

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
| E6 | heading | Judge guide | main | 4.1%, 14.8% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E7 | element | I can help with: Where each rubric criterion is built, with its honest | main | 4.1%, 19.8% · 358 x 144 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E8 | tab | Assistant [selected] | main | 8.5%, 40.3% · 324 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Shows text or a value. |
| E9 | tab | About this product | main | 8.5%, 46% · 324 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Shows text or a value. |
| E10 | label | View as Judge Teacher Mentor Coach Officer | main | 8.5%, 51.7% · 324 x 79 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Label for the field next to it. |
| E11 | combobox | View as Judge Teacher Mentor Coach Officer | main | 8.5%, 55.3% · 324 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Dropdown: she chooses one value. |
| E12 | button | Who is the user? Efficacy and user centricity (35%) | main | 4.1%, 66.4% · 358 x 72 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to who is the user? efficacy and user centricity (35%). |
| E13 | button | What is real and what is simulated? Efficacy and user centricity (35%) | main | 4.1%, 75.8% · 358 x 99 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to what is real and what is simulated? efficacy and user centricity (35%) · effective ai use and technical strength (30%). |
| E14 | button | Where is AI used? Effective AI use and technical strength (30%) | main | 4.1%, 30.3% · 358 x 72 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to where is ai used? effective ai use and technical strength (30%). |
| E15 | button | How does it work offline? Efficacy and user centricity (35%) | main | 4.1%, 39.8% · 358 x 72 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to how does it work offline? efficacy and user centricity (35%). |
| E16 | button | What does it cost per teacher? Effective AI use and technical strength | main | 4.1%, 49.3% · 358 x 99 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Button: tap to what does it cost per teacher? effective ai use and technical strength (30%) · efficacy and user centricity (35%). |
| E17 | label | Ask your own question | main | 4.1%, 62% · 358 x 79 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E18 | textbox | Ask your own question | main | 4.1%, 65.6% · 358 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E19 | button | Ask [disabled] | main | 4.1%, 72.7% · 358 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Button: tap to ask. |
| E20 | element | Answers come from the repository documents, the rubric map, the deck a | main | 4.1%, 78.4% · 358 x 72 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E21 | link | Home | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E22 | link | Enter check | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E23 | link | My class | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to What my class gets wrong. |
| E24 | link | Practice | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the Practice Class. |
| E25 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

## 5. Content and data

A role title and scope note, five suggested questions, a question box and send button. Answers show sources and follow-up questions. Judges see a view-as switch and the test path.

The text on screen, copied exactly from the page in the first state:

```text
Judge guide

I can help with: Where each rubric criterion is built, with its honest status, the code path, the deck slide and the video time. Use View as to see another role's assistant on demo data. I can't see: Any real user's data. This demo has none. Everything here is simulated or labelled.

Assistant
About this product
View as
Judge
Teacher
Mentor
Coach
Officer
Who is the user? Efficacy and user centricity (35%)
What is real and what is simulated? Efficacy and user centricity (35%) · Effective AI use and technical strength (30%)
Where is AI used? Effective AI use and technical strength (30%)
How does it work offline? Efficacy and user centricity (35%)
What does it cost per teacher? Effective AI use and technical strength (30%) · Efficacy and user centricity (35%)
Ask your own question
Ask

Answers come from the repository documents, the rubric map, the deck and the video script. · Commit 8b0f87f
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
