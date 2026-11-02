# 01 · Landing page and role picker

_Written for Stitch: what this screen is, what each part does, and what to keep. Tables are generated from the live page; the purpose and behaviour lines are written from the component source._

## 1. Screen

- **Route:** `#/roles`
- **Roles shown:** judge
- **Languages captured:** en, hi
- **Inventory id:** X1
- **When a user sees it:** The first screen a judge or teacher opens. No role is chosen yet and there is no bottom bar.
- **What they are trying to do:** Choose a role (Teacher, Mentor, Coach, Programme officer), read what that role can and cannot do, or start the guided tour.
- **Source:** apps/pwa/src/screens/Landing.tsx

## 2. Images

| File | What it shows | Viewport | Scroll | State |
| --- | --- | --- | --- | --- |
| 01-landing_default_judge_en_phone.png | First viewport, clean | 390 x 844 @2x | top | default · judge · en |
| 01-landing_default_judge_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | default · judge · en |
| 01-landing_default_judge_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | default · judge · en |
| 01-landing_default_judge_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 558 px | default · judge · en |
| 01-landing_default_judge_en_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 639 px | default · judge · en |
| 01-landing_default_judge_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · judge · en |
| 01-landing_default_judge_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · judge · en |
| 01-landing_default_judge_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · judge · en |
| 01-landing_default_judge_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · judge · en |
| 02-landing_scope-dialog_judge_en_phone.png | First viewport, clean | 390 x 844 @2x | top | scope-dialog · judge · en |
| 02-landing_scope-dialog_judge_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | scope-dialog · judge · en |
| 02-landing_scope-dialog_judge_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | scope-dialog · judge · en |
| 02-landing_scope-dialog_judge_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 558 px | scope-dialog · judge · en |
| 02-landing_scope-dialog_judge_en_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 875 px | scope-dialog · judge · en |
| 02-landing_scope-dialog_judge_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | scope-dialog · judge · en |
| 02-landing_scope-dialog_judge_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | scope-dialog · judge · en |
| 02-landing_scope-dialog_judge_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | scope-dialog · judge · en |
| 02-landing_scope-dialog_judge_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | scope-dialog · judge · en |
| 03-landing_default_judge_hi_phone.png | First viewport, clean | 390 x 844 @2x | top | default · judge · hi |
| 03-landing_default_judge_hi_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | default · judge · hi |
| 03-landing_default_judge_hi_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | default · judge · hi |
| 03-landing_default_judge_hi_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 558 px | default · judge · hi |
| 03-landing_default_judge_hi_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 591 px | default · judge · hi |
| 03-landing_default_judge_hi_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · judge · hi |
| 03-landing_default_judge_hi_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · judge · hi |
| 03-landing_default_judge_hi_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · judge · hi |
| 03-landing_default_judge_hi_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · judge · hi |
| 04-landing_default_judge_en_desktop.png | First viewport, clean | 1280 x 800 @1x | top | default · judge · en |
| 04-landing_default_judge_en_desktop-annotated.png | Same, with numbered boxes E1, E2, E3… | 1280 x 800 @1x | top | default · judge · en |
| 04-landing_default_judge_en_desktop-s01.png | Scroll slice (80 px overlap) | 1280 x 800 @1x | 0 px | default · judge · en |
| 04-landing_default_judge_en_desktop-s02.png | Scroll slice (80 px overlap) | 1280 x 800 @1x | 21 px | default · judge · en |
| 04-landing_default_judge_en_desktop-long.png | Stitched long image (fixed header and bottom bar kept once) | 1280 x 800 @1x | full page | default · judge · en |
| 04-landing_default_judge_en_desktop-long-annotated.png | Long image with numbered boxes | 1280 x 800 @1x | full page | default · judge · en |
| landing-sheet.png | Contact sheet of the main states | — | — | all |

## 3. Layout

Top to bottom in the first state ("default"), by region, with the numbered elements in each:

