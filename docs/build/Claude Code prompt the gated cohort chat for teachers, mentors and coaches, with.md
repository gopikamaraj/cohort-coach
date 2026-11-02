# Claude Code prompt: the gated cohort chat for teachers, mentors and coaches, with AI answering after a timeout

Paste everything below the line into Claude Code at the repo root. Work on a branch. No push, no merge.

---

**Task.** The Cohort chat page is empty: it shows only its heading and one line (A small space for teachers working on the same mistake. You appear as a label, never a name). Build the real chat:

1. A **gated** chat where the teachers of a cohort, the cohort's mentor and its coach talk to each other.
2. Everyone appears as a **label**, never a name.
3. When a teacher asks a question and **no mentor or coach replies within a configured time, the AI answers** from approved sources, clearly labelled, and a coach can correct it afterwards.
4. The timeout is **configurable. For the demo it is 5 seconds.**

## Rules

- **Code gates. The AI only words.** Who may post, what is masked, what is blocked, when the AI answers, and who may correct are decided by code with tests.
- **The server owns the timer,** not the browser. A closed browser, a restart or a slow phone cannot change when the AI answers.
- **No names anywhere.** Teachers appear as stable labels (Teacher A, Teacher B and so on, assigned per cohort), the mentor as Mentor, the coach as Coach, the AI as AI assistant, and you as You. No screen, log or API response contains a real name. Moderation works by label.
- **Children are never identified.** Names, roll numbers, class codes, phone numbers, emails and links are masked or blocked before a message is stored. Counts and percentages of a child's data are not posted.
- **AI answers come only from approved sources,** show their sources, say so when they have none, and are always labelled. They never judge a teacher, diagnose a child, or promise an outcome.
- **Honest labels.** Everything the AI wrote is marked AI. A recorded answer (AI mode recorded) is marked Recorded AI answer. Seed or demo messages are marked Demo.
- **Counts only for officers,** who do not see the chat at all.
- Follow `docs/design/stitch/DESIGN.md` (Calm Institutional), colours from `theme.css`, 44 px touch targets, every string in `en`, `hi` and `ta`, text that fits in Hindi and Tamil. Never weaken or delete a test.

## Step 0. Read first, and find why it is empty

Read `CLAUDE.md`, `DECISIONS.md`, `PROGRESS.md`, `AI_USAGE.md`, `docs/design/stitch/DESIGN.md`, the Cohort chat screen and route, any chat API, tables and models, call 13 (chat reply drafting) and call 7 (the checker), the masking function, the retrieval or sources code that the assistant uses, the coach inbox (if any), cohort membership and roles, the scheduler or background job code, the offline queue, the demo scenario seeding, and the end-to-end tests.

Before changing anything, **write down why the page is empty**, with file and line evidence (a placeholder screen, no thread or members created for the cohort, a missing API, or no data), and list what already exists and can be reused. Put this at the top of the report.

## Step 1. Data model

Add or extend, with a migration:

- `chat_thread`: one per cohort (a single-class cohort gets a thread with its coach and mentor).
- `chat_member`: thread, user, role (`teacher`, `mentor`, `coach`), a stable **label**, joined at. The identity link stays server-side and is never returned by any API.
- `chat_message`: id, thread, author member (or `ai`), **type** (`question`, `reply`, `tip`, `ai_reply`, `correction`, `system`, `checkin_summary`), masked text, reply-to id, status, language, created at, `ai_due_at`, `answered_by` (`human` or `ai`), source ids, AI call id, `corrects` (the message it corrects), `hidden` with reason and who hid it.
- `chat_event`: an audit log of posts, AI answers, corrections, hiding, resolving and timeout changes.

Status of a question: `waiting` (a human may still answer), `answered_human`, `answered_ai`, `corrected`, `resolved`, `hidden`.

## Step 2. The gates (pure code, tested)

