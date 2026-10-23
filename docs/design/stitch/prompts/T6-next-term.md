# T6 · Next term

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Next term
- Role: Teacher
- Device priority: Phone first
- Purpose: Tell her, privately, how many children in her class still show the tracked error after the track, as a count against last term.

## Layout

### Phone (360px wide)

- Header two rows; title Next term.
- Result card, success container when the count fell, tertiary container when it did not: a PlayButton, a sentence with two counts, and an icon.
- Reassurance card: A failed track counts against the track, not you.
- Next-step card: one plain suggestion.
- One primary button: Enter next term's check.

### Desktop (1280px wide)

- Phone-first column; no extra regions.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Next term
- Result when it fell: Last term 11 of 28 children took the smaller digit from the larger. Now 6 of 28 do.
- Result when it did not: Last term 11 of 28 children took the smaller digit from the larger. Now 10 of 28 do.
- Awaiting state: Your next check is not entered yet. Your result will show here after it.
- Reassurance: A failed track counts against the track, not you.
- Next step: Try the Practice Class again before the next lesson.
- Privacy line: Only you can see this.
- Button: Enter next term's check

## Components

Use these components from DESIGN.md: TopBar, BottomNav, FeedbackCard, PlayButton, PrivacyNote, StatusChip.

## States

- Default: result with two counts.
- Awaiting next check: neutral card; the funnel step Changed reads awaiting next check.
- Not improved: tertiary card with kind wording; never failed.
- Offline: shown from the phone; nothing needs the network.
- Simulated: banner and tag.

## Interactions

- Play reads the result aloud.
- Primary button opens Enter check for the new term.

## Do not show

- No comparison with other teachers and no percentage.
- Never posted to the cohort chat, never shown to a coach or officer by teacher.
- Never the word failed about her.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
