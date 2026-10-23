# X20 · Mentor dashboard

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Mentor dashboard
- Role: Mentor
- Device priority: Phone first, desktop for review
- Purpose: Show a mentor her cohorts and where each recording stands, without any teacher-level numbers.

## Layout

### Phone (360px wide)

- Header two rows; title Mentor.
- Cohort dropdown (56px) with a StatusChip: Proposed, Active, Closing, Closed.
- Cohort summary card: size and schools in counts, and the week of the track.
- Recordings list: each with its status chip and a note when changes are requested.
- Time card: This week 14 of 30 minutes.
- Buttons: Open cohort chat (primary), Record a method.

### Desktop (1280px wide)

- Two columns: cohort summary and time on the left, recordings table on the right.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Mentor
- Intro: A mentor is a teacher whose class fixed an error. Your way of teaching helps the next cohort.
- Dropdown option: Subtract, smaller from larger. Hindi. Active.
- Summary: 9 teachers in 7 schools. Week 2 of 3.
- Recording row: What you do first. Approved. In use.
- Recording row: Which materials. Awaiting coach. 2 days.
- Change note: Changes requested: say the exact words you use.
- Time: This week 14 of 30 minutes.
- Buttons: Open cohort chat; Record a method
- Statuses: Draft; Submitted; Awaiting coach; Changes requested; Approved; In use; Retired

## Components

Use these components from DESIGN.md: TopBar, NavRail, StatusChip, DataTable, ProgressMeter, VoiceRecorder.

## States

- Default: one active cohort.
- Empty: You are not mentoring a cohort yet. Invitations come after the next check shows whose class fixed the error.
- In use only after a published track version includes the item.
- Offline: recordings wait in the outbox.
- Simulated: banner.

## Interactions

- Selecting a cohort changes the summary and the recordings.
- Open cohort chat opens the thread.

## Do not show

- Never a cohort she does not mentor.
- Never a number about any teacher's class.
- In use is shown only after a published track version includes the item.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
