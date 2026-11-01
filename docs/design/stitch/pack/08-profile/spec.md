# 08 · My profile and data

_Written for Stitch: what this screen is, what each part does, and what to keep. Tables are generated from the live page; the purpose and behaviour lines are written from the component source._

## 1. Screen

- **Route:** `#/profile`
- **Roles shown:** teacher
- **Languages captured:** en, hi
- **Inventory id:** X16
- **When a user sees it:** A teacher manages her classes, language, consents and backup.
- **What they are trying to do:** Change language, add a class, back up her data, see how much data the app used, give feedback and withdraw consent.
- **Source:** apps/pwa/src/screens/Profile.tsx
- **Data:** simulated demo data (judge mode, recorded AI answers). Every capture of data was checked for a Demo or Simulated label.

## 2. Images

| File | What it shows | Viewport | Scroll | State |
| --- | --- | --- | --- | --- |
| 01-profile_default_teacher_en_phone.png | First viewport, clean | 390 x 844 @2x | top | default · teacher · en |
| 01-profile_default_teacher_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | default · teacher · en |
| 01-profile_default_teacher_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | default · teacher · en |
| 01-profile_default_teacher_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 573 px | default · teacher · en |
| 01-profile_default_teacher_en_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1146 px | default · teacher · en |
| 01-profile_default_teacher_en_phone-s04.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1719 px | default · teacher · en |
| 01-profile_default_teacher_en_phone-s05.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 2292 px | default · teacher · en |
| 01-profile_default_teacher_en_phone-s06.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 2681 px | default · teacher · en |
| 01-profile_default_teacher_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · teacher · en |
| 01-profile_default_teacher_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · teacher · en |
| 01-profile_default_teacher_en_phone-long-p3.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · teacher · en |
| 01-profile_default_teacher_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · teacher · en |
| 01-profile_default_teacher_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · teacher · en |
| 01-profile_default_teacher_en_phone-long-annotated-p3.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · teacher · en |
| 02-profile_default_teacher_hi_phone.png | First viewport, clean | 390 x 844 @2x | top | default · teacher · hi |
| 02-profile_default_teacher_hi_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | default · teacher · hi |
| 02-profile_default_teacher_hi_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | default · teacher · hi |
| 02-profile_default_teacher_hi_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 597 px | default · teacher · hi |
| 02-profile_default_teacher_hi_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1194 px | default · teacher · hi |
| 02-profile_default_teacher_hi_phone-s04.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1791 px | default · teacher · hi |
| 02-profile_default_teacher_hi_phone-s05.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 2388 px | default · teacher · hi |
| 02-profile_default_teacher_hi_phone-s06.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 2603 px | default · teacher · hi |
| 02-profile_default_teacher_hi_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · teacher · hi |
| 02-profile_default_teacher_hi_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · teacher · hi |
| 02-profile_default_teacher_hi_phone-long-p3.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · teacher · hi |
| 02-profile_default_teacher_hi_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · teacher · hi |
| 02-profile_default_teacher_hi_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · teacher · hi |
| 02-profile_default_teacher_hi_phone-long-annotated-p3.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · teacher · hi |
| profile-sheet.png | Contact sheet of the main states | — | — | all |

## 3. Layout

Top to bottom in the first state ("default"), by region, with the numbered elements in each:

