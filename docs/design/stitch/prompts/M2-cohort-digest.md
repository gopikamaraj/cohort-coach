# M2 · Cohort digest

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Cohort digest
- Role: Mentor
- Device priority: Desktop first
- Purpose: Show a mentor the themes in this week's teacher reflections and let her answer the cohort with one voice note.

## Layout

### Phone (360px wide)

- Header two rows; title Cohort digest.
- Week selector pill: Week 2 of 3.
- Theme cards stacked: a theme name, a count of reflections, and two short anonymous example phrases.
- Reply card with a VoiceRecorder and a note about the cap.

### Desktop (1280px wide)

- Left: a list of five themes with a count each and a small bar made of counts, never percentages. Right: the selected theme with its phrases.
- Bottom right: the reply recorder.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Cohort digest
- Subtitle: Week 2 of 3. 9 teachers, 6 reflections.
- Theme 1: Children opened a bundle by themselves. 4 reflections.
- Theme 2: Not enough bundles for the whole class. 3 reflections.
- Theme 3: Children were quieter than expected. 2 reflections.
- Example phrase: We used sticks from the school garden.
- Reply prompt: Record one voice note for your cohort. Up to 2 minutes.
- Source label: Self-report from voice reflections.
- Button: Send reply
- Suppression: Fewer than 5 reflections this week, so themes are hidden.

## Components

Use these components from DESIGN.md: TopBar, NavRail, DataTable, StatusChip, VoiceRecorder, SuppressionNote, PrivacyNote.

## States

- Default: themes with counts.
- Empty: No reflections yet this week.
- Suppressed: fewer than 5 reflections, themes hidden with the reason.
- Loading, offline and error as in the shell.
- Simulated: banner.

## Interactions

- Selecting a theme shows its phrases.
- Record and send one reply; the coach approves it before teachers hear it.

## Do not show

- No names, schools or teacher-level rows.
- No quotes that could identify a child or a teacher.
- No percentage; counts only.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
