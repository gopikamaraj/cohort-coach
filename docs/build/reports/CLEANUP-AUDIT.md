# Cleanup audit: identity, sharing, privacy, sync, error rule, officer cohorts, terms, audio

Phase 1 of `docs/build/Claude Code prompt clean-up audit and corrections (...).md`. Read-only: no code, data, database or deploy was changed. Branch `cleanup/identity-sharing-sync` (created from `cohort-chat`, nothing committed on it yet). Date: 3 Nov 2026.

Evidence comes from code reading with file and line (four parallel read-only passes plus my own greps). **Not done:** the officer numbers were not recomputed against the database by script (the dev database holds none of the 3A/3B data, and I did not query the cloud database); that recomputation is the first task of step G. No two-user reproduction was run: findings marked "by code" are code reading, not a live reproduction.

## Headline findings

1. **There are three parallel identities, and none of them is the nickname as a key.** (a) a random browser "device id" in localStorage, mapped on the server to a `Teacher` row (`t-` plus 16 hex) that owns cohorts, modules, chat, the pack-audio quota and consents; (b) a "store key", a 64-bit non-secret hash of the lower-cased nickname, which keys the cloud store (classes, checks, results, settings); (c) a separate tester analytics `device_hash`. Nicknames are not unique anywhere (the dev database holds "3A Math" three times).
2. **Entered data is not private.** A second person who types the same nickname reads and overwrites the first person's checks, results and answer maps (`devicestore.py:50-58`, `cloudStore.ts:81-93`). `/api/store/peers` gives any teacher other teachers' nicknames, class names and which errors they show.
3. **Papers are already shared** (lists have no per-class filter), but the assignment feature is fully live with no flag.
4. **Sync is partial and silent.** Classes, checks, results and settings are written through at once; there is no reconnect popup, no per-record version, no conflict list, and a refused save (any 4xx) is dropped without a word (`cloudStore.ts:117`). Cohort, chat, check-in and module writes have no offline queue.
5. **The error rule is not one rule.** The teacher's results page has a local checkbox (default off, not saved); the coach and officer pages always count a mistake seen even once; no endpoint takes a rule; a cohort does not store its rule; a third (25%) rule survives in unused officer endpoints.
6. **The officer can create cohorts only in bulk** (one button), with no class selection, no rule control, no nickname list and no audit entry. About a dozen caps and suppressions exist (table below); none depends on a demo flag. The officer page's error map and track results are not rendered or are always empty.
7. **Term logic is everywhere** (ids, state, labels, sorting, server grouping). The "term 1 to term 2" loss has identified causes (below); the term-1 data is not deleted, it is hidden.
8. **No audio player exists for modules.** Download only.

## Matrix: pages and features against corrections 1 to 10

OK = meets the target, P = partly, N = no, n/a = not applicable. Numbers in brackets point to the evidence list after the matrix.

| Page or feature | 1 id | 2 papers | 3 private | 4 sync | 5 rule | 6 officer | 7/8 scope | 9 term | 10 audio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| First run, nickname | N [1] | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| Roles and sign-in | N [2] | n/a | n/a | n/a | n/a | n/a | P [2] | n/a | n/a |
| Home | N | P [8] | P | P | n/a | n/a | P | N [9] | n/a |
| Papers (list, detail, import, create) | N | P [8] (visible to all; assignment live) | n/a | P | n/a | n/a | P | P | n/a |
| Enter check (chooser, entry, approve) | N | P [8] | N [3] | P [4] | n/a | n/a | N | N [9] | n/a |
| Results (class card, answer map, explanations, matrix) | N | n/a | N [3] | P | P [5] (local checkbox only) | n/a | N | P | n/a |
| My class and cohort maker | N | n/a | N | P | P [5] | n/a | P | N | n/a |
| Cohort list and cohort page | N | n/a | n/a | N [4] (online only) | P | n/a | P [7] | n/a | n/a |
| Improvement plan, modules | N | n/a | n/a | N [4] | n/a | n/a | N [7] (belongs to one teacher) | n/a | N [10] |
| Feedback and check-in | N | n/a | OK [7] | N [4] | n/a | n/a | OK (owner only) | n/a | n/a |
| Practice Class | N | n/a | n/a | OK by design (stays on device) | n/a | n/a | P [7] (no server owner) | n/a | n/a |
| Cohort chat | N | n/a | n/a | N [4] | n/a | n/a | P [7] | n/a | n/a |
| Assistant | N | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| Coach pages, review queue | N | n/a | P [6] | n/a | N [5] (fixed any-rule; old block panel uses the 5-class rule) | n/a | P [7] (not scoped to assigned cohorts) | N (per-term) | n/a |
| Officer page | N | n/a | OK (counts) | n/a | N [5] | P [6] | P [7] | N [9] | n/a |
| Testing evidence | N [1] (device hash) | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| Demo stepper and Tour | N | n/a | n/a | n/a | n/a | n/a | n/a | N [9] (advance buttons) | n/a |
| Settings, privacy notice | N | n/a | n/a | N [4] (wording: "only on this phone") | n/a | n/a | n/a | n/a | n/a |

