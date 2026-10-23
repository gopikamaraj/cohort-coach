# X16 · My profile and data

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: My profile and data
- Role: Teacher
- Device priority: Phone first
- Purpose: Let a teacher manage her classes, protect and back up her data, see what the app used, change her consents and erase everything.

## Layout

### Phone (360px wide)

- Header two rows; title My profile.
- Section cards stacked: My classes; Storage and backup; Data used; Privacy; Erase my data.
- Classes: a card per class with In use chip, Rename, Delete this class, and Add a class.
- Storage: a status line with Protect my data; Backup file with an optional passphrase field, Save a backup and Restore from a file.
- Data used: Sent, Received, Total in MB, an optional price per GB and an estimated cost, Clear the count.
- Privacy: four consent switches, each with a one-line why; Read the privacy notice; Withdraw all.
- Erase: a tertiary card with Erase everything.

### Desktop (1280px wide)

- Phone-first column of 440px.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: My profile
- Classes: My classes. Class 3A, In use, simulated.
- Storage: Your data is protected: the browser will not clear it when space runs low.
- Storage used: This app uses 1.2 MB of about 250 MB available.
- Backup: The file holds your checks, including each child's answers, and your rehearsals. Keep it safe.
- Data used: Sent 0.3 MB. Received 2.1 MB. Total 2.4 MB. Counted since 12 Oct.
- Consents: Send my class counts; Use AI in the Practice Class; Share my rehearsals to improve the simulator; Send my feedback to the team
- Consent intro: Choose what you agree to. Everything is off until you turn it on, and you can change your mind at any time.
- Withdraw: Withdraw all
- Erase: Erase everything. Removes every class, check, rehearsal and setting from this phone, and asks our server to erase the class counts.
- Confirm: Erase all your data on this phone? This cannot be undone.

## Components

Use these components from DESIGN.md: TopBar, BottomNav, StatusChip, PrivacyNote, AnswerBox, ProgressMeter.

## States

- Default: protected, no consents on.
- Not protected: tertiary card with Protect my data.
- Backup sealed with a passphrase: restore asks for it.
- Erased: a success card.
- Offline: all local actions work; erasing the server counts waits.
- Error: What happened and what to do.

## Interactions

- Switches save at once with the notice version and date.
- Erase asks to confirm, then clears the phone and requests server erasure.
- Delete class removes its checks and rehearsals after confirmation.

## Do not show

- No consent on by default; no dark patterns.
- No percentage; data used is in megabytes.
- Never show another teacher's data.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