- **header**: E1 to E5 (5 elements)
- **main**: E6 to E54 (49 elements)
- **bottom bar**: E55 to E59 (5 elements)
- The page scrolls inside one container: 653 px visible of 3334 px (the header and bottom bar stay fixed).

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
| E6 | heading | My profile | main | 4.1%, 14.8% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E7 | link | Change role | main | 34%, 19.8% · 96 x 44 | 18px / 400; rgb(0, 0, 238); bg rgb(247, 250, 250) (--paper); radius 0px | Opens #/roles. |
| E8 | label | Language English हिन्दी தமிழ் | main | 4.1%, 26.4% · 358 x 79 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E9 | combobox | Language English हिन्दी தமிழ் | main | 4.1%, 30.1% · 358 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Dropdown: she chooses one value. |
| E10 | button | How to install | main | 4.1%, 37.2% · 358 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to how to install. |
| E11 | heading | My classes | main | 8.5%, 44.9% · 324 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E12 | button | Rename | main | 61.8%, 50.8% · 56 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to rename. |
| E13 | button | Delete this class | main | 77.2%, 50.8% · 56 x 48 | 18px / 600; rgb(179, 38, 30) (--margin); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Button: tap to delete this class. |
| E14 | textbox | Class name | main | 8.5%, 58.6% · 26 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E15 | button | Add a class | main | 17.2%, 58.6% · 290 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Button: tap to add a class. |
| E16 | heading | Storage and backup | main | 8.5%, 80.2% · 324 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E17 | element | Your data is not protected yet: the browser may clear it when space ru | main | 8.5%, 84.1% · 324 x 82 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Shows text or a value. |
| E18 | button | Protect my data | main | 8.5%, 27.3% · 324 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to protect my data. |
| E19 | heading | Backup file | main | 8.5%, 41.2% · 324 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E20 | label | Passphrase (optional, needed again to restore) | main | 8.5%, 60.2% · 324 x 106 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Label for the field next to it. |
| E21 | textbox | Passphrase (optional, needed again to restore) | main | 8.5%, 67.1% · 324 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E22 | button | Save a backup | main | 8.5%, 74.2% · 158 x 72 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Button: tap to save a backup. |
| E23 | button | Restore from a file | main | 51%, 74.2% · 158 x 72 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to restore from a file. |
| E24 | heading | Data used | main | 8.5%, 22.2% · 324 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E25 | element | 1.2 KB | main | 10.5%, 29.9% · 87 x 30 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E26 | element | 56 KB | main | 38.9%, 29.9% · 87 x 30 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E27 | element | 57 KB | main | 67.3%, 29.9% · 87 x 30 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E28 | label | What 1 GB of data costs you (optional) | main | 8.5%, 40.1% · 324 x 79 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Label for the field next to it. |
| E29 | textbox | What 1 GB of data costs you (optional) | main | 8.5%, 43.7% · 324 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E30 | button | Clear the count | main | 8.5%, 50.8% · 324 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to clear the count. |
| E31 | heading | Privacy | main | 8.5%, 72.4% · 324 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E32 | label | Send my class counts How many children show each error, for grouping t | main | 8.5%, 20.4% · 324 x 99 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Label for the field next to it. |
| E33 | checkbox | Send my class counts How many children show each error, for grouping t [checked] | main | 9.5%, 20.6% · 28 x 28 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 0px | Tick box: turns an option on or off. |
| E34 | label | Use AI in the Practice Class What you type or say there goes to AI ser | main | 8.5%, 34.1% · 324 x 147 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Label for the field next to it. |
| E35 | checkbox | Use AI in the Practice Class What you type or say there goes to AI ser [checked] | main | 9.5%, 34.4% · 28 x 28 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 0px | Tick box: turns an option on or off. |
| E36 | label | Share my rehearsals to improve the simulator Off by default. Without t | main | 8.5%, 53.6% · 324 x 102 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Label for the field next to it. |
| E37 | checkbox | Share my rehearsals to improve the simulator Off by default. Without t | main | 9.5%, 53.8% · 28 x 28 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 0px | Tick box: turns an option on or off. |
| E38 | label | Send my feedback to the team App feedback, simulation notes and flags. | main | 8.5%, 67.7% · 324 x 99 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Label for the field next to it. |
| E39 | checkbox | Send my feedback to the team App feedback, simulation notes and flags. [checked] | main | 9.5%, 67.9% · 28 x 28 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 0px | Tick box: turns an option on or off. |
| E40 | link | Read the privacy notice | main | 8.5%, 87.6% · 158 x 99 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Opens #/privacy. |
| E41 | button | Withdraw all | main | 51%, 87.6% · 158 x 99 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to withdraw all. |
| E42 | heading | Erase my data | main | 8.5%, 33.9% · 324 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E43 | button | Erase everything | main | 8.5%, 64.3% · 324 x 48 | 18px / 600; rgb(179, 38, 30) (--margin); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Button: tap to erase everything. |
| E44 | heading | Tell us what you think | main | 8.5%, 75.9% · 324 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E45 | label | About The app The lessons and cards The pretend children | main | 8.5%, 79.8% · 324 x 79 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Label for the field next to it. |
| E46 | combobox | About The app The lessons and cards The pretend children | main | 8.5%, 83.5% · 324 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Dropdown: she chooses one value. |
| E47 | button | 1 stars | main | 8.5%, 44.5% · 48 x 48 | 13.3333px / 400; rgb(63, 73, 72) (--muted); bg rgb(255, 255, 255) (--surface); radius 0px | Button: tap to 1 stars. |
| E48 | button | 2 stars | main | 21.8%, 44.5% · 48 x 48 | 13.3333px / 400; rgb(63, 73, 72) (--muted); bg rgb(255, 255, 255) (--surface); radius 0px | Button: tap to 2 stars. |
| E49 | button | 3 stars | main | 35.1%, 44.5% · 48 x 48 | 13.3333px / 400; rgb(63, 73, 72) (--muted); bg rgb(255, 255, 255) (--surface); radius 0px | Button: tap to 3 stars. |
| E50 | button | 4 stars | main | 48.5%, 44.5% · 48 x 48 | 13.3333px / 400; rgb(63, 73, 72) (--muted); bg rgb(255, 255, 255) (--surface); radius 0px | Button: tap to 4 stars. |
| E51 | button | 5 stars | main | 61.8%, 44.5% · 48 x 48 | 13.3333px / 400; rgb(63, 73, 72) (--muted); bg rgb(255, 255, 255) (--surface); radius 0px | Button: tap to 5 stars. |
| E52 | label | Your words (optional, up to 500 characters) | main | 8.5%, 51.6% · 324 x 157 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Label for the field next to it. |
| E53 | textbox | Your words (optional, up to 500 characters) | main | 8.5%, 58.5% · 324 x 99 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E54 | button | Send [disabled] | main | 8.5%, 78.8% · 324 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Button: tap to send. |
| E55 | link | Home | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E56 | link | Enter check | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E57 | link | My class | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to What my class gets wrong. |
| E58 | link | Practice | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the Practice Class. |
| E59 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