### Evidence

- **[1] Identity.**
  - The device id is created at `apps/pwa/src/lib/consent.ts:69-76`, stored in localStorage `cc.device`, and sent as `X-Device-Id` from `assistant.ts:70`, `cloudStore.ts:97`, `cohort.ts:45`, `flow.ts:40`, `gatedChat.ts:67`, `keptSheets.ts:14`, `modules.ts:67,286`, `packAudio.ts:68,86`, `paperHub.ts:31,52`. The consent body carries `device_id` (`consent.ts:87`).
  - The tester device hash is `sha256(salt + deviceUuid)` (`tester.ts:238-246`), sent as `X-Device-Hash` and `device_hash` (`tester.ts:338,380,390,408`).
  - The server maps a device id to a teacher with `ChannelLink("pwa", device)` and `Teacher` (`services/api/flows/engine.py:76-93`, `db.py:285-306`). Header readers: `channels/pwa/__init__.py`, `cohorts/routes.py:56-59`, `cohorts/class_only.py`, `cohort_chat/api.py:23-28`, `modules/api.py:108-153`, `api/pack_audio.py:122-171`, `api/assistant.py:135-143`, `api/devicestore.py:85-158`, `sheets_keep/api.py`, `api/feedback.py:72-90`, `tester/routes.py`.
  - The nickname lives in tester prefs (`tester.ts:40,269-286`, max 30 characters, optional) and a mirrored settings document; server `tester_device.nickname` has no unique constraint. A nickname can be a real name (dev data has one).
