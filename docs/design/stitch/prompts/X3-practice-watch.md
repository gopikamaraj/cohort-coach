# X3 · Practice Class: Watch two rehearsals

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Practice Class: Watch two rehearsals
- Role: Judge
- Device priority: Desktop first
- Purpose: Let a judge watch an AI teacher run the Practice Class in an experienced or a struggling style and compare the two.

## Layout

### Phone (360px wide)

- One style at a time; tabs switch style; controls under the transcript.

### Desktop (1280px wide)

- Two panels side by side: Experienced and Struggling, each with the ClassCard, the transcript of turns and a SayLine per turn.
- Under each turn: the move tag and a Show the machinery toggle.
- Playback bar: Pause, Step, 2x speed, Skip to feedback.
- Bottom: the two feedback cards side by side.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Watch a rehearsal
- Label on every teacher line: AI playing the teacher (demo only)
- Run label: Recorded run, or Live run
- Style tabs: Experienced; Struggling
- Turn: Meena: 37, Miss! Subtitle: 37, Miss!
- Move tag: Uses bundles of ten sticks. Approved strategy.
- Machinery: Code decided the speaker and the answer. AI call 10 chose the move. Checks passed.
- Playback: Pause; Step; 2x; Skip to feedback
- Meter words: Meena low; Karthik medium
- Banner: Simulated data: these children are made up.

## Components

Use these components from DESIGN.md: TopBar, NavRail, ClassCard, ChildAvatar, SayLine, ProgressMeter, FeedbackCard, SimulatedBanner, StatusChip.

## States

- Recorded run: label Recorded run with the date.
- Live run: label Live run and a cost meter; falls back to recorded if a call fails.
- Paused and stepping states.
- Empty: no recorded run for this choice.
- Loading and error as in the shell.

## Interactions

- Play, pause, step and speed controls.
- Show the machinery expands the five layers for a turn.
- Skip to feedback jumps to the cards.

## Do not show

- Never offered outside judge mode; the AI teacher never reaches a real teacher.
- Never present a recorded run as live.
- No score about a teacher.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
