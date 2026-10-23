# X28 · Chat steps (same flows as the bot)

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Chat steps (same flows as the bot)
- Role: Teacher
- Device priority: Phone first
- Purpose: Render the same teacher flows that run in Telegram, step by step, with the same words.

## Layout

### Phone (360px wide)

- Header two rows; title Step by step.
- A column of step cards: a message card with a PlayButton; choice buttons beneath; a link card; a media card for audio or a picture.
- A scene picture card when a step shows a picture, with alt text.
- One primary action per step.

### Desktop (1280px wide)

- Phone-first column.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Step by step
- Welcome: Welcome to Cohort Coach.
- Menu: What would you like to do? Rehearse in the Practice Class; What my class gets wrong; Check a class; Delete my data
- Practice: Rehearse with five pretend children before you try it in class. It opens in the web app. Open the Practice Class
- Delete: Delete everything we hold about you, including your class counts? This cannot be undone. Yes, delete; No, keep it
- Picture alt: Items in a row.
- Loading: Loading.
- Error: Could not reach the server. Check your signal and try again. Try again
- Telegram line: Try it in Telegram: send /start judge to the bot.
- Continue: Continue

## Components

Use these components from DESIGN.md: TopBar, BottomNav, PlayButton, StatusChip, SpriteTile, PrivacyNote.

## States

- Default: one step.
- Loading, offline and error as in the shell.
- Scene step: picture plus words.
- Consent step and link-code step.

## Interactions

- A choice posts the answer and shows the next step.
- The same journey runs in Telegram with the same words.

## Do not show

- No logic in the renderer; the server decides every step.
- No percentage and no child names.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
