# X1 · Landing page and role picker

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Landing page and role picker
- Role: Judge
- Device priority: Desktop first, works on a phone
- Purpose: Let a judge or a signed-in person choose a role and read what that role can and cannot do before entering.

## Layout

### Phone (360px wide)

- Header two rows; title Who are you today?
- Tour card first, in primary container, with the tag Start here if you're judging.
- Four RoleCards stacked, equal width: Teacher, Mentor, Coach, Programme officer. Each has an icon, one line of what the role does, and who holds it.
- Scope dialog opens as a full-height sheet from the bottom.

### Desktop (1280px wide)

- Four RoleCards in an equal grid that follows the width (four across at 1280px, two by two below 900px), tour card spanning the full width above.
- Scope dialog is a centred 560px dialog.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Who are you today?
- Intro: Pick a role to see what it can and cannot do. Everything here is simulated data.
- Tour card: Guided tour (5 min). Start here if you're judging.
- Teacher card: Check your class, rehearse the fix, follow a 3-week track. A Grade 3 teacher.
- Mentor card: Record how your class fixed an error, so the next cohort can learn it. A teacher whose class fixed the same error.
- Coach card: Approve recordings and lessons, and keep the cohort chat safe. A BRC, CRC, DIET faculty member or head teacher.
- Officer card: Approve cohorts and read results across the block. Block or district programme staff.
- Dialog blocks: You can; You can't; Data you'll see; Also on; Weekly time
- Dialog buttons: Enter dashboard; 60-second walk-through; Back
- Weekly time lines: At most 20 minutes a week (teacher); At most 30 minutes a week (mentor and coach); One weekly batch; no minute cap set yet (officer)
- Officer boundary: See a teacher's class: counts only, and nothing under 5 classes.

## Components

Use these components from DESIGN.md: TopBar, RoleCard, ScopeDialog, SimulatedBanner, StatusChip.

## States

- Default: all four cards selectable in judge mode.
- Production: only the roles she holds appear; a single role goes straight to the dashboard.
- Dialog open: focus trapped, Escape closes.
- Loading and error as in the shell.
- Simulated: banner at the top.

## Interactions

- Tapping a card opens its dialog.
- Enter dashboard saves that the dialog was seen and opens the role's home.
- 60-second walk-through starts the tour at that role's step.

## Do not show

- No login form and no password.
- No role selectable by changing something on the phone in production.
- No percentage on any teacher card.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
