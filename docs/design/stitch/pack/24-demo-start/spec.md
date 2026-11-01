# 24 · Demo flow, step 1 (start)

_Written for Stitch: what this screen is, what each part does, and what to keep. Tables are generated from the live page; the purpose and behaviour lines are written from the component source._

## 1. Screen

- **Route:** `#/demo?step=1`
- **Roles shown:** judge
- **Languages captured:** en, hi
- **Inventory id:** X36
- **When a user sees it:** A judge starts the 12-step demo flow.
- **What they are trying to do:** Begin as a teacher with the made-up class 3A.
- **Source:** apps/pwa/src/screens/DemoStudio.tsx, apps/pwa/src/components/DemoPanel.tsx
- **Data:** simulated demo data (judge mode, recorded AI answers). Every capture of data was checked for a Demo or Simulated label.

## 2. Images

| File | What it shows | Viewport | Scroll | State |
| --- | --- | --- | --- | --- |
| 01-demo-start_default_judge_en_phone.png | First viewport, clean | 390 x 844 @2x | top | default · judge · en |
| 01-demo-start_default_judge_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | default · judge · en |
| 01-demo-start_default_judge_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | default · judge · en |
| 01-demo-start_default_judge_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 264 px | default · judge · en |
| 01-demo-start_default_judge_en_phone-long.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · judge · en |
| 01-demo-start_default_judge_en_phone-long-annotated.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · judge · en |
| 02-demo-start_default_judge_hi_phone.png | First viewport, clean | 390 x 844 @2x | top | default · judge · hi |
| 02-demo-start_default_judge_hi_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | default · judge · hi |
| 02-demo-start_default_judge_hi_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | default · judge · hi |
| 02-demo-start_default_judge_hi_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 240 px | default · judge · hi |
| 02-demo-start_default_judge_hi_phone-long.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · judge · hi |
| 02-demo-start_default_judge_hi_phone-long-annotated.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · judge · hi |
| 03-demo-start_default_judge_en_desktop.png | First viewport, clean | 1280 x 800 @1x | top | default · judge · en |
| 03-demo-start_default_judge_en_desktop-annotated.png | Same, with numbered boxes E1, E2, E3… | 1280 x 800 @1x | top | default · judge · en |
| 03-demo-start_default_judge_en_desktop-s01.png | Scroll slice (80 px overlap) | 1280 x 800 @1x | 0 px | default · judge · en |
| 03-demo-start_default_judge_en_desktop-s02.png | Scroll slice (80 px overlap) | 1280 x 800 @1x | 496 px | default · judge · en |
| 03-demo-start_default_judge_en_desktop-long.png | Stitched long image (fixed header and bottom bar kept once) | 1280 x 800 @1x | full page | default · judge · en |
| 03-demo-start_default_judge_en_desktop-long-annotated.png | Long image with numbered boxes | 1280 x 800 @1x | full page | default · judge · en |
| demo-start-sheet.png | Contact sheet of the main states | — | — | all |

## 3. Layout

Top to bottom in the first state ("default"), by region, with the numbered elements in each:

- **header**: E1 to E5 (5 elements)
- **demo bar**: E6 to E10 (5 elements)
- **main**: E11 to E15 (5 elements)
- **bottom bar**: E16 to E20 (5 elements)
- The page scrolls inside one container: 502 px visible of 766 px (the header and bottom bar stay fixed).

## 4. Elements

Position is the box's top-left as a share of the viewport, then its size in CSS pixels. Style is the font size / weight, text colour, background, radius; a design token name in brackets means the value matches that token.