- **header**: E1 to E5 (5 elements)
- **language strip**: E6 to E9 (4 elements)
- **main**: E10 to E16 (7 elements)
- The page scrolls inside one container: 638 px visible of 1277 px (the header and bottom bar stay fixed).

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
| E6 | button | About Role [collapsed] | language strip | 9.2%, 13.2% · 44 x 44 | 13.3333px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 999px (--r-pill) | Button: tap to about role. |
| E7 | button | About Language [collapsed] | language strip | 67.2%, 13.2% · 44 x 44 | 13.3333px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 999px (--r-pill) | Button: tap to about language. |
| E8 | combobox | Judge Teacher Mentor Coach Officer Admin | language strip | 3.1%, 17.7% · 179 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Dropdown: she chooses one value. |
| E9 | combobox | English हिन्दी தமிழ் | language strip | 51%, 17.7% · 179 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Dropdown: she chooses one value. |
| E10 | heading | Who are you today? | main | 4.1%, 26.8% · 358 x 36 | 28px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E11 | link | Guided tour (5 min) Start here if you're judging | main | 4.1%, 52.1% · 358 x 96 | 18px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 16px (--s4) | Opens #/tour/1. |
| E12 | button | Teacher A Grade 3 teacher Check your class, rehearse the fix, follow a | main | 4.1%, 64.9% · 358 x 134 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Button: tap to teacher a grade 3 teacher check your class, rehearse the fix, follow a 3-week track. |
| E13 | button | Mentor A teacher whose class fixed the same error Record how your clas | main | 4.1%, 82.2% · 358 x 182 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Button: tap to mentor a teacher whose class fixed the same error record how your class fixed an error, so the next cohort can learn it. |
| E14 | button | Coach A BRC, CRC, DIET faculty member or head teacher Approve recordin | main | 4.1%, 39.1% · 358 x 182 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Button: tap to coach a brc, crc, diet faculty member or head teacher approve recordings and lessons, and keep the cohort chat safe. |
| E15 | button | Officer Block or district programme staff Approve cohorts and read res | main | 4.1%, 62.1% · 358 x 158 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Button: tap to officer block or district programme staff approve cohorts and read results across the block. |
| E16 | button | How to install | main | 8.5%, 94.8% · 324 x 48 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(204, 232, 231) (--tonal); radius 8px (--s2) | Button: tap to how to install. |

