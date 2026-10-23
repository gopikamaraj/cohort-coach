# X2 · Guided tour

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Guided tour
- Role: Judge
- Device priority: Desktop first
- Purpose: Walk a judge through all four roles in six steps in about five minutes, with the judging criterion named at each step.

## Layout

### Phone (360px wide)

- Progress bar and step title on top; the step card; What to notice card; Skip and Back at the bottom.

### Desktop (1280px wide)

- Top: progress bar with six segments and the label Step 2 of 6.
- Left: the step card with a short description and an Open button that jumps to the real screen.
- Right: What to notice card naming the criterion.
- A banner line when the role changes: Now you're the coach.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Guided tour
- Progress: Step 2 of 6
- Time: about 20 seconds
- Step titles: Check a class; Approve a proposed cohort; Approve a mentor recording; Watch two rehearsals, then try one; Advance to Term 2; Under the hood
- Banner: Now you're the coach
- What to notice (step 2): Guardrails: a person approves; nothing is approved by itself.
- What to notice (step 4): AI use in layers: every turn shows what code decided, which AI call ran and which checks passed.
- Buttons: Skip to the next step; Back; Finish the tour; Leave the tour
- Practice link: Open the Practice Class to try it yourself

## Components

Use these components from DESIGN.md: TopBar, TourProgress, WhatToNotice, SimulatedBanner, StatusChip.

## States

- Default: step 1.
- Resumed: opening step 4 by its link resumes there.
- Pending step: a card says This step arrives later and that nothing on it is a result.
- Finished: a summary card lists the six criteria.
- Loading, offline and error as in the shell.

## Interactions

- Open jumps to the screen for the step; Back returns to the tour.
- Skip and Back work at every step.
- Progress is kept as the step number in the address.

## Do not show

- No separate demo interface; the tour uses the real screens.
- No percentage shown to a teacher or mentor view.
- Every step says Simulated.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
