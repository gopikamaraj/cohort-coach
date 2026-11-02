# 05 · Practice Class

_Written for Stitch: what this screen is, what each part does, and what to keep. Tables are generated from the live page; the purpose and behaviour lines are written from the component source._

## 1. Screen

- **Route:** `#/practice`
- **Roles shown:** teacher
- **Languages captured:** en, hi
- **Inventory id:** T5
- **When a user sees it:** A teacher rehearses privately before using a technique on real children.
- **What they are trying to do:** Practise one teaching move with five simulated children who make her own class's mistakes, and get private feedback.
- **Source:** apps/pwa/src/screens/Practice.tsx, apps/pwa/src/components/practice.tsx
- **Data:** simulated demo data (judge mode, recorded AI answers). Every capture of data was checked for a Demo or Simulated label.

## 2. Images

| File | What it shows | Viewport | Scroll | State |
| --- | --- | --- | --- | --- |
| 01-practice_default_teacher_en_phone.png | First viewport, clean | 390 x 844 @2x | top | default · teacher · en |
| 01-practice_default_teacher_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | default · teacher · en |
| 02-practice_started_teacher_en_phone.png | First viewport, clean | 390 x 844 @2x | top | started · teacher · en |
| 02-practice_started_teacher_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | started · teacher · en |
| 02-practice_started_teacher_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | started · teacher · en |
| 02-practice_started_teacher_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 573 px | started · teacher · en |
| 02-practice_started_teacher_en_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1146 px | started · teacher · en |
| 02-practice_started_teacher_en_phone-s04.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1421 px | started · teacher · en |
| 02-practice_started_teacher_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | started · teacher · en |
| 02-practice_started_teacher_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | started · teacher · en |
| 02-practice_started_teacher_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | started · teacher · en |
| 02-practice_started_teacher_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | started · teacher · en |
| 03-practice_default_teacher_hi_phone.png | First viewport, clean | 390 x 844 @2x | top | default · teacher · hi |
| 03-practice_default_teacher_hi_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | default · teacher · hi |
| practice-sheet.png | Contact sheet of the main states | — | — | all |

## 3. Layout

Top to bottom in the first state ("default"), by region, with the numbered elements in each:

- **header**: E1 to E5 (5 elements)
- **main**: E6 to E12 (7 elements)
- **bottom bar**: E13 to E17 (5 elements)
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
| E6 | heading | Practice class | main | 4.1%, 14.8% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E7 | tab | Practise [selected] | main | 4.1%, 19.8% · 179 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E8 | tab | Review | main | 50%, 19.8% · 179 x 48 | 18px / 600; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E9 | element | Help children who take the smaller digit from the larger. Teach as you | main | 4.1%, 47% · 358 x 108 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E10 | button | Start practice | main | 4.1%, 61.3% · 358 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Starts a rehearsal with five simulated children. |
| E11 | label | Share this session to improve the simulator | main | 4.1%, 68.4% · 358 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E12 | checkbox | Share this session to improve the simulator | main | 5.1%, 70.1% · 23 x 24 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(247, 250, 250) (--paper); radius 0px | Tick box: turns an option on or off. |
| E13 | link | Home | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E14 | link | Enter check | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E15 | link | My class | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to What my class gets wrong. |
| E16 | link | Practice [current] | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the Practice Class. |
| E17 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

### State "started" · teacher · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | Online Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | heading | Practice class | main | 4.1%, 14.8% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E7 | tab | Practise [selected] | main | 4.1%, 19.8% · 179 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E8 | tab | Review | main | 50%, 19.8% · 179 x 48 | 18px / 600; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E9 | heading | What to practise | main | 18.7%, 38% · 284 x 26 | 16px / 700; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 0px | Heading: names the section below it. |
| E10 | heading | Your simulated class | main | 8.5%, 30.8% · 324 x 26 | 18px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E11 | element | Listening | main | 9.7%, 59.4% · 52 x 46 | 16px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E12 | element | Listening | main | 26.6%, 59.4% · 52 x 46 | 16px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E13 | element | Shy | main | 44.6%, 59.4% · 42 x 25 | 16px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E14 | element | Listening | main | 60.2%, 59.4% · 52 x 46 | 16px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E15 | element | Listening | main | 77%, 59.4% · 52 x 46 | 16px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E16 | element | Turn 0 of 40 | main | 8.5%, 71.9% · 324 x 21 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(255, 255, 255) (--surface); radius 0px | Shows text or a value. |
| E17 | tab | Your turn [selected] | main | 8.5%, 81.7% · 108 x 57 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(255, 255, 255) (--surface); radius 0px | Shows text or a value. |
| E18 | tab | Coaching feedback | main | 36.2%, 81.7% · 108 x 57 | 18px / 600; rgb(63, 73, 72) (--muted); bg rgb(255, 255, 255) (--surface); radius 0px | Shows text or a value. |
| E19 | tab | For judges | main | 63.8%, 81.7% · 108 x 57 | 18px / 600; rgb(63, 73, 72) (--muted); bg rgb(255, 255, 255) (--surface); radius 0px | Shows text or a value. |
| E20 | heading | Your turn | main | 8.5%, 22.6% · 324 x 26 | 18px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E21 | button | Speak to the children | main | 19.7%, 35.1% · 236 x 72 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 36px | Button: tap to speak to the children. |
| E22 | element | Simulated voice: scripted lines and a tone, not real speech recognitio | main | 8.5%, 45.1% · 324 x 48 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(255, 255, 255) (--surface); radius 0px | Shows text or a value. |
| E23 | button | Type instead | main | 8.5%, 52.7% · 324 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Switches to typing her turn. |
| E24 | button | What can I say? [collapsed] | main | 8.5%, 60.3% · 324 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to what can i say?. |
| E25 | button | Bundles of ten | main | 8.5%, 72% · 324 x 48 | 16px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Button: tap to bundles of ten. |
| E26 | button | Loose sticks | main | 8.5%, 78.6% · 324 x 48 | 16px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Button: tap to loose sticks. |
| E27 | button | Place-value chart | main | 8.5%, 85.3% · 324 x 48 | 16px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Button: tap to place-value chart. |
| E28 | element | Tap a tool to show it to the children, as if you held it up. Bundles o | main | 8.5%, 59.3% · 324 x 168 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(255, 255, 255) (--surface); radius 0px | Shows text or a value. |
| E29 | button | End and see feedback [disabled] | main | 8.5%, 80.6% · 324 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Ends the rehearsal and asks for feedback. |
| E30 | link | Home | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E31 | link | Enter check | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E32 | link | My class | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to What my class gets wrong. |
| E33 | link | Practice [current] | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the Practice Class. |
| E34 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