- **[2] Roles.** `X-Role` is read by `role_of` (`services/api/roles/__init__.py:39-46`); a non-teacher role is accepted only when `JUDGE_MODE=1`, so in judge mode anyone can send `X-Role: coach`. Coach and mentor identity is `X-Person` (`cohorts/routes.py:32-37`), honoured only in a judge session, otherwise `<role>-demo`, so all coaches share one identity. There is no sign-in and no session token today.
- **[3] Privacy.** `GET /api/store` returns everything under the key (`devicestore.py:90-100`); `/all/profiles` and `/all/settings` return raw documents to coach and mentor (`devicestore.py:254-265`); `/peers` has no role check (`devicestore.py:151-180`).
- **[4] Sync.** `cloudStore.ts:44-166` (queue holds ids only, no payload or version; 4xx dropped at `:117`; hydrate deletes unqueued local rows at `:164`); `sync.ts` is a second, older profile queue; cohort, chat, check-in and module calls are online-only (`cohort.ts:60`, `gatedChat.ts:70`, `modules.ts:70`).
- **[5] Rule.** `MIN_HITS=2` in `engine/diagnosis.py:26`; checkbox in `components/MistakesTable.tsx:28-32,74` with state in `screens/Cards.tsx:45` (not persisted); `InterventionPack.tsx:28` and `PackSummary.tsx:38` fixed at 2; server `devicestore.py:139-143,183-243` and `officer.py:147` use the any-rule; `officer.py:36,44-48` holds the old 25% rule.
- **[6] Coach.** `RoleScreens.tsx:116-148` still reads the synthetic block with a client-side `MIN_CLASSES=5` beside the real entered-classes panel, so the two cannot agree.
- **[7] Ownership.** `ClassCohort.teacher_id` is the creator's teacher id or the constant `coach-cohorts`; `Track` belongs to one teacher (`modules/api.py:104-120`), so cohort members who are not the creator get "no_cohort" unless `_adopt_group_cohorts` made them a copy; `coach_counts` and `mentor_counts` have no assignment check; `cohort_run` routes have no auth; `/programme/{class_id}` does not check the class belongs to the caller. Not verified: every `cohort_chat` route's membership check; Practice Class session ownership.
- **[8] Papers.** `papers_hub/api.py:286-311` and `services/api/papers.py:129-135` list every non-archived paper and ignore `class_id`; `_visible()` (`api.py:234-251`) is dead scoping. Assignment appears at `Papers.tsx:215-227,279-287,500`, `Home.tsx:34`, `PaperHubParts.tsx:257-340,410,424-439`, backend routes `api.py:406,458,486,494,505,513`; no flag exists.
- **[9] Term.** See the section below.
- **[10] Audio.** `ModuleTrack.tsx:245-257` renders `AudioDownload` only; `packAudio.ts:95-115` builds a Blob and clicks a download link. Players exist elsewhere (`LessonAudio.tsx:49`, `Programme.tsx:137`, `TwoClasses.tsx:412`, `DemoStudio.tsx:402`).

## Correction 9: why term 1 data "moved to term 2 and disappeared" (by code)

The data is **not deleted**. A check is stored as `classId:term` and the screens load only `classId:currentTerm` (`state.tsx:72-73`, `Check.tsx:132,181`). When the term moves to 2, the term-1 check and result are still in IndexedDB and the cloud but no page asks for them. The term moves on its own through three paths:

- **A.** Every "Check another paper" unconditionally sets `term + 1` (`Check.tsx:259-274`).
- **B.** The Tour and Judge "advance" buttons set term 2 (`state.tsx:161-164`, `Judge.tsx:54`, `Tour.tsx:118`).
- **C.** `term` is a synced setting, and the store key is the nickname hash. Any other browser using the same nickname that hits A or B writes term 2 into the shared cloud copy; the first browser reads it back on its next open (`cloudStore.ts:160-166`). This is the "it shows term 1 first and then goes to term 2" you saw.

Also, "Choose another paper" deletes `classId:currentTerm` (`Check.tsx:244-245`), which removes the check if the term was already 2. A stopgap `FIXED_TERM = 1` (`db.ts`, commit `f72be8d`) makes the term read as 1; it does not remove term from ids, labels, sorting (`history.ts:42` sorts by term first) or the server (`entered_summary`, `officer.py:80,137-156`, `class_only.py:139-207`, `profiles.py:40,102`).

The live cloud store currently holds the real checks under `classId:1` and one store with `term` = 2 (set back to 1 on 2 Nov, but a browser that writes it again can flip it).

## Caps and suppressions (correction 6)

| Name | Value | File and line | What it hides |
| --- | --- | --- | --- |
| `MIN_CLASSES_SHOWN` | 5 | `engine/evaluation.py:33` (used `officer.py:64,139,205,206,216`) | old error map cells, results, funnel cells |
| `PILOT_MIN_CLASSES` / `OFFICER_MIN_CLASSES` | 2 (env) | `officer.py:35,119-125` | entered-classes figures below 2 |
| `MIN_CELL` | 5 | `services/demo/cohorts.py:24` | demo officer view |
| `MIN_CELL` | 5 | `services/cohort_run/service.py:58` | cohort-run classes and feedback |
| `MIN_FIGURE` | 5 | `services/api/cohorts/lifecycle.py:27` | schools and members counts |
| `MIN_CLASSES` | 5 | `services/content/lesson_audio.py:31` | lesson script and audio for small cohorts |
| `MIN_FOR_SUMMARY` | 5 | `services/api/programme.py:27` | programme summary |
| thread read-only | under 5 members | `services/api/cohorts/thread.py:32` | cohort thread posting |
| `COHORT_MIN_CLASSES` | 15 (env) | `services/cohort_run/settings.py:34-37` | cohort formation |
| hard-coded 2-class minimum | 2 | `class_only.py:150,203` | coach and officer cohort creation |
| `MIN_CHILDREN_CHECKED` | 10 | `engine/diagnosis.py:31` | eligibility |
| `MIN_CLASSES` in `Coach()` | 5 | `RoleScreens.tsx:114,138` | whole coach block term |
| assistant suppress | 5 | `services/assistant/scopes.py:76`, `tools.py:83` | assistant counts |
| time budget | under 5 teachers | `services/api/time_budget.py:70` | time-budget figures |

