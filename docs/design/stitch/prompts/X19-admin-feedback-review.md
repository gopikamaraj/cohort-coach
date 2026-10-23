# X19 · Admin: feedback and simulation reports

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Admin: feedback and simulation reports
- Role: Admin (team)
- Device priority: Desktop first
- Purpose: Let the team read anonymous feedback and simulation reports from teachers and mark each reviewed.

## Layout

### Phone (360px wide)

- A single list with filters on top; each item is a card with a status chip and an action.

### Desktop (1280px wide)

- Left: filters (Kind: App, Lessons and cards, Pretend children, Card flag; Status: New, Reviewed, All).
- Main: a table of items with date, kind, rating, text and status.
- Right: a Simulation reports panel with error, likeness answer and what differed.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Admin
- Key field: Admin key
- Auth error: The admin key is missing or wrong.
- Filters: Kind; Status; All; New; Reviewed
- Kinds: App; Lessons and cards; Pretend children; Card flag
- Row: 14 Oct. Pretend children. Rating 4 stars. The children were quieter than mine.
- Simulation panel: Simulation reports from teachers. Error. Like her class? What differed. Language.
- Actions: Mark reviewed; Reopen
- Note field: A note for the team (optional)
- Empty: Nothing here yet.

## Components

Use these components from DESIGN.md: TopBar, NavRail, DataTable, StatusChip, PrivacyNote.

## States

- Locked: key required.
- Default: new items first.
- Empty: Nothing here yet.
- Open warning when no key is set on the server, shown only in development.
- Loading and error as in the shell.

## Interactions

- Mark reviewed sets the status and stores the note.
- Filters narrow the table.

## Do not show

- Never shown to teachers, coaches or officers.
- No name, class or phone number exists in the data; show none.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
