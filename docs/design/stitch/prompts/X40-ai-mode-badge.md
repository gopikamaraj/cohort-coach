# X40 · AI mode badge and Recorded AI answer label

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: AI mode badge and Recorded AI answer label
- Role: Every role
- Device priority: Phone first

- Purpose: Say plainly, on every screen that uses the AI, when the AI is not live, so a replayed answer is never taken for a live one and a missing AI never blocks the work.

## Layout

### Phone (360px wide)

- A small badge in the title bar, AI: recorded answers or AI: off, beside the online pill. A chip reading Recorded AI answer beside each replayed answer. In off mode, a one-line note under each AI feature with the way to carry on without it.

### Desktop (1280px wide)

- The same badge and chips in the top bar and beside the answers.

## Exact copy

- AI: recorded answers. AI: off. Recorded AI answer. Reading a photo needs the AI, which is off right now. Type the answers in the boxes; nothing you typed is lost.

## Reading order

- Badge, then the feature, then its chip or note.

## Components

A pill, a chip, a note line.

## States

- Live (no badge). Recorded. Off.

## Interactions

- None. The badge and chips are read-only. Tapping a note's link, where it has one, opens the non-AI way to do the same job: typing the answers in the boxes, the code's template for a lesson, a person for a chat question, Generate from rules for a paper, the set lines of the Practice Class.
- The badge never moves the layout. On a narrow phone it drops under the title; it keeps its words and its icon, and never relies on colour alone.
- Screen readers hear the badge as a status line once when the page opens, and the Recorded AI answer chip is read with the answer it labels.

## Do not show

- Never present a recorded answer as live. Never hide that the AI is off.

## Accessibility and tone

- Contrast at least 4.5 to 1 in light and dark. A visible focus ring on every control. Text scales to 200 percent without clipping or sideways scroll. Every icon has a text label. Reduced motion turns transitions off.
- Tone is plain and warm, one short sentence per idea, no jargon, no pressure. Nothing here scores or judges the teacher.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons; let them wrap or grow. Hindi and Tamil strings are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