None depends on a demo flag. There is no "Demo: no minimum group sizes" label and no demo switch in `cohort_run/settings.py`.

## Officer page numbers (what I could check without a database recompute)

Shown on the page now: entered classes, track results (always empty while the term is fixed), cohort lifecycle list (counts hidden under 5), review-waiting line. Computed by the server but **not shown**: the error map. A class is counted once per profile with children, so a class entered twice in a term counts twice (`entered_summary`). The old `/error-map`, `/results` and `/funnel` rows still read the synthetic block and disagree with `/entered`. Full recomputation against the database is the first task of step G.

## Conflicts: statements the corrections make untrue

Documents and interface text (I will update these in Phase 2; **I will not edit any deck**):

- `CLAUDE.md` rule 2 ("random device id", "per-child answers stay on the device", phone keeps only a cache), rule 3 ("transcripts stay on her phone"; "any figure covering fewer than 5 classes is hidden"), rule 15 and the cohort-space bullet (pseudonymous ids), section 6 ("IndexedDB … holds Practice Class transcripts and the offline outbox only"), section 5 ("Eligibility … ≥ 10 children checked"; "Check … one per term").
- `docs/privacy.md` lines 11-21, 31, 36, 48 (random class id, random device id, per-child answers never leave the phone, consent under a random device id).
- `docs/offline.md` "What stays on the phone" (line 34) and line 53.
- `docs/help/product.md:55` ("Per-child answers stay on your phone; only counts … are sent"), `docs/help/teacher.md:45,49,61` ("papers assigned to you come first", term wording), `docs/help/coach.md:13,59`, `docs/help/judge.md:57`, `docs/help/officer.md`, `docs/design/addendum-v3.1.md:56,91` (officers see nothing under 5 classes; role records tied to a pseudonymous id).
- `README.md:107,266` (rehearsal stays on the phone; tester stats collect a nickname and device class).
- Interface strings (`strings/en.json`, with hi and ta): `check.saved` "Saved on this phone", `history.private`, `notice.answers_where` "Only on your phone", `notice.children_body`, `notice.consent_where` "our server under a random device id", `onb.consent_core` ("each child's answers stay on your phone"), `profile.delete_class_confirm`, `profile.erase_confirm`, `profile.data_note`, `ba.counts_note`, `review.private`, `practice.saved`, `officer.rule`, `officer.hidden_teachers`, `officer.fewer_than_5_classes`, `officer.cohort_hidden`, `judge.term`, `judge.advance`, `home.term`, `home.status.*`, `home.action.check`, `cards.none`, `history.check_line`, `check.term_n`, `coach.term`, `t1.status`, `t6.result`, `tour.s5.title`, `roles.can.officer_advance`, `officer.map`, and the `ph.assign_*` and "Assigned to you" strings.
- The assistant's help index (`services/assistant/index/*.json`) is built from `docs/help/*.md` and must be rebuilt after those change.
- Tests that encode old rules (to be changed with a reason, never deleted): tests and specs mentioning device ids (`tests/api/test_admin_data.py`, `test_feedback_admin.py`, `test_tester.py`, `tests/channels/test_golden.py`, `tests/speech/test_pack_audio.py`, `cloudStore.test.ts`, `papers.test.ts`, `tester.test.ts`), term logic (`flow.test.ts`, `profile.test.ts`, `checks` tests), `tests/store/test_devicestore.py` (separate store per key, peers), the five-class tests for the officer and coach, and the Playwright specs that click the old cohort buttons. 53 test files mention a device id or a term.

