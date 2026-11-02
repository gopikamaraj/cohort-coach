# 12 · Privacy notice

_Written for Stitch: what this screen is, what each part does, and what to keep. Tables are generated from the live page; the purpose and behaviour lines are written from the component source._

## 1. Screen

- **Route:** `#/privacy`
- **Roles shown:** teacher
- **Languages captured:** en
- **Inventory id:** X17
- **When a user sees it:** A teacher opens the privacy link from the welcome or profile.
- **What they are trying to do:** Read in plain words what is kept where, who sees what, how long, and her rights.
- **Source:** apps/pwa/src/screens/PrivacyNotice.tsx

## 2. Images

| File | What it shows | Viewport | Scroll | State |
| --- | --- | --- | --- | --- |
| 01-privacy_default_teacher_en_phone.png | First viewport, clean | 390 x 844 @2x | top | default · teacher · en |
| 01-privacy_default_teacher_en_phone-annotated.png | Same, with numbered boxes E1, E2, E3… | 390 x 844 @2x | top | default · teacher · en |
| 01-privacy_default_teacher_en_phone-s01.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 0 px | default · teacher · en |
| 01-privacy_default_teacher_en_phone-s02.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 573 px | default · teacher · en |
| 01-privacy_default_teacher_en_phone-s03.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1146 px | default · teacher · en |
| 01-privacy_default_teacher_en_phone-s04.png | Scroll slice (80 px overlap) | 390 x 844 @2x | 1677 px | default · teacher · en |
| 01-privacy_default_teacher_en_phone-long-p1.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · teacher · en |
| 01-privacy_default_teacher_en_phone-long-p2.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · teacher · en |
| 01-privacy_default_teacher_en_phone-long-p3.png | Stitched long image (fixed header and bottom bar kept once) | 390 x 844 @2x | full page | default · teacher · en |
| 01-privacy_default_teacher_en_phone-long-annotated-p1.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · teacher · en |
| 01-privacy_default_teacher_en_phone-long-annotated-p2.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · teacher · en |
| 01-privacy_default_teacher_en_phone-long-annotated-p3.png | Long image with numbered boxes | 390 x 844 @2x | full page | default · teacher · en |
| privacy-sheet.png | Contact sheet of the main states | — | — | all |

## 3. Layout

Top to bottom in the first state ("default"), by region, with the numbered elements in each:

- **header**: E1 to E5 (5 elements)
- **main**: E6 to E13 (8 elements)
- **bottom bar**: E14 to E18 (5 elements)
- The page scrolls inside one container: 653 px visible of 2330 px (the header and bottom bar stay fixed).

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
| E6 | heading | Privacy notice | main | 4.1%, 14.8% · 358 x 31 | 24px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E7 | heading | What we hold | main | 4.1%, 37.8% · 358 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E8 | heading | Children's data | main | 4.1%, 23% · 358 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E9 | heading | Who else handles data | main | 4.1%, 54.4% · 358 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E10 | heading | Your rights | main | 4.1%, 76.2% · 358 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E11 | heading | Who to write to | main | 4.1%, 60.7% · 358 x 25 | 20px / 700; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Heading: names the section below it. |
| E12 | element | Grievance contact: to be added by the programme before real teachers u | main | 4.1%, 64.6% · 358 x 81 | 18px / 400; rgb(25, 28, 28) (--ink); bg rgb(247, 250, 250) (--paper); radius 0px | Shows text or a value. |
| E13 | link | Choose what you agree to | main | 4.1%, 82.7% · 358 x 48 | 18px / 600; rgb(255, 255, 255) (--surface); bg rgb(11, 107, 107) (--pen); radius 8px (--s2) | Opens #/profile. |
| E14 | link | Home | bottom bar | 0%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to Home. |
| E15 | link | Enter check | bottom bar | 20%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the check entry. |
| E16 | link | My class | bottom bar | 40%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to What my class gets wrong. |
| E17 | link | Practice | bottom bar | 60%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Goes to the Practice Class. |
| E18 | button | More [collapsed] | bottom bar | 80%, 90.3% · 78 x 82 | 16px / 400; rgb(63, 73, 72) (--muted); bg rgb(238, 244, 243) (--chalk); radius 0px | Opens the menu of the other screens. |

## 5. Content and data

A long page of headings and short paragraphs. No actions other than the back link.

The text on screen, copied exactly from the page in the first state:

```text
Privacy notice

This is how Cohort Coach uses your data under India's Digital Personal Data Protection Act, 2023. We collect as little as we can, and most of it never leaves your phone.

What we hold
Data	Why	Where	How long
Each child's answers	To find which mistakes your class makes	Only on your phone	Until you delete them
Class counts	To group teachers by shared mistakes	Our server, under a random class id	Until you erase the class or leave
Practice Class words	So the pretend children can answer	Sent to AI services for the reply; the record stays on your phone	Not kept on our servers
Your voice in the Practice Class	To turn what you say into text	Sent to the speech service, then dropped	Not stored
Feedback and notes	To improve the app and the pretend children	Our server, with no name or id	While we improve the product
Your consent choices	To prove what you agreed to	Your phone, and our server under a random device id	As long as the programme runs
Children's data

We do not collect any child's name, face, voice or roll number, and sheets carry no name. A child's answers stay on your phone. Photos of sheets are read and dropped at once. Because no child is identifiable to us, we hold no children's personal data; the programme's legal team should still confirm this.

Who else handles data

Anthropic (Claude) and Sarvam AI process what you type or say in the Practice Class, and photos of sheets, only to answer you. Our hosting provider stores class counts and feedback.

Your rights
See your data. My profile > Save a backup, and What I entered.
Correct it. Open the check and change any answer.
Erase it. My profile > Erase everything, or delete one class.
Withdraw consent. My profile > Privacy, at any time; withdrawing is as easy as agreeing.
Complain. Write to the contact below; you can also go to the Data Protection Board of India.
Nominate someone to act for you. Tell the contact below in writing.
Who to write to

Grievance contact: to be added by the programme before real teachers use the app (TODO: name, email, phone).

This notice is a draft for the programme's legal review.

Choose what you agree to
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
