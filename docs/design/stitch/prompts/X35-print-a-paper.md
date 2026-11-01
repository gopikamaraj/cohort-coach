# X35 · Print a paper for this check

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Print a paper for this check
- Role: Teacher
- Device priority: Phone first

- Purpose: Inside Start a check, a collapsible card where she makes the paper for this check: the pilot paper (answers entered on this phone) or a new paper for her class (printed and marked by hand with its key), built by code from her last check's class counts, four short questions, or the standard paper.

## Layout

### Phone (360px wide)

- A collapsible card titled Print a paper for this check. Two radio rows (the pilot paper, a new paper). For a new paper: a muted note, a line saying where the paper comes from, and a button to answer four short questions (what the class finds hard, which topics were taught, children in the class, whether they took a test like this before). A language select (English, Hindi, Tamil, English and Hindi). The primary button Make the paper. Then the paper view: the check code in bold, a status chip, a source line, Anchor items with a one-line note and a numbered list, Adaptive items with a one-line note, Not on this paper when a topic was not taught, a coverage grid (errors as rows, item numbers as columns, a dot where an item checks an error, a count column), Automatic checks, and buttons Print the paper, Print the answer key, Show the answers. A status line says the post-test twin was made.

### Desktop (1280px wide)

- The same, in the content column of Start a check.

## Exact copy

- The pilot paper (Form A): answers can be entered on this phone. A new paper for this class: print it and mark it by hand with its answer key.
- Anchor items: The same skills and level on every paper. Before and after are compared on these only.
- Adaptive items: Extra items on what this class finds hard. For finding errors only, never to claim improvement.
- Its post-test twin (Form B) was made with it: the same skills, new numbers. It is frozen until the track ends.

## Reading order

- The choice, where the paper comes from, language, Make the paper, then the paper top to bottom.

## Components

Radio rows, checkboxes, a number field, a select, a primary button, cards, a data table in a scrollable region, chips, a status line.

## States

- Closed card. Pilot chosen. New chosen with the standard paper, with past counts, with intake answers. Making. Made and approved. Made and waiting for a reviewer (Print disabled). Cannot be made, naming the rule. Offline.

## Interactions

- Make the paper sends the choice, the class counts and the language; the server builds the paper. Print opens the PDF. A pilot paper made here is attached to the check when she starts on that paper, and its code shows in the check header.

## Do not show

- No child or roll number. No percentage: the source line and grid show counts. No AI badge: the paper is made by code.

## Accessibility and tone

- Contrast at least 4.5 to 1 in light and dark. A visible focus ring on every control. Text scales to 200 percent without clipping or sideways scroll. Every icon has a text label. Reduced motion turns transitions off. Scrolling tables can be reached by keyboard.
- Tone is plain and warm, one short sentence per idea, no jargon, no pressure. Nothing here scores or judges the teacher.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons; let them wrap or grow. Hindi and Tamil strings are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
