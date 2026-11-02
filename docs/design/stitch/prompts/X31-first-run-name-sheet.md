# X31 · First-run name sheet

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: First-run name sheet
- Role: Teacher
- Device priority: Phone first

- Purpose: The first time a person opens a public demo or tester link, a short friendly sheet asks how they would like to be called and whether the team may save which screens they open and the feedback they give. It appears once. Choosing "Use without sharing" skips everything, sends nothing, and the app works in full.
- It never appears in a pilot deployment or for a real pilot teacher.

## Layout

### Phone (360px wide)

- A bottom sheet over the landing page with a dimmed scrim, 28px top corners, a drag handle, the title at the top, then one text field, two checkboxes with their explanations, one quiet line of warning, and a sticky action area at the bottom: a filled primary button and a text button beneath it.
- The sheet grows with its content and scrolls inside itself if the text is large; the action area stays visible.

### Desktop (1280px wide)

- The same sheet as a centred dialog, 560px wide, with the scrim over the rail and top bar. Focus starts in the nickname field.

## Exact copy

- Title: How would you like to be called here?
- Field label: Nickname. Hint: 1 to 30 characters, any language.
- First choice, on by default: Save which screens I open and my feedback, so the team can improve the app.
- Second choice, off by default: Show my nickname to the judges and the team.
- Warning line: Please don't type any child's name or personal details.
- Primary button: Save and continue. It stays disabled until the field has at least one character and the first choice is on.
- Text button: Use without sharing.

## Reading order

- Title, nickname field, the two choices, the warning, the primary button, then the text button. The warning sits directly under the choices so it is read before the person types.

## Components

Bottom sheet, text field with a visible label and hint, two checkbox rows with 44px tap targets, filled button, text button, a muted caption.

## States

- Default with the first choice on and the second off. Field focused. Field empty with the primary button disabled. Field filled with the primary button enabled. First choice switched off, which disables the primary button and leaves the text button as the way forward. Large text.

## Interactions

- Save and continue stores the nickname on the phone and starts sharing; the sheet closes with no confirmation page. Use without sharing, the scrim tap and the escape key all mean the same thing: no sharing, never asked again. Settings in My profile lets the person change the nickname, pause sharing, turn it on later or delete their data.

## Do not show

- No real name prompt, no email or phone field, no location prompt, no percentage, no child name, no countdown or pressure to agree. Do not pre-fill the nickname. Do not show a technical identifier on this sheet.

## Accessibility and tone

- Contrast at least 4.5 to 1 in light and dark. A visible focus ring on every control. Text scales to 200 percent without clipping or sideways scroll. Every icon has a text label. Reduced motion turns transitions off. The screen reader reads the sheet title first, then each field with its label, then the actions.
- Tone is plain and warm, one short sentence per idea, no jargon, no pressure. Nothing here scores or judges the person.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons; let them wrap or grow. Hindi and Tamil strings are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
