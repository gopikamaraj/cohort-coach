# X5 · AI map, AI layers and audit trail

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: AI map, AI layers and audit trail
- Role: Judge
- Device priority: Desktop first
- Purpose: Show every AI call, what it does, and the five layers (input, processing, guardrails, evaluation, output), plus the latest audit rows.

## Layout

### Phone (360px wide)

- Cards per call instead of a table; layers as an accordion.

### Desktop (1280px wide)

- AI map: a table, one row per call (ten of them), five layer columns; a legend on top.
- AI layers overlay: a side panel in the Practice Class listing the five layers for one turn.
- Audit trail: a table of the latest calls, metadata only.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: AI map
- Intro: Every Claude call, what it does, and its five layers.
- Layer headings: Input; Processing; Guardrails; Evaluation; Output
- Row: Call 1, Child voices. Input: persona, language, the engine's answer. Guardrails: every number equals the engine's answer.
- Overlay title: AI layers for this turn. Judge view. Not shown to teachers.
- Audit title: Audit trail
- Audit intro: The last AI calls. Metadata only: never what anyone said.
- Audit columns: Call; Model; Latency; Cost; Checks passed; Checker; Fallback
- Empty: No AI calls yet.
- Offline: This page needs a connection to the server.

## Components

Use these components from DESIGN.md: TopBar, NavRail, DataTable, StatusChip, SimulatedBanner.

## States

- Default: ten rows.
- Empty audit trail.
- Offline: a card says the page needs a connection.
- Loading and error as in the shell.

## Interactions

- Expanding a row shows the full layer text.
- Show AI layers toggles the overlay in the Practice Class.

## Do not show

- Never show what anyone said; the audit holds metadata only.
- Never reachable by teachers in production.
- No child names or transcript text.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
