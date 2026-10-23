# T1 · Home

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Home
- Role: Teacher
- Device priority: Phone first
- Purpose: Show where this term stands for one class and offer the single next thing to do.

## Layout

### Phone (360px wide)

- Header, two rows: row one is the title Home and the Works offline pill; row two is the EN / हिं / தமி switch and the account button.
- Class chip row: the active class name and a small Simulated tag when the class is made up.
- Status card (16px, outlined): a PlayButton on the left, the status sentence, and the focus line beneath it.
- One primary button, 48px, full width, label changes with state (see Exact copy).
- Two quiet text buttons under it: Practice with the children, My programme.
- Privacy card with a lock icon, a short sentence and a secondary button Review and choose.
- Outbox line at the bottom of the content: result waiting to send, or all results sent.
- Bottom navigation: Home, Enter check, My class, Practice, More.

### Desktop (1280px wide)

- Left rail with the same destinations; top bar with title Home and subtitle Term 2.
- Content in a 12-column grid capped at 1280px: status card spans 7 columns, privacy card spans 5.
- The primary button sits inside the status card; the two quiet buttons sit under the privacy card as links.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Home
- Subtitle: Term 2
- Status when nothing is entered: You have not entered this term's check yet.
- Status after a check: You checked 28 children this term.
- Focus line: Your class's focus: take the smaller digit from the larger.
- Focus line when none: No focus is chosen yet.
- Primary button before a check: Enter this term's check
- Primary button after a check: See what my class gets wrong
- Quiet buttons: Practice with the children; My programme; What I entered
- Privacy card title: Your privacy choices
- Privacy card body: Nothing is shared until you say so. Read how your data is used and choose.
- Privacy card button: Review and choose
- Outbox: 1 result waiting to send. / All results sent.
- Simulated banner when the class is made up: Simulated data: this class and these children are made up for the demo.

## Components

Use these components from DESIGN.md: TopBar, BottomNav, OfflinePill, LangSwitch, AccountButton, SimulatedBanner, PlayButton, StatusChip, PrivacyNote.

## States

- Default: after a check, the primary button opens What my class gets wrong.
- Empty: no check yet, primary button Enter this term's check, no focus line.
- Loading: card skeletons in outline colour only, no shimmer gradient.
- Offline: the pill reads Works offline in primary container; every card still opens; the outbox line explains what will send later.
- Error: a tertiary card says what happened and what to do, with a Try again button.
- Simulated: banner on top; the focus line carries a Simulated tag.

## Interactions

- Tapping the play button reads the status sentence aloud in her language.
- Primary button routes to Enter check or to What my class gets wrong, depending on state.
- Review and choose opens the profile privacy section.
- Switching language changes every string at once without a reload.

## Do not show

- No percentages anywhere; the status is a count of children.
- No second primary button; the quiet buttons are text buttons.
- No leaderboard, no comparison with other teachers, no score about her.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
