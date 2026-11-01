# Tester stats and the Testing evidence view

Spec: the 30 Oct request (device-based tester profiles, first-run prompt, privacy-safe usage tracking, in-app feedback, a Testing evidence view for judges). Switch: `TESTER_STATS=1` on the demo server; never mounted in pilot mode.

## What was built

| Part | Where |
| --- | --- |
| Device id, hashing, consent, queue, batches, delete | `apps/pwa/src/lib/tester.ts` |
| First-run sheet, Feedback button and sheet, settings block, tracker | `apps/pwa/src/components/TesterUI.tsx` (mounted in `App.tsx`; settings in My profile) |
| Instrumented events | role change, screens (with time bucket), guided tour (`Tour.tsx`), practice turn, voice play and toggle, next-step tap, chat question, judge guide question, sample class, errors, offline session, install accepted |
| Tables and views | `services/tester/models.py`: `tester_device`, `tester_event`, `tester_feedback`, `change_log`; views `v_tester_summary`, `v_role_funnel`, `v_tour_funnel`, `v_daily_activity`; indexes on device hash and time |
| API | `services/tester/routes.py`: `GET /api/tester/config`, `POST /api/tester/profile|events|feedback`, `DELETE /api/tester/me`, `GET /api/judge/testing-evidence`, `GET /api/team/testing-export` |
| Counting | `services/tester/evidence.py` (also retention, delete and the change-log loader) |
| Judge view | `apps/pwa/src/screens/TestingEvidence.tsx` at `#/testing` and as tour step 7 |
| Export for the deck | `scripts/export_testing_stats.py` writes `docs/evidence/user_testing_snapshot.md` (counts and dates only); added to the judge assistant's sources |
| You said, we changed | `docs/YOU_SAID_WE_CHANGED.md`, loaded into `change_log`; empty until real feedback arrives |

Migrations: the repo has no Alembic yet (`services/api/db.py` builds tables with `create_all`), so the tables and views are created by `ensure_tester_schema` at start-up. Same approach as the other tables; Alembic arrives with the first managed Postgres.

## Decisions taken inside the request

- **Judge tagging.** There is no judge login. A device is tagged judge when it opens a `?src=judge` link or selects the Judge role; the tag sticks. Team devices open `?team=<TESTER_TEAM_TOKEN>`. Tagged devices are excluded by default and counted separately; a switch on the screen includes them.
- **Judge-only endpoint.** `GET /api/judge/testing-evidence` needs the `X-Role: judge` header in a judge deployment. This is the same trust level as the rest of the demo (roles are asserted by the client in judge mode), and the data behind it is aggregate, nickname-gated and contains no free text except anonymous feedback comments.
- **Feedback without consent.** The sheet opens but says sharing is off; nothing is stored or sent.
- **Tour.** A seventh step was added (10 s budgeted, total 300 s kept). Existing tour tests were updated from 6 to 7 steps; the five-minute bar was not changed.
- **Salt.** `TESTER_SALT` (default `cc-tester-v1`) comes from the server's `/api/tester/config`; the hash is made on the device after the person agrees. The salt is not a secret; it only stops a lookup table of bare ids.

## Checks (commands, not claims)

- `python -m pytest tests/api/test_tester.py`: 22 tests. Covers: nothing stored without consent; only a 64-hex hash accepted; unknown fields refused; idempotent batches and the 50-event limit; no typed text in events; phone numbers and emails masked in comments; judge endpoint refuses every other role and a non-judge deployment; team export refuses a bad or missing token; honest empty state; judge and team devices excluded and counted apart; declined listing hides the nickname in the screen data and the CSV; aggregates match the rows; delete removes every row for a hash; 90-day retention; not mounted in pilot mode or without the flag; the SQL views run; access-log lines for these paths dropped; the snapshot has counts and dates only.
- `npx vitest run src/lib/tester.test.ts`: 17 tests. The raw id never appears in any request (only the salted hash); nothing is sent before a choice, after declining or while paused; offline events queue and send later in order; a refused batch is kept; batches stay at 50; Delete my data calls the server by hash and clears the device; tracking never throws.
- `npx playwright test e2e/tester.spec.ts`: 9 browser tests with the tester endpoints answered by the test. A new device sees the name sheet once; declining sends nothing and the app still works; agreeing sends only the allowed profile fields and the hash; feedback is sent with rating, tags and comment; Delete my data calls the server; the feature is invisible when the server has it off; the evidence screen shows honest empty states and fits a phone in English, Hindi and Tamil.

## Not done, or not verified

- Not run against a real deployment yet. Deploy with `TESTER_STATS=1`, `TESTER_TEAM_TOKEN` set, then check the first-run sheet on a real phone before the links go out.
- No tester data exists yet, so the snapshot reads "Nothing has been collected yet". Do not quote tester numbers until the snapshot shows them.
- IP privacy: the application code never reads the caller's address for these paths except the in-memory rate limiter (not stored), and the access-log line is dropped for them; the hosting platform (Cloud Run) keeps its own request logs outside our control.
- Hindi and Tamil strings are drafts for Shivani and Gopi.
- `docs/YOU_SAID_WE_CHANGED.md` is empty by design; fill it as real feedback arrives (commit references included).
