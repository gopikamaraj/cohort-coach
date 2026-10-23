# R2 · Roadmap card: grade handoff

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Roadmap card: grade handoff
- Role: Teacher
- Device priority: Phone first
- Purpose: Show that passing a class's patterns to next year's teacher is planned, without implying it is built.

## Layout

### Phone (360px wide)

- A RoadmapCard with a lock icon, a Roadmap tag and a status line.
- A muted Tell us if this would help you link.

### Desktop (1280px wide)

- Same card beside the Next term screen.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Tag: Roadmap. Not built yet.
- Title: Grade handoff
- Promise: At the end of the year, hand the next teacher the patterns your class showed, as counts, so she starts where they are. Planned, not available.
- Status: Not built yet. It would need your agreement and the next teacher's.
- Link: Tell us if this would help you
- TODO-HUMAN(Gopi): the brief names this card but the repo does not define it; confirm the promise and the consent model before it is shown.

## Components

Use these components from DESIGN.md: RoadmapCard, StatusChip, PrivacyNote.

## States

- Default: locked.
- Interest recorded.
- Offline: identical.

## Interactions

- The link opens the feedback sheet; nothing else is tappable.

## Do not show

- Never imply it works; no data about a child would move with it.
- No teacher-level number would be shared without her agreement.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.
- A RoadmapCard is always locked: lock icon, the tag Roadmap, the words Not built yet, and no working control other than a link.
- Never draw a screenshot or a sample of the feature; a roadmap card promises nothing it cannot keep.
- Use secondary container for the card and outline for the border; no tertiary tint, because nothing needs watching.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
