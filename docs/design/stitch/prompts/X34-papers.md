# X34 · Papers

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Papers
- Role: Teacher, Coach
- Device priority: Phone first

- Purpose: The check papers of a class, made by code from approved rules (no AI), with their status and a Print button for the teacher; for the coach, who is the reviewer, the papers waiting for review and the paper rules.

## Layout

### Phone (360px wide)

- One column. Title and one intro line. Teacher: a list of paper cards (check code in bold, language, a status chip, a Frozen chip when sheets are in) with an Open button that expands the paper view (X35 shows its parts). Coach: a list of queue cards (check code, language, a reason chip) that expand into the paper view with Approve, a reason field and Reject; then Paper rules: the version in use, a scrollable table of item templates (skill, digit pattern, errors it checks), and a card per version (status chip, written by and approved by, the lines that changed, Export as YAML, Test these rules).

### Desktop (1280px wide)

- Content capped at 72rem. Queue on the left, rules on the right.

## Exact copy

- Title: Check papers. Intro: Papers are made by code from approved rules. No AI writes them. Only approved papers can be printed.
- Status chips: Approved by the rules, Waiting for a reviewer, Approved by a reviewer, Rejected, Frozen.
- Queue reasons: Changed by hand, Failed an automatic check, Wording not yet reviewed in this language, Spot check of an approved paper.
- Rules: In use: rules version 1. Written by a pseudonymous id; approved by a pseudonymous id.

## Reading order

- Title, intro, the teacher's papers or the coach's queue, then the rules.

## Components

Cards, chips, buttons, a text field, a data table in a scrollable region, a status line.

## States

- Loading. Empty (No papers for this class yet; Nothing is waiting). Filled. A paper that failed a check, whose Approve button is disabled. Offline: Could not reach the server. Hindi and Tamil.

## Interactions

- Open expands a paper. Approve and Reject (with a reason) act on one paper and refresh the queue. Export downloads the rules as YAML. Test these rules runs every automatic check on a sample paper per blueprint and says how many passed.

## Do not show

- No child, roll number or answer of a child. No AI badge: nothing here is AI. No percentage. No teacher name: reviewers see pseudonymous ids only.

## Accessibility and tone

- Contrast at least 4.5 to 1 in light and dark. A visible focus ring on every control. Text scales to 200 percent without clipping or sideways scroll. Every icon has a text label. Reduced motion turns transitions off. Scrolling tables can be reached by keyboard.
- Tone is plain and warm, one short sentence per idea, no jargon, no pressure. Nothing here scores or judges the teacher.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons; let them wrap or grow. Hindi and Tamil strings are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