### State "default" · teacher · hi · phone

| # | Type | Label or text | Region | Position and size | Style | What it does |
| --- | --- | --- | --- | --- | --- | --- |
| E1 | link | कोहॉर्ट कोच | header | 4.1%, 0.9% · 140 x 44 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Goes to the role picker (the landing page). |
| E2 | image |  | header | 4.1%, 1.7% · 32 x 32 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Picture. |
| E3 | button | सहायक | header | 4.1%, 6.6% · 112 x 44 | 18px / 600; rgb(0, 32, 31) (--on-pen-container); bg rgb(189, 238, 238) (--pen-container); radius 999px (--r-pill) | Opens the assistant drawer, scoped to the user's role. |
| E4 | status | ऑनलाइन अच्छा सिग्नल · 9.2 एमबीपीएस | header | 34.8%, 7.2% · 166 x 34 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 16px (--s4) | Shows whether the app is online and the measured connection speed. |
| E5 | element | अच्छा सिग्नल · 9.2 एमबीपीएस | header | 44.8%, 7.8% · 114 x 24 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E6 | heading | मेरी प्रोफ़ाइल | main | 4.1%, 14.8% · 358 x 30 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E7 | link | भूमिका बदलें | main | 30.7%, 19.8% · 90 x 44 | 18px / 400; rgb(0, 0, 238); bg rgb(247, 250, 250) (--paper); radius 0px | Opens #/roles. |
| E8 | label | भाषा English हिन्दी தமிழ் | main | 4.1%, 26.4% · 358 x 79 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Label for the field next to it. |
| E9 | combobox | भाषा English हिन्दी தமிழ் | main | 4.1%, 30.1% · 358 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Dropdown: she chooses one value. |
| E10 | button | कैसे इंस्टॉल करें | main | 4.1%, 37.2% · 358 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to कैसे इंस्टॉल करें. |
| E11 | heading | मेरी कक्षाएँ | main | 8.5%, 44.9% · 324 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E12 | button | नाम बदलें | main | 61.8%, 50.8% · 56 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to नाम बदलें. |
| E13 | button | यह कक्षा हटाएँ | main | 77.2%, 50.8% · 56 x 48 | 18px / 600; rgb(179, 38, 30) (--margin); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Button: tap to यह कक्षा हटाएँ. |
| E14 | textbox | कक्षा का नाम | main | 8.5%, 58.6% · 26 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E15 | button | कक्षा जोड़ें | main | 17.2%, 58.6% · 290 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Button: tap to कक्षा जोड़ें. |
| E16 | heading | स्टोरेज और बैकअप | main | 8.5%, 80.2% · 324 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E17 | element | आपका डेटा अभी सुरक्षित नहीं है: जगह कम पड़ने पर ब्राउज़र उसे मिटा सकता | main | 8.5%, 84.1% · 324 x 54 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Shows text or a value. |
| E18 | button | मेरा डेटा सुरक्षित करें | main | 8.5%, 21.3% · 324 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to मेरा डेटा सुरक्षित करें. |
| E19 | heading | बैकअप फ़ाइल | main | 8.5%, 35.1% · 324 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E20 | label | पासफ़्रेज़ (वैकल्पिक, बहाल करते समय फिर चाहिए) | main | 8.5%, 54.2% · 324 x 106 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Label for the field next to it. |
| E21 | textbox | पासफ़्रेज़ (वैकल्पिक, बहाल करते समय फिर चाहिए) | main | 8.5%, 61% · 324 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E22 | button | बैकअप सहेजें | main | 8.5%, 68.1% · 158 x 72 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Button: tap to बैकअप सहेजें. |
| E23 | button | फ़ाइल से बहाल करें | main | 51%, 68.1% · 158 x 72 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to फ़ाइल से बहाल करें. |
| E24 | heading | इस्तेमाल हुआ डेटा | main | 8.5%, 84% · 324 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E25 | element | 0.5 KB | main | 10.5%, 21% · 87 x 30 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E26 | element | 26 KB | main | 38.9%, 21% · 87 x 30 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E27 | element | 27 KB | main | 67.3%, 21% · 87 x 30 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Shows text or a value. |
| E28 | label | 1 GB डेटा आपको कितने का पड़ता है (वैकल्पिक) | main | 8.5%, 31.2% · 324 x 106 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Label for the field next to it. |
| E29 | textbox | 1 GB डेटा आपको कितने का पड़ता है (वैकल्पिक) | main | 8.5%, 38% · 324 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E30 | button | गिनती साफ़ करें | main | 8.5%, 45.2% · 324 x 48 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to गिनती साफ़ करें. |
| E31 | heading | गोपनीयता | main | 8.5%, 66.7% · 324 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E32 | label | मेरी कक्षा की गिनती भेजें कितने बच्चों में कौन सी गलती है, शिक्षकों को | main | 8.5%, 82.6% · 324 x 99 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Label for the field next to it. |
| E33 | checkbox | मेरी कक्षा की गिनती भेजें कितने बच्चों में कौन सी गलती है, शिक्षकों को [checked] | main | 9.5%, 82.8% · 28 x 28 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 0px | Tick box: turns an option on or off. |
| E34 | label | अभ्यास कक्षा में AI इस्तेमाल करें वहाँ आप जो लिखती या बोलती हैं वह जवा | main | 8.5%, 25.6% · 324 x 147 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Label for the field next to it. |
| E35 | checkbox | अभ्यास कक्षा में AI इस्तेमाल करें वहाँ आप जो लिखती या बोलती हैं वह जवा [checked] | main | 9.5%, 25.8% · 28 x 28 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 0px | Tick box: turns an option on or off. |
| E36 | label | सिम्युलेटर सुधारने के लिए मेरे अभ्यास साझा करें पहले से बंद। इसके बिना | main | 8.5%, 45% · 324 x 102 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Label for the field next to it. |
| E37 | checkbox | सिम्युलेटर सुधारने के लिए मेरे अभ्यास साझा करें पहले से बंद। इसके बिना | main | 9.5%, 45.3% · 28 x 28 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 0px | Tick box: turns an option on or off. |
| E38 | label | मेरी प्रतिक्रिया टीम को भेजें ऐप की प्रतिक्रिया, सिम्युलेशन के नोट और  | main | 8.5%, 59.1% · 324 x 99 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Label for the field next to it. |
| E39 | checkbox | मेरी प्रतिक्रिया टीम को भेजें ऐप की प्रतिक्रिया, सिम्युलेशन के नोट और  [checked] | main | 9.5%, 59.4% · 28 x 28 | 13.3333px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 0px | Tick box: turns an option on or off. |
| E40 | link | गोपनीयता सूचना पढ़ें | main | 8.5%, 79% · 158 x 72 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Opens #/privacy. |
| E41 | button | सब वापस लें | main | 51%, 79% · 158 x 72 | 18px / 600; rgb(11, 107, 107) (--pen); bg rgb(247, 250, 250) (--paper); radius 8px (--s2) | Button: tap to सब वापस लें. |
| E42 | heading | मेरा डेटा मिटाएँ | main | 8.5%, 90.1% · 324 x 32 | 21.06px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E43 | button | सब कुछ मिटाएँ | main | 8.5%, 49.7% · 324 x 48 | 18px / 600; rgb(179, 38, 30) (--margin); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Button: tap to सब कुछ मिटाएँ. |
| E44 | heading | हमें बताइए आप क्या सोचती हैं | main | 8.5%, 61.4% · 324 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Heading: names the section below it. |
| E45 | label | किसके बारे में ऐप पाठ और कार्ड काल्पनिक बच्चे | main | 8.5%, 65.3% · 324 x 79 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Label for the field next to it. |
| E46 | combobox | किसके बारे में ऐप पाठ और कार्ड काल्पनिक बच्चे | main | 8.5%, 68.9% · 324 x 48 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Dropdown: she chooses one value. |
| E47 | button | 1 सितारे | main | 8.5%, 76% · 48 x 48 | 13.3333px / 400; rgb(63, 73, 72) (--muted); bg rgb(255, 255, 255) (--surface); radius 0px | Button: tap to 1 सितारे. |
| E48 | button | 2 सितारे | main | 21.8%, 76% · 48 x 48 | 13.3333px / 400; rgb(63, 73, 72) (--muted); bg rgb(255, 255, 255) (--surface); radius 0px | Button: tap to 2 सितारे. |
| E49 | button | 3 सितारे | main | 35.1%, 76% · 48 x 48 | 13.3333px / 400; rgb(63, 73, 72) (--muted); bg rgb(255, 255, 255) (--surface); radius 0px | Button: tap to 3 सितारे. |
| E50 | button | 4 सितारे | main | 48.5%, 76% · 48 x 48 | 13.3333px / 400; rgb(63, 73, 72) (--muted); bg rgb(255, 255, 255) (--surface); radius 0px | Button: tap to 4 सितारे. |
| E51 | button | 5 सितारे | main | 61.8%, 76% · 48 x 48 | 13.3333px / 400; rgb(63, 73, 72) (--muted); bg rgb(255, 255, 255) (--surface); radius 0px | Button: tap to 5 सितारे. |
| E52 | label | आपके शब्द (वैकल्पिक, 500 अक्षर तक) | main | 8.5%, 83.2% · 324 x 130 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(255, 255, 255) (--surface); radius 0px | Label for the field next to it. |
| E53 | textbox | आपके शब्द (वैकल्पिक, 500 अक्षर तक) | main | 8.5%, 86.8% · 324 x 99 | 18px / 400; rgb(0, 0, 0); bg rgb(255, 255, 255) (--surface); radius 8px (--s2) | Field: she types or chooses a value. |
| E54 | button | भेजें [disabled] | main | 8.5%, 81.6% · 324 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Button: tap to भेजें. |
| E55 | link | होम | bottom bar | 0%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/home. |
| E56 | link | जाँच भरें | bottom bar | 20%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/check. |
| E57 | link | मेरी कक्षा | bottom bar | 40%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/cards. |
| E58 | link | अभ्यास | bottom bar | 60%, 93.1% · 78 x 58 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens #/practice. |
| E59 | button | और [collapsed] | bottom bar | 80%, 93.1% · 78 x 58 | 16px / 400; rgb(25, 28, 28) (--ink); bg rgb(238, 244, 243) (--chalk); radius 0px | Button: tap to और. |

