# Clean-up steps B and C: identity, ownership and access

Branch `cleanup/identity-sharing-sync`. Date: 3 Nov 2026. Decisions: `docs/build/DECISIONS.md` (2026-11-03). Local only: nothing is pushed, merged or deployed, and **no hosted database was touched**.

## What changed

- **The nickname is the user id** (`services/api/identity.py`, `apps/pwa/src/lib/identity.ts`, `SignInForm.tsx`). Normalised (NFKC, single spaces, lower case), 3 to 30 letters, numbers, spaces, dots, dashes or underscores (Tamil and Hindi included). A taken nickname is refused with "That nickname is taken. If it is yours, press Sign in with it." Sign-in is by nickname; there is no password and the screen says so (demo-grade). Every request carries one header, `X-User` (URL-encoded id).
- **Removed** from code, storage, headers and columns: the random device id (`X-Device-Id`, `cc.device`), the tester device hash (`X-Device-Hash`, `device_hash`), the nickname-hash store key (`X-Store-Key`, `storeKey`) and `STORE_SHARED`. Renamed columns: `device_docs.device` → table `user_docs.owner`; `kept_sheet.device` → `owner`; `tester_*.device_hash` → `user_id`. New: `users`, `profile_sync.owner`, `class_cohorts.group_id`, `tracks.plan_id`, `cohort_plans`, `cohort_plan_modules`. The Telegram adapter is untouched.
- **A browser's cache belongs to one user**: a different user signing in on the same browser starts from an empty cache, so one person's classes are never uploaded under another's nickname.
- **Every route has an access rule** (`services/api/access.py`, table below), enforced by one gate in front of every handler. A route with no rule is closed. Object-level checks in the handlers: the store, consents, practice sessions (owner recorded at creation), kept sheets, class results, `/api/programme/{class}`, papers (`X-Class-Id` must be a class she owns), module tracks, cohort copies.
- **Staff see only what is assigned**: a coach or mentor sees the classes of cohorts assigned to them; the officer sees counts across all (no nickname, no class). `/api/store/peers` and the "other teachers" line are gone; `/api/store/all/*` offers only checks, as counts.
- **A class is its owner plus its class code** (primary key `(owner, collection, doc_id)`).
- **The improvement plan belongs to the cohort** (`services/modules/plans.py`): one `CohortPlan` per (cohort, error) holds module templates and due dates; each teacher's `Track` follows it and keeps her own progress, feedback and branch. A coach's holiday shift and date edits move the cohort's calendar and every member's planned modules.
- **Kept sheets (opt-in, 60 days)** are keyed to the user id; strings and docs now say pictures are held in memory only unless she opts in to keep them for 60 days.

## Migration (local dev databases only)

Backups before any change: `backups/dev.sqlite.pre-identity`, `backups/pwa-dev.sqlite.pre-identity` (and `.pre-cleanup`, `.pre-plans`). Revert logs: `backups/identity-migration-*.json`. Dry-run outputs saved: `backups/identity-dry-run-dev.txt`, `backups/identity-dry-run-pwa-dev.txt`.

Dry run on `dev.sqlite` (a copy of the file, because pysqlite cannot roll DDL back), then applied with identical counts:

```
channel_links.external_id 5     class_cohorts.teacher_id 1     cohort_members.teacher_id 1
channel_links.teacher_id 5      consents.subject_id 43         flow_state.teacher_id 2
profile_sync.owner 5            teachers.rekeyed 5             tester_device.merged 2
tester_device.user_id 2         tester_event.user_id 1464      thread_posts.author_teacher_id 1
user_docs.rows 34               users.created 2
unclaimed (kept under an `unclaimed:<old id>` owner, never deleted): 66 rows
  channel_links 10, class_cohorts 1, cohort_members 1, consents 8, device_docs 34, flow_state 2, profile_sync 4, teachers 5, thread_posts 1
```

`apps/pwa/dev.sqlite`: channel_links 22+22, flow_state 21, teachers 22 re-keyed, all 87 rows unclaimed (no nickname is recorded with them). The second run (plans) is a no-op for the identity steps: **idempotent**.

Why so much is unclaimed: the dev data had no stored nickname for those devices (they came from test and demo sessions). On the real data the mapping is the nickname document stored under each store key (3A, 3B, ...); a device that never stored one cannot be mapped, so it is listed, not guessed. `scripts/claim_unclaimed.py --list` shows them; `--from unclaimed:<id> --to "<nickname>" --apply` hands a set to a real user.

**Plans merged:** the local databases hold no improvement tracks, so the count there is 0 tracks, 0 plans. The merge is covered by `tests/modules/test_plans.py::test_existing_per_teacher_plans_are_merged_without_losing_anyones_progress`: 3 tracks (two in one coach cohort, one on its own) → 2 plans, **1 plan merged**; every module, feedback row and due date is identical before and after.

