# P1 · Error map

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Error map
- Role: Programme officer
- Device priority: Desktop first
- Purpose: Show a programme officer where the block's classes are, by error and medium, with honest small-number handling.

## Layout

### Phone (360px wide)

- Single column: filters first, then one card per error with its class count and a small table by medium.

### Desktop (1280px wide)

- Top: filter row (Term, Grade 3, Medium: Hindi, Tamil, English).
- Main: a table of errors by medium; each cell shows a class count and a percentage of classes, or the words fewer than 5 classes.
- Right panel: stage mix per error as counts labelled Directional.
- Below: a separate panel, Real pilot, with n classes and the words read as directional.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Error map
- Subtitle: Term 1, Grade 3, block B1
- Banner: Simulated data: a fictional block of 40 schools and 120 classes.
- Row: Subtract, smaller from larger. Hindi 17 of 48 classes (35 percent). Tamil 19 of 42 classes (45 percent). English 8 of 30 classes (27 percent).
- Row: Subtract, borrow without reducing. Hindi 10 of 48 classes (21 percent). Tamil 12 of 42 classes (29 percent). English 13 of 30 classes (43 percent).
- Suppressed cell: Fewer than 5 classes
- Stage panel: Where it most likely went wrong. Directional. Core, Input (test), Output, Input (teaching).
- Pilot panel: Pilot, 3 classes. Read as directional.
- Source label: System: class counts sent by teachers who agreed.

## Components

Use these components from DESIGN.md: TopBar, NavRail, DataTable, SuppressionNote, StatusChip, SimulatedBanner.

## States

- Default: table with counts.
- Suppressed cell: outlined muted cell with the words fewer than 5 classes.
- Empty: No classes have sent a check yet.
- Loading, offline and error as in the shell; a printed view for meetings.
- Simulated and Real pilot panels clearly separated.

## Interactions

- Filters change the table without leaving the page.
- Selecting a row opens its stage mix.
- Export as a plain table for printing.

## Do not show

- No teacher-level or school-level row below 5 classes.
- No names of schools or teachers beside a count.
- Never mix simulated and real data in one cell.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