## 5. Content and data

Sections for language, classes, storage protection, backup and restore with a password, data used (sent, received, total, cost), three optional consents and a feedback form.

The text on screen, copied exactly from the page in the first state:

```text
My profile

Teacher
·
Change role

 Language
English
हिन्दी
தமிழ்
How to install
My classes
Class 3B (simulated)
simulated
In use
Class name
Add a class

Each class has its own checks and rehearsals. Deleting a class also asks our server to erase its counts.

Storage and backup

 Your data is not protected yet: the browser may clear it when space runs low.

Protect my data

This app uses 0.1 MB of about 10737.5 MB available.

Backup file

The file holds your checks, including each child's answers, and your rehearsals. Keep it safe. A passphrase locks it; without it the file is readable by anyone who has it.

Passphrase (optional, needed again to restore)
Save a backup
Restore from a file
Data used
Sent
1.2 KB
Received
56 KB
Total
57 KB

Counted since 31/10/2026.

What 1 GB of data costs you (optional)
Clear the count

Only this app's own calls are counted, on this phone. Photos are shrunk before sending to keep this small.

Privacy

Choose what you agree to. Everything is off until you turn it on, and you can change your mind at any time.

Send my class counts
How many children show each error, for grouping teachers. Never a child's answer.
Use AI in the Practice Class
What you type or say there goes to AI services (Claude for the replies, Sarvam for speech) to answer you. We do not keep it, and each service has its own retention rules.
Share my rehearsals to improve the simulator
Off by default. Without this, rehearsals stay on your phone.
Send my feedback to the team
App feedback, simulation notes and flags. Anonymous: no name, class or phone number.

Your choices were saved on 1/1/1970, 5:30:00 am (notice version 1).

Read the privacy notice
Withdraw all
Erase my data

Removes every class, check, rehearsal and setting from this phone, including your consent record, and asks our server to erase the class counts (if you are offline, the counts stay on the server: erase again when online). Feedback you sent has no name on it, so it cannot be found to erase. Consent records on the server are kept as proof.

Erase everything
Tell us what you think
About
The app
The lessons and cards
The pretend children
Your words (optional, up to 500 characters)

Please do not write names, phone numbers or anything about a particular child.

Send
```

