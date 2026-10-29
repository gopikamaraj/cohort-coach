# X29 · Assistant panel (one assistant, scoped by role)

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Assistant panel (one assistant, scoped by role)
- Role: Teacher
- Device priority: Phone first
- Purpose: Let anyone ask how the app works and get a short answer from the documents their role may read, with the sources shown and a way to check them. The same panel serves the teacher, the mentor, the coach and reviewer, the programme officer and the judge; the server decides what each may see, and the panel only shows what it is given.

## Layout

### Phone (360px wide)

- Header two rows. The title is set by the role: Your assistant, Mentor assistant, Review assistant, Programme assistant, or Judge guide.
- A two-line scope note under the title, always visible: "I can help with: ..." and "I can't see: ...", in secondary container.
- Five suggested question chips, one per row, each a full-width pill with a line icon and its text. The five change with the screen the person came from.
- A free-text field, 56px high, with a primary Ask button below it.
- The answer card appears under the chips: a small chip first (for example "pre-written from the docs"), then the answer in short paragraphs, then status lines, then Sources as links, then "How to check" and "Limits" lines.
- Footer line: "Answers come from the approved help pages. Commit 3f2a9c1."

### Judge session only

- Two tabs under the title: Assistant and About this product.
- A View as menu on the Assistant tab, listing Teacher, Mentor, Coach, Officer. While a role is chosen, the title, scope note and chips switch to that role's, on simulated data.
- On About this product, a numbered ten-minute test path: each step has a title, a link to the screen, the role to use, a sample input, and buttons for the matching questions.

### Desktop (1280px wide)

- Content capped at 720px beside the navigation rail; chips wrap two to a row. The answer card sits under the chips.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title for a teacher: Your assistant
- Scope note: I can help with: how to use the app and what each screen means. I can't see: other teachers, drafts, or anything about a child.
- Chips: What should I do today? What does this error card mean? I'm stuck, what can I try? Why was this audio chosen? How do I delete my data?
- Free-text label: Ask your own question
- Button: Ask
- Chip on a suggested answer: pre-written from the docs
- Sources heading: Sources
- How to check: How to check: open the page named under Sources.
- Limits: Limits: this answer is extracted from the help pages and may not cover your case.
- Nothing found: I could not find that in the pages I can read. Try the Practice Class help, or ask your mentor.
- Out of scope: That is outside what I can help with here. Ask your coach, or open the screen it belongs to.
- Error: The assistant could not answer. Check your signal and try again. Try again
- Judge tabs: Assistant; About this product
- View as label: View as
- Test path heading: 10-minute test path
- Status words, each with an icon and its text: Built; Partly built; Simulated; Mock; Roadmap
- Provisional note: Slide numbers and video times are provisional until the final deck and video exist.
- Simulated note: Simulated data: this class and these children are made up for the demo.

## Components

Use these components from DESIGN.md: TopBar, BottomNav, StatusChip, PlayButton, PrivacyNote, and the pill quick move for the question chips.

## States

- Default: scope note, five chips, an empty field.
- Loading: chips stay; the Ask button shows Loading and the answer card holds its place.
- Answer: the card with sources and a check line.
- No answer: the nothing-found card with where to look.
- Out of scope: the card that says what it can help with and which role or screen to use.
- Offline: suggested answers still open (they are pre-written); free text says it needs a signal.
- Error: the error line with Try again.

## Interactions

- Tapping a chip opens its pre-written answer at once.
- Typing a question and pressing Ask sends it; the answer replaces the previous one and is announced politely to a screen reader.
- A source link opens the file, the slide in the deck, or the video at the start time.
- The assistant never approves, sends or deletes anything; no answer card has a button that changes data.
- View as changes the scope on the server; the panel then reloads its chips.

## Do not show

- No names of children, no handle or phone number, and nothing about an individual teacher.
- No percentage on a teacher's panel.
- No claim stronger than the status shown beside it.
- No write action of any kind.
- No view of another role's material unless the person is the judge, using View as.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone, so every status has its word beside its icon.
- Every icon has a visible text label; reading order matches visual order; the answer card is a live region.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