1. **Membership gate:** only members of the cohort can read or post. A teacher outside the cohort, an officer and a user from another block get nothing. Judge mode can view as each role.
2. **Input gate, on every post:** trim, a limit of 500 characters, a rate limit (for example 10 messages a minute per member), treat the text as untrusted data (ignore any instruction inside it), strip links, and **mask** names, roll numbers, class codes, phone numbers and emails with the existing masking function. If masking changed the text, show the poster the posted version and say what was hidden. If the text still looks like an identifier after masking, block it and say what to remove.
3. **Role gate for actions:** teachers ask, reply and share tips. Mentors and coaches also reply and mark a question resolved. **Only coaches** correct an AI answer, hide a message, pin a message and change the cohort's timeout. Mentors cannot correct the AI.
4. **AI output gate:** an AI answer is posted only if it has at least one approved source, passes the checker (call 7), contains no names, is in the asker's language, and is at most about 120 words. Otherwise follow Step 4's abstain rule.
5. **Every gate decision is logged** in `chat_event` without the message text.

## Step 3. The timeout and who cancels it

- Config: `CHAT_AI_TIMEOUT_SECONDS`. **Demo mode sets it to 5.** The production default is 1800 (30 minutes) until the team decides otherwise, and a coach can set it per cohort (a minimum of 5, a maximum of 86400). Show the current value to the coach on the cohort settings, labelled (demo) when it comes from demo mode.
- When a `question` is stored, set `ai_due_at = created_at + timeout` on the server.
- **A reply from a mentor or a coach cancels the AI timer** and sets the question to `answered_human`. **A reply from a peer teacher does not cancel it**, but is shown. Put this in a setting (`CHAT_AI_CANCELLED_BY`, default `mentor,coach`).
- If a coach or mentor is composing a reply when the timer ends, the AI still answers, and their reply then appears normally.
- **Durable and idempotent:** the AI answer is created by a job that cannot be run twice for one question (a unique constraint on the question and `ai_reply`). Use a poller or scheduled task that finds due questions every second, **and also catch up when anyone loads the thread after the due time**, so a restart or scale-to-zero loses nothing. Time is injectable for tests.
- Only `question` messages start the timer. Tips and replies do not.

## Step 4. The AI answer

Use call 13, with retrieval over the approved sources the assistant already uses (the module and strategy content, the library, the help documents):

- Answer in the asker's language, in plain words, at most about 120 words, with the sources named at the end (for example Source: Module 2, Exchanging a ten).
- **Abstain** when no approved source supports an answer. Post a short notice, I could not find an approved source for that. A mentor or coach will see your question., keep the question `waiting`, and put it at the top of the coach inbox. Never guess.
- Label every AI message with an icon and the words AI answer. It was posted after N seconds with no mentor or coach reply. A coach can correct it.
- Cost caps and the AI mode (`live`, `recorded`, `off`) apply. In `recorded` mode return a recorded answer (create fixtures for the demo questions below, plus one abstain case) and label it Recorded AI answer. In `off` mode post nothing and keep the question waiting, with the coach inbox showing that the AI is off.
- A **coach correction** is a new `correction` message that points at the AI message, and the AI message gets a Corrected by a coach badge. Nothing is deleted.

## Step 5. The interface

Replace the empty page, keeping the existing title bar:

- **Header:** the cohort name, the error it is about, the number of members as counts (for example 14 teachers, 1 mentor, 1 coach), and an AI answers after N seconds line. If the user belongs to several cohorts, a selector.
- **A pinned note** from the coach, or a default one: how this chat works, that names are hidden, and when the AI answers.
- **The thread:** oldest at the top, grouped by day, newest at the bottom, scrolling to the newest on open. A message card shows the label and role chip, the time, the text, and a status chip for questions (Waiting for a mentor or coach, Answered by a mentor, Answered by AI, Corrected, Resolved). Replies are indented under their question. A `checkin_summary` card renders if that type exists (Part C of the earlier brief), otherwise leave the type ready for it.
- **The countdown:** under a waiting question, everyone sees a quiet line, A mentor or coach may reply. If nobody does in 5 s, the AI will answer., counting down and announced politely to screen readers. After the AI posts, it changes to AI answered after 5 s.
- **The composer:** a text box with a counter, buttons **Ask a question** (primary, starts the timer) and **Share a tip**, a note that names are hidden, and Ctrl+Enter to send. Disabled when empty or over the limit. When masking changed the text, show what was posted.
- **Actions on a message** (a small menu, 44 px): Reply, Report, and for mentors and coaches Mark resolved; for coaches also Correct the AI answer, Hide, Pin.
- **Coach inbox:** a tab or panel for coaches and mentors listing open questions (waiting first, with time left), with a count badge on the Cohort chat navigation item. Opening an item scrolls to it.
- **Live updates:** use the mechanism the app already has. If there is none, poll every 2 seconds while the thread is open and every 30 seconds in the background, and stop when it is closed. New messages appear without losing the scroll position, and the list is announced politely.
- **Offline:** read the cached thread, queue a new post in the offline queue with a Waiting to send chip, and send it when back online. **The timer starts when the server receives it,** and the card says so.
- **States:** a real empty state (No messages yet. Ask the first question.), loading, error with retry, hidden messages shown as Hidden by a coach, a cohort with no peers (a single-class cohort: only you, the mentor and the coach), and a member removed from the cohort.
- Hindi and Tamil text fit at 360 px. The list uses `role=log`. Every message has an accessible name such as Teacher B, question, 2 minutes ago.

