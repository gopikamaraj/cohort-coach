# P4 · Track results

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Track results
- Role: Programme officer
- Device priority: Desktop first
- Purpose: Show whether a track version worked, with honest uncertainty, per version and never per teacher.

## Layout

### Phone (360px wide)

- Verdict cards stacked; the interval chart scrolls horizontally inside its card; the funnel follows.

### Desktop (1280px wide)

- Top: version selector and the Advance to Term 2 button in judge mode.
- Left: results table, one row per track version: classes (track and comparison), effect in points, 95 percent interval, verdict chip, note.
- Right: the interval chart for the selected version (a horizontal interval on a zero line).
- Below: the funnel (Delivered, Tried, Practised, Changed), each step with a source label.
- Footer line: A failed track counts against the track, not the teacher.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Track results
- Banner: Simulated data: Term 2 results for a fictional block.
- Row 1: Subtract, smaller from larger, version 1. 21 and 23 classes. Effect -19.5 points. Interval -24.1 to -15.1. Working.
- Row 2: Subtract, borrow without reducing, version 1. 18 and 17 classes. Effect -0.3 points. Interval -3.3 to 2.8. Not working.
- Row 3: Forgets the carried ten, version 1. 8 and 7 classes. Effect -15.7 points. Inconclusive. From 7 classes, read as directional.
- Row 4: Writes a number as it is said, version 1. Hidden: fewer than 5 classes.
- Verdict meanings: Working: the whole interval is below zero and the fall is at least 10 points. Inconclusive: not enough to say. Not working: a fall under 5 points, or a rise.
- Funnel: Delivered (system): lessons sent. Tried (self-report): taps. Practised (system): Practice Class sessions. Changed (next check): awaiting next check.
- Footer: A failed track counts against the track, not the teacher.

## Components

Use these components from DESIGN.md: TopBar, NavRail, DataTable, IntervalChart, VerdictChip, FunnelBar, SuppressionNote, SimulatedBanner.

## States

- Default: three verdict rows plus one hidden row.
- Before Term 2: Changed reads awaiting next check; verdict chips absent.
- Suppressed: fewer than 5 classes.
- Empty, loading, offline and error as in the shell.
- Simulated: banner on every panel.

## Interactions

- Selecting a row updates the chart and the funnel.
- Advance to Term 2 (judge mode only) computes the verdicts.
- Hovering the verdict chip explains its rule in plain words.

## Do not show

- No teacher-level view: no row, tooltip or export that names a teacher or one class.
- No delivered or tried step presented as adoption; every step carries its source label.
- Never the word failed about a teacher.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
