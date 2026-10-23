# M1 · Invitation and method capture

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Invitation and method capture
- Role: Mentor
- Device priority: Phone first, desktop for editing
- Purpose: Invite a teacher whose class fixed an error to record her method by voice, check the written card and approve it for the coach.

## Layout

### Phone (360px wide)

- Header two rows; title Share how you fixed it.
- Why card in primary container: a sentence built from facts about her class's change, in counts.
- Consent card with a switch: Show my name and my class's improvement to my cohort.
- Four prompt cards stacked, each with a PlayButton (the prompt read aloud), a VoiceRecorder (record, stop, play back) and a status chip (Not recorded, Recorded, Approved).
- Method card section after recording: steps, materials, exact phrases and timing, each as an outlined row with an edit icon and text label Edit.
- Primary button: Send for approval.

### Desktop (1280px wide)

- Two columns: the recorder prompts on the left; the editable method card with citations on the right, each step showing the sentence it came from.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Share how you fixed it
- Why: Your class went from 20 of 32 children to 10 of 32 on this error. Other teachers could learn from how you taught it.
- Consent: Show my name and my class's improvement to my cohort
- Prompt 1: Say what you do first
- Prompt 2: Say which materials you use and how
- Prompt 3: Say the exact words you use
- Prompt 4: Say how long it takes and when
- Recorder: Record; Stop; Play back; Record again
- Card headings: Steps; Materials; Words you say; Time
- Statuses: Draft; Submitted; Awaiting coach; Changes requested; Approved; In use
- Time note: This takes about 20 minutes once. After that, about 10 minutes a week.
- Primary button: Send for approval

## Components

Use these components from DESIGN.md: TopBar, BottomNav, VoiceRecorder, PlayButton, StatusChip, PrivacyNote, DataTable.

## States

- Default: first prompt open, others collapsed.
- Recording: waveform bars either side of the stop button, a timer, a two-minute cap.
- Transcribing: a calm progress line, then the transcript sentences numbered.
- Card ready: steps with their source sentences; a phrase she edited is marked.
- Awaiting coach: the whole screen is read-only with a status chip.
- Changes requested: a tertiary card with the coach's reason in plain words.
- Offline: recordings wait in the outbox with a Waiting to send chip.
- Simulated: banner when the mentor is made up.

## Interactions

- Record and stop per prompt; playing back is local.
- Editing a step changes only the card text; the approval is hers.
- Send for approval moves the item to Awaiting coach.

## Do not show

- No numbers about any other teacher's class.
- No names of children; a recording that says one is stopped before it is saved.
- The recording never reaches teachers before the coach approves it.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