### Cloud migration script (not run)

`scripts/migrate_identity.py` with `DATABASE_URL` pointing at the hosted database. It refuses `--apply` without `--i-mean-the-hosted-database`. A dry run there runs the same statements in one transaction and rolls back; on Postgres that takes brief table locks, so run it at a quiet time after a Cloud SQL backup. I did not connect to the hosted database, so there is **no cloud dry-run output**; the dry-run output above is from the local databases. Command:

```
$env:DATABASE_URL = "<hosted url>"; python scripts/migrate_identity.py                 # dry run
python scripts/migrate_identity.py --apply --backup-done --i-mean-the-hosted-database  # after a backup
python scripts/migrate_identity.py --list-unclaimed
```

## What `X-Role` lets a judge-mode user do (unchanged)

In a judge deployment (`JUDGE_MODE=1`) `role_of` accepts `X-Role` coach, mentor or officer from **any signed-in user**; a production deployment accepts only teacher. The role's permissions (`services/api/roles/permissions.yaml`; `officer.advance_term` was removed in step D, since terms are off):

| Role | Can |
| --- | --- |
| teacher | assistant.ask, practice.rehearse, check.read_sheets, profile.sync, programme.view_own, cohort.chat, judge.inspect, papers.generate, papers.rules_view |
| mentor | assistant.ask, mentor.record, mentor.items_view, cohort.chat, content.mentor_approve, papers.generate, papers.rules_view |
| coach | assistant.ask, coach.approve_items, coach.moderate, library.view, content.review_view, content.coach_approve, content.propose, papers.generate, papers.review, papers.rules, papers.rules_view |
| officer | assistant.ask, officer.approve_cohorts, officer.results, officer.assign_roles, library.view, content.review_view, content.officer_activate, content.propose |

What the new gate adds on top: a staff user still reaches only the cohorts **assigned to her user id** (a coach: cohorts she made, or cohort spaces naming her; a mentor: spaces naming her), so choosing the coach role does not show another coach's cohorts. The demo role accounts are users like any other (`coach-demo`, `mentor-demo`, `officer-demo` are ordinary nicknames). In judge mode, the demo and judge routes (`/api/demo`, `/api/cohort-run`, `/api/judge`, `/api/pilot-data`) are open to any signed-in user and return 404 outside judge mode. Papers and paper rules are shared by design. `X-Demo-Person` (a or b, one browser acting as two coaches in the papers demo) is unchanged and judge-only.

## Access table (generated from `services/api/access.py`)

| # | Methods | Path pattern | Caller | Handler enforces | Roles |
| --- | --- | --- | --- | --- | --- |
| 1 | any | `/api/health` | public | shared | - |
| 2 | any | `/api/roles` | public | shared | - |
| 3 | POST | `/api/users/register\|/api/users/signin` | public | shared | - |
| 4 | GET | `/api/flow/token/[^/]+` | public | shared | - |
| 5 | GET | `/api/tester/config` | public | shared | - |
| 6 | POST | `/api/telegram/webhook` | external | shared | - |
| 7 | POST | `/api/modules/jobs/due` | external | shared | - |
| 8 | any | `/api/admin/.*` | admin | shared | - |
| 9 | GET | `/api/users/me` | user | self | - |
| 10 | DELETE GET | `/api/store` | user | self | - |
| 11 | DELETE PUT | `/api/store/[^/]+/[^/]+` | user | self | - |
| 12 | GET | `/api/store/coach-summary` | staff | assigned | coach mentor officer |
| 13 | GET | `/api/store/all/[^/]+` | staff | assigned | coach mentor |
| 14 | POST | `/api/consents` | user | self | - |
| 15 | DELETE POST | `/api/classes/[^/]+(/profile)?` | user | class | - |
| 16 | GET | `/api/programme/[^/]+` | user | class | - |
| 17 | any | `/api/flow/.*` | user | self | - |
| 18 | any | `/api/audio/pack(/cap\|/script)?` | user | self | - |
| 19 | any | `/api/assistant/.*` | user | self | - |
| 20 | POST | `/api/feedback` | user | self | - |
| 21 | any | `/api/tester/.*` | user | self | - |
| 22 | GET | `/api/judge/testing-evidence` | user | counts | - |
| 23 | GET | `/api/team/testing-export` | external | counts | - |
| 24 | GET | `/api/actions/[^/]+/usage` | user | self | - |
| 25 | any | `/api/sheet-keep/.*` | user | class | - |
| 26 | POST | `/api/sheets/read` | user | self | - |
| 27 | POST | `/api/stages` | user | self | - |
| 28 | any | `/api/practice/.*` | user | self | - |
| 29 | GET | `/api/lessons/audio` | user | shared | - |
| 30 | any | `/api/modules/coach/.*` | staff | assigned | coach |
| 31 | any | `/api/modules/mentor/.*` | staff | assigned | mentor |
| 32 | any | `/api/modules/.*` | user | cohort | - |
| 33 | any | `/api/cohort-chat/.*` | user | cohort | - |
| 34 | GET POST | `/api/cohorts/class-only` | user | self | - |
| 35 | GET POST | `/api/cohorts/class-only/coach` | staff | assigned | coach |
| 36 | GET POST | `/api/cohorts/class-only/(officer\|form)` | staff | counts | officer |
| 37 | any | `/api/cohorts/coach/.*` | staff | assigned | coach |
| 38 | any | `/api/cohorts/mentor/.*` | staff | assigned | mentor |
| 39 | any | `/api/cohorts/officer/.*` | staff | counts | officer |
| 40 | any | `/api/cohorts/.*` | user | cohort | - |
| 41 | GET | `/api/officer/.*` | staff | counts | officer |
| 42 | any | `/api/paper-hub/.*` | user | shared | - |
| 43 | any | `/api/papers(/.*)?` | user | shared | - |
| 44 | any | `/api/paper-rules(/.*)?` | user | shared | - |
| 45 | any | `/api/review/.*` | staff | shared | coach mentor officer |
| 46 | any | `/api/demo/.*` | judge | self | - |
| 47 | any | `/api/cohort-run/.*` | judge | self | - |
| 48 | any | `/api/judge/.*` | judge | self | - |
| 49 | any | `/api/pilot-data/.*` | judge | self | - |

