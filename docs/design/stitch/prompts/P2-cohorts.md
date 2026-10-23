# P2 · Cohorts

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Cohorts
- Role: Programme officer
- Device priority: Desktop first
- Purpose: Let the officer review proposed cohorts and approve them, each with a one-line reason.

## Layout

### Phone (360px wide)

- Cohort cards stacked, each with size, schools, mentor status and an Approve button.

### Desktop (1280px wide)

- Table of proposed cohorts: error, medium, size, schools, mentor status, split, status chip, row action Approve.
- Detail drawer on the right with the explanation lines and the audit entry preview.
- Banner for small pilot cohorts: Pilot cohorts are small; the caps apply at block scale.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Cohorts
- Row: Subtract, smaller from larger. Hindi. 9 teachers in 7 schools. Mentor: candidate. This term. Proposed.
- Row: Subtract, borrow without reducing. Tamil. 6 teachers in 4 schools. Mentor: invited. Next term. Proposed.
- Explanation: Grouped for this error because 11 of 28 children in each class showed it.
- Mentor status chips: Candidate: method interview needed; Invited; Active
- Status chips: Proposed; Active; Closing; Closed; Cancelled
- Button: Approve cohort
- Audit line: Approved by programme officer. Recorded.
- Print: Print visit brief for a school

## Components

Use these components from DESIGN.md: TopBar, NavRail, DataTable, StatusChip, SuppressionNote, ThreadPost.

## States

- Default: proposed rows.
- Approving: the row shows a progress line, then the Active chip.
- Empty: No cohorts are proposed yet.
- Undersized: a tertiary chip Small pilot cohort.
- Loading, offline and error as in the shell.
- Simulated: banner.

## Interactions

- Approve is recorded in the audit trail; nothing auto-approves.
- Selecting a row opens the drawer.
- Print opens the CRC visit brief for a school.

## Do not show

- No teacher names beside numbers; a cohort lists counts and schools by number.
- No percentage of any teacher's class.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