## Step 6. Roles and visibility

| Role | Can do |
| --- | --- |
| Teacher | Read, ask, reply, share a tip, report |
| Mentor | The above, mark resolved, reply to cancel the AI timer |
| Coach | The above, correct the AI answer, hide, pin, set the timeout, see the inbox |
| Officer | No access to the chat |
| Judge | View as any of the roles |

Every one of these is enforced on the server, never only in the interface.

## Step 7. Demo seeding and the demo script

- For the demo cohort, seed a pinned note and **two short starter messages marked Demo** (one tip, one resolved question), so the page is never empty on first open. Seed from the demo scenario code, not by hand.
- Create recorded AI fixtures for these questions: How do I teach borrowing across a zero with bundles? Children keep taking the smaller digit from the bigger one. What can I do in 10 minutes? Do I need to teach place value first? And one question with no approved source, for the abstain path.
- A demo run, written in the help documents: Teacher A asks a question, nobody replies, after 5 seconds an AI answer appears with its sources, the coach corrects it, Teacher B sees both; then Teacher B asks another question and the mentor replies within 5 seconds, so the AI stays silent.

## Step 8. Tests

- **Gates:** membership, masking (a made-up child's name, a roll number, a class code, a phone number, a link), blocking of leftover identifiers, the length and rate limits, role permissions for every action, and prompt-injection text treated as data.
- **Timer:** with a frozen clock, a question gets `ai_due_at`; a mentor or coach reply cancels the AI; a peer reply does not; a coach composing a reply does not stop the AI; two job runs create one AI answer; a missed run is caught up on the next thread load; a restart loses nothing; the production and demo values; the per-cohort override and its limits.
- **AI answer:** it needs a source and passes the checker; the abstain path; the label and the recorded label; AI mode off; the cost cap; the language; a correction links to its message and badges it.
- **API and privacy:** no response ever contains a real name or identity; a teacher outside the cohort, an officer and a user from another block are refused.
- **End to end, with three signed-in users** (two teachers and a coach, plus a mentor in a second test): Teacher A asks, nobody replies, the AI answers after 5 seconds, the coach corrects it, Teacher B sees the thread; a second question is answered by the mentor in time, so the AI stays silent; a post with a child's name is masked; an offline post is queued and its timer starts only after it reaches the server.
- **Screens:** the empty, loading, error, waiting, answered, corrected, hidden and offline states, the countdown announcement, the inbox badge, axe, Hindi and Tamil fit at 360 px, and the phone and laptop layouts. A thread of 200 messages stays smooth.
- Existing suites still pass. Report the counts before and after.

## Step 9. Report and docs

`docs/build/reports/COHORT-CHAT.md`: why the page was empty, what was reused, what was built, the gates, the timer rules and settings, the recorded fixtures, and the tests. Update `docs/help` for teachers, mentors and coaches, `docs/design/stitch/INVENTORY.md`, the README (the timeout settings and the demo mode value), `docs/RUBRIC_MAP.md`, `AI_USAGE.md` and `DECISIONS.md` (entry dated today).

**Order:** Step 0, then Steps 1 to 3 with unit tests, then Step 4, then Steps 5 to 7, then Steps 8 and 9.

**Done when** the Cohort chat page is a working thread with labels and no names, teachers, mentors and coaches can post, reply and act within their roles, an unanswered question is answered by the AI after the configured time (5 seconds in demo mode) with sources and an AI label, a mentor or coach reply cancels it, a coach can correct it, offline and masking work, the tests pass, and the report is written.
