# 02 · Home

_Written for Stitch: what this screen is, what each part does, and what to keep. Tables are generated from the live page; the purpose and behaviour lines are written from the component source._

## 1. Screen

- **Route:** `#/home`
- **Roles shown:** teacher
- **Languages captured:** en, hi
- **Inventory id:** T1
- **When a user sees it:** A teacher opens the app. It is her landing screen with a class loaded.
- **What they are trying to do:** See where the term stands and take the one next action.
- **Source:** apps/pwa/src/screens/Home.tsx
- **Data:** simulated demo data (judge mode, recorded AI answers). Every capture of data was checked for a Demo or Simulated label.

## 2. Images

| File | What it shows | Viewport | Scroll | State |
| --- | --- | --- | --- | --- |
| 01-home_default_teacher_en_phone.png | First viewport, clean | 390 x 844 @2x | top | default · teacher · en |
| 01-home_default_teacher_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | default · teacher · en |
| 01-home_default_teacher_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | default · teacher · en |
| 01-home_default_teacher_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 50 px | default · teacher · en |
| 01-home_default_teacher_en_phone-long.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · teacher · en |
| 01-home_default_teacher_en_phone-long-annotated.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · teacher · en |
| 02-home_default_teacher_hi_phone.png | First viewport, clean | 390 x 844 @2x | top | default · teacher · hi |
| 02-home_default_teacher_hi_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | default · teacher · hi |
| 02-home_default_teacher_hi_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | default · teacher · hi |
| 02-home_default_teacher_hi_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 26 px | default · teacher · hi |
| 02-home_default_teacher_hi_phone-long.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · teacher · hi |
| 02-home_default_teacher_hi_phone-long-annotated.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · teacher · hi |
| home-sheet.png | Contact sheet of the main states | — | — | all |

## 3. Layout

Top to bottom in the first state ("default"), by region, with the numbered elements in each:

- **header**: E1 to E5 (5 elements)
- **main**: E6 to E14 (9 elements)
- **bottom bar**: E15 to E19 (5 elements)
- The page scrolls inside one container: 653 px visible of 703 px (the header and bottom bar stay fixed).

## 4. Elements

Position is the box's top-left as a share of the viewport, then its size in CSS pixels. Style is the font size / weight, text colour, background, radius; a design token name in brackets means the value matches that token.

### State "default" · teacher · en · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | Cohort Coach | header | 4.1%, 0.9% · 168 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | Assistant | header | 4.1%, 6.6% · 125 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | 1 result waiting to send Good signal · 9.2 Mbps | header | 38.2%, 7.2% · 137 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | Good signal · 9.2 Mbps | header | 48.2%, 7.8% · 85 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | heading | Home | main | 4.1%, 14.8% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E7 | element | You checked 28 children this term. | main | 4.1%, 33.1% · 358 x 27 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E8 | link | See what my class gets wrong | main | 4.1%, 45.5% · 358 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | The one next action for her term. |
| E9 | link | Practice with the children | main | 4.1%, 53.1% · 173 x 116 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Opens the Practice Class. |
| E10 | link | My programme | main | 51.5%, 53.1% · 173 x 116 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Opens My programme. |
| E11 | link | What I entered | main | 4.1%, 68.2% · 173 x 96 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Opens What I entered. |
| E12 | link | Watch a rehearsal | main | 51.5%, 68.2% · 173 x 96 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Opens #/watch. |
| E13 | link | Chat steps | main | 4.1%, 81% · 173 x 96 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Opens #/flow. |
| E14 | link | My profile | main | 51.5%, 81% · 173 x 96 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Opens My profile. |
| E15 | link | Home [current] | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E16 | link | Enter check | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E17 | link | My class | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to What my class gets wrong. |
| E18 | link | Practice | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the Practice Class. |
| E19 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

### State "default" · teacher · hi · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | कोहॉर्ट कोच | header | 4.1%, 0.9% · 140 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | सहायक | header | 4.1%, 6.6% · 112 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | ऑनलाइन अच्छा सिग्नल · 9.2 एमबीपीएस | header | 34.8%, 7.2% · 166 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | अच्छा सिग्नल · 9.2 एमबीपीएस | header | 44.8%, 7.8% · 114 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | heading | होम | main | 4.1%, 14.8% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E7 | element | आपने इस सत्र में 28 बच्चों की जाँच की। | main | 4.1%, 33.1% · 358 x 27 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E8 | link | देखें मेरी कक्षा कहाँ गलती करती है | main | 4.1%, 45.5% · 358 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | The one next action for her term. |
| E9 | link | बच्चों के साथ अभ्यास करें | main | 4.1%, 53.1% · 173 x 116 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Opens the Practice Class. |
| E10 | link | मेरा कार्यक्रम | main | 51.5%, 53.1% · 173 x 116 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Opens My programme. |
| E11 | link | मैंने क्या भरा | main | 4.1%, 68.2% · 173 x 96 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Opens What I entered. |
| E12 | link | एक अभ्यास देखें | main | 51.5%, 68.2% · 173 x 96 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Opens #/watch. |
| E13 | link | चरण-दर-चरण | main | 4.1%, 81% · 173 x 96 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Opens #/flow. |
| E14 | link | मेरी प्रोफ़ाइल | main | 51.5%, 81% · 173 x 96 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 16px (--s4) | Opens My profile. |
| E15 | link | होम [current] | bottom bar | 0%, 93.1% · 78 x 58 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/home. |
| E16 | link | जाँच भरें | bottom bar | 20%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/check. |
| E17 | link | मेरी कक्षा | bottom bar | 40%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/cards. |
| E18 | link | अभ्यास | bottom bar | 60%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/practice. |
| E19 | button | और [collapsed] | bottom bar | 80%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Button: tap to और. |

## 5. Content and data

Shows the term status and one main action button (the next step: start a check, see her track, practise). Links below go to history, profile, programme, the practice class and the sample rehearsal watch. A privacy prompt appears until she has chosen her consents.

The text on screen, copied exactly from the page in the first state:

```text
Home

Term 1

Simulated data: this class and these children are made up for the demo.

You checked 28 children this term.

Your class's focus: Takes the smaller digit from the larger.

See what my class gets wrong
Practice with the children
My programme
What I entered
Watch a rehearsal
Chat steps
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
