# X10 · After you try it in class

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: After you try it in class
- Role: Teacher
- Device priority: Phone first
- Purpose: Let a teacher say, in two taps, whether her real children were like the pretend ones, so the simulator can improve.

## Layout

### Phone (360px wide)

- Header two rows; title After you try it in class.
- Question card: Were your real children like the pretend ones? Three choices as large pills.
- Differences card: a set of chips she can select, any number.
- Note with a lock icon.
- Primary button: Save what I saw.

### Desktop (1280px wide)

- Phone-first column.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: After you try it in class
- Question: Were your real children like the pretend ones?
- Choices: Very like; A little like; Not like
- Differences: What was different? Choose any.
- Chips: Their mistakes were different; The mistake was easier to fix; The mistake was harder to fix; They were quieter; They talked more; They explained in other ways
- Button: Save what I saw
- Saved: Saved on your phone and sent. Thank you.
- Saved offline: Saved on your phone. It will be sent when you are online.
- Consent off: Sharing is off, so this stays on your phone. Turn it on in My profile to send it.
- Note: Only your choices are sent, with no name and no class.

## Components

Use these components from DESIGN.md: QuickMove, StatusChip, PrivacyNote, PlayButton.

## States

- Default: nothing chosen.
- Chosen: the primary button enables.
- Saved, saved offline, and consent-off states.
- Error: Try again.

## Interactions

- Choices are saved on the phone; they are sent only if sharing is on.
- Chips toggle on and off.

## Do not show

- No free text about a child; only the chips.
- No name, class or phone number is sent.
- No score and no percentage.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
