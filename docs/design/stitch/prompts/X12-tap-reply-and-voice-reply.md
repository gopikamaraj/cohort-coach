# X12 · Tap reply, voice reply and silence states

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Tap reply, voice reply and silence states
- Role: Teacher
- Device priority: Phone first
- Purpose: After a lesson, collect two taps and an optional voice note, and give back one approved next step linked to her own words.

## Layout

### Phone (360px wide)

- Header two rows; title After lesson 3.
- Tap card one: Tried it in class? with two buttons, Yes and Not yet.
- Tap card two (after Yes): How did it go? with three buttons, Worked, Partly, Didn't work.
- Voice card: Tell me in a one-minute voice note, with a VoiceRecorder and a Skip link.
- Pointer card (success container): one next step with a short link quoting her words, a PlayButton and a BadgeLine.
- Check-in card every two weeks: Still using it? Yes; Sometimes; No.

### Desktop (1280px wide)

- Phone-first column.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: After lesson 3
- Tap 1: Tried it in class? Yes; Not yet
- Tap 2: How did it go? Worked; Partly; Didn't work
- Voice: Tell me in a one-minute voice note: what did you try, and what did the children say? Skip
- Recorder: Record; Stop; Send
- Pointer: You said children opened a bundle by themselves. Next step: ask them to say each step aloud.
- Check-in: Still using it? Yes; Sometimes; No
- Thanks: Thank you. Nobody sees this but the programme team's counts.
- No response state: No response yet.
- Silence nudge: Lesson 4 is ready when you are.

## Components

Use these components from DESIGN.md: TapReply, VoiceRecorder, PlayButton, BadgeLine, StatusChip, PrivacyNote.

## States

- Default: first tap card.
- Not yet: skips the second tap and the voice card.
- Recording, transcribing and pointer ready.
- Pointer unavailable: nothing new is sent; no error shown.
- Silent teacher: no replies for a week reads No response yet, never failed or ignored.
- Offline: taps and the recording wait in the outbox.

## Interactions

- Each tap is saved per lesson against her pseudonymous id.
- The voice note is optional; Skip leaves nothing.
- The pointer never scores or judges.

## Do not show

- Never the word failed, ignored or late about a teacher; no response reads as no response.
- Taps shown to officers are counts labelled self-report.
- No transcript is shown to anyone else.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
