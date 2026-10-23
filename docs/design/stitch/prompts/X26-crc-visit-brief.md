# X26 · CRC visit brief

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: CRC visit brief
- Role: Programme officer
- Device priority: Desktop first, printable
- Purpose: Give a CRC a one-page brief for a school visit that contains no number about any class.

## Layout

### Phone (360px wide)

- A single printable column.

### Desktop (1280px wide)

- A one-page printable layout with a school header and one row per opted-in teacher.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Visit brief
- Header: School S07. Visit on 28 Oct.
- Row: Teacher 3. Track: children take the smaller digit from the larger. Current lesson: lesson 3, open one bundle.
- Look for: Does the child open a bundle when she has too few loose sticks?
- Ask a child: Show me 52 with sticks. What do you do to take away 9?
- Footer: This brief has no numbers about any class. It lists only teachers who agreed.
- Button: Print
- Empty: No teacher in this school has agreed to a visit brief.

## Components

Use these components from DESIGN.md: TopBar, NavRail, DataTable, StatusChip, PrivacyNote.

## States

- Default: one to three teachers.
- Empty: nobody opted in.
- Printed view without the navigation.
- Loading, offline and error as in the shell.

## Interactions

- Print opens the print dialog.
- It is also sent to the CRC in Telegram.

## Do not show

- No number about a class, no teacher name beside a number, no children.
- No teacher who did not agree.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
