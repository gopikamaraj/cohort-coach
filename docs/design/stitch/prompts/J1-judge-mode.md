# J1 · Judge mode

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Judge mode
- Role: Judge
- Device priority: Desktop first
- Purpose: Give a judge a no-login control room: load a simulated class, switch language, simulate offline, advance the term and open the AI map.

## Layout

### Phone (360px wide)

- Single column of control cards with the test script as a numbered list.

### Desktop (1280px wide)

- Left: test script card with nine numbered steps, each with an Open button.
- Right: control card with Load a simulated class, term chip with Advance to Term 2, Simulate offline, Clear this phone.
- Bottom: For judges card with links to the AI map and the audit trail.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Judge mode
- Intro: A five-minute tour. No login. Everything marked simulated is made up.
- Step 1: Load a simulated class of 28 children.
- Step 2: Open Home and read the one next action.
- Step 3: Open Enter check and type the answers for one child.
- Step 4: Open My class and read the cards. They show how many children, as counts.
- Step 5: Switch the language to Hindi or Tamil.
- Step 6: Turn on offline mode and open My class again.
- Buttons: Load a simulated class; Advance to Term 2; Simulate offline; Go back online; Clear this phone
- Confirmation: Simulated class loaded: 28 children.
- Links: AI map; Audit trail

## Components

Use these components from DESIGN.md: TopBar, NavRail, SimulatedBanner, StatusChip, RoleCard.

## States

- Default: nothing loaded, Load a simulated class is primary.
- Loaded: confirmation and the step list becomes active.
- Term 2: the term chip changes.
- Offline simulated: pill reads Offline mode is on for the demo.
- Error: a tertiary card with Try again.

## Interactions

- Each step button opens the matching screen.
- Advance to Term 2 changes the data the other screens read.
- Clear this phone empties local data after a confirmation.

## Do not show

- Never reachable in a production deployment; the server decides who is a judge.
- No real data; the banner is always visible.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