Dynamic parts: counts, dates, names of the demo class and every number come from the demo class loaded in Judge mode or from the 12-step demo session; the code computes them.

## 6. States and transitions

- **default**: open the route.
- Empty, loading, error and offline states were not captured in this pack (core scope). The loaders and messages are listed in the product's own strings (`strings/en.json`).

## 7. What works and what to change

Measured from the numbered elements (touch targets, font sizes, sideways scroll, labels). There is no current UI audit of this app: `docs/design/audit/AUDIT.md` describes the original front end before the re-skin, so it is not used here.

- Touch target under 44 px: "Class name" (default/en: 26 x 48 px).
- Touch target under 44 px: "Send my class counts How many children s" (default/en: 28 x 28 px).
- Touch target under 44 px: "Use AI in the Practice Class What you ty" (default/en: 28 x 28 px).
- Touch target under 44 px: "Share my rehearsals to improve the simul" (default/en: 28 x 28 px).
- Touch target under 44 px: "Send my feedback to the team App feedbac" (default/en: 28 x 28 px).
- Touch target under 44 px: "कक्षा का नाम" (default/hi: 26 x 48 px).
- 6 distinct font sizes among the numbered elements in default, en, phone: 13.3333px, 16px, 18px, 20px, 21.06px, 24px.

## 8. Constraints

- Phone first at 390 px; desktop for coach, officer, judge and mentor screens.
- Touch targets at least 44 px, primary buttons 48 px.
- English, Hindi and Tamil text must fit without cutting.
- Use the tokens in `../00-tokens.md`: Material 3, Calm Institutional palette (teal primary), no new colours.
- Teacher-facing numbers are counts, never percentages. Simulated data stays labelled.
- No new features: redesign what exists.
