# X27 · Materials tray and avatar expressions

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Materials tray and avatar expressions
- Role: Teacher
- Device priority: Phone first
- Purpose: Define how the Practice Class materials tray and the five avatars look, so every state is readable without colour.

## Layout

### Phone (360px wide)

- Component sheet in one column.
- Tray: three SpriteTiles in a row (bundles of ten, loose sticks, place-value chart), each at least 56px with its word beneath.
- Help line under the tray.
- Avatar sheet: one avatar with each expression: neutral, thinking, confused, got it, wrong answer, shy, distracted, each with its StateTag.

### Desktop (1280px wide)

- The same sheet in a 12-column grid.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Tray tiles: Bundles of ten; Loose sticks; Place-value chart
- Tray help: Tap a tool to show it to the children, as if you held it up. Bundles of ten and loose sticks show the number as tens and ones. The place-value chart is for reference only.
- Avatar labels: Ready; Listening; Confused; Got it; Wrong answer; Quiet; Distracted
- Tag words: Ready; Listening; Confused; Quiet
- Alt text example: A child with a worried face. Confused.
- Mouth frames: Closed; Open (while audio plays)
- Count example: 5 bundles and 2 sticks. Tens 5. Ones 2.

## Components

Use these components from DESIGN.md: MaterialsTray, SpriteTile, ChildAvatar, StateTag, BoardCard.

## States

- Default tray with three tiles.
- Tile pressed and tile disabled while a reply is playing.
- Each avatar expression with its tag.
- Reduced motion: no animation; the open-mouth frame shows as a static state.
- High-contrast palette: shapes and outlines carry meaning without colour.

## Interactions

- Tapping a tile counts as using the material.
- The speaking child's avatar shows the open mouth while audio plays.

## Do not show

- No real child's face, no photo, no name, no gender, caste, religion or disability marker.
- No text inside the pictures.
- No meaning by colour alone.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
