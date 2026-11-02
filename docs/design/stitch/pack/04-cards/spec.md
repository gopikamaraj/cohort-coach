# 04 · What my class gets wrong

_Written for Stitch: what this screen is, what each part does, and what to keep. Tables are generated from the live page; the purpose and behaviour lines are written from the component source._

## 1. Screen

- **Route:** `#/cards`
- **Roles shown:** teacher
- **Languages captured:** en, hi
- **Inventory id:** T3
- **When a user sees it:** After a check is entered.
- **What they are trying to do:** See the errors her class made, as counts of children, with an example and a focus tag.
- **Source:** apps/pwa/src/screens/Cards.tsx
- **Data:** simulated demo data (judge mode, recorded AI answers). Every capture of data was checked for a Demo or Simulated label.

## 2. Images

| File | What it shows | Viewport | Scroll | State |
| --- | --- | --- | --- | --- |
| 01-cards_default_teacher_en_phone.png | First viewport, clean | 390 x 844 @2x | top | default · teacher · en |
| 01-cards_default_teacher_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | default · teacher · en |
| 01-cards_default_teacher_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | default · teacher · en |
| 01-cards_default_teacher_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 573 px | default · teacher · en |
| 01-cards_default_teacher_en_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1146 px | default · teacher · en |
| 01-cards_default_teacher_en_phone-s04.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1293 px | default · teacher · en |
| 01-cards_default_teacher_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · teacher · en |
| 01-cards_default_teacher_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · teacher · en |
| 01-cards_default_teacher_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · teacher · en |
| 01-cards_default_teacher_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · teacher · en |
| 02-cards_default_teacher_hi_phone.png | First viewport, clean | 390 x 844 @2x | top | default · teacher · hi |
| 02-cards_default_teacher_hi_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | default · teacher · hi |
| 02-cards_default_teacher_hi_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | default · teacher · hi |
| 02-cards_default_teacher_hi_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 597 px | default · teacher · hi |
| 02-cards_default_teacher_hi_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1194 px | default · teacher · hi |
| 02-cards_default_teacher_hi_phone-s04.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1215 px | default · teacher · hi |
| 02-cards_default_teacher_hi_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · teacher · hi |
| 02-cards_default_teacher_hi_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · teacher · hi |
| 02-cards_default_teacher_hi_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · teacher · hi |
| 02-cards_default_teacher_hi_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · teacher · hi |
| cards-sheet.png | Contact sheet of the main states | — | — | all |

## 3. Layout

Top to bottom in the first state ("default"), by region, with the numbered elements in each:

