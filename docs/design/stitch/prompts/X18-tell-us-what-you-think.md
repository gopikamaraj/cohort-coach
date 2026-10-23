# X18 · Tell us what you think

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Tell us what you think
- Role: Teacher
- Device priority: Phone first
- Purpose: Let a teacher send anonymous feedback to the team in under a minute.

## Layout

### Phone (360px wide)

- Header two rows; title Tell us what you think.
- About chips: The app; The lessons and cards; The pretend children.
- Star row: five outlined stars with a number label.
- A text field of up to 500 characters with a counter.
- Note line: Please do not write names, phone numbers or anything about a particular child.
- Primary button: Send.

### Desktop (1280px wide)

- Phone-first column.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Tell us what you think
- About: The app; The lessons and cards; The pretend children
- Rating: Rating. 4 stars
- Text label: Your words (optional, up to 500 characters)
- Note: Please do not write names, phone numbers or anything about a particular child.
- Button: Send
- Need consent: Turn on Send my feedback to the team in My profile first.
- Refused: That could not be sent. Remove phone numbers, emails or other personal details and try again.
- Sent: Thank you. Sent.
- Queued: Saved. It will be sent when you are online.

## Components

Use these components from DESIGN.md: QuickMove, AnswerBox, StatusChip, PrivacyNote, TypedFallback.

## States

- Default: nothing chosen.
- Consent off: the form is disabled with a link to My profile.
- Refused text: personal details found.
- Sent and queued states.
- Offline: queued.

## Interactions

- Send runs the personal-details filter first.
- A flag on any card sends only the card and the term, with no free text.

## Do not show

- No name, class or phone number is attached.
- No percentage.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