Deck sentences that will become untrue (listed for you; not edited): "answers never leave the phone"; "no accounts or logins"; "pseudonymous random id, nothing links to a person"; "officers never see a figure over fewer than 5 classes"; "term-based check"; any slide that says assignments are how teachers receive papers; the guardrail and privacy slides that describe the device id and the 60-day sheet keep (unchanged but described with the device id).

## Decisions I need from you before Phase 2

1. **Nickname is a credential-less identity.** As written (correction 1) anyone who types a nickname reads that person's data, and a nickname is free text that can be a real name. Your prompt asks me to document this as "demo-grade". I will do exactly that, plus: unique nicknames, a clear "taken" message, and sign-in by nickname. I will **not** add a password unless you ask. Tell me if you want a PIN or password later.
2. **Coaches and officers in the demo.** Role accounts keep their credentials in the demo; in judge mode the server accepts any `X-Role`. I will map each role account to a user id but leave the judge-mode behaviour as is. Confirm that is acceptable for the demo.
3. **Telegram and `STORE_SHARED`.** The Telegram adapter keys by chat id and `STORE_SHARED=1` collapses everyone. Telegram is roadmap only; I plan to leave the adapter as is (and not part of the demo) and remove `STORE_SHARED`. Confirm.
4. **Privacy rule 2 and the "never store sheet pictures" line.** Unchanged, as you said. The opt-in "keep my sheets 60 days" feature currently keys by device id; I will re-key it to the user id.
5. **Peers line on the class page** ("other teachers whose classes show this mistake") shows other users' nicknames to teachers. Correction 3 says a user sees only their own data and the prompt says "other teachers never see a nickname". I plan to **remove it**. Confirm.

## Fix plan (Phase 2 order)

Each step ends with tests, a local commit on this branch, no push or deploy. Back up `dev.sqlite` and `apps/pwa/dev.sqlite` before any migration, and note the paths in `CLEANUP-REPORT.md`.

