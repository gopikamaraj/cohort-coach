# X38 · Import a paper from a PDF

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Import a paper from a PDF
- Role: Teacher, Mentor, Coach
- Device priority: Phone first

- Purpose: On the Papers page, bring in a paper already used: upload a PDF or up to three photos, check what was read beside the page image, answer the assistant's open questions one at a time, and confirm. The AI reads only the printed questions; code computes every answer.

## Layout

### Phone (360px wide)

- An upload card with a plain privacy note and one primary button. After reading: the uploaded page above an editable table (item, operation, first number, second number, computed answer, include tick), small chips for unsure, photos disagree, printed answer differs and not supported yet. Class, kind and form fields. A coverage list of which items check each error with a warning when fewer than two. A side card titled The assistant asks: one question, why it matters, answer chips or a box, and I don't know. Under each changed field a chip Assistant changed this with the previous value and an Undo button. Buttons Confirm the paper, Undo, Discard this upload.

### Desktop (1280px wide)

- The page image on the left, the table and the assistant card on the right, Confirm below.

## Exact copy

- Only the printed questions are read. Handwriting and names are ignored and not kept. The upload is deleted when you confirm, or after 24 hours.
- Confirm stays off until open questions are answered.
- Imported, awaiting review.

## Reading order

- Upload, the page, class kind form, the table, coverage, the assistant card, the buttons.

## Components

File input, a table in a scrollable region, number fields, ticks, selects, chips, a side card, primary and secondary buttons.

## States

- Loading: a short line says what is happening. Empty: one plain sentence and the next action. Error: what happened and what to do. Offline: the page says it needs a connection to read an upload.

## Interactions

- Choosing the file sends it to be read; a short line says Reading the paper while it works. Editing a number, the class, the kind, the form or an include tick sends one change and the table recomputes every answer and the coverage list at once. Choosing an answer chip in the assistant card sends the same change a typed edit would, marks it Assistant changed this with the previous value, and moves to the next question. I don't know leaves the question open and says what that means. Undo puts back the last change. Confirm the paper turns the draft into a paper that can be used for a check; Discard this upload deletes the pages at once.
- A question that blocks Confirm is shown first. A dictated item asks which number was said. An item the system cannot score yet, such as a word problem, can be left out or entered by hand as an addition or a subtraction.
- If two photos of one paper disagree on a number, the row says The photos disagree and asks for the number. If a printed answer differs from the computed one, the row says so and Confirm stays off until she chooses.

## Do not show

- No child name, no handwriting and no answer a child wrote. The page image is shown only while she reviews it. No percentage. No AI badge on the computed answers: code works them out, and the screen says so in the note. Nothing the assistant says is a score or a judgement of a teacher or a child. The assistant never presses Confirm.
