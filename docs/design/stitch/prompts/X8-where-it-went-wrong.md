# X8 · Where it most likely went wrong

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Where it most likely went wrong
- Role: Teacher
- Device priority: Phone first
- Purpose: Group the mistakes by where in her children's thinking they most likely arose, with a one-minute check for each group.

## Layout

### Phone (360px wide)

- Header two rows; title Where it most likely went wrong.
- Note card: These are most likely, not certain.
- Stage cards stacked: stage name, count lines, a ProbeNote and a PlayButton.
- Missed-teaching lines per concept under the cards.
- One primary button: Open my track.

### Desktop (1280px wide)

- Phone-first column; probes in a two-column grid on wide screens.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Where it most likely went wrong
- Note: These are most likely, not certain: final answers cannot prove a cause. A child can appear on more than one line.
- Stage: The idea or the method. 11 of 28 children: take the smaller digit from the larger.
- Stage: Heard or read the question differently. 2 of 28 children: answered as if the sign were the other way round.
- Stage: How the answer was written down. 2 of 28 children: had the right answer but wrote its digits the wrong way round.
- Stage: May not have received the idea. 1 of 28 children: gave answers that follow no pattern we know.
- Probe: One-minute check: ask her to show the same question with bundles and say each step aloud.
- Missed teaching: 2 children missed the teaching on subtraction with borrowing. Their answers there are not counted above.
- Blank line: 1 of 28 children left most of the subtraction blank.
- Layout note: the counts on the lines other than the first are illustrative, to show the shape of the card.
- Button: Open my track

## Components

Use these components from DESIGN.md: TopBar, BottomNav, StageLine, ProbeNote, PlayButton, StatusChip.

## States

- Default: two to four stage cards.
- Empty: No stage lines yet; enter the check first.
- Small class: a note says too few children for stage lines.
- Offline: computed on the phone.
- Simulated: banner.

## Interactions

- Play reads a stage card aloud.
- A probe is text only; nothing to submit.
- Open my track continues to the track.

## Do not show

- Never state a stage as a cause; always most likely.
- Never show a stage or a tag for one child; counts only.
- Never show this to a child; no judgement of the child or the teacher.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
