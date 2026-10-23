# X11 · Lesson card and model run

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Lesson card and model run
- Role: Teacher
- Device priority: Phone first
- Purpose: Let a teacher hear one five-minute lesson, then hear the move done well in a short model run, then open the Practice Class.

## Layout

### Phone (360px wide)

- Header two rows; title Lesson 3; subtitle Open one bundle.
- Lesson card: a large PlayButton, a seek bar, the length and size, the BadgeLine, and a Downloaded chip.
- Text card with the lesson words and a second PlayButton (audio first, text second).
- Model-lesson script row with her class's own wrong answers.
- Model run card: Hear it done well, 3 minutes, labelled Simulated, with a PlayButton.
- One primary button: Open the Practice Class.

### Desktop (1280px wide)

- Phone-first column; the text card sits to the right of the audio card on wide screens.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Lesson 3
- Subtitle: Open one bundle. 5 minutes.
- Badge line: Checked. Reviewed by the programme team.
- Size: About 0.6 MB. Downloaded for offline.
- Lesson words: Today we open one bundle of ten and trade it for ten loose sticks, so we can take away without a wrong turn.
- Model-lesson script: Model lesson with your class's own wrong answers
- Model run: Hear it done well. 3 minutes. Simulated children.
- Practice link: Open the Practice Class
- After lesson: Tried it in class? Yes; Not yet
- Offline: Needs a connection to download. Downloaded lessons play offline.

## Components

Use these components from DESIGN.md: TopBar, BottomNav, LessonCard, PlayButton, BadgeLine, StatusChip, ProgressMeter.

## States

- Default: not played.
- Playing: seek bar and a pause icon with the word Pause.
- Downloaded and Needs a connection to download.
- Silent teacher: no lesson played for a week; a gentle card, never a warning.
- Loading and error as in the shell.
- Simulated: the model run is always labelled Simulated.

## Interactions

- Play and pause; the seek bar moves by ten seconds.
- Open the Practice Class opens the web app screen.
- The same lesson plays as a voice note in Telegram with the same badge line.

## Do not show

- Never say listened or watched; delivery and play are not shown as adoption.
- No percentage and no score.
- No lesson over five minutes.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