### State "scope-dialog" · judge · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | Online Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | button | About Role [collapsed] | language strip | 9.2%, 13.2% · 44 x 44 | 13.3333px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 999px (--r-pill) | Button: tap to about role. |
| E7 | button | About Language [collapsed] | language strip | 67.2%, 13.2% · 44 x 44 | 13.3333px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 999px (--r-pill) | Button: tap to about language. |
| E8 | combobox | Judge Teacher Mentor Coach Officer Admin | language strip | 3.1%, 17.7% · 179 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Dropdown: she chooses one value. |
| E9 | combobox | English हिन्दी தமிழ் | language strip | 51%, 17.7% · 179 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Dropdown: she chooses one value. |
| E10 | heading | Who are you today? | main | 4.1%, 26.8% · 358 x 36 | 28px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E11 | dialog | Teacher A Grade 3 teacher You can Ask the assistant for help (read-onl | dialog | 4.1%, 52.1% · 358 x 1215 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Shows text or a value. |
| E12 | heading | Teacher | dialog | 8.5%, 55.1% · 324 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E13 | heading | You can | dialog | 8.5%, 64.3% · 324 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E14 | heading | You can't | dialog | 8.5%, 54.9% · 324 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E15 | heading | Data you'll see | dialog | 8.5%, 82.9% · 324 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E16 | button | Enter dashboard | dialog | 8.5%, 67.7% · 324 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Button: tap to enter dashboard. |
| E17 | button | 60-second walk-through | dialog | 8.5%, 74.8% · 324 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to 60-second walk-through. |
| E18 | button | Back | dialog | 8.5%, 81.9% · 324 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to back. |

### State "default" · judge · hi · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | कोहॉर्ट कोच | header | 4.1%, 0.9% · 140 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | सहायक | header | 4.1%, 6.6% · 112 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | ऑनलाइन अच्छा सिग्नल · 9.2 एमबीपीएस | header | 34.8%, 7.2% · 166 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | अच्छा सिग्नल · 9.2 एमबीपीएस | header | 44.8%, 7.8% · 114 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | button | भूमिका के बारे में [collapsed] | language strip | 13.5%, 13.2% · 44 x 44 | 13.3333px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 999px (--r-pill) | Button: tap to भूमिका के बारे में. |
| E7 | button | भाषा के बारे में [collapsed] | language strip | 57.5%, 13.2% · 44 x 44 | 13.3333px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 999px (--r-pill) | Button: tap to भाषा के बारे में. |
| E8 | combobox | जज शिक्षक मेंटर कोच अधिकारी एडमिन | language strip | 3.1%, 17.7% · 179 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Dropdown: she chooses one value. |
| E9 | combobox | English हिन्दी தமிழ் | language strip | 51%, 17.7% · 179 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Dropdown: she chooses one value. |
| E10 | heading | आज आप कौन हैं? | main | 4.1%, 26.8% · 358 x 36 | 28px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E11 | link | गाइडेड टूर (5 मिनट) जज हैं तो यहाँ से शुरू करें | main | 4.1%, 52.1% · 358 x 96 | 18px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 16px (--s4) | Opens #/tour/1. |
| E12 | button | शिक्षक कक्षा 3 की शिक्षिका या शिक्षक अपनी कक्षा की जाँच करें, उपाय का  | main | 4.1%, 64.9% · 358 x 134 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Button: tap to शिक्षक कक्षा 3 की शिक्षिका या शिक्षक अपनी कक्षा की जाँच करें, उपाय का अभ्यास करें, 3 हफ़्ते का ट्रैक चलाएँ।. |
| E13 | button | मेंटर वह शिक्षक जिसकी कक्षा ने वही गलती सुधारी रिकॉर्ड करें कि आपकी कक | main | 4.1%, 82.2% · 358 x 182 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Button: tap to मेंटर वह शिक्षक जिसकी कक्षा ने वही गलती सुधारी रिकॉर्ड करें कि आपकी कक्षा ने गलती कैसे सुधारी, ताकि अगला समूह सीख सके।. |
| E14 | button | कोच बीआरसी, सीआरसी, डाइट संकाय सदस्य या प्रधानाध्यापक रिकॉर्डिंग और पा | main | 4.1%, 39.1% · 358 x 158 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Button: tap to कोच बीआरसी, सीआरसी, डाइट संकाय सदस्य या प्रधानाध्यापक रिकॉर्डिंग और पाठ मंज़ूर करें, और समूह की चैट सुरक्षित रखें।. |
| E15 | button | अधिकारी ब्लॉक या ज़िला कार्यक्रम कर्मी समूह मंज़ूर करें और पूरे ब्लॉक  | main | 4.1%, 59.2% · 358 x 134 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Button: tap to अधिकारी ब्लॉक या ज़िला कार्यक्रम कर्मी समूह मंज़ूर करें और पूरे ब्लॉक के नतीजे देखें।. |
| E16 | button | कैसे इंस्टॉल करें | main | 8.5%, 89.1% · 324 x 48 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(204, 232, 231) (--tonal); radius 8px (--s2) | Button: tap to कैसे इंस्टॉल करें. |

### State "default" · judge · en · desktop

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 1.3%, 1% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | button | Assistant | header | 64.8%, 1% · 129 x 44 | 19px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E3 | status | Online Good signal · 9.2 Mbps | header | 75.5%, 1.6% · 297 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E4 | image |  | header | 1.3%, 1.8% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E5 | element | Good signal · 9.2 Mbps | header | 82.8%, 2.3% · 191 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | button | About Role [collapsed] | language strip | 2.8%, 7.9% · 44 x 44 | 13.3333px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 999px (--r-pill) | Button: tap to about role. |
| E7 | button | About Language [collapsed] | language strip | 55.2%, 7.9% · 44 x 44 | 13.3333px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 999px (--r-pill) | Button: tap to about language. |
| E8 | combobox | Judge Teacher Mentor Coach Officer Admin | language strip | 0.9%, 12.6% · 624 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Dropdown: she chooses one value. |
| E9 | combobox | English हिन्दी தமிழ் | language strip | 50.3%, 12.6% · 624 x 48 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Dropdown: she chooses one value. |
| E10 | heading | Who are you today? | main | 2.5%, 23.3% · 1216 x 36 | 28px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E11 | link | Guided tour (5 min) Start here if you're judging | main | 2.5%, 40.8% · 1216 x 96 | 19px / 400; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 16px (--s4) | Opens #/tour/1. |
| E12 | button | Teacher A Grade 3 teacher Check your class, rehearse the fix, follow a | main | 2.5%, 54.3% · 295 x 218 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Button: tap to teacher a grade 3 teacher check your class, rehearse the fix, follow a 3-week track. |
| E13 | button | Mentor A teacher whose class fixed the same error Record how your clas | main | 26.5%, 54.3% · 295 x 218 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Button: tap to mentor a teacher whose class fixed the same error record how your class fixed an error, so the next cohort can learn it. |
| E14 | button | Coach A BRC, CRC, DIET faculty member or head teacher Approve recordin | main | 50.5%, 54.3% · 295 x 218 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Button: tap to coach a brc, crc, diet faculty member or head teacher approve recordings and lessons, and keep the cohort chat safe. |
| E15 | button | Officer Block or district programme staff Approve cohorts and read res | main | 74.5%, 54.3% · 295 x 218 | 19px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Button: tap to officer block or district programme staff approve cohorts and read results across the block. |
| E16 | button | How to install | main | 83.1%, 85.6% · 167 x 48 | 19px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(204, 232, 231) (--tonal); radius 8px (--s2) | Button: tap to how to install. |

## 5. Content and data

Each role card opens a dialog that says what the role can do, cannot do, which data it sees and which other roles exist. "Enter" goes to that role's home. The tour card starts the 5-minute guided tour. Language and mode are chosen above the cards.

The text on screen, copied exactly from the page in the first state:

```text
Who are you today?

Pick a role to see what it can and cannot do. Everything here is simulated data.

Mode: Judge demo
Role now: Teacher
Guided tour (5 min)
Start here if you're judging
Teacher
A Grade 3 teacher
Check your class, rehearse the fix, follow a 3-week track.
Mentor
A teacher whose class fixed the same error
Record how your class fixed an error, so the next cohort can learn it.
Coach
A BRC, CRC, DIET faculty member or head teacher
Approve recordings and lessons, and keep the cohort chat safe.
Officer
Block or district programme staff
Approve cohorts and read results across the block.
Keep the app on your phone
Opens fast, uses little data, and works without signal.
How to install
```

Dynamic parts: counts, dates, names of the demo class and every number come from the demo class loaded in Judge mode or from the 12-step demo session; the code computes them.

## 6. States and transitions

- **default**: open the route.
- **scope-dialog**: tap css:[data-testid=role-cards] button, then wait for role-dialog.
- Empty, loading, error and offline states were not captured in this pack (core scope). The loaders and messages are listed in the product's own strings (`strings/en.json`).

## 7. What works and what to change

Measured from the numbered elements (touch targets, font sizes, sideways scroll, labels). There is no current UI audit of this app: `docs/design/audit/AUDIT.md` describes the original front end before the re-skin, so it is not used here.

- 6 distinct font sizes among the numbered elements in scope-dialog, en, phone: 13.3333px, 16px, 18px, 20px, 21.06px, 28px.

## 8. Constraints

- Phone first at 390 px; desktop for coach, officer, judge and mentor screens.
- Touch targets at least 44 px, primary buttons 48 px.
- English, Hindi and Tamil text must fit without cutting.
- Use the tokens in `../00-tokens.md`: Material 3, Calm Institutional palette (teal primary), no new colours.
- Teacher-facing numbers are counts, never percentages. Simulated data stays labelled.
- No new features: redesign what exists.
