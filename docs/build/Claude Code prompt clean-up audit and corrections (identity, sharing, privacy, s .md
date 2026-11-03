# Claude Code prompt: clean-up audit and corrections (identity, sharing, privacy, sync, error rule, officer cohorts, terms, audio)

Paste everything below the line into Claude Code at the repo root.

---

**Task.** The app has drifted from how it should work. Do this in two phases.

- **Phase 1, read-only audit:** find out where every page and feature stands against the ten corrections below, with evidence. Write a report and a fix plan, then **STOP and wait** until I say go.
- **Phase 2, fixes:** when I say go, make the corrections in the order given, test them, and verify them in the browser.

## Rules for the whole job

- Work on a branch called `cleanup/identity-sharing-sync`. Commit locally after each correction. **No push, no merge, no deploy.**
- **Back up the development database** before any migration, and note the path in the report. **Never delete user data.** Migrations must be reversible and have a dry run that prints what would change.
- **Never weaken or delete a test to make it pass.** If a test encodes an old rule that these corrections replace, change it, and list it in the report with the reason.
- **These corrections override older decisions.** Where `CLAUDE.md`, `DECISIONS.md`, help documents or interface text say otherwise (for example that answers stay on the phone, or that officers never see fewer than 5), the correction wins. Update those documents and add a dated `DECISIONS.md` entry. **Do not edit any deck.** List the deck sentences that will become untrue.
- **Unchanged:** no child names anywhere, roll numbers only, masking in the chat and the assistant, chat labels in place of names, code decides every number, honest labels, and sheet pictures held in memory only and never stored.
- Follow `docs/design/stitch/DESIGN.md`, 44 px touch targets, every string in `en`, `hi` and `ta`.

## The ten corrections (the target)

1. **The nickname is the user id.** All data is linked by the user id, which is the nickname. Remove every browser id, device id, installation id, fingerprint or device hash, everywhere: generation, storage, headers, database columns and analytics keys. Sign-in session tokens may stay, but they identify a session, never a device, and are never used to link data.
2. **Papers are shared.** Every created paper is visible to every user on the Papers page and in Enter check's paper chooser. The assignment feature is not available, so hide its interface (Assigned to you, Assign) behind a flag that is off.
3. **Entered check data is private in the interface.** A user sees only the checks, answers, approvals, results and answer maps that **their user id entered**. The backend may use every user's entered data to build cohorts and to compute coach and officer counts.
4. **Sync, with the cloud as the source of truth.** When online, nothing exists on the device alone: every change is written to the cloud database at once, and the device keeps only a cache and an offline outbox. When the app comes back online with unsynced changes, show a popup saying they will now be synced to the cloud, then show the result.
5. **One error-rule control everywhere.** An error is confirmed when it is seen in two or more questions, and possible when it is seen in one. The results page has a checkbox to count one question or two. **Every place that uses these counts gets the same control**, above all the coach and officer pages.
6. **Officers can create cohorts, with no caps in the demo.** The officer page has Create a cohort. Every number on the officer page must be correct. In demo mode, remove every cap and suppression (at least 5 children, 5 schools, 5 teachers, a minimum number of classes, and so on).
7. **Cohorts, improvement tracks and Practice Class are scoped to users.** Access in the interface follows the table below.
8. **A clear line between shared and user-specific data:**

| Data | Belongs to | Who sees it in the interface | The backend may use it for |
| --- | --- | --- | --- |
| Papers | shared | everyone | everything |
| Classes | the user who created or entered them | that user | cohort building, counts |
| Checks, entered answers, approvals, results, answer map | the user who entered them | only that user | cohort building, coach and officer counts |
| Cohorts | the creator (a teacher for a single-class cohort, an officer for a multi-class one) | its members and its creator | membership, counts |
| Improvement plan (modules) | the cohort | the cohort's members | module choice, counts |
| Module feedback and check-ins | the user who gave them | that user (coaches and officers see counts) | the next module, counts |
| Practice Class | the class (owned by its teacher) | that teacher | nothing else |
| Cohort chat | the cohort | members, its mentor and coach | nothing else |
| Coach and officer pages | not applicable | counts across all users | not applicable |

9. **Turn off term logic.** No current term, no term filter, no term blocking, and no automatic change of term. All of a user's checks show in one list by date. My data entered in term 1 was moved to term 2 and disappeared: find out why, fix it, and make all of it visible again.
10. **Listen in the browser (second priority).** The audio files of an improvement plan can be played in the browser, not only downloaded.

## Phase 1. The audit (read only)

**Step 0. Read** `CLAUDE.md`, `DECISIONS.md`, `PROGRESS.md`, `AI_USAGE.md`, `docs/RUBRIC_MAP.md`, `docs/design/stitch/INVENTORY.md`, the README, `docs/help/*.md`, the reports in `docs/build/reports/`, the router, every screen, the API routes and their authorisation, the database models and migrations, the local stores (IndexedDB, localStorage, caches, the service worker and the offline queue), the engine's error rule, cohort formation, the officer and coach pages, the module and track code, Practice Class, the chat, and the test suites.

**Step 1. Inventory.** List every page and feature with its route, its components, the API endpoints it calls, the tables it reads and writes, and anything it keeps on the device. Include at least: first run and nickname, sign-in and roles, Home, Papers (list, create, import, detail), Enter check, Results (class card, answer map, error explanations, coverage matrix), My class, cohort list and cohort page, the improvement plan and modules, feedback and check-in, Practice Class, Cohort chat, the assistant, the coach pages and review queue, the officer page, the Testing evidence page, the demo stepper and the settings.

**Step 2. Check each correction, with evidence** (file and line, a query result, or a reproduced behaviour):

- **1:** every place a browser or device id is created, stored, sent or used to link data; how users are identified today; where the nickname is stored and whether it is unique; how each role signs in; how existing rows are keyed.
- **2:** every filter on papers (by class, teacher, assignment); where the assignment interface appears.
- **3:** which endpoints and screens list or return checks and results, and whether another user can see them (test it with two users); whether cohort formation and the officer counts read every user's data.
- **4:** every data type the app writes (checks, answers, marks, tags, approvals, feedback, check-ins, chat posts, settings, Practice Class sessions), and for each one whether it reaches the server, when, and what stays only on the device; how the offline queue works, how it reconnects, and how it handles conflicts.
- **5:** every place that shows an error count, and which rule each one uses; how the results page checkbox works; whether the API supports both rules.
- **6:** recompute every number on the officer page from the database with a script, and compare. List **every cap or suppression** (its name, value, file and line, and what it hides). Say whether officers can create a cohort.
- **7 and 8:** for each entity in the table, its current owner field and access checks, compared with the target.
- **9:** where the term is computed, stored, filtered and blocked; **reproduce the term 1 to term 2 move** with my data and explain its cause.
- **10:** how module audio is served and downloaded today, and whether a player exists.

**Step 3. A matrix:** pages and features as rows, corrections 1 to 10 as columns, each cell OK, Partly, No or not applicable, with an evidence reference.

**Step 4. Conflicts:** documents, interface text and deck sentences that the corrections make untrue. For example: answers stay on the phone; only counts leave the phone; this table stays on this phone; officers never see fewer than 5; Assigned to you. List them, and do not edit decks.

**Step 5. A fix plan** in the order of Phase 2, with the files, migrations, data changes (with a dry run), risks and tests for each step, and the size of each.

Write `docs/build/reports/CLEANUP-AUDIT.md`, print the matrix summary and the plan in the chat, and **STOP. Wait for me to say go.**

## Phase 2. The fixes (only after I say go), in this order

**A. Terms off (correction 9).** Remove term computation, filtering, blocking and automatic change. Leave any term column in the database but stop reading and writing it. Remove term labels and selectors from the interface. Keep the kind (pre-test, post-test, termly check). Fix the cause of the term 1 to term 2 move, add a regression test, and confirm my earlier entries are visible.

**B. Identity (correction 1).**

- The user id is the normalised nickname: trimmed, lower case, single spaces, letters, digits, spaces and hyphens, 3 to 30 characters, **unique**. When a nickname is taken, say so and ask for another.
- First run: choose a nickname (reuse the existing tester prompt). On another device: sign in by nickname and get all of your data from the cloud. Role accounts in the demo keep their credentials, and each maps to a user id. The role is an attribute of the user.
- Remove every device or browser id in code, storage, headers, columns and analytics.
- **Migration:** move rows keyed by a device id to the matching user id where a mapping exists. Rows that cannot be mapped go to an unclaimed owner, are listed in the report and are never deleted. Add a script to claim them by nickname.
- Other teachers never see a nickname. The chat keeps its labels. Coaches and officers may see nicknames only in cohort membership.
- Write in the report and the README that a nickname without a password is demo-grade identity.

**C. Ownership and access (corrections 3, 7 and 8).**

- Add an owner user id where it is missing (classes, checks, entries, approvals, feedback, check-ins, Practice Class sessions, cohorts as creator), and backfill it.
- A class is identified by the owner and the class code together, so two users can both have 3A.
- **Enforce access on the server, for every endpoint:** list, get, update and delete return only the user's own records, following the table. Aggregate endpoints for coaches and officers return counts only. The cohort builder and the officer counts read across all users.
- The interface shows only the user's own checks, results and answer maps, the cohorts they belong to or created, their improvement plan, and the Practice Class for their own classes.

**D. Shared papers (correction 2).** All users see all papers on the Papers page and in Enter check, with optional filters by class code, kind and form that never hide another user's paper. Hide the assignment interface behind a flag that is off. A paper keeps its creator's label.

**E. Sync (correction 4).**

- The cloud is the source of truth. Every change made online is written to it at once. The device keeps a cache for reading and an outbox for offline changes, with a version on each record.
- **When the app comes back online with items in the outbox,** show a popup: You made N changes while you were offline. They will now be saved to your account in the cloud. Show progress, then the result: All saved, or the list of what could not be saved, with the reason and Retry. Nothing stays on the device alone after that.
- **Conflicts:** check versions. The later write wins per record, but nothing is lost silently: keep the overwritten version in a short Changes that conflicted list the user can open.
- Remove device-only logic and wording for entered data, marks, the Missed the teaching tags, approvals and feedback. **Sheet pictures stay in memory only and are never stored**, unchanged.
- After signing in on a new device, pull the user's data from the cloud.

**F. One error-rule control (correction 5).**

- A single shared control: Count an error when it is seen in: two or more questions (confirmed), or one question (possible). The default is two or more. It is saved per user in the cloud.
- **Use it everywhere** error counts appear: the results page (class card, answer map legend, error explanations, coverage matrix), the cohort page, the coach pages, the officer page and officer cohort creation, and any export. Each view says which rule it is showing.
- Endpoints take the rule as a parameter, and the engine's own classification decides. No arithmetic happens in the interface. A cohort record stores the rule it was built with.

**G. The officer page (correction 6).**

- Fix every number that did not match the recomputation from Phase 1.
- **Caps:** in demo mode, turn every cap and suppression off (cell minimums, minimum classes, teachers or schools for a cohort, hidden small groups). Keep the production values in configuration, and show a small label Demo: no minimum group sizes.
- **Create a cohort:** the officer chooses an error (with the rule control), sees the classes that show it (nickname, class code, and the number of children with that error, with no child-level data), selects all or some, names it, and creates it. Members then see the cohort, its improvement plan starts as it does today, and its chat opens. Write an audit entry.

**H. Listen in the browser (correction 10, second priority).** On each module of an improvement plan, add a player: play and pause, a seek bar, the time and length, speed 0.75, 1 and 1.25, and the existing Download. Use the same audio file. Play the downloaded copy when offline. No autoplay. Accessible labels. Record a played event in the module's status.

## Phase 3. Verify

- **Tests:** unit tests for the nickname rules, ownership, the rule control and the sync outbox. API tests for every endpoint with **two teacher users, a coach and an officer**, proving each sees only what the table allows. Browser tests for the flows below. Existing suites still pass, with counts before and after.
- **Browser walk-through** (two browser profiles stand in for two devices):
  1. Teacher A enters a check. Teacher B cannot see it. The officer sees counts, switches the rule, and creates a cohort from both classes. Both teachers see the cohort and its plan.
  2. Teacher A goes offline, enters answers, comes back online, sees the popup, and everything is saved. The cloud database has it.
  3. Teacher A signs in with the same nickname on the second profile and sees the same data.
  4. No term appears anywhere, and my earlier entries are visible.
  5. A module's audio plays in the browser.
  6. Every page shows the error rule control where counts appear, and the counts change correctly.
- **Report:** `docs/build/reports/CLEANUP-REPORT.md` with the matrix before and after, the migrations run, unclaimed rows, the tests, and the list of deck sentences to change. Update `CLAUDE.md`, `DECISIONS.md`, the help documents, `docs/design/stitch/INVENTORY.md` and the README.

**Done when** the audit report exists and I have said go, then every correction is in place and tested, the walk-through passes, no device or browser id remains anywhere, my term 1 data is visible, and the cleanup report is written.