- **header**: E1 to E5 (5 elements)
- **main**: E6 to E31 (26 elements)
- **bottom bar**: E32 to E36 (5 elements)
- The page scrolls inside one container: 653 px visible of 1946 px (the header and bottom bar stay fixed).

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
| E6 | heading | What my class gets wrong | main | 4.1%, 14.8% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E7 | element | Pre-test · Form A · Class 3B (simulated) · 31 Oct 2026 | main | 4.1%, 28.8% · 358 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E8 | heading | Takes the smaller digit from the larger | main | 9.2%, 42.4% · 321 x 50 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E9 | img | 11 of 28 children take the smaller digit from the larger. | main | 9.2%, 55.3% · 278 x 26 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E10 | element | 11 of 28 children take the smaller digit from the larger. | main | 9.2%, 59.4% · 321 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E11 | button | Listen | main | 9.2%, 76.4% · 156 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to listen. |
| E12 | button | This is wrong | main | 51.4%, 76.4% · 156 x 48 | 18px / 600; rgb(179, 38, 30) (--margin); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to this is wrong. |
| E13 | heading | Forgets the carried ten | main | 8.5%, 88.5% · 324 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E14 | img | 5 of 28 children forget the carried ten. | main | 8.5%, 30.6% · 278 x 26 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E15 | element | 5 of 28 children forget the carried ten. | main | 8.5%, 34.6% · 324 x 27 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E16 | button | Listen | main | 8.5%, 43.8% · 158 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to listen. |
| E17 | button | This is wrong | main | 51%, 43.8% · 158 x 48 | 18px / 600; rgb(179, 38, 30) (--margin); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to this is wrong. |
| E18 | heading | Borrows a ten but does not reduce the tens digit | main | 8.5%, 55.9% · 324 x 50 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E19 | img | 3 of 28 children borrow a ten but do not reduce the tens digit. | main | 8.5%, 68.8% · 278 x 26 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E20 | element | 3 of 28 children borrow a ten but do not reduce the tens digit. | main | 8.5%, 72.9% · 324 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E21 | button | Listen | main | 8.5%, 85.3% · 158 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to listen. |
| E22 | button | This is wrong | main | 51%, 85.3% · 158 x 48 | 18px / 600; rgb(179, 38, 30) (--margin); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to this is wrong. |
| E23 | heading | Writes a number the way it is said | main | 8.5%, 29.5% · 324 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E24 | img | 2 of 28 children write a number the way they hear it. | main | 8.5%, 39.5% · 278 x 26 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E25 | element | 2 of 28 children write a number the way they hear it. | main | 8.5%, 43.5% · 324 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E26 | button | Listen | main | 8.5%, 55.9% · 158 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to listen. |
| E27 | button | This is wrong | main | 51%, 55.9% · 158 x 48 | 18px / 600; rgb(179, 38, 30) (--margin); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to this is wrong. |
| E28 | element | 2 answers also had the whole ones total written in, like 28 + 36 → 514 | main | 4.1%, 66.5% · 358 x 81 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E29 | heading | Before and after | main | 4.1%, 71.6% · 358 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E30 | element | Demo data | main | 4.1%, 75.5% · 101 x 31 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E31 | element | Enter a pre-test and a post-test to see before and after. | main | 4.1%, 80.6% · 358 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E32 | link | Home | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E33 | link | Enter check | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E34 | link | My class [current] | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to What my class gets wrong. |
| E35 | link | Practice | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the Practice Class. |
| E36 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

