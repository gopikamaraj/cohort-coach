# X32 · Feedback sheet

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Feedback sheet
- Role: Teacher
- Device priority: Phone first

- Purpose: A small Feedback button floats above the bottom bar on every screen. It opens a bottom sheet where a person rates the app from 1 to 5, picks up to three tags and may add a comment. The role and the screen they were on are saved with it, nothing else about them.
- If the person has not agreed to share, the sheet says so plainly and offers no form.

## Layout

### Phone (360px wide)

- The floating button is a pill with a chat icon and the word Feedback, 44px high, bottom right, above the navigation bar and never covering a primary action.
- The sheet has the title, a row of five numbered round buttons, six tag chips that wrap onto two or three lines, a three-line comment box, the warning line, and a sticky action area with a filled Send button and a text Close button.

### Desktop (1280px wide)

- The button sits bottom right of the content area. The sheet opens as a centred 560px dialog.

## Exact copy

- Button: Feedback.
- Title: Tell us how it went.
- Rating label: How was it? Each number button is read as, for example, 4 of 5.
- Tag label: Pick up to three. Tags: Easy to use, Confusing, Useful, Slow, Voice problem, Hard to read.
- Comment label: Anything else? (optional)
- Warning line: Please don't type any child's name or personal details.
- Buttons: Send feedback, Close.
- Thanks toast: Thank you. This helps us improve the app. When offline: Thank you. It will be sent when you are online.
- Sharing off message: Sharing is off, so feedback can't be sent. You can turn it on in My profile.

## Reading order

- Title, rating, tags, comment, warning, Send. Send stays disabled until a rating is chosen.

## Components

Floating pill button, bottom sheet, five toggle buttons in a group, six toggle chips, multi-line text field, filled button, text button, toast.

## States

- Closed button. Sheet with nothing chosen. A rating chosen. Three tags chosen, with the fourth tap ignored. Comment filled. Send disabled. Offline, where the thanks toast changes. Sharing off, where only the message and Close remain.

## Interactions

- Tapping a rating or tag toggles it and keeps focus. Send queues the feedback on the phone and closes the sheet; it goes to the team when the phone is online. Phone numbers and email addresses in the comment are hidden before it is saved.

## Do not show

- No name, class, school or child on the sheet. No percentage. No promise that every comment gets a reply. No emoji faces for the rating; numbers with text labels only.

## Accessibility and tone

- Contrast at least 4.5 to 1 in light and dark. A visible focus ring on every control. Text scales to 200 percent without clipping or sideways scroll. Every icon has a text label. Reduced motion turns transitions off. The screen reader reads the sheet title first, then each field with its label, then the actions.
- Tone is plain and warm, one short sentence per idea, no jargon, no pressure. Nothing here scores or judges the person.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons; let them wrap or grow. Hindi and Tamil strings are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