### State "default" · teacher · hi · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | कोहॉर्ट कोच | header | 4.1%, 0.9% · 140 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | सहायक | header | 4.1%, 6.6% · 112 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | ऑनलाइन अच्छा सिग्नल · 9.2 एमबीपीएस | header | 34.8%, 7.2% · 166 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | अच्छा सिग्नल · 9.2 एमबीपीएस | header | 44.8%, 7.8% · 114 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | heading | प्रैक्टिस क्लास | main | 4.1%, 14.8% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E7 | tab | अभ्यास [selected] | main | 4.1%, 19.8% · 179 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E8 | tab | समीक्षा | main | 50%, 19.8% · 179 x 48 | 18px / 600; rgb(63, 73, 72) (--muted); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E9 | element | उन बच्चों की मदद करें जो हर स्तंभ में छोटे अंक को बड़े में से घटाते है | main | 4.1%, 47% · 358 x 108 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E10 | button | अभ्यास शुरू करें | main | 4.1%, 61.3% · 358 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Starts a rehearsal with five simulated children. |
| E11 | label | सिमुलेटर को बेहतर बनाने के लिए यह सत्र साझा करें | main | 4.1%, 68.4% · 358 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E12 | checkbox | सिमुलेटर को बेहतर बनाने के लिए यह सत्र साझा करें | main | 5.1%, 70.1% · 22 x 24 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(247, 250, 250) (--paper); radius 0px | Tick box: turns an option on or off. |
| E13 | link | होम | bottom bar | 0%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/home. |
| E14 | link | जाँच भरें | bottom bar | 20%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/check. |
| E15 | link | मेरी कक्षा | bottom bar | 40%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/cards. |
| E16 | link | अभ्यास [current] | bottom bar | 60%, 93.1% · 78 x 58 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/practice. |
| E17 | button | और [collapsed] | bottom bar | 80%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Button: tap to और. |

## 5. Content and data

A scenario card states the error and the goal. Five children appear with their state. She speaks or types what she would say to the class; the simulated children answer. A turn counter runs to 40 turns. At the end she gets two strengths and one thing to try, quoting her own words, and no score.

The text on screen, copied exactly from the page in the first state:

```text
Cohort Coach
Assistant

Online
Good signal ·
9.2 Mbps

Practice class
Practise
Review

Simulated data: this class and these children are made up for the demo.

Rehearse with five pretend children before you try it in class. What you say here is not kept on our servers.

Help children who take the smaller digit from the larger. Teach as you would in class; the pretend children make the mistakes your own class makes.

Start practice
Share this session to improve the simulator

Off by default. Your sessions stay on this phone. Sharing opens in a later update; your choice is saved.

Home
Enter check
My class
Practice
More
```

Dynamic parts: counts, dates, names of the demo class and every number come from the demo class loaded in Judge mode or from the 12-step demo session; the code computes them.

## 6. States and transitions

- **default**: open the route.
- **started**: tap start-practice.
- Empty, loading, error and offline states were not captured in this pack (core scope). The loaders and messages are listed in the product's own strings (`strings/en.json`).

## 7. What works and what to change

Measured from the numbered elements (touch targets, font sizes, sideways scroll, labels). There is no current UI audit of this app: `docs/design/audit/AUDIT.md` describes the original front end before the re-skin, so it is not used here.

- Touch target under 44 px: "Share this session to improve the simula" (default/en: 23 x 24 px).
- Touch target under 44 px: "सिमुलेटर को बेहतर बनाने के लिए यह सत्र स" (default/hi: 22 x 24 px).

## 8. Constraints

- Phone first at 390 px; desktop for coach, officer, judge and mentor screens.
- Touch targets at least 44 px, primary buttons 48 px.
- English, Hindi and Tamil text must fit without cutting.
- Use the tokens in `../00-tokens.md`: Material 3, Calm Institutional palette (teal primary), no new colours.
- Teacher-facing numbers are counts, never percentages. Simulated data stays labelled.
- No new features: redesign what exists.
