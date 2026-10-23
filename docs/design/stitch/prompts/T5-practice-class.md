# T5 · Practice Class

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Practice Class
- Role: Teacher
- Device priority: Phone first (style anchor, already approved)
- Purpose: Rehearse the fix with five simulated children, by voice or by typing, before trying it on real children.

## Layout

### Phone (360px wide)

- Header two rows; title Practice Class; subtitle Rehearse with five pretend children.
- Scenario card in primary container: the error, the problem, the goal. A Hide button collapses it after turn one.
- Class card: five ChildAvatar tiles in a row (wraps to a 3 plus 2 grid on narrow phones). The avatar expression carries the state; a StateTag sits beneath each tile: Confused, Listening, Ready, Quiet. The speaker has a primary underline.
- Child-says line in tertiary container: the child's name, the words, a tick icon with Checked, and an English subtitle in muted text when the language is not English.
- Board card: Tens and Ones counts in two columns and the slate line On Meena's slate: 23.
- Mic panel: a large circular hold-to-speak button with waveform bars either side; status text under it.
- Quick moves: pill chips, for example Ask her to explain, Show with bundles, Check by adding back.
- Materials tray: three tiles drawn as inline SVG (bundles of ten, loose sticks, place-value chart) with a one-line help text under the tray.
- Typed fallback: a 56px text field and Send, shown when voice is off or the signal is weak.
- Progress meter: Turn 4 of 40 and a small confusion meter per child in words (low, medium, high), shown in judge mode only.
- Privacy note with a lock icon: Practice stays on this phone.

### Desktop (1280px wide)

- Content column 440px for the rehearsal and a right column with What can I say? cues and, in judge mode, the AI layers panel.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Scenario: Take the smaller digit from the larger. Try 52 - 29 with bundles of ten.
- Goal tips: Ask a child to explain her steps. Show the number with bundles. Check by adding back.
- State tags: Confused; Listening; Ready; Quiet
- Child-says example: Meena: 37, Miss! Checked. Subtitle: 37, Miss!
- Board: Tens 3, Ones 7. On Meena's slate: 37
- Mic status: Hold to speak. / Listening. / Sending.
- Quick moves: Ask her to explain; Show with bundles; Check by adding back; Praise the trying
- Tray help: Tap a tool to show it to the children, as if you held it up.
- Typed fallback placeholder: Type what you would say
- Simple-reply notes: A check held back the first reply, so a simple reply was used.
- Privacy note: Practice stays on this phone. Nobody else sees it unless you choose to share.
- Buttons: End and get feedback; What can I say?

## Components

Use these components from DESIGN.md: ScenarioCard, ClassCard, ChildAvatar, StateTag, SayLine, BoardCard, MicPanel, QuickMove, MaterialsTray, SpriteTile, TypedFallback, ProgressMeter, PrivacyNote.

## States

- Default: listening state, no child has spoken yet.
- Speaking: the speaker's avatar opens its mouth frame and the SayLine appears.
- Confused: a child who cannot yet do the step shows the confused expression and tag.
- Quiet: a scolded or shy child shows the shy expression and the Quiet tag.
- Loading: the mic panel shows Thinking with three dots in outline colour.
- Offline or weak signal: the typed fallback opens and a pill says Typing mode.
- Error: practice paused for today, with a recorded sample offered.
- Finished: all children right twice in a row or 40 turns; a success card offers Get feedback.

## Interactions

- Hold the mic button to speak; release to send.
- Tapping a quick move fills the typed field so she can change it.
- Tapping a tool in the tray counts as showing it to the children.
- End and get feedback opens the feedback screen.

## Do not show

- Simulated children are the only place names appear; never a real child's name.
- No score about the teacher; no percentage.
- Never show a child's stage of breakdown or error strength as a number to a teacher.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
