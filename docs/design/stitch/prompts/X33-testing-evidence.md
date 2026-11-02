# X33 · Testing evidence

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Testing evidence
- Role: Judge
- Device priority: Phone and laptop

- Purpose: A judge-mode screen, and the last step of the guided tour (See who has tried it), that shows live proof of testing from the people who agreed to share: how many testers, sessions and returning testers, which roles and tours they tried, what they said, and what the team changed because of it. Nothing is seeded; with no data it says so.

## Layout

### Phone (360px wide)

- A one-column page. A title, one intro line, and a status line with the collection date range. Then a two-column grid of eight number cards, then six charts one under another (testers by day, role funnel, tour funnel, invite source, device class, language), each with a text version of its numbers beneath. Then the testers table in a horizontally scrollable region that can be reached by keyboard, the feedback list as cards, the You said, we changed list as cards, and a notes block with a toggle.

### Desktop (1280px wide)

- Content capped at 72rem. Number cards in a row of four. Charts two to a row. The table shows all columns without scrolling.

## Exact copy

- Title: Testing evidence. Intro: Live counts from people who agreed to share. Nothing is seeded or invented.
- Range: Collected between a start date and an end date. With no data: Nothing collected yet.
- Cards: Testers, Sessions, Returning testers, Roles tried (average), Tours completed, Feedback received, Average rating, Used it offline. Empty values read None yet.
- Table columns: Nickname, Device, Roles, Tours, Features, Sessions, Last seen, Rating. Testers who did not agree to be listed read Anonymous tester 01, 02 and so on.
- Empty messages: No feedback yet. No changes recorded yet. Rows are added by hand as feedback arrives.
- Change cards: a date, then You said and We changed.
- Notes: a line giving how many judge and team devices are left out, a switch Include judge and team devices, a plain list of what is collected, and a plain list of what is never collected.

## Reading order

- Title, range, number cards, charts, testers, feedback, You said we changed, notes. The headline numbers come first so a judge sees the evidence before the method.

## Components

Number cards, horizontal bar charts drawn in inline SVG with a text list under each, a data table, feedback cards with a rating line and chips, change cards, a switch, a status line.

## States

- Loading. Empty, where every number is zero or None yet and every list shows its empty message. Filled. The switch on, with judge and team devices included. Error, where the screen says the evidence is not available here. Hindi and Tamil with longer labels.

## Interactions

- The switch reloads the numbers with or without judge and team devices. Nothing on this screen edits or deletes data, and nothing links to a single person's activity.

## Do not show

- No per-person timelines, no free text in the testers table, no names beside feedback comments, no hash beyond its first six characters, no percentage next to a teacher, no invented testers or placeholder numbers.

## Accessibility and tone

- Contrast at least 4.5 to 1 in light and dark. A visible focus ring on every control. Text scales to 200 percent without clipping or sideways scroll. Every icon has a text label. Reduced motion turns transitions off. The screen reader reads the sheet title first, then each field with its label, then the actions.
- Tone is plain and warm, one short sentence per idea, no jargon, no pressure. Nothing here scores or judges the person.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons; let them wrap or grow. Hindi and Tamil strings are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
