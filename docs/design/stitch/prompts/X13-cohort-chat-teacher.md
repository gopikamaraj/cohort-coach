# X13 · Cohort chat

<!-- stitch-header:start -->
Design system: Calm Institutional Material (Material 3), tokens in DESIGN.md. Colour: primary #0B6B6B, primary container #BDEEEE, secondary container #CCE8E7, tertiary #A04A00 with container #FFDCC4, success #1B6D2F with container #B4F2BC, background #F7FAFA, surface #FFFFFF, outline #BEC9C8, text #191C1C and #3F4948. Light and dark themes. Shape: cards 16px radius, 1px outline, no shadow; buttons, chips and inputs 8px; quick moves are full pills. Touch targets at least 44px, primary buttons 48px, inputs 56px. Type: Inter with Noto Sans Devanagari and Noto Sans Tamil. No gradients, no blurs, no emojis; line icons always paired with text. Layout: desktop has an 88px left navigation rail and a top bar (title, subtitle, Works offline pill, EN / हिं / தமி switch, account button), content capped at 1280px. Phone: bottom navigation bar, header wraps to two rows. Teacher screens are phone first; others desktop first. Reuse the approved Practice Class pattern: scenario card in primary container; class card with child avatars whose expressions carry state, a state tag beneath; a child-says line in tertiary container; a board card with Tens and Ones counts; a mic panel with waveform bars either side; pill quick moves; a typed fallback; feedback cards tinted by meaning (success for good, tertiary for watch); a progress meter; a lock-icon privacy note. Copy: sentence case, plain verbs. Teachers see counts, never percentages. Children appear as counts and patterns, never real names. Every teacher text card has a play button; one primary action per teacher screen.
<!-- stitch-header:end -->

## Screen

- Name: Cohort chat
- Role: Teacher
- Device priority: Phone first
- Purpose: Give teachers in one cohort a small, moderated, pseudonymous thread to talk about the week's prompt.

## Layout

### Phone (360px wide)

- Header two rows; title Cohort chat; subtitle Subtract with borrowing, week 2.
- Prompt card in primary container: the week's question with a PlayButton.
- Thread of ThreadPost cards: a pseudonym, a role tag (Teacher, Mentor, Coach), the text, and a Report button.
- Compose bar at the bottom: a text field with a notice line and Post.

### Desktop (1280px wide)

- Phone-first column; the prompt card pins to the top.

## Exact copy

Use these strings as they are, in English. Values come from the synthetic data (a fictional block of 40 schools and 120 classes) and are labelled simulated where shown.

- Title: Cohort chat
- Prompt: This week: what did you use when you did not have enough bundles?
- Post: Blue Heron, Teacher: We tied ten sticks with grass from the school yard.
- Post: Mentor reply: Try a rubber band cut in rings.
- Role tags: Teacher; Mentor; Coach
- Compose notice: Do not write a child's name, roll number or anything that points to a child.
- Blocked: That post was not sent: it looked like it had a child's name.
- Report: Report this post. A coach will look at it.
- Hidden: This post was hidden by the coach.
- Button: Post

## Components

Use these components from DESIGN.md: ThreadPost, ReportButton, PlayButton, PrivacyNote, StatusChip, TypedFallback.

## States

- Default: prompt plus a few posts.
- Empty: No posts yet. Be the first to answer.
- Blocked post: the compose bar shows why, with an example of what to change.
- Hidden post: replaced by a muted line.
- Read-only: after the cohort closes, a card says the thread is read-only.
- Offline: posts wait in the outbox.

## Interactions

- Posting runs the name and phone filters before anything is shown.
- Report sends the post to the coach and hides it from view for the reporter.
- The bot relays the same thread in Telegram.

## Do not show

- No handles, phone numbers or real names; pseudonyms only.
- No post written by AI; no number about any teacher's class.
- No thread text goes to an AI service.

## Accessibility and tone

- Body text contrast at least 4.5 to 1 in both themes; focus ring 3px in primary; meaning never by colour alone.
- Every icon has a visible text label; every picture has alt text; reading order matches visual order.
- The layout still works with the system text size at 200 percent.
- Plain verbs and sentence case; no jargon; short sentences read well aloud.
- Do not copy Stitch's font link or its Tailwind CDN into our code; icons are inline SVG.

## Language note

Labels must survive text 30 percent longer in Hindi and Tamil. Do not use fixed-width buttons, chips or tabs; let them wrap or grow and keep room for a second line in every row. Never truncate a label to fit. Test the layout with the longest string. Hindi and Tamil strings in this brief are drafts to be reviewed by Shivani (Hindi) and Gopi (Tamil).
