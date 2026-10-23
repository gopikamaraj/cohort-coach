# T2 · Check entry

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Check entry
- Role: Teacher
- Device priority: Phone first
- Purpose: Let a teacher type the ten answers of each child in roll order in under five minutes for 30 children, on the phone's own number keyboard.

## Layout

### Phone (360px wide)

- Header two rows as in the shell; title Enter the check.
- Helper line in muted text: Enter the papers in roll order. Only your phone knows which paper is which child.
- Sheet picker: a 56px select with the label Choose a child's sheet; each option reads Child 7, entered or Child 8, absent.
- Absent toggle row: a switch with the label Absent today: skip this roll number.
- Answer grid, two columns of AnswerBox cards. Each card has the label Question 3, a 56px numeric input, and two small toggles under it: Blank and a Can't read mark.
- Concept tags card titled Missed the teaching (from my register) with three checkboxes, one per concept.
- Secondary button with a camera icon: Take a photo of this sheet.
- Footer row: Previous child and Next child buttons; the Next child button is the primary action.
- A thin status line: 10 children entered, 1 absent, Saved on this phone.

### Desktop (1280px wide)

- Teacher screens stay phone first: on desktop the same layout sits in a 440px column inside the 1280px content area, with a read-only preview of the sheet list on the right.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Enter the check
- Form choice (first visit): Which form did you use? Form A / Form B
- Child heading: Child 4
- Question label: Question 7
- Placeholders: dash for empty; blank; can't read
- Marks: Blank; Can't read
- Absent: Absent today: skip this roll number
- Absent note: Skipped. The roll number is kept, so the next papers stay in register order, and this child is not counted.
- Concept tag 1: Missed the teaching on place value (questions 1-2)
- Concept tag 2: Missed the teaching on addition with carrying (questions 3-5)
- Concept tag 3: Missed the teaching on subtraction with borrowing (questions 7-10)
- Count line: 10 children entered, 1 absent. Saved on this phone.
- Buttons: Previous child; Next child; Finish and see my class
- Sample sheet button, judge mode only: Use sample sheets

## Components

Use these components from DESIGN.md: TopBar, BottomNav, SheetPicker, AbsentToggle, AnswerBox, MarkToggle, ConceptTag, PhotoCapture, StatusChip, PrivacyNote.

## States

- Default: first empty child, question 1 focused, the phone's numeric keyboard open.
- Filled child: every AnswerBox shows its digits; the picker option reads entered.
- Absent child: the grid and tags collapse and the absent note shows; Next child is still primary.
- Blank or can't read marks: the input shows a dashed border and the word in muted text; typing replaces it.
- Low-confidence read (after a photo): boxes the reader was unsure of get a tertiary container and the word Check this.
- Offline: nothing changes; the line says Saved on this phone.
- Error: if autosave fails, a tertiary banner says it and offers Save a backup.
- Simulated: banner on top when the class is made up.

## Interactions

- Typing digits fills a box; the Enter key moves to the next question; digits in Hindi or Tamil script are shown as 0 to 9.
- The sheet picker jumps to any child and shows what was entered.
- Toggling Absent clears nothing silently: if answers exist, a dialog asks first.
- Checking a concept tag applies only to this child and only to that concept.
- Finish and see my class diagnoses on the phone and opens What my class gets wrong.

## Do not show

- No on-screen keypad of our own; the phone's number keyboard is used.
- No child name field, no roll-number field: the position in the list is the roll order.
- No percentages, no per-child result, no score.
- Do not show the tags or an absent child to anyone else; they stay on the phone.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
