# X14 · My programme

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: My programme
- Role: Teacher
- Device priority: Phone first
- Purpose: Show a teacher where she stands in the programme in five plain steps.

## Layout

### Phone (360px wide)

- Header two rows; title My programme.
- Five step cards stacked with a status icon and word each: Done, Waiting, Not yet.
- Where you will hear card with a lock icon.
- One primary button depending on state: Enter this term's check, or Open my track.

### Desktop (1280px wide)

- Phone-first column.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: My programme
- Step 1, Your check: Done: 28 children checked.
- Step 2, Your track: No track yet.
- Step 3, Your cohort: You are in a cohort of 9 teachers who share this error. Your track starts now.
- Step 3 alternative: You are on the waiting list. Your track starts next term.
- Step 4, Your mentor: Your cohort will have a mentor: a teacher whose class fixed this error.
- Step 5, Lessons and model-lesson script: None published yet. They appear here after a reviewer approves them, each with audio and text.
- Where you will hear: Open this screen any time to see where you stand.
- Offline: Could not reach the server, so only the steps from this phone are shown.
- Button: Try again

## Components

Use these components from DESIGN.md: TopBar, BottomNav, StatusChip, ProgressMeter, PlayButton, PrivacyNote.

## States

- Default: step 1 done, others waiting.
- Placed: cohort card names size.
- Waitlist and not placed yet.
- Offline: steps from the phone only, with a retry.
- Simulated: banner and an example placement label.

## Interactions

- Play reads a step aloud.
- Try again re-fetches placement.

## Do not show

- No other teacher's name or class.
- No percentage.
- No wording that suggests she is behind.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