### State "default" · teacher · hi · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | कोहॉर्ट कोच | header | 4.1%, 0.9% · 140 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | सहायक | header | 4.1%, 6.6% · 112 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | ऑनलाइन अच्छा सिग्नल · 9.2 एमबीपीएस | header | 34.8%, 7.2% · 166 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | अच्छा सिग्नल · 9.2 एमबीपीएस | header | 44.8%, 7.8% · 114 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | heading | मेरी कक्षा कहाँ गलती करती है | main | 4.1%, 14.8% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E7 | element | पूर्व-परीक्षा · फ़ॉर्म A · कक्षा 3B (नकली) · 31 अक्टू॰ 2026 | main | 4.1%, 28.8% · 358 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E8 | heading | छोटे अंक को बड़े में से घटाना | main | 9.2%, 42.4% · 321 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E9 | img | 28 में से 11 बच्चे हर स्तंभ में छोटे अंक को बड़े में से घटाते हैं। | main | 9.2%, 52.4% · 278 x 26 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E10 | element | 28 में से 11 बच्चे हर स्तंभ में छोटे अंक को बड़े में से घटाते हैं। | main | 9.2%, 56.4% · 321 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E11 | button | सुनें | main | 9.2%, 73.5% · 156 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to सुनें. |
| E12 | button | यह गलत है | main | 51.4%, 73.5% · 156 x 48 | 18px / 600; rgb(179, 38, 30) (--margin); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to यह गलत है. |
| E13 | heading | हासिल की दहाई भूल जाना | main | 8.5%, 85.5% · 324 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E14 | img | 28 में से 5 बच्चे हासिल की दहाई भूल जाते हैं। | main | 8.5%, 24.8% · 278 x 26 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E15 | element | 28 में से 5 बच्चे हासिल की दहाई भूल जाते हैं। | main | 8.5%, 28.8% · 324 x 27 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E16 | button | सुनें | main | 8.5%, 38% · 158 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to सुनें. |
| E17 | button | यह गलत है | main | 51%, 38% · 158 x 48 | 18px / 600; rgb(179, 38, 30) (--margin); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to यह गलत है. |
| E18 | heading | दहाई उधार लेकर दहाई का अंक कम न करना | main | 8.5%, 50.1% · 324 x 50 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E19 | img | 28 में से 3 बच्चे दहाई उधार लेते हैं पर दहाई का अंक कम नहीं करते। | main | 8.5%, 63% · 278 x 26 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E20 | element | 28 में से 3 बच्चे दहाई उधार लेते हैं पर दहाई का अंक कम नहीं करते। | main | 8.5%, 67.1% · 324 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E21 | button | सुनें | main | 8.5%, 79.5% · 158 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to सुनें. |
| E22 | button | यह गलत है | main | 51%, 79.5% · 158 x 48 | 18px / 600; rgb(179, 38, 30) (--margin); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to यह गलत है. |
| E23 | heading | संख्या को जैसे बोला जाता है वैसे लिखना | main | 8.5%, 20.9% · 324 x 50 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E24 | img | 28 में से 2 बच्चे संख्या को वैसे लिखते हैं जैसे सुनते हैं। | main | 8.5%, 33.8% · 278 x 26 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E25 | element | 28 में से 2 बच्चे संख्या को वैसे लिखते हैं जैसे सुनते हैं। | main | 8.5%, 37.8% · 324 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E26 | button | सुनें | main | 8.5%, 50.2% · 158 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to सुनें. |
| E27 | button | यह गलत है | main | 51%, 50.2% · 158 x 48 | 18px / 600; rgb(179, 38, 30) (--margin); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to यह गलत है. |
| E28 | element | 2 जवाबों में इकाई का पूरा जोड़ भी लिखा था, जैसे 28 + 36 → 514। यह अभी  | main | 4.1%, 60.8% · 358 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E29 | heading | पहले और बाद | main | 4.1%, 76.9% · 358 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E30 | element | डेमो डेटा | main | 4.1%, 80.8% · 81 x 31 | 15.3px / 600; rgb(25, 28, 28) (--ink); bg rgb(204, 232, 231) (--tonal); radius 999px (--r-pill) | Shows text or a value. |
| E31 | element | पहले और बाद देखने के लिए पूर्व-परीक्षा और उत्तर-परीक्षा दर्ज करें। | main | 4.1%, 85.9% · 358 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E32 | link | होम | bottom bar | 0%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/home. |
| E33 | link | जाँच भरें | bottom bar | 20%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/check. |
| E34 | link | मेरी कक्षा [current] | bottom bar | 40%, 93.1% · 78 x 58 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/cards. |
| E35 | link | अभ्यास | bottom bar | 60%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/practice. |
| E36 | button | और [collapsed] | bottom bar | 80%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Button: tap to और. |

## 5. Content and data

One card per error with how many children showed it, a worked example, a "simulated" label on demo data and a play button that reads the card aloud. Counts are shown as "11 of 28 children", never as percentages.

The text on screen, copied exactly from the page in the first state:

```text
What my class gets wrong

Simulated data: this class and these children are made up for the demo.

Pre-test · Form A · Class 3B (simulated) · 31 Oct 2026

28 children checked.

Takes the smaller digit from the larger

11 / 28

11 of 28 children take the smaller digit from the larger.

From your class: 74 − 36 → 42

This is the focus for your class.

Forgets the carried ten

5 / 28

5 of 28 children forget the carried ten.

From your class: 38 + 47 → 75

Borrows a ten but does not reduce the tens digit

3 / 28

3 of 28 children borrow a ten but do not reduce the tens digit.

From your class: 74 − 36 → 48

Writes a number the way it is said

2 / 28

2 of 28 children write a number the way they hear it.

From your class: 346 → 3046

2 answers also had the whole ones total written in, like 28 + 36 → 514. This is not a focus yet.

1 children got the simple subtraction (question 6) wrong, so read the subtraction cards with care.

Before and after

Demo data

Enter a pre-test and a post-test to see before and after.
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
