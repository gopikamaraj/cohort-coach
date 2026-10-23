# X21 · Coach home

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Coach home
- Role: Coach
- Device priority: Desktop first
- Purpose: Give a coach one weekly batch: what waits for approval, what was flagged, and how each assigned cohort is going.

## Layout

### Phone (360px wide)

- Summary cards first, then the cohort cards; filters collapse into a sheet.

### Desktop (1280px wide)

- Top row of three summary cards: Waiting for approval, Flagged posts, Minutes this week.
- Cohort table: error, medium, size, schools, status chip, mentor status, items awaiting approval, oldest age.
- Right: mini funnel per selected cohort with source labels.
- Filter chips by status.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Coach
- Intro: A coach sees how many children show each error across the block. Counts only; nothing about one class or teacher.
- Summary: 3 items waiting. Oldest 2 days. 1 flagged post. 18 of 30 minutes this week.
- Row: Subtract, smaller from larger. Hindi. 9 teachers in 7 schools. Active. Mentor: active. 1 item waiting.
- Mentor statuses: Candidate; Invited; Active
- Funnel: Delivered (system); Tried (self-report); Practised (system); Changed: awaiting next check
- Hidden: Fewer than 5 classes.
- Filters: Proposed; Active; Closing; Closed
- Buttons: Open approval queue; Open cohort

## Components

Use these components from DESIGN.md: TopBar, NavRail, DataTable, StatusChip, FunnelBar, SuppressionNote, ProgressMeter.

## States

- Default: assigned cohorts only.
- Empty: No cohorts are assigned to you yet.
- Suppressed values.
- Loading, offline and error as in the shell.
- Simulated: banner.

## Interactions

- A row opens the cohort page.
- Open approval queue goes to the review queue.

## Do not show

- Never a number about one teacher's class.
- Never a cohort she is not assigned to.
- Participation is shown as cohort medians, never per teacher.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
