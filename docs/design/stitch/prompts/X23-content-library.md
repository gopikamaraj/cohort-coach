# X23 · Content library

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Content library
- Role: Coach
- Device priority: Desktop first
- Purpose: Show a coach and an officer the content a block uses, what they can change, and what is fixed by code.

## Layout

### Phone (360px wide)

- Tabs: Scenarios, Strategies, Fixed by code, Topic packs; each as a list.

### Desktop (1280px wide)

- Tabs across the top.
- Strategies: a table with description, worked example, errors it fits, approval status.
- Fixed by code: a two-column read-only table with a version beside each row.
- Topic packs: cards with a status chip.
- Right: the two keys explained with the current item's status.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Content library
- Tabs: Scenarios; Strategies; Fixed by code; Topic packs
- Strategy: Decomposition. Fits subtract, smaller from larger, and subtract, borrow without reducing. Approved.
- Strategy: Check by adding back. Fits subtraction. Approved.
- Fixed by code: Error functions and the item generator. Version 1. Read only.
- Fixed by code: The two-item rule. Version 1. Read only.
- Configurable: Which strategies are approved, and their order; scenario descriptions; stage routines on or off.
- Two keys: The coach approves. The programme officer switches it on for the block. Neither key alone publishes.
- Packs: Place value, add and subtract. In use for the demo. Fractions demo. Draft.
- Usage: Fewer than 5 classes, hidden.

## Components

Use these components from DESIGN.md: TopBar, NavRail, DataTable, StatusChip, ApprovalQueueRow, SuppressionNote.

## States

- Default: strategies tab.
- Read-only items show a lock icon and a version.
- Edit locked for a role that does not hold the key.
- Usage hidden below 5 classes.
- Loading, offline and error as in the shell.

## Interactions

- A strategy opens its worked example.
- Editing a configurable item makes a new version; the old stays in use until both keys.

## Do not show

- No editing of scoring, rules, validators or anything that computes a number.
- No free prompt editor.
- No worked example that is a check item.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
