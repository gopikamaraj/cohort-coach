# Report: labelled checks, pre-test and post-test pairing

Date: 2026-10-30. Source prompt: `docs/build/Claude Code prompt identify every check (pre-test, post-test, termly) and pair t.md`. Scope chosen by Gopi: the phone-side slice.

## What was built

| Step | What | Where | Tests |
| --- | --- | --- | --- |
| 1 Data model | Check fields: kind, round, date, paper version, track, papers expected, status, notes, confirm. Dexie version 2 with a `checkDate` index; the upgrade labels old checks and marks them to confirm | `apps/pwa/src/lib/db.ts`, `apps/pwa/src/lib/checkMigrate.ts` | `apps/pwa/src/lib/dbUpgrade.test.ts`, `apps/pwa/src/lib/checks.test.ts` |
| 2 Start a check | Kind chips with the suggested one marked, paper buttons with the suggested one marked, date, papers expected, what is saved for the class, a plain note when a post-test has no pre-test | `apps/pwa/src/components/StartCheck.tsx` | `apps/pwa/e2e/checks.spec.ts` |
| 3 Visible everywhere | Header on every entry screen with label, progress and Change; label on My class and in History; a check switcher in Before and after | `apps/pwa/src/screens/Check.tsx`, `Cards.tsx`, `History.tsx` | `apps/pwa/e2e/checks.spec.ts` |
| 5 Twins | `twin_of` and a test that every Form B item is the twin of the Form A item with the same number | `engine/forms.py` | `tests/engine/test_checkpair.py` |
| 6 Pairing | Pairing by roll order, absent and unentered children left out and counted, counts per competency, small-sample flag; Python and TypeScript tested on one case file | `engine/checkpair.py`, `apps/pwa/src/lib/checks.ts`, `apps/pwa/src/components/BeforeAfter.tsx` | `tests/engine/test_checkpair.py`, `tests/fixtures/check_pairing_cases.json`, `apps/pwa/src/lib/checks.test.ts` |
| 7 Demo | The judge demo class has a pre-test (Form A) and a post-test (Form B) with the same children in the same order, labelled Demo data; the tour's first step names Start a check | `apps/pwa/src/lib/demo.ts`, `apps/pwa/src/state.tsx`, `strings/*.json` | `apps/pwa/src/lib/demoPair.test.ts`, `apps/pwa/e2e/checks.spec.ts` |
| 8 Evidence | `docs/evidence/pilot_results.md` from an unsealed backup, counts only, small pilot label | `scripts/pilot_results.py` | `tests/test_pilot_results.py` |
| 8 Accessibility | axe (WCAG 2 A and AA) on Start a check, the header and Before and after; one finding fixed (the scrolling table could not be reached by keyboard) | `apps/pwa/e2e/checks.spec.ts` | same |

## Differences from the prompt

- The check record is on the phone, not a server table: per-child answers never leave the phone (CLAUDE.md rule 2), and the repo has no Alembic migrations.
- Old checks keep their real paper (A or B), not "Form A".
- One check per class per term; the term is the app's current term. A second round in a term needs the server's class counts keyed by round first.
- "Unique per class, kind, form and date" and "only one open check per class" are rules in `apps/pwa/src/lib/checks.ts` with tests; with one check per class per term the screen cannot create a duplicate.

## Not built

Step 4 (printed check code read back by call 8), the server-side check table and upload of the comparison counts, verdicts carrying the two check ids, and the label on the cohort and track pages. Logged in `docs/build/PARKING.md`.

## Evidence

No real pre-test and post-test pair exists yet, so `docs/evidence/pilot_results.md` says so and shows no number. The demo numbers on My class come from `DEMO_COUNTS` in `apps/pwa/src/lib/demo.ts` and are labelled Demo data.
