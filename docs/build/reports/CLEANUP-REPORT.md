# Clean-up report: identity, sharing, privacy, sync, error rule, officer cohorts, terms, audio

Branch `cleanup/identity-sharing-sync`, 5 Nov 2026. Nothing is pushed, merged or deployed. **No hosted or cloud database was touched**; every migration ran on local dev databases, after a backup. Companion reports: `CLEANUP-AUDIT.md` (before), `IDENTITY-ACCESS.md` (identity and access), `OFFICER-NUMBERS.md` (officer recompute), decisions in `docs/build/DECISIONS.md` (2026-11-03 and both 2026-11-04 entries).

## 1. Matrix, before and after (corrections 1 to 10)

"Before" is the audit of 3 Nov (`CLEANUP-AUDIT.md`). "After" is what the code, the tests and the Phase 3 walk-through show now.

| # | Correction | Before | After | Honest caveat |
| --- | --- | --- | --- | --- |
| 1 | The nickname is the user id | N: three parallel identities (device id, store key, tester hash) | Met. One id, `X-User`; the others are removed from code, headers and columns. | Demo-grade: no password. A taken nickname is not protected against someone who types it. |
| 2 | Papers shared | P: visible to all, assignment live | Met. Papers are shared; assignment is off. | |
| 3 | Entered data private to its owner | N: same nickname read and overwrote; peers route open | Met. Store keyed by (owner, collection, doc); `/peers` removed; every route has an access rule and an unlisted route is closed. | In judge mode any signed-in user may send `X-Role` (the demo). |
| 4 | Cloud-first sync with outbox, versions, conflicts | P/N: partial, silent drops | Met for classes, checks, profiles, settings and (new) Practice Class transcripts. Failed and retry states show; the reconnect popup shows only for changes made offline. | Cohort chat and module writes still need a connection. |
| 5 | One error rule | N: three rules | Met. `min_hits` 2 or 1, saved per user, stored on the cohort; the 25% rule is gone. | |
| 6 | Officer: create cohorts, caps | P: bulk button only | Met after the walk-through found it missing (see section 6). Class picker, rule control, audit row. Caps live in `services/api/caps.py` and are off in judge mode. | The first code review said this was met when it was not; corrected in DECISIONS. |
| 7/8 | Scope: staff see only what is assigned | P | Met. A coach or mentor reaches only cohorts assigned to her; officer sees counts. | Not exercised against real staff accounts. |
| 9 | No terms | N | Met in data and on screen: a check is current by its date; no screen shows the word term (a spec visits 12 routes plus the paper entry). Old stored paper codes keep a hidden `· T1` suffix. | |
| 10 | Audio plays in the browser | N | Met: a player on the module page, not only a download. | Live voice still needs Sarvam. |

Three further decisions by Gopi on 4 Nov are in: Practice Class transcripts sync to her account and are readable only by her user id; the 60-day opt-in sheet keep stays; **one cohort per mistake**, with what each teacher gets next following her own feedback.

## 2. Migrations run (local dev only)

- Identity migration on `dev.sqlite` (dry run on a copy, then applied with identical counts) and on `apps/pwa/dev.sqlite`: teachers re-keyed 5 and 22, tester events 1,464 rows moved to user ids, consents 43, user docs 34. The second run is a no-op (idempotent).
- New tables `user_docs`, `doc_versions`, `doc_conflicts` come from `create_all` (no Alembic here).
- Backups before every change under `backups/` (**not committed**), with revert logs.
- Cloud: `scripts/migrate_identity.py` exists and refuses `--apply` without `--i-mean-the-hosted-database`. **Not run.**

## 3. Unclaimed rows

66 rows in `dev.sqlite` and 87 in `pwa-dev.sqlite` have no nickname on record (test and demo sessions). They are kept under `unclaimed:<old id>` owners and never deleted. `scripts/claim_unclaimed.py --list` shows them; `--from ... --to "<nickname>" --apply` hands a set to a user.

## 4. Tests

| Suite | Result | Notes |
| --- | --- | --- |
| Python, full | See table below | All failures are in test files that also fail on base commit ec700e9 |
| Vitest | all pass | was 513 passed and 3 failed in the earlier B/C run; the 3 were tests of the old reconnect popup and are changed (section 5) |
| Playwright, full | 208 passed, 67 failed, 7 skipped | 64 of the 67 also fail on ec700e9 (run in a worktree, compared by test name with `cmp_runs.py`); the other 3 were my changes' timing and ordering, fixed or shown flaky |
| Walk-through spec | passes | two teacher nicknames, a coach and an officer; the six flows; clean and dirty database |
| Assistant index | rebuilt, 1,833 chunks, `tests/assistant` 218 passed | `vectors.npz` not rebuilt |

