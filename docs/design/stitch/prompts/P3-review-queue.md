# P3 · Review queue and two-key approval

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Review queue and two-key approval
- Role: Programme officer
- Device priority: Desktop first
- Purpose: Show the content waiting for a person: the coach approves, the programme officer then switches it on for the block; each change is a new version.

## Layout

### Phone (360px wide)

- List of items with age and status; opening one shows its draft and its checks in one column.

### Desktop (1280px wide)

- Left: queue list filtered by status (Draft, Awaiting coach, Approved, Active, Changes requested), oldest first, each row with its age.
- Centre: the draft in readable text with a PlayButton, its provenance (citations to the sentence it came from) and the arithmetic check.
- Right: the checks (code checks, pre-filter, output checker), version, and the two keys: Approve (coach), Switch on for the block (officer).
- Bottom: rejection reason select and a note.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Review queue
- Row: Lesson 3, Open one bundle. Subtract, smaller from larger. Hindi. Awaiting coach. 2 days.
- Checks: Code checks passed. Pre-filter passed. Output checker passed. Arithmetic correct.
- Version: Track version 2. Draft from approved method card 1.
- Coach key: Approve for teachers
- Officer key: Switch on for the block
- Rejection reasons: Wrong maths; Culturally off; Too complex for the medium; Tone issue; Factually shaky
- Rule line: Neither key alone publishes. Each change makes a new version.
- Audit: Approved by coach, enabled by officer. Time and version recorded.

## Components

Use these components from DESIGN.md: TopBar, NavRail, DataTable, StatusChip, BadgeLine, PlayButton, ApprovalQueueRow, ReasonSelect.

## States

- Default: oldest item first with its age.
- Awaiting coach, Approved (waiting for officer), Active.
- Rejected: reason chosen and the item returned; the reason feeds the checker for later drafts.
- Empty: Nothing is waiting.
- Loading, offline and error as in the shell.
- A coach sees only the coach key; an officer sees only the officer key.

## Interactions

- Approve moves Awaiting coach to Approved; Switch on moves Approved to Active.
- Reject asks for exactly one reason.
- An edit to an active item makes a new draft; the old version stays in use until the new one has both keys.

## Do not show

- Nothing auto-approves and no item is published by one key.
- No teacher-level numbers anywhere in the draft or the checks.
- No child names in any draft.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
