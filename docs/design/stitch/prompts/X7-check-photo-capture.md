# X7 · Check entry: photo capture and confirm

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Check entry: photo capture and confirm
- Role: Teacher
- Device priority: Phone first
- Purpose: Let a teacher photograph one answer sheet, see the numbers the reader found, and confirm only the boxes it was unsure about.

## Layout

### Phone (360px wide)

- Header two rows; title Photo of this sheet.
- Capture card: a large secondary button with a camera icon, and a tip line (hold the phone flat, no shadow).
- Reading card: a progress line and the words Reading the sheet.
- Result grid: the ten AnswerBoxes filled in; boxes the reader was unsure of use tertiary container with the word Check this.
- Primary button: Looks right, next child.

### Desktop (1280px wide)

- Phone-first column; on desktop the photo preview appears to the right while the grid stays on the left.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Button: Take a photo of this sheet
- Tip: Keep the whole sheet in the picture and the phone flat.
- Reading: Reading the sheet
- Done: Filled in from the photo. Check the boxes marked Check this.
- Flag: Check this
- Failure: Could not read the photo. Type the answers instead.
- Offline: Reading a photo needs a connection. Type the answers, or try again later.
- Replace warning: This sheet already has answers. Replace them with the photo?
- Sample sheets (judge mode): Use sample sheets. These are recorded reads of made-up sheets.
- Privacy note: The photo is read and then dropped. It is not kept anywhere.

## Components

Use these components from DESIGN.md: PhotoCapture, ConfirmBox, AnswerBox, StatusChip, PrivacyNote, SimulatedBanner.

## States

- Default: capture button.
- Reading, with a progress line.
- Low-confidence read: tertiary boxes with Check this, first one focused.
- Failed read: tells her to type.
- Offline: nothing is sent; she is told to type.
- Replace warning when digits already exist.

## Interactions

- Take a photo opens the camera; the photo is shrunk before it is sent.
- Editing a flagged box clears its flag.
- Looks right moves to the next child.

## Do not show

- No photo is kept, shown again or shared; no child name or roll number appears on the sheet.
- No score and no percentage.
- Never claim the reader is certain; low-confidence boxes are always shown.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
