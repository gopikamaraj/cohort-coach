# X39 · Paper details, Assign, Assigned to you, Choose a paper

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Paper details and assigning
- Role: Teacher, Mentor, Coach
- Device priority: Phone first

- Purpose: On the Papers page: tabs for one paper (overview, questions, coverage, usage and cohorts, history, files), an Assign panel with who, dates and a note, an Assigned to you card, and in Enter check a Choose a paper list.

## Layout

### Phone (360px wide)

- A paper row with buttons Open, Details, Assign. Details opens tabs as chips. Assign opens a card with a select (a class or a cohort with its class count), start and due dates, a note field and a primary Assign button. The Assigned to you card lists kind, form and due date with a Start this check button. In Enter check a Choose a paper fieldset of radio rows (form, kind, items, source, a cohort chip) and a link Create a paper.

### Desktop (1280px wide)

- The same, in the content column.

## Exact copy

- Cohorts form from the pre-test results, so a pre-test goes to teachers or classes.
- Locked: the first sheet of a check is entered. Make a new version to change it.
- Mark this paper by hand with its key. The phone knows the pilot Forms A and B only.

## Reading order

- The paper row, its tabs, the assign card; then Assigned to you; then Choose a paper.

## Components

Tabs as chips, cards, selects, date fields, radio rows, chips, primary and secondary buttons.

## States

- Loading: a short line says what is happening. Empty: one plain sentence and the next action. Error: what happened and what to do. Offline: the page says it needs a connection to read an upload.

## Interactions

- Details opens one paper's tabs without leaving the list. Questions lists each item as a sum with its computed answer. Coverage lists which items check each error. Usage and cohorts gives counts: how many assigned, opened and completed, and whether cohorts have formed with the reason if not. History lists what happened and who did it, by role. Files says that an imported paper is already printed, so the system does not print it.
- Assign sends the paper, the class or the cohort, the kind, the form, the dates and the note. A pre-test is offered to classes only, because cohorts form from its results. One assignment is made for each class in a cohort. A message says if the pre-test a post-test twins was never assigned.
- In Enter check, choosing a paper starts the check with the right kind and form. The paper assigned to her is listed first and the suggested form is already chosen. A paper the phone cannot score says Mark this paper by hand with its key.

## Do not show

- No child, no roll number, no name of a teacher. Progress is counts only: assigned, opened, sheets entered and completed. No percentage to a teacher. The note field accepts no phone number, handle or link. The assistant prepares nothing here that a person has not pressed.
