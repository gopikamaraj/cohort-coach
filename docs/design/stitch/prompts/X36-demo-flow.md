# X36 · Demo flow

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Demo flow
- Role: Judge
- Device priority: Phone and laptop

- Purpose: A guided path for a judge through the whole product in about 15 minutes, on a made-up class, using the product's own screens. Every made-up sheet, class and number says Demo, Simulated or Synthetic.

## Layout

### Phone (360px wide)

- A thin bar under the title bar on every screen: Demo step n of 11 and one line saying what to do, then chips Back, Next, Judge guide for this step, Reset demo. The demo's own screens are one column: a title, a Demo chip, the step's card and one primary button.

### Desktop (1280px wide)

- The same bar spans the content column. Cohort cards two to a row; the officer tables side by side.

## Exact copy

- Demo step 1 of 11. Next. Back. Reset demo. Judge guide for this step.
- Demo: made-up class 3A, 20 simulated children, no real child.
- Generate 20 filled sheets for this paper. Simulate other classes' results. Make the first audio lesson. Skip the wait. Simulate the post-test.

## Reading order

- The step bar, the screen title, the Demo label, the step's card, the primary button.

## Components

A sticky step bar, chips, cards, a status line, buttons, a bottom drawer (X37), tables in scrollable regions.

## States

- Not started. Each step done or waiting. A step that needs an earlier one (it says which). Offline or the demo ended (Reset). Hindi and Tamil.

## Interactions

- Next opens the right screen as the right role. Reset asks first and clears only this device's demo. Each demo step leaves a tester-stats event.

## Do not show

- No real child, name, school or teacher. No number without its Simulated label. No AI read presented as an answer-file load, or the other way round.

## Accessibility and tone

- Contrast at least 4.5 to 1 in light and dark. A visible focus ring on every control. Text scales to 200 percent without clipping or sideways scroll. Every icon has a text label. Reduced motion turns transitions off. Scrolling tables can be reached by keyboard.
- Tone is plain and warm, one short sentence per idea, no jargon, no pressure. Nothing here scores or judges the teacher.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons; let them wrap or grow. Hindi and Tamil strings are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
