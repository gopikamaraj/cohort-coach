# T4 · My track

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: My track
- Role: Teacher
- Device priority: Phone first
- Purpose: Show the three-week track on her one error: who is in the cohort, who the mentor is, which lessons are done, and the next lesson.

## Layout

### Phone (360px wide)

- Header two rows; title My track; subtitle Subtract with borrowing, 3 weeks.
- Cohort card: cohort size and number of schools, in counts.
- Mentor card: a short why-line built from facts; the mentor appears only with her consent.
- Week strip: three week chips with two lesson dots each; the current lesson is filled.
- Lesson list: six LessonCards with title, length in minutes, PlayButton, BadgeLine and a status chip (Ready, Played, Tried it).
- Model-lesson script row: a link card that opens the cached page with her own class's wrong answers.
- Time card: This week about 12 minutes of your 20.
- One primary button: Play lesson 3.

### Desktop (1280px wide)

- Same phone-first column; the lesson list becomes a two-column grid and the cohort and mentor cards sit in a right column.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: My track
- Cohort: You are in a cohort of 9 teachers in 7 schools who share this error. Your track starts now.
- Mentor: Your mentor is a teacher whose class fixed this error. She teaches in the same language as you.
- Lesson row: Lesson 3, Open one bundle, 5 min. Checked. Reviewed.
- Status chips: Ready; Played; Tried it; Not yet
- Model-lesson script: Model lesson with your class's own wrong answers
- Time card: This week: 12 minutes of your 20.
- Primary button: Play lesson 3
- Waitlist state: You are on the waiting list. Your track starts next term.
- Reassurance line: A failed track counts against the track, not you.

## Components

Use these components from DESIGN.md: TopBar, BottomNav, LessonCard, BadgeLine, StatusChip, ProgressMeter, PlayButton, PrivacyNote.

## States

- Default: lesson 3 is next and highlighted.
- Not placed yet: Cohorts are formed once enough classes have sent their check. It will show here.
- Waitlist: the waiting-list card replaces the cohort card.
- Offline: downloaded lessons show a Downloaded chip and replay; others show Needs a connection to download.
- Silent teacher: no lesson played for a week shows a calm card, Lesson 2 is waiting when you are ready, never a warning.
- Not judged: a lesson marked Not yet reads No response yet, never Failed.
- Simulated: banner and Simulated tag on the cohort figures.

## Interactions

- Play lesson opens the Lesson card and starts audio.
- A lesson row opens its Lesson card.
- The model-lesson link opens the cached script.
- The same journey also runs in Telegram; both channels show the same words.

## Do not show

- No teacher-level comparison and no score about her.
- No percentage; cohort figures are counts.
- Never the word failed for a teacher; a track that did not work is a fact about the track.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