## Tests

Run on 4 Nov 2026 on this branch. Python was run one directory at a time (the whole tree at once collides on duplicate test file names). Failures were compared with the step A commit (85bcebd), checked out in a separate worktree and run area by area, so a failure is called pre-existing only where the same area fails the same number of tests there.

| Area | Passed | Failed | Against step A |
| --- | --- | --- | --- |
| ai, api (133, incl. the new identity and access tests), channels, cohort_chat, cohorts, evals, media, modules (254, incl. the new plan tests), papers, pilot_demo, practice, roles, sheets_keep, sprites, store | 2,106 | 0 | n/a |
| assistant | 217 | 1 (index current) | same 1 |
| chat | 129 | 2 (scheduler) | same 2 |
| cohort_run | 16 | 20 | same 20 (25% rule removed 2 Nov; tests not yet updated) |
| content | 138 | 1 (configurable thresholds) | same 1 |
| demo | 21 | 5 | same 5 |
| engine | 432 | 4 (25% eligibility) | same 4 |
| flows | 30 | 2 (t4) | same 2 |
| papers_hub | 56 | 3 | same 3 |
| spoken | 30 (+4 skipped) | 1 | same 1 |
| usage | 7 | 1 | same 1 (this run stopped at the first failure; full run not repeated) |
| speech | 102 | at least 1 | not compared; this run stopped at the first failure |
| data | - | collection error | same error on step A (not checked by name) |
| top-level `tests/test_*.py` | not run | | |

Result: **2,741 passed; 40 failed in the areas run in full, all in areas that fail the same number at step A.** None of the 40 is caused by steps B or C, but I compared counts per area, not test by test. Two things that only the full run found and that were mine, now fixed: `/api/judge/*` answered 404 instead of 403 outside judge mode (3 tests in `tests/ai/test_judge_api.py`; it now answers 403 again), and the README "Where AI is used" block was out of date (regenerated).

Vitest: 513 passed, 3 failed (`flow.test.ts` x2, `profile.test.ts` x1), the same 3 that fail at step A.

**Playwright was not completed (the user chose to skip it).** A 107-spec subset (landing, tester, profile, check, checks, enter-check, app, tour, programme) was started: 47 specs ran before I stopped it, and every one of the 10 `enter-check.spec.ts` specs in that stretch failed. I ran `enter-check.spec.ts:341` in a visible browser: it times out at `e2e/sample.ts:55`, waiting for `paper-attached` ("the only paper is chosen for her"). I did not find the cause. It is likely mine (papers are now limited to a class she owns, `X-Class-Id`), but I did not confirm it. The `app.spec.ts:44` judge-mode spec also failed in that run. Neither was compared with step A. **Treat Playwright as red for these specs until Phase 3.**

## Not done in this step (as planned)

Sync/outbox and the reconnect popup (E), shared-papers flag (D), one error-rule control (F), the officer page work (G), the browser audio player (H), the full docs/help/INVENTORY/README rewrite and assistant index rebuild (Phase 3). The remaining old wording ("answers stay on your phone", "random device id") in strings and docs that are outside the sheet-picture statements is listed in the Phase 3 conflicts.
