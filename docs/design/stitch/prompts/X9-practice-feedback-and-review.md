# X9 · Practice feedback and rehearsal review

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Practice feedback and rehearsal review
- Role: Teacher
- Device priority: Phone first
- Purpose: End a rehearsal with a private card, two things done well and one to try, then let her review past rehearsals on her phone.

## Layout

### Phone (360px wide)

- Header two rows; title Your feedback.
- Two FeedbackCards in success container, each with a heading, her own quote in a quote block and a short comment.
- One FeedbackCard in tertiary container: One thing to try, with a quote and a suggestion.
- Thumbs row: Helped, No difference, Did not help, as three outlined buttons with icons.
- A This is wrong flag button.
- Share switch row, off by default.
- Primary button: Practise again with the same children.
- Review tab: a list of rehearsals with date, language, turn count and the impact tag; opening one shows a turn-by-turn replay.

### Desktop (1280px wide)

- Phone-first column; the review list on the left and the replay on the right.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Your feedback
- Strength 1: You asked a child to explain. You said: Tell me how you got that. This showed her thinking.
- Strength 2: You showed the number with bundles. You said: Here is 52 as 5 bundles and 2 sticks.
- To try: Check by adding back. You could say: Let us check by adding back. What is 23 plus 29?
- Privacy: Private. Stays on this phone unless you choose to share.
- Impact: Did this rehearsal help? It helped; No difference; It did not help. Your own view. It stays on this phone and is not a score.
- Flag: This is wrong
- Review title: Your rehearsals
- Review summary: Rehearsals: 3. Helped: 2. No difference: 1.
- Replay: Turn 2 of 7. Previous; Next
- Buttons: Practise again with the same children; Delete this recording

## Components

Use these components from DESIGN.md: FeedbackCard, PlayButton, PrivacyNote, StatusChip, ProgressMeter, BadgeLine.

## States

- Default: two strengths and one thing to try.
- Loading: Writing your feedback.
- Template card: a simple card when the checks held the first one; labelled so.
- Empty review list: No rehearsals recorded yet. Practise once and it will appear here.
- Offline: the review list works; new feedback needs a connection.
- Error: a tertiary card with Try again.

## Interactions

- Thumbs set the impact tag, stored on the phone.
- Share switch is off unless she turns it on.
- Delete removes a recording after a confirmation.

## Do not show

- No score, grade or ranking of the teacher.
- No percentage.
- Nothing from the rehearsal is shown to a coach or officer unless she shares.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