### State "default" · judge · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | Online Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | element | Demo step 1 of 11 | demo bar | 3.1%, 13.4% · 135 x 21 | 15.75px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 220, 196) (--warn-container); radius 0px | Shows text or a value. |
| E7 | button | Back [disabled] | demo bar | 3.1%, 19.3% · 71 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Goes to the previous demo step. |
| E8 | button | Next | demo bar | 22.2%, 19.3% · 71 x 44 | 18px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Goes to the next demo step, as the right role. |
| E9 | link | Judge guide for this step | demo bar | 3.1%, 25% · 231 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Opens the judge guide's question for this step. |
| E10 | button | Reset demo | demo bar | 63.2%, 25% · 128 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Resets the demo: clears this session's server rows and this phone's demo class. |
| E11 | heading | Demo flow | main | 4.1%, 34.6% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E12 | element | Demo: made-up class 3A, 20 simulated children, no real child | main | 4.1%, 41% · 358 x 54 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E13 | heading | Step 1: start | main | 4.1%, 54% · 358 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E14 | button | Start as a teacher | main | 4.1%, 71.7% · 358 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Starts the demo as a teacher. |
| E15 | button | Make a different class (seed 2026 now) | main | 4.1%, 78.9% · 358 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to make a different class (seed 2026 now). |
| E16 | link | Judge | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/judge. |
| E17 | link | Demo flow [current] | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/demo. |
| E18 | link | Home | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E19 | link | Enter check | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E20 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

### State "default" · judge · hi · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | कोहॉर्ट कोच | header | 4.1%, 0.9% · 140 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | सहायक | header | 4.1%, 6.6% · 112 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | ऑनलाइन अच्छा सिग्नल · 9.2 एमबीपीएस | header | 34.8%, 7.2% · 166 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | अच्छा सिग्नल · 9.2 एमबीपीएस | header | 44.8%, 7.8% · 114 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | element | डेमो चरण 1 / 11 | demo bar | 3.1%, 13.4% · 112 x 21 | 15.75px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 220, 196) (--warn-container); radius 0px | Shows text or a value. |
| E7 | button | पीछे [disabled] | demo bar | 3.1%, 19.3% · 64 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Goes to the previous demo step. |
| E8 | button | आगे | demo bar | 20.5%, 19.3% · 65 x 44 | 18px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Goes to the next demo step, as the right role. |
| E9 | link | इस चरण के लिए जज गाइड | demo bar | 38.1%, 19.3% · 225 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Opens the judge guide's question for this step. |
| E10 | button | डेमो दोबारा शुरू करें | demo bar | 3.1%, 25% · 180 x 44 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Resets the demo: clears this session's server rows and this phone's demo class. |
| E11 | heading | डेमो | main | 4.1%, 34.6% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E12 | element | डेमो: बनाई हुई कक्षा 3A, 20 सिम्युलेटेड बच्चे, कोई असली बच्चा नहीं | main | 4.1%, 41% · 358 x 54 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E13 | heading | चरण 1: शुरुआत | main | 4.1%, 54% · 358 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E14 | button | शिक्षक के रूप में शुरू करें | main | 4.1%, 74.6% · 358 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Starts the demo as a teacher. |
| E15 | button | दूसरी कक्षा बनाएँ (अभी सीड 2026) | main | 4.1%, 81.7% · 358 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to दूसरी कक्षा बनाएँ (अभी सीड 2026). |
| E16 | link | जज | bottom bar | 0%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/judge. |
| E17 | link | डेमो [current] | bottom bar | 20%, 93.1% · 78 x 58 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/demo. |
| E18 | link | होम | bottom bar | 40%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/home. |
| E19 | link | जाँच भरें | bottom bar | 60%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/check. |
| E20 | button | और [collapsed] | bottom bar | 80%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Button: tap to और. |

