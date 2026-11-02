# Gated cohort chat: report

Branch `cohort-chat` (from `for-submission`). Nothing pushed or merged.

## Why the page was empty

`apps/pwa/src/screens/Cohort.tsx` (before this work), `TeacherView`: `{!current && cohorts.length === 0 ? null : ...}` rendered nothing when the teacher had no open cohort, so only the heading and the intro line showed. When she did join, the page was the older shared-post list, which had no timer, no question type, no AI answer, no mentor view and no inbox. The question-and-answer flow (private per teacher, mentor sends a draft, timeout in hours, auto-send off by default) lived elsewhere (`services/chat/`) and had no screen on this page.

## What was reused

- `thread_posts`, `CohortMember` (labels "Teacher 7"), `lifecycle` (assignment, audit rows, status), `ai/validators/mask.py` (masking), `ai/validators/thread.py` (leftover identifiers), `services/chat/draft.py` (call 13 then call 7 on approved sources), `thread.decide` (hide, pin).
- New: `services/cohort_chat/` (`models.py`: `chat_post_meta`, `chat_timeout`; `service.py`; `api.py`; `poller.py`), `apps/pwa/src/components/GatedChat.tsx`, `apps/pwa/src/lib/gatedChat.ts`. A message is a `thread_posts` row with one meta row. This differs from the brief's four new tables (a decision, in DECISIONS.md).

## Gates, timer and settings

- Membership, input (500 characters, 10 a minute, links stripped, names / roll numbers / phone numbers / emails masked, leftover identifiers blocked), role, and AI output (a cited source, call 7 passed, no personal data, at most 120 words). Gate decisions are audited in `cohort_audit` with codes and ids, never text.
- Timer: `ai_due_at` is set on the server when a question is stored. `CHAT_AI_TIMEOUT_SECONDS`, else 5 in demo mode, else 1800; a coach can set 5 to 86400 per cohort. A mentor or coach reply (`CHAT_AI_CANCELLED_BY`) cancels it. The poller (`CHAT_POLLER=1`) answers every second; loading the thread also catches up. A question is claimed with one compare-and-set, so two runs make one answer.
- No approved source, a failed check, personal data or too long: a notice is posted, the question keeps waiting and shows first in the coach inbox. AI off: nothing is posted.

## Tests

- New: `tests/cohort_chat/` (27: gates, roles, timer with a frozen clock, claim, catch-up, abstain, AI off, recorded label, correction, privacy, demo seed, older posts) and `apps/pwa/src/lib/gatedChat.test.ts` (3).
- Before this work the Python suite had 55 failures from earlier changes (`test_versions`, the cohort-run, admin-data and others); after it, the new tests pass and no existing one was changed except that `tests/conftest.py` turns the poller off. Front end: 3 failures before and after (`flow.test.ts` x2, `profile.test.ts`). The full suite was not rerun after this work.

## Not done

- Recorded AI fixtures for the demo questions (they need a live model run to record). With `AI_MODE=recorded` the AI answers only if a recording exists, otherwise the no-source notice appears.
- Offline queue for posts (offline you can read what loaded; posting is disabled and says so), a badge on the navigation item, "Opening an inbox item scrolls to it" (it switches to the thread).
- The end-to-end browser test, axe, the Hindi and Tamil fit check at 360 px, the 200-message smoothness check.
- Moderation by label for an erased identifier (the older coach "erase text" button is gone from this page; the server route still exists).
- The brief's single `chat_event` table: audit rows reuse `cohort_audit`.
- Hindi and Tamil strings are my drafts for Seema and Shivani.
