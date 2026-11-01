# X37 · Demo entry and review drawer

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Demo entry and review drawer
- Role: Judge (as teacher)
- Device priority: Phone and laptop

- Purpose: Steps 4 and 5 of the demo: sheet 1 read by the AI, the other sheets loaded from the demo answer file, a status per roll number, and a drawer to check each sheet beside what was read before approving it.

## Layout

### Phone (360px wide)

- Two cards (Sheet 1: read by the AI; The other sheets: auto-fill), a progress line, a list of roll numbers (status chip, source line, Open), and Finish entering. The drawer comes up from the bottom, full width, 40 percent of the height: the sheet image (zoom, rotate) above the ten boxes, with unsure boxes outlined, and Approve, Next unreviewed, Mark absent, Re-read with AI.

### Desktop (1280px wide)

- The drawer is anchored bottom right, 40 percent of the width, the image beside the boxes.

## Exact copy

- Read by AI. Read from demo answer file. Read, needs review. Approved. Absent. Not entered. Printed code does not match this check. 19 sheets loaded from the demo answer file, with no AI call.

## Reading order

- Sheet 1, auto-fill, the roll numbers, Finish entering; in the drawer: the title, the source chip, the image, the boxes, the actions.

## Components

Cards, file inputs as buttons, chips, a list, a bottom drawer with an image region, number fields, buttons.

## States

- Nothing read yet. Sheet 1 read. Auto-filled. A code mismatch. The AI read cap reached (a plain message). The answer file missing (upload reads.json). All approved.

## Interactions

- Open moves focus into the drawer; Escape closes it and returns focus. Approve moves to the next sheet to review. Re-read with AI replaces the boxes and relabels them Read by AI.

## Do not show

- No child name: roll numbers only. Never call an answer-file load an AI read.

## Accessibility and tone

- Contrast at least 4.5 to 1 in light and dark. A visible focus ring on every control. Text scales to 200 percent without clipping or sideways scroll. Every icon has a text label. Reduced motion turns transitions off. Scrolling tables can be reached by keyboard.
- Tone is plain and warm, one short sentence per idea, no jargon, no pressure. Nothing here scores or judges the teacher.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons; let them wrap or grow. Hindi and Tamil strings are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
