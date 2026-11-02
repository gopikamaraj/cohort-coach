# X41 · Enter check

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Enter check
- Role: Teacher, Mentor (Judge sees it as a teacher)
- Device priority: Phone first, laptop second

- Purpose: Enter one class's answer sheets for a paper that already exists: choose the paper, add the sheets by typing, by the camera or by a folder of pictures, check each roll number against its picture, approve it, and finish.

## Layout

### Phone (360px wide)

- Start a check: a Choose a paper list (Assigned to you first, one chosen), the kind, the date, How many papers, Start the check with the reason it is off, and a Create a paper link.
- Entering: the check label and a line of counts (entered, approved, absent, not entered); one roll list with a chip beside it and a small image icon; Absent today; an Add the sheets card (Take a photo of this sheet, Select a folder of pictures); the question boxes; the Missed the teaching checkboxes; Approve; Previous, Next, Next not entered, Next to approve; a sticky bar with a note and Finish entering.
- The sheet picture opens in a bottom drawer, 40 percent of the height, full width, not modal.

### Desktop (1280px wide)

- The same column. The sheet picture opens in a side drawer on the right, 40 percent of the width, below the top bar; the page stays editable.

## Exact copy

- Choose a paper. Assigned to you. Create a paper. No paper for this class yet. Roll no 7 · Entered · Not approved. Add the sheets. Select a folder of pictures. Choose pictures. Missed the teaching (from my register). Approve. Finish entering. All 3 roll numbers are approved or absent.

## Reading order

- Title, label and counts, roll list, absent, add the sheets, boxes, checkboxes, approve, moves, Finish note, Finish.

## Components

Radio list, selects, chips with icon and words, file inputs as buttons, a progress bar, number fields, checkboxes, a non-modal drawer with an image, a sticky bar.

## States

- No paper. Not entered, entered, absent, approved. Reading 7 of 20 with Cancel. A picture needs a roll number. A picture from another class. Two pictures for one roll. A roll that already has answers (Replace, Keep mine). Offline or AI off (the camera and folder are off with the reason; typing works). Finish off with its reason; finished with See results and Reopen.

## Interactions

- Absent approves the roll. Any change to an approved roll needs approving again. Escape closes the drawer and returns focus to the image icon. Finish asks first.

## Do not show

- No child name, no data source, no synthetic, pilot or demo wording. Counts, never percentages.

## Accessibility and tone

- Contrast at least 4.5 to 1 in light and dark. A visible focus ring on every control. Text scales to 200 percent without clipping or sideways scroll. Every icon has a text label. Reduced motion turns transitions off.
- Tone is plain and warm, one short sentence per idea, no jargon, no pressure. Nothing here scores or judges the teacher.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons; let them wrap or grow. Hindi and Tamil strings are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
