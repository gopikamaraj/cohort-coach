# X6 · Welcome, language and consent

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Welcome, language and consent
- Role: Teacher
- Device priority: Phone first
- Purpose: Welcome a new teacher in her language and ask, one question at a time, for the choices she is willing to make.

## Layout

### Phone (360px wide)

- One question per screen with a progress dots row.
- Language screen: three large buttons, each in its own script.
- Welcome screen: a short paragraph with a PlayButton.
- Consent screens: one switch-style choice each with a one-line why.
- Final screen: the link code card for the other channel.

### Desktop (1280px wide)

- Phone-first column of 440px centred on the surface background.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Language: Choose your language. English; हिन्दी; தமிழ்
- Welcome: Welcome to Cohort Coach. It helps you teach the mistakes your own class makes, with five pretend children to practise on first.
- Core: Your privacy: each child's answers stay on your phone. We keep only class counts and anonymous feedback, and nothing is sent until you say yes.
- Core buttons: I agree; Not now
- Declined: No problem. Nothing is saved and nothing is sent. You can read the notice and come back any time.
- Counts: Send your class counts (how many children show each error, never a child's answer) so teachers can be grouped?
- Practice: Use AI in the Practice Class? What you type or say there goes to AI services to answer you. We do not keep it.
- Feedback: Send your feedback and notes to the team? They have no name or class on them.
- Buttons: Yes; No, thanks; Ask me again
- Link: You can use the bot and the web app together. Your code is KX7M2R9T (valid 15 minutes, works once).

## Components

Use these components from DESIGN.md: TopBar, PlayButton, PrivacyNote, StatusChip, LangSwitch.

## States

- Default: first question.
- Declined: calm card with Ask me again.
- Offline: all questions work; choices are saved on the phone.
- Error: a tertiary card with Try again.

## Interactions

- Each choice is saved with a notice version and date.
- Declining any optional choice never blocks the rest of the app.
- The link code can be copied or sent to the bot.

## Do not show

- Nothing is on by default.
- No legal jargon; one plain sentence per choice.
- No collection of a name, a phone number or a child's data.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