Earlier B/C Python run for comparison: 2,741 passed, 40 pre-existing failures.

Python, per directory (final run): ai 162, api 133, channels 16, cohort_chat 28, cohorts 57, evals 30, media 10, modules 255, papers 107, engine 437, pilot_demo 38, practice 180, roles 12, sheets_keep 8, sprites 628, store 24 all passed. Failing (all pre-existing): assistant 1 (the stale index, now fixed: 218 passed), chat 2, cohort_run 1, content 1, demo 5, flows 2, papers_hub 3, spoken 1, usage 1, speech 2, top-level 4 (data_budget, design_tokens, health, results16 fixture), and `tests/data` (collection error).

**Pre-existing, not fixed here:** the failures above; 64 Playwright specs (checks, cohort-pack, cohort, officer, qa-screens, programme and others); 33 assistant question GAPs. One cohort_run test (call-5 wording) has no recorded fixture. None is hidden or skipped by me.

## 5. Tests and specs changed, with the reason

Each encodes a rule that was removed or corrected. No bar was lowered; where an assertion became weaker in one place it was made stronger in another.

- **25% share rule removed (2 Nov):** `tests/engine/test_diagnosis.py` (two tests: eligible with 1 child and 10 checked; NODEC joins the list), `tests/engine/test_export_keys.py` (`min_children_with_error`), `tests/engine/test_grouping.py`, `tests/cohort_run/test_rules.py` and `test_api.py` (one cohort per mistake), `flow.test.ts` and `e2e/results.spec.ts` (the demo class focuses on PV-HEARD).
- **Identity (no device id or hash):** `tests/speech/test_pack_audio.py`, `e2e/profile.spec.ts`, `e2e/tester.spec.ts` (counts on by default in the demo), `tests/store/test_devicestore.py` (an unknown collection stands in for the old "transcripts are refused", since transcripts are now synced).
- **Cloud-first:** `e2e/app.spec.ts` (answers may go to her own account store and nowhere else).
- **Demo caps:** `tests/api/test_officer.py` (production caps restored in the fixture, so "hidden under 5 classes" is unchanged).
- **Terms:** `tests/papers/*`, `tests/demo/test_sheets.py`, e2e paper-code assertions; `checks.test.ts` (ids, `nextRound` removed), `history.test.ts` (order by date).
- **Offline-only reconnect popup:** three unit tests in `cloudOutbox.test.ts` now make their change offline.
- **Term-advance spec replaced:** the old spec drove "Advance to Term 2". It is replaced by the no-term spec in `e2e/app.spec.ts`, tightened on 4 Nov to visit the tour, the demo studio and the two-class run and to reject a paper code ending in ` · T1`. The first version passed while those screens still said "Advance to Term 2".
- **One timing allowance:** the keep-ask spec waits up to 20 s (cold first API call); its assertion text is unchanged.
- **New specs and tests:** `walkthrough.spec.ts`, `paperKeysSecondDevice.test.ts`, transcript sync tests, the no-term loop.

## 6. What the walk-through found (and one earlier wrong claim)

1. The officer page had no Create a cohort picker; an earlier commit replaced it with one button. The first code review and step G's summary called this met. **That was wrong.** Fixed (`CohortMaker who="officer"`).
2. A second device got a teacher's checks but not the answer keys of the papers they used, so My class had no answer map. Fixed (`fetchMissingPaperKeys`).
3. A reload after every save broke folder-cancel and sync specs; the reload now happens only after the save that creates the class.

## 7. Deck sentences that are now untrue (no deck was edited)

The real `.pptx` is not in the repo; these come from `docs/submission/deck.md` and `slides.md` and the audit.

- Slide 3: "termly 10-item check" (there are no terms).
- Slide 10: "groups under 5 hidden" is true in production only; off in the demo.
- Slide 9: the pilot-mode text (pilot mode was removed on 31 Oct).
- "Answers never leave the phone" and any "stay on the device" line: answers and Practice Class transcripts now sync to her account.
- "No accounts or logins" and "pseudonymous random id": the nickname is now the user id.
- "Term-based check" and any term 1 to term 2 line.
- Any line on assignments (off) and on 25% eligibility (removed).

## 8. Not done, on purpose

- `vectors.npz` is not rebuilt.
- `docs/design/*` historical documents are not updated; DECISIONS wins.
- The demo's two-class scenario (Seema's) now forms a cohort per mistake.
- Hosted database migration and any deploy: waiting for a human.
- `docs/build/qa/screens/*.jpg` regenerated by the QA spec are not committed.