### State "default" · judge · en · desktop

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 9.4%, 1% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | button | Assistant | header | 64.8%, 1% · 129 x 44 | 19px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E3 | status | Online Good signal · 9.2 Mbps | header | 75.5%, 1.6% · 297 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E4 | image |  | header | 9.4%, 1.8% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E5 | link | Judge | side rail | 0.6%, 2% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/judge. |
| E6 | element | Good signal · 9.2 Mbps | header | 82.8%, 2.3% · 191 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E7 | button | Back [disabled] | demo bar | 57.5%, 8.6% · 73 x 44 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Goes to the previous demo step. |
| E8 | button | Next | demo bar | 63.5%, 8.6% · 73 x 44 | 19px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Goes to the next demo step, as the right role. |
| E9 | link | Judge guide for this step | demo bar | 69.5%, 8.6% · 241 x 44 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Opens the judge guide's question for this step. |
| E10 | button | Reset demo | demo bar | 88.7%, 8.6% · 133 x 44 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 999px (--r-pill) | Resets the demo: clears this session's server rows and this phone's demo class. |
| E11 | element | Demo step 1 of 11 | demo bar | 9.1%, 9.7% · 163 x 26 | 19px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 220, 196) (--warn-container); radius 0px | Shows text or a value. |
| E12 | link | Demo flow [current] | side rail | 0.6%, 12.5% · 87 x 100 | 16px / 700; rgb(0, 32, 31) (--on-pen-container); bg rgb(204, 232, 231) (--tonal); radius 16px (--s4) | Opens #/demo. |
| E13 | heading | Demo flow | main | 10.6%, 20.3% · 1112 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E14 | link | Home | side rail | 0.6%, 26% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/home. |
| E15 | element | Demo: made-up class 3A, 20 simulated children, no real child | main | 10.6%, 27% · 1112 x 32 | 16.15px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E16 | link | Enter check | side rail | 0.6%, 36.5% · 87 x 100 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/check. |
| E17 | heading | Step 1: start | main | 10.6%, 38% · 1112 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E18 | link | My class | side rail | 0.6%, 50% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/cards. |
| E19 | link | Practice | side rail | 0.6%, 60.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/practice. |
| E20 | button | Start as a teacher | main | 10.6%, 70.7% · 1112 x 48 | 19px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Starts the demo as a teacher. |
| E21 | link | My programme | side rail | 0.6%, 71% · 87 x 124 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/programme. |
| E22 | button | Make a different class (seed 2026 now) | main | 10.6%, 78.2% · 1112 x 48 | 19px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to make a different class (seed 2026 now). |
| E23 | link | History | side rail | 0.6%, 87.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/history. |
| E24 | link | Coach | side rail | 0.6%, 98% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/coach. |
| E25 | link | Review | side rail | 0.6%, 46.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/review. |
| E26 | link | Papers | side rail | 0.6%, 57% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/papers. |
| E27 | link | Cohort | side rail | 0.6%, 67.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/cohort. |
| E28 | link | Admin | side rail | 0.6%, 78% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/admin. |
| E29 | link | My profile | side rail | 0.6%, 88.5% · 87 x 76 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Opens #/profile. |

## 5. Content and data

The orange demo bar (Demo step n of 11, Back, Next, judge guide, Reset demo) is on every screen. Step 1 explains the demo and has one button, "Start as a teacher".

The text on screen, copied exactly from the page in the first state:

```text
Demo flow

Demo: made-up class 3A, 20 simulated children, no real child

Step 1: start

You are a Grade 3 teacher. Your class 3A has 20 children. Everything in this demo is made up and labelled: no real child, school or teacher.

Real AI calls where the product makes them: reading sheet 1, the lesson draft, the cohort chat.
Every made-up sheet, class and number says Demo or Simulated.
Reset demo (in the bar above) starts again with a fresh class.
Start as a teacher
Make a different class (seed 2026 now)
```

Dynamic parts: counts, dates, names of the demo class and every number come from the demo class loaded in Judge mode or from the 12-step demo session; the code computes them.

## 6. States and transitions

- **default**: open the route.
- Empty, loading, error and offline states were not captured in this pack (core scope). The loaders and messages are listed in the product's own strings (`strings/en.json`).

## 7. What works and what to change

Measured from the numbered elements (touch targets, font sizes, sideways scroll, labels). There is no current UI audit of this app: `docs/design/audit/AUDIT.md` describes the original front end before the re-skin, so it is not used here.

- 6 distinct font sizes among the numbered elements in default, en, phone: 15.3px, 15.75px, 16px, 18px, 20px, 24px.

## 8. Constraints

- Phone first at 390 px; desktop for coach, officer, judge and mentor screens.
- Touch targets at least 44 px, primary buttons 48 px.
- English, Hindi and Tamil text must fit without cutting.
- Use the tokens in `../00-tokens.md`: Material 3, Calm Institutional palette (teal primary), no new colours.
- Teacher-facing numbers are counts, never percentages. Simulated data stays labelled.
- No new features: redesign what exists.
