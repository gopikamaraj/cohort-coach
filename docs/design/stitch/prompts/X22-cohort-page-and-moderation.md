# X22 · Cohort page and moderation

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Cohort page and moderation
- Role: Coach
- Device priority: Desktop first
- Purpose: Let a coach manage one cohort, move it through its lifecycle and moderate its chat.

## Layout

### Phone (360px wide)

- Cohort card then flagged posts as cards with Hide and Keep buttons.

### Desktop (1280px wide)

- Left: cohort card with status chip and lifecycle actions (Start, Close, Cancel).
- Centre: the thread with a filter All, Flagged, Hidden.
- Right: the selected post with the reason it was flagged and the actions Hide and Restore.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Cohort page
- Lifecycle: Proposed; Active; Closing; Closed; Cancelled
- Close rule: Closing needs the post-test sheets received, or Closed without post-test with a reason.
- Thread filter: All; Flagged; Hidden
- Flag reasons: Reported by a teacher; Name found by the filter; Phone number found
- Actions: Hide this post; Restore; Keep
- Retention: Text is deleted 30 days after the cohort closes.
- Audit line: Hidden by coach. Recorded.
- Empty: No flagged posts.

## Components

Use these components from DESIGN.md: TopBar, NavRail, ThreadPost, StatusChip, ReportButton, DataTable, PrivacyNote.

## States

- Default: active cohort with a few flagged posts.
- Closing: needs a reason or the post-test sheets.
- Closed: read-only thread.
- Empty, loading, offline and error as in the shell.

## Interactions

- Hide removes a post from teachers' view at once.
- Each lifecycle move writes an audit row.

## Do not show

- No handles or phone numbers; pseudonyms only.
- No post written by AI.
- No teacher-level numbers.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