| Step | What | Main files | Data change (with dry run) | Risks | Size |
| --- | --- | --- | --- | --- | --- |
| **A. Terms off (9)** | Remove term from ids, state, labels, sorting, server grouping; list all checks by date; keep existing `classId:1/2` rows and the database term columns (unread); delete `nextPaper` term bump, `advanceTerm`, Tour/Judge advance, `FIXED_TERM`; kind kept (pre, post, termly) | `db.ts`, `state.tsx`, `Check.tsx`, `StartCheck.tsx`, `Home.tsx`, `History.tsx`, `history.ts`, `checks.ts`, `check.ts`, `Papers.tsx`, `papers.ts`, `backup.ts`, `sync.ts`, `Tour.tsx`, `Judge.tsx`, `devicestore.py`, `officer.py`, `class_only.py`, `profiles.py`; strings | none (rows kept; the cloud `term` setting stops being read) | many files; a stale `classId:term` key can collide if a class has two checks of the same kind: key by class and date instead | large |
| **B. Identity (1)** | Nickname (normalised, unique, 3 to 30 characters) is the user id; sign-in by nickname on a new device; remove device id, tester hash, `X-Device-Id`, `X-Device-Hash`, `X-Store-Key` in code, storage, headers, columns | `consent.ts`, `tester.ts`, `cloudStore.ts` and the `*.ts` libs above; server header readers listed in [1]; models for `Teacher`, `ChannelLink`, `device_docs`, `kept_sheet`, `consents`, `tester_*` | **Alembic migration**, reversible: re-key rows to the user id where a mapping exists (store key and device id both known for a nickname), others to an `unclaimed` owner, listed in the report; `scripts/claim_unclaimed.py`; dry run prints counts per table | touches about 15 tables; Telegram external ids; tests that send device headers | very large |
| **C. Ownership and access (3, 7, 8)** | Owner user id on classes, checks, entries, approvals, feedback, check-ins, Practice sessions, cohorts as creator; class key is owner plus class code; enforce on every endpoint; modules belong to the cohort; remove `/peers`, raw `/all/*` documents; scope coach and officer endpoints to counts; scope coach cohort counts to assigned cohorts; auth on `cohort_run` and `/programme/{class_id}` | `devicestore.py`, `class_only.py`, `modules/api.py`, `modules/service.py`, `cohort_chat/api.py`, `cohorts/routes.py`, `programme.py`, `cohort_run/api.py`, `practice.py` | backfill owner columns (dry run) | cohort and track ownership change is the biggest design shift | large |
| **D. Shared papers (2)** | Keep every paper visible; hide the assignment interface and routes behind `ASSIGNMENT_ENABLED` (off); filters never hide another user's paper; drop the dead `_visible` scoping | `Papers.tsx`, `Home.tsx`, `PaperHubParts.tsx`, `papers_hub/api.py`, `services/api/papers.py`; strings | none | `PaperSelect` sorts assigned first today | small |
| **E. Sync (4)** | Versioned outbox (record id, payload, version, time, status, reason); server version column and compare; conflict table and "Changes that conflicted" list; reconnect popup (count, progress, result, Retry); queue cohort, chat, check-in and module writes; merge the two profile paths; stop dropping 4xx silently; stop hydrate deleting unsynced rows; reword the "on this phone" strings; pictures stay in memory only (replace the persisted outbox blobs) | `cloudStore.ts`, `sync.ts`, `sendnow.ts`, `devicestore.py` (+ conflicts table), `db.ts`, a new popup component | new columns and a conflicts table (migration, reversible) | race between hydrate and queued writes; the outbox blob rule needs a decision on the photo outbox | large |
| **F. One rule control (5)** | One shared control saved per user in the cloud (default two or more); every count view and endpoint takes `min_hits`; engine helper decides; a cohort stores its rule; each view says which rule it shows | `engine/diagnosis.py`, `devicestore.py`, `officer.py`, `class_only.py`, `Cards.tsx`, `MistakesTable.tsx`, `ClassCohortMaker.tsx`, `InterventionPack.tsx`, `PackSummary.tsx`, `RoleScreens.tsx`, `OfficerHome.tsx` | none (cohort `rule` field added) | the any-count currently stored on profiles must be recomputed per rule from the answers | medium |
| **G. Officer page (6)** | Recompute every number against the database by script and fix mismatches; demo mode turns every cap off (production values stay in config; "Demo: no minimum group sizes" label); Create a cohort: error plus rule control, class list (nickname, class code, children count), select all or some, name, create, audit entry; remove the old block panels from the coach page | `officer.py`, `class_only.py`, `OfficerHome.tsx`, `RoleScreens.tsx`, `lifecycle.py` and the cap files above; config | none | many cap files; keep production behaviour tested | large |
| **H. Listen in the browser (10)** | Player on each module (play and pause, seek, time and length, speeds 0.75, 1 and 1.25, Download, offline copy, no autoplay, labels, "played" event) | `AudioDownload.tsx`, `ModuleTrack.tsx`, `packAudio.ts`, `modules.ts` + server event; strings | none | needs a stored file or the Blob kept in memory | small |
| **Phase 3** | Unit tests (nickname rules, ownership, rule control, outbox); API tests with two teachers, a coach and an officer for every endpoint; Playwright for the six flows; counts before and after; `CLEANUP-REPORT.md`; update `CLAUDE.md`, `DECISIONS.md`, help docs, `INVENTORY.md`, README; rebuild the assistant index | `tests/`, `apps/pwa/e2e/`, docs | | the Playwright suite already has failures that predate this work | large |

## Stopping here

Per the instructions I stop. Nothing is committed on `cleanup/identity-sharing-sync` beyond this report (uncommitted). Say **go**, and answer the five decisions above (or say "use your recommendations"), and I will start with step A.
