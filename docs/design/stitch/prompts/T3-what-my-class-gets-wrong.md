# T3 · What my class gets wrong

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: What my class gets wrong
- Role: Teacher
- Device priority: Phone first
- Purpose: Say in plain words which mistakes children in her class make and how many, and mark the one she should work on.

## Layout

### Phone (360px wide)

- Header two rows; title What my class gets wrong.
- Summary line: 28 children checked.
- Focus card first, in primary container, with the focus tag and the example.
- Other error cards below, outlined, in order of count: each has a PlayButton, the count sentence, an example row and nothing else.
- A muted card at the end for errors no child showed.
- One primary button pinned above the bottom bar: See where it most likely went wrong (leads to the stage lines) or, when a track exists, Open my track.

### Desktop (1280px wide)

- Phone-first column of 440px centred; the stage lines open as a side panel to the right on screens wider than 1024px.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: What my class gets wrong
- Summary: 28 children checked.
- Focus card sentence: 11 of 28 children take the smaller digit from the larger.
- Example: From your class: 52 - 29 gives 37.
- Focus tag: This is the focus for your class.
- Second card: 5 of 28 children forget the carried ten. From your class: 47 + 25 gives 62.
- Third card: 3 of 28 children borrow a ten but do not reduce the tens digit.
- Empty card: No child showed this error.
- Small class: Fewer than 10 children were checked, so no focus is chosen yet.
- Untracked note: 2 of 28 children wrote the whole ones total in the answer.
- Button: See where it most likely went wrong

## Components

Use these components from DESIGN.md: TopBar, BottomNav, ErrorCard, PlayButton, StatusChip, SimulatedBanner.

## States

- Default: focus card plus two or three other cards.
- Empty: No results yet. Enter this term's check first, with a button to Enter check.
- Small class: the small-class card replaces the focus card.
- Loading: outlined skeleton cards.
- Offline: identical; computed on the phone.
- Simulated: banner and a Simulated tag on the counts.

## Interactions

- Each play button reads the count sentence and the example aloud.
- The primary button opens the stage lines.
- A card is not tappable except its play button; the screen is for reading.

## Do not show

- Never a percentage and never a bar chart of children; counts in words only.
- No child names and no list of which children made the mistake.
- No ranking of her class against others.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
