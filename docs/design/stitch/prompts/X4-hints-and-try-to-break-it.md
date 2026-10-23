# X4 · Try with hints and Try to break it

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Try with hints and Try to break it
- Role: Judge
- Device priority: Desktop first
- Purpose: Show judges how a good, a weak and a neutral reply change the children, and how the pre-filter stops bad lines.

## Layout

### Phone (360px wide)

- Hints card above the typed field; break-it cards below the AI map.

### Desktop (1280px wide)

- Right column of the Practice Class: Try with hints toggle and three reply cards.
- On the AI map page: four prepared buttons and a result card under them.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Toggle: Try with hints
- Intro: Three things you could say next. Pick one and see how the children react.
- Hint examples: Tell me how you got your answer. What did you do first? / Just remember the rule: always take the smaller number from the bigger one. / Good, thank you for trying.
- After choosing: Move: asks the child to explain. Approved strategy.
- Break it title: Try to break it
- Break it intro: These lines are prepared. Each one runs through the real pre-filter, and you see which check stopped it.
- Buttons: Tell the system to ignore its rules; Insult a child; Share a phone number; Name a child with a roll number
- Result: Held back: a phone number was found, so the pre-filter stopped it.
- Labels: The line; Stopped by

## Components

Use these components from DESIGN.md: QuickMove, StatusChip, DataTable, PrivacyNote.

## States

- Hints off: nothing shown.
- Hints on: three reply cards, order shuffled, no label of which is strong.
- After choice: the move tag appears.
- Break it default and result states.
- Loading and error as in the shell.

## Interactions

- Tapping a hint sends it as the teacher's line.
- Tapping a break-it button runs the real pre-filter and shows the reason.

## Do not show

- Not offered to real teachers.
- Never say which hint is strong before she chooses.
- No real phone number or name; the lines are prepared and made up.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
