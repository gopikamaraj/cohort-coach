# X17 · Privacy notice

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Privacy notice
- Role: Teacher
- Device priority: Phone first
- Purpose: Tell a teacher in plain words what the app keeps, where, who can see it and how to erase it.

## Layout

### Phone (360px wide)

- Header two rows; title Privacy notice.
- A PlayButton at the top to hear the whole notice.
- Accordion sections with a lock icon each: What stays on your phone; What we keep; What AI services see; Who sees what; How long; Your rights.
- A table in the last section: Data item, Purpose, Where stored, How long, Who sees it, Your choice.

### Desktop (1280px wide)

- Phone-first column; the table can use the wider width.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Privacy notice
- Intro: Short version: each child's answers stay on your phone. We keep only class counts and anonymous feedback.
- Section: What stays on your phone. Your checks, each child's answers by position, your rehearsals.
- Section: What we keep. How many children showed each error in your class. Never a child's answer, a name or a photo.
- Section: What AI services see. What you type or say in the Practice Class, only if you agreed.
- Section: Who sees what. Coaches and officers see counts across classes, never one teacher's class.
- Section: Your rights. You can see, change, withdraw and erase at any time.
- Version line: Notice version 1.
- Button: Back to My profile

## Components

Use these components from DESIGN.md: TopBar, BottomNav, PrivacyNote, PlayButton, DataTable, StatusChip.

## States

- Default: all sections collapsed except the first.
- Offline: identical; the notice is stored on the phone.
- Loading and error as in the shell.

## Interactions

- Sections expand and collapse.
- Play reads the open section aloud.

## Do not show

- No legal jargon without a plain sentence beside it.
- No promise the system cannot keep; say what it does.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
